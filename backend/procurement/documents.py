"""Shared policy corpus. Human authorization precedes every external operation."""

import hashlib
import json
from pathlib import PurePath
from uuid import uuid4

from fastapi import HTTPException

from .document_adapters import MAX_BYTES, PIPELINE, validate_vectors


def buyer(user):
    if user["role"] != "buyer":
        raise HTTPException(403, "Only the procurement buyer manages team policies")


def source_text(filename, content):
    if (
        not filename
        or len(filename) > 160
        or "/" in filename
        or "\\" in filename
        or any(ord(c) < 32 for c in filename)
    ):
        raise HTTPException(422, "Use a plain .md or .txt filename")
    if PurePath(filename).suffix.lower() not in (".md", ".txt"):
        raise HTTPException(415, "Only Markdown and plain text are supported")
    if not content or len(content) > MAX_BYTES:
        raise HTTPException(413, "Document must contain 1–65536 bytes")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(422, "Document must use UTF-8") from None
    if not text.strip() or any(ord(c) < 32 and c not in "\r\n\t" for c in text):
        raise HTTPException(422, "Document must contain readable text")
    return text


def event(c, document, version, user, action):
    c.execute(
        "INSERT INTO document_events(document_id,version_id,actor_id,action) VALUES (%s,%s,%s,%s)",
        (document, version, user["id"] if user else None, action),
    )


def detail(c, document_id):
    d = c.execute(
        "SELECT * FROM documents WHERE id=%s AND deleted_at IS NULL", (document_id,)
    ).fetchone()
    if not d:
        raise HTTPException(404, "Document not found")
    d["versions"] = c.execute(
        """SELECT v.id,v.generation,v.filename,v.content_hash,v.pipeline,v.state,v.error_code,
        v.created_at,j.attempts,j.state AS job_state FROM document_versions v LEFT JOIN ingestion_jobs j ON j.version_id=v.id
        WHERE v.document_id=%s ORDER BY v.generation DESC""",
        (document_id,),
    ).fetchall()
    return d


def upload(
    db,
    blobs,
    user,
    key,
    filename,
    title,
    content,
    document_id=None,
    expected_generation=None,
):
    buyer(user)
    source_text(filename, content)
    if not 3 <= len(title.strip()) <= 150:
        raise HTTPException(422, "Title must contain 3–150 characters")
    digest = hashlib.sha256(content).hexdigest()
    fingerprint = hashlib.sha256(
        json.dumps(
            [str(document_id), expected_generation, filename, title.strip(), digest]
        ).encode()
    ).hexdigest()
    with db.connect() as c:
        c.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s,12))",
            (user["id"] + ":" + key,),
        )
        replay = c.execute(
            "SELECT * FROM document_uploads WHERE actor_id=%s AND command_key=%s",
            (user["id"], key),
        ).fetchone()
        if replay:
            if replay["fingerprint"] != fingerprint:
                raise HTTPException(
                    409, "Idempotency key was used for different content"
                )
            v = c.execute(
                "SELECT * FROM document_versions WHERE id=%s", (replay["version_id"],)
            ).fetchone()
            document_id = v["document_id"]
            d = c.execute(
                "SELECT * FROM documents WHERE id=%s FOR UPDATE", (document_id,)
            ).fetchone()
            if (
                d["deleted_at"]
                or d["generation"] != v["generation"]
                or v["state"] in ("superseded", "deleted")
            ):
                raise HTTPException(409, "Upload has been deleted or superseded")
            if v["state"] != "uploading":
                return detail(c, document_id)
        else:
            if document_id:
                d = c.execute(
                    "SELECT * FROM documents WHERE id=%s AND deleted_at IS NULL FOR UPDATE",
                    (document_id,),
                ).fetchone()
                if not d:
                    raise HTTPException(404, "Document not found")
                if d["generation"] != expected_generation:
                    raise HTTPException(
                        409, "Document changed; refresh before replacing"
                    )
                generation = d["generation"] + 1
                c.execute(
                    "UPDATE documents SET generation=%s,title=%s WHERE id=%s",
                    (generation, title.strip(), document_id),
                )
            else:
                document_id, generation = uuid4(), 1
                c.execute(
                    "INSERT INTO documents(id,title,owner_id) VALUES (%s,%s,%s)",
                    (document_id, title.strip(), user["id"]),
                )
            version_id = uuid4()
            blob_key = (
                db.settings.schema + "/" + str(document_id) + "/" + str(version_id)
            )
            v = c.execute(
                """INSERT INTO document_versions(id,document_id,generation,filename,content_hash,blob_key,pipeline,state)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'uploading') RETURNING *""",
                (
                    version_id,
                    document_id,
                    generation,
                    filename,
                    digest,
                    blob_key,
                    PIPELINE,
                ),
            ).fetchone()
            c.execute(
                "INSERT INTO document_uploads VALUES (%s,%s,%s,%s)",
                (user["id"], key, fingerprint, version_id),
            )
            event(c, document_id, version_id, user, "source_reserved")
    try:
        blobs.put(v["blob_key"], content)
    except Exception:
        # Retain a tracked pending upload; a same-key retry can recover it.
        raise HTTPException(
            503, "Source storage unavailable; retry with the same upload key"
        ) from None
    with db.connect() as c:
        d = c.execute(
            "SELECT * FROM documents WHERE id=%s FOR UPDATE", (document_id,)
        ).fetchone()
        current = c.execute(
            "SELECT * FROM document_versions WHERE id=%s FOR UPDATE", (v["id"],)
        ).fetchone()
        if (
            d["deleted_at"]
            or d["generation"] != v["generation"]
            or current["state"] in ("superseded", "deleted")
        ):
            # A tracked orphan is cleaned by the worker; never enqueue stale content.
            c.execute(
                "UPDATE document_versions SET cleaned_at=NULL WHERE id=%s", (v["id"],)
            )
            c.commit()
            raise HTTPException(409, "Document changed during upload")
        if current["state"] == "uploading":
            c.execute(
                "UPDATE document_versions SET state='queued',error_code=NULL WHERE id=%s",
                (v["id"],),
            )
            c.execute(
                "INSERT INTO ingestion_jobs(id,version_id,state) VALUES (%s,%s,'queued') ON CONFLICT(version_id) DO NOTHING",
                (uuid4(), v["id"]),
            )
            event(c, document_id, v["id"], user, "source_uploaded")
        return detail(c, document_id)


