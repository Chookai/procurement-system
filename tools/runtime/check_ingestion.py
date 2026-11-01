"""Small paid synthetic ingestion/retrieval development probe. Never a holdout eval."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from fastapi.testclient import TestClient
from procurement.app import create_app
from procurement.config import Settings
from procurement.document_adapters import BlobStore, Embeddings
from procurement.ingestion import Worker
from psycopg import sql


def main():
    settings = Settings(
        schema="probe_ingestion_" + uuid4().hex, secret="synthetic-probe-" + "x" * 40
    )
    blobs, embeddings = BlobStore(), Embeddings()
    app = create_app(settings, document_blobs=blobs, document_embeddings=embeddings)
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scope": "Synthetic development checks; not a frozen holdout or RAG answer evaluation",
        "checks": [],
    }
    sources = []
    try:
        with TestClient(app) as client:
            session = client.post(
                "/api/v1/auth/login",
                json={"username": "chloe", "password": "harbor-demo"},
            ).json()
            headers = {"X-CSRF-Token": session["csrf_token"]}
            for path in sorted((ROOT / "fixtures/policies").iterdir()):
                response = client.post(
                    "/api/v1/documents",
                    params={"filename": path.name, "title": path.stem},
                    content=path.read_bytes(),
                    headers={**headers, "Idempotency-Key": str(uuid4())},
                )
                assert response.status_code == 202, "Source upload failed"
                sources.append(response.json()["id"])
            worker = Worker(app.state.db, blobs, embeddings)
            for _ in sources:
                assert worker.run_once()
            docs = client.get("/api/v1/documents").json()["items"]
            assert all(d["active_version"] for d in docs), "Some jobs did not publish"
            report["checks"].append(
                {
                    "check": "real Blob upload and complete index publication",
                    "status": "passed",
                    "documents": len(docs),
                }
            )
            cases = [
                ("Does invoice review authorize payment?", "invoice-review.md"),
                ("Who issues an approved PO revision?", "po-revisions.md"),
                ("What happens when a policy is deleted?", "source-handling.txt"),
            ]
            for query, expected in cases:
                response = client.get("/api/v1/documents/search", params={"q": query})
                assert response.status_code == 200, "Retrieval failed"
                items = response.json()["items"]
                assert items and items[0]["filename"] == expected, (
                    "Expected fixture was not top ranked"
                )
                source = client.get(items[0]["source_url"])
                assert (
                    source.status_code == 200
                    and source.content
                    == (ROOT / "fixtures/policies" / expected).read_bytes()
                )
                report["checks"].append(
                    {
                        "check": "labelled retrieval and original source",
                        "query": query,
                        "expected": expected,
                        "top1": items[0]["filename"],
                        "status": "passed",
                        "line_start": items[0]["line_start"],
                        "line_end": items[0]["line_end"],
                    }
                )
            report["embedding_manifest"] = {
                "pipeline": response.json()["pipeline"],
                **getattr(embeddings, "last_result", {}),
            }
            for d in docs:
                assert (
                    client.delete(
                        "/api/v1/documents/" + d["id"],
                        params={"expected_generation": d["generation"]},
                        headers=headers,
                    ).status_code
                    == 204
                )
            worker.cleanup()
            assert not client.get(
                "/api/v1/documents/search", params={"q": "invoice"}
            ).json()["items"]
            report["checks"].append(
                {
                    "check": "delete excludes evidence and cleans sources",
                    "status": "passed",
                }
            )
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["error_type"] = type(error).__name__
        raise
    finally:
        # Cleanup only this probe's schema and generated Blob prefix.
        with app.state.db.connect() as c:
            for row in c.execute("SELECT blob_key FROM document_versions").fetchall():
                blobs.delete(row["blob_key"])
            c.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(
                    sql.Identifier(settings.schema)
                )
            )
        (ROOT / "runtime-results/document-ingestion-live.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
