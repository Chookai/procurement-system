"""HTTP and durable-job contracts against isolated real PostgreSQL schemas.
External adapters are deterministic fakes; separate live probe exercises real I/O.
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from procurement.app import create_app
from procurement.config import Settings
from procurement.document_adapters import DIMENSIONS, validate_vectors
from procurement.ingestion import LeaseLost, Worker, chunks


class MemoryBlobs:
    def __init__(self):
        self.data = {}
        self.fail = False

    def put(self, key, body):
        if self.fail:
            raise RuntimeError("synthetic private failure")
        if key in self.data:
            assert self.data[key] == body
        self.data[key] = body

    def get(self, key):
        return self.data[key]

    def delete(self, key):
        if self.fail:
            raise RuntimeError("storage unavailable")
        self.data.pop(key, None)


class TestEmbeddings:
    __test__ = False

    def __init__(self):
        self.fail = False

    def embed(self, texts):
        if self.fail:
            raise RuntimeError("secret provider response must never be persisted")
        result = []
        for text in texts:
            v = [0.0] * DIMENSIONS
            # Deterministic synthetic vectors, explicitly not a real quality eval.
            v[0] = 1.0
            v[1] = float("invoice" in text.lower())
            v[2] = float("receipt" in text.lower())
            result.append(v)
        return result


@pytest.fixture(scope="module")
def setup():
    settings = Settings(
        schema="test_documents_" + uuid4().hex, secret="documents-test-" + "x" * 40
    )
    blobs, embeddings = MemoryBlobs(), TestEmbeddings()
    app = create_app(settings, document_blobs=blobs, document_embeddings=embeddings)
    with TestClient(app):
        yield app, blobs, embeddings
    with app.state.db.connect() as c:
        c.execute(
            sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(settings.schema))
        )


@pytest.fixture
def env(setup):
    app, blobs, embeddings = setup
    with app.state.db.connect() as c:
        c.execute("TRUNCATE documents,sessions CASCADE")
    blobs.data.clear()
    blobs.fail = False
    embeddings.fail = False
    with TestClient(app) as client:
        yield app, blobs, embeddings, client, Worker(app.state.db, blobs, embeddings)


def login(client, user="chloe"):
    client.cookies.clear()
    r = client.post(
        "/api/v1/auth/login", json={"username": user, "password": "harbor-demo"}
    )
    assert r.status_code == 200
    return {"X-CSRF-Token": r.json()["csrf_token"], "Idempotency-Key": str(uuid4())}


def upload(
    client,
    headers,
    text=b"# Policy\nReceipt evidence is required for invoice review.",
    filename="policy.md",
    doc=None,
    generation=1,
):
    path = "/api/v1/documents" + (f"/{doc}/versions" if doc else "")
    return client.post(
        path,
        params={
            "title": "Team policy",
            "filename": filename,
            "expected_generation": generation,
        },
        content=text,
        headers=headers,
    )


def details(client, doc):
    return client.get("/api/v1/documents/" + doc).json()


def test_upload_publish_search_replace_and_delete(env):
    app, blobs, embeddings, client, worker = env
    h = login(client)
    r = upload(client, h)
    assert r.status_code == 202, r.text
    d = r.json()
    doc = d["id"]
    v1 = d["versions"][0]["id"]
    assert d["active_version"] is None and len(blobs.data) == 1
    assert client.get("/api/v1/documents/search?q=invoice").json()["items"] == []
    assert worker.run_once()
    result = client.get("/api/v1/documents/search?q=invoice").json()["items"]
    assert result[0]["version_id"] == v1 and result[0]["line_start"] == 1
    source = client.get(result[0]["source_url"])
    assert (
        source.content == b"# Policy\nReceipt evidence is required for invoice review."
    )
    newer = upload(
        client,
        {**h, "Idempotency-Key": str(uuid4())},
        b"Invoice review does not authorize payment.",
        doc=doc,
    )
    assert newer.status_code == 202
    assert details(client, doc)["active_version"] == v1
    assert worker.run_once()
    d = details(client, doc)
    assert d["active_version"] != v1
    with app.state.db.connect() as c:
        assert (
            c.execute(
                "SELECT count(*) AS n FROM document_passages WHERE version_id=%s", (v1,)
            ).fetchone()["n"]
            == 0
        )
    assert (
        client.get(f"/api/v1/documents/{doc}/versions/{v1}/source").status_code == 200
    )
    assert (
        client.delete(
            "/api/v1/documents/" + doc + "?expected_generation=2", headers=h
        ).status_code
        == 204
    )
    assert client.get("/api/v1/documents/search?q=invoice").json()["items"] == []
    assert client.get(source.request.url).status_code == 404
    worker.cleanup()
    assert not blobs.data


def test_authenticated_reads_buyer_only_writes_and_csrf(env):
    _, _, _, client, _ = env
    assert client.get("/api/v1/documents").status_code == 401
    assert client.get("/api/v1/documents/search?q=invoice").status_code == 401
    for user in ["aina", "ben", "dinesh", "eva"]:
        h = login(client, user)
        assert client.get("/api/v1/documents").status_code == 200
        assert upload(client, h).status_code == 403
    h = login(client)
    assert upload(client, {"Idempotency-Key": str(uuid4())}).status_code == 403
    assert upload(client, {**h, "Origin": "https://foreign.invalid"}).status_code == 403


@pytest.mark.parametrize(
    "filename,body,status",
    [
        ("file.pdf", b"hello", 415),
        ("../policy.md", b"hello", 422),
        ("policy.txt", b"\xff", 422),
        ("policy.txt", b"\x00abc", 422),
        ("policy.txt", b"   ", 422),
        ("policy.txt", b"x" * 65537, 413),
    ],
)
def test_validation(env, filename, body, status):
    _, _, _, client, _ = env
    assert upload(client, login(client), body, filename).status_code == status


def test_upload_retries_conflicts_and_storage_failure(env):
    app, blobs, _, client, worker = env
    h = login(client)
    blobs.fail = True
    assert upload(client, h).status_code == 503
    blobs.fail = False
    first = upload(client, h)
    assert first.status_code == 202
    assert upload(client, h).json()["id"] == first.json()["id"]
    assert upload(client, h, b"different content").status_code == 409
    with app.state.db.connect() as c:
        assert (
            c.execute("SELECT count(*) AS n FROM ingestion_jobs").fetchone()["n"] == 1
        )
    assert worker.run_once()
    assert not worker.run_once()


def test_failure_bounded_retry_keeps_old_index_and_manual_retry(env):
    app, _, embed, client, worker = env
    h = login(client)
    doc = upload(client, h).json()["id"]
    worker.run_once()
    previous = details(client, doc)["active_version"]
    upload(
        client,
        {**h, "Idempotency-Key": str(uuid4())},
        b"Updated invoice policy",
        doc=doc,
    )
    embed.fail = True
    for _ in range(3):
        assert worker.run_once()
        with app.state.db.connect() as c:
            c.execute(
                "UPDATE ingestion_jobs SET available_at=now()-interval '1 second' WHERE state='queued'"
            )
    assert not worker.run_once()
    d = details(client, doc)
    assert d["active_version"] == previous
    assert d["versions"][0]["state"] == "failed"
    assert d["versions"][0]["error_code"] == "ingestion_failed"
    assert "secret provider" not in str(d)
    assert (
        client.post("/api/v1/documents/" + doc + "/retry", headers=h).status_code == 200
    )
    embed.fail = False
    worker.run_once()
    assert details(client, doc)["active_version"] != previous


def test_lease_reclaim_and_stale_worker_cannot_publish(env):
    app, blobs, embed, client, worker = env
    doc = upload(client, login(client)).json()["id"]
    first = worker.claim()
    assert first and worker.claim() is None
    with app.state.db.connect() as c:
        v = c.execute(
            "SELECT * FROM document_versions WHERE id=%s", (first["version_id"],)
        ).fetchone()
        c.execute(
            "UPDATE ingestion_jobs SET lease_until=now()-interval '1 second' WHERE id=%s",
            (first["id"],),
        )
    with pytest.raises(LeaseLost):
        worker.renew(first)
    assert worker.run_once()
    with pytest.raises(LeaseLost):
        worker.publish(first, v, chunks("stale source"), embed.embed(["stale source"]))
    assert details(client, doc)["active_version"] == str(v["id"])
    with app.state.db.connect() as c:
        assert (
            c.execute("SELECT count(*) AS n FROM document_passages").fetchone()["n"]
            == 1
        )


def test_newest_generation_and_delete_fence_publication(env):
    app, _, embed, client, worker = env
    h = login(client)
    doc = upload(client, h).json()["id"]
    old = worker.claim()
    with app.state.db.connect() as c:
        v = c.execute(
            "SELECT * FROM document_versions WHERE id=%s", (old["version_id"],)
        ).fetchone()
    assert (
        upload(
            client,
            {**h, "Idempotency-Key": str(uuid4())},
            b"New version policy",
            doc=doc,
        ).status_code
        == 202
    )
    worker.publish(old, v, chunks("old"), embed.embed(["old"]))
    assert details(client, doc)["active_version"] is None
    newest = worker.claim()
    with app.state.db.connect() as c:
        v = c.execute(
            "SELECT * FROM document_versions WHERE id=%s", (newest["version_id"],)
        ).fetchone()
    assert (
        client.delete(
            "/api/v1/documents/" + doc + "?expected_generation=1", headers=h
        ).status_code
        == 409
    )
    assert (
        client.delete(
            "/api/v1/documents/" + doc + "?expected_generation=2", headers=h
        ).status_code
        == 204
    )
    with pytest.raises(LeaseLost):
        worker.publish(newest, v, chunks("new"), embed.embed(["new"]))
    with app.state.db.connect() as c:
        assert (
            c.execute("SELECT count(*) AS n FROM document_passages").fetchone()["n"]
            == 0
        )


def test_atomic_publication_rolls_back_partial_insert(env):
    app, _, embed, client, worker = env
    doc = upload(client, login(client)).json()["id"]
    job = worker.claim()
    with app.state.db.connect() as c:
        v = c.execute(
            "SELECT * FROM document_versions WHERE id=%s", (job["version_id"],)
        ).fetchone()
    # Force a duplicate passage ordinal midway through an invalid direct publication.
    passages = chunks("x" * 2500)
    with pytest.raises(ValueError):
        worker.publish(job, v, passages, embed.embed(["only one"]))
    with app.state.db.connect() as c:
        assert (
            c.execute("SELECT count(*) AS n FROM document_passages").fetchone()["n"]
            == 0
        )
    assert details(client, doc)["active_version"] is None


def test_abandoned_upload_and_deleted_blob_cleanup_retry(env):
    app, blobs, _, client, worker = env
    h = login(client)
    blobs.fail = True
    assert upload(client, h).status_code == 503
    blobs.fail = False
    with app.state.db.connect() as c:
        v = c.execute(
            "UPDATE document_versions SET created_at=now()-interval '2 hours' RETURNING *"
        ).fetchone()
    blobs.data[v["blob_key"]] = b"orphan"
    worker.cleanup()
    assert not blobs.data
    assert upload(client, h).status_code == 409


def test_expired_last_attempt_is_terminal_and_concurrent_claims_are_unique(env):
    app, _, _, client, worker = env
    doc = upload(client, login(client)).json()["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: worker.claim(), range(2)))
    assert sum(x is not None for x in results) == 1
    with app.state.db.connect() as c:
        c.execute(
            "UPDATE ingestion_jobs SET attempts=3,lease_until=now()-interval '1 second'"
        )
        c.execute("UPDATE document_versions SET state='processing'")
    assert worker.claim() is None
    worker.cleanup()
    assert details(client, doc)["versions"][0]["state"] == "failed"


def test_vectors_and_chunking_bounds():
    with pytest.raises(ValueError):
        validate_vectors([[float("nan")] * DIMENSIONS], 1)
    with pytest.raises(ValueError):
        validate_vectors([[0.0] * DIMENSIONS], 1)
    with pytest.raises(ValueError):
        validate_vectors([[1.0]], 1)
    text = "line\n" * 12000
    parts = chunks(text)
    assert all(
        len(p["body"]) <= 1200 and p["line_end"] >= p["line_start"] for p in parts
    )
    assert len(parts) <= 80