def remove(db, user, document_id, expected_generation):
    buyer(user)
    with db.connect() as c:
        d = c.execute(
            "SELECT * FROM documents WHERE id=%s FOR UPDATE", (document_id,)
        ).fetchone()
        if not d:
            raise HTTPException(404, "Document not found")
        if d["deleted_at"]:
            return
        if d["generation"] != expected_generation:
            raise HTTPException(409, "Document changed; refresh before deletion")
        c.execute(
            "UPDATE documents SET deleted_at=now(),active_version=NULL WHERE id=%s",
            (document_id,),
        )
        c.execute(
            "UPDATE document_versions SET state='deleted' WHERE document_id=%s",
            (document_id,),
        )
        c.execute(
            "UPDATE ingestion_jobs SET state='cancelled',lease_token=NULL,lease_until=NULL WHERE state IN ('queued','running') AND version_id IN (SELECT id FROM document_versions WHERE document_id=%s)",
            (document_id,),
        )
        c.execute(
            "DELETE FROM document_passages WHERE version_id IN (SELECT id FROM document_versions WHERE document_id=%s)",
            (document_id,),
        )
        event(c, document_id, None, user, "document_deleted")


def retry(db, user, document_id):
    buyer(user)
    with db.connect() as c:
        d = c.execute(
            "SELECT * FROM documents WHERE id=%s AND deleted_at IS NULL FOR UPDATE",
            (document_id,),
        ).fetchone()
        if not d:
            raise HTTPException(404, "Document not found")
        v = c.execute(
            "SELECT * FROM document_versions WHERE document_id=%s AND generation=%s FOR UPDATE",
            (document_id, d["generation"]),
        ).fetchone()
        if v["state"] != "failed":
            raise HTTPException(409, "Only the latest failed version can be retried")
        c.execute(
            "UPDATE ingestion_jobs SET state='queued',attempts=0,available_at=now(),error_code=NULL WHERE version_id=%s",
            (v["id"],),
        )
        c.execute(
            "UPDATE document_versions SET state='queued',error_code=NULL WHERE id=%s",
            (v["id"],),
        )
        event(c, document_id, v["id"], user, "ingestion_retried")
        return detail(c, document_id)


def search(db, embeddings, query, limit=5):
    if not 2 <= len(query.strip()) <= 500:
        raise HTTPException(422, "Search must contain 2–500 characters")
    # No model call if there is no published corpus.
    with db.connect() as c:
        if not c.execute(
            "SELECT 1 FROM documents WHERE deleted_at IS NULL AND active_version IS NOT NULL LIMIT 1"
        ).fetchone():
            return {"items": [], "pipeline": PIPELINE}
    try:
        vector = validate_vectors(embeddings.embed([query]), 1)[0]
    except Exception:
        raise HTTPException(
            503, "Embedding service unavailable; no search result was generated"
        ) from None
    with db.connect() as c:
        rows = c.execute(
            """WITH allowed AS (
          SELECT p.*,d.id AS document_id,d.title,v.generation,v.filename FROM document_passages p
          JOIN document_versions v ON v.id=p.version_id JOIN documents d ON d.active_version=v.id
          WHERE d.deleted_at IS NULL AND v.pipeline=%s AND v.state='ready'
        ), semantic AS (
          SELECT id,row_number() OVER(ORDER BY embedding OPERATOR(public.<=>) %s::public.vector,id) AS rank FROM allowed
          ORDER BY embedding OPERATOR(public.<=>) %s::public.vector,id LIMIT 20
        ), lexical AS (
          SELECT id,row_number() OVER(ORDER BY ts_rank(search,websearch_to_tsquery('english',%s)) DESC,id) AS rank
          FROM allowed WHERE search @@ websearch_to_tsquery('english',%s)
          ORDER BY ts_rank(search,websearch_to_tsquery('english',%s)) DESC,id LIMIT 20
        ) SELECT a.id,a.version_id,a.document_id,a.title,a.generation,a.filename,a.line_start,a.line_end,a.body,
          COALESCE(1.0/(60+s.rank),0)+COALESCE(1.0/(60+l.rank),0) AS score
          FROM allowed a LEFT JOIN semantic s ON s.id=a.id LEFT JOIN lexical l ON l.id=a.id
          WHERE s.id IS NOT NULL OR l.id IS NOT NULL ORDER BY score DESC,a.id LIMIT %s""",
            (PIPELINE, str(vector), str(vector), query, query, query, limit),
        ).fetchall()
        for row in rows:
            row["source_url"] = (
                f"/api/v1/documents/{row['document_id']}/versions/{row['version_id']}/source"
            )
        return {"items": rows, "pipeline": PIPELINE}
