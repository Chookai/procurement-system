"""One durable worker. Publication uses a lease token as a fencing boundary."""

import argparse
import hashlib
import time
from uuid import NAMESPACE_URL, uuid4, uuid5

from .config import Settings
from .database import Database
from .document_adapters import MAX_BYTES, PIPELINE, BlobStore, Embeddings, validate_vectors
from .documents import event, source_text

LEASE_SECONDS = 120
MAX_ATTEMPTS = 3
CHUNK_CHARS = 1200
OVERLAP_CHARS = 150
SNAP_CHARS = 600
# A snapped chunk ends at least SNAP_CHARS + 1 characters after its start.
MIN_ADVANCE_CHARS = SNAP_CHARS + 1 - OVERLAP_CHARS
MAX_PASSAGES = (MAX_BYTES + MIN_ADVANCE_CHARS - 1) // MIN_ADVANCE_CHARS


def chunks(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    result, start = [], 0
    while start < len(text):
        end = min(start + CHUNK_CHARS, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start + SNAP_CHARS, end)
            if boundary > start:
                end = boundary + 1
        body = text[start:end]
        if body.strip():
            result.append(
                {
                    "body": body,
                    "line_start": text.count("\n", 0, start) + 1,
                    "line_end": text.count("\n", 0, max(start, end - 1)) + 1,
                }
            )
        if end == len(text):
            break
        start = end - OVERLAP_CHARS
    if not result or len(result) > MAX_PASSAGES:
        raise ValueError("Invalid passage count")
    return result


class LeaseLost(Exception):
    pass


class Worker:
    def __init__(self, db, blobs=None, embeddings=None):
        self.db, self.blobs, self.embeddings = (
            db,
            blobs or BlobStore(),
            embeddings or Embeddings(),
        )

    def claim(self):
        with self.db.connect() as c:
            # Expired final attempts cannot remain running forever.
            c.execute(
                """UPDATE ingestion_jobs SET state='failed',error_code='attempts_exhausted',lease_token=NULL,lease_until=NULL
                WHERE state='running' AND lease_until<clock_timestamp() AND attempts >= %s""",
                (MAX_ATTEMPTS,),
            )
            job = c.execute(
                """SELECT * FROM ingestion_jobs WHERE attempts<%s AND
                ((state='queued' AND available_at<=now()) OR (state='running' AND lease_until<clock_timestamp()))
                ORDER BY available_at,id FOR UPDATE SKIP LOCKED LIMIT 1""",
                (MAX_ATTEMPTS,),
            ).fetchone()
            if not job:
                return None
            return c.execute(
                """UPDATE ingestion_jobs SET state='running',attempts=attempts+1,
                lease_token=%s,lease_until=clock_timestamp()+(%s * interval '1 second') WHERE id=%s RETURNING *""",
                (uuid4(), LEASE_SECONDS, job["id"]),
            ).fetchone()

    def renew(self, job):
        with self.db.connect() as c:
            c.execute("SELECT id FROM ingestion_jobs WHERE id=%s FOR UPDATE", (job["id"],))
            row = c.execute(
                """UPDATE ingestion_jobs SET lease_until=clock_timestamp()+(%s * interval '1 second')
                WHERE id=%s AND lease_token=%s AND state='running' AND lease_until>clock_timestamp() RETURNING id""",
                (LEASE_SECONDS, job["id"], job["lease_token"]),
            ).fetchone()
            if not row:
                raise LeaseLost()

    def run_once(self):
        job = self.claim()
        if not job:
            return False
        try:
            with self.db.connect() as c:
                v = c.execute(
                    "SELECT * FROM document_versions WHERE id=%s", (job["version_id"],)
                ).fetchone()
                d = c.execute(
                    "SELECT * FROM documents WHERE id=%s FOR UPDATE",
                    (v["document_id"],),
                ).fetchone()
                if d["deleted_at"] or d["generation"] != v["generation"]:
                    c.execute(
                        "UPDATE ingestion_jobs SET state='cancelled',lease_token=NULL,lease_until=NULL WHERE id=%s AND lease_token=%s",
                        (job["id"], job["lease_token"]),
                    )
                    c.execute(
                        "UPDATE document_versions SET state=%s WHERE id=%s",
                        ("deleted" if d["deleted_at"] else "superseded", v["id"]),
                    )
                    return True
                if v["pipeline"] != PIPELINE:
                    raise ValueError("Pipeline mismatch")
                c.execute(
                    "UPDATE document_versions SET state='processing' WHERE id=%s AND state IN ('queued','processing')",
                    (v["id"],),
                )
            content = self.blobs.get(v["blob_key"])
            if hashlib.sha256(content).hexdigest() != v["content_hash"]:
                raise ValueError("Source checksum mismatch")
            passages = chunks(source_text(v["filename"], content))
            vectors = []
            for offset in range(0, len(passages), 16):
                self.renew(job)
                batch = passages[offset : offset + 16]
                vectors.extend(
                    validate_vectors(
                        self.embeddings.embed([p["body"] for p in batch]), len(batch)
                    )
                )
            self.publish(job, v, passages, vectors)
        except LeaseLost:
            pass  # Another worker/deletion owns the outcome; stale writes are forbidden.
        except Exception:
            with self.db.connect() as c:
                # Lock document before job/version, matching deletion/publication order.
                c.execute(
                    "SELECT id FROM documents WHERE id=(SELECT document_id FROM document_versions WHERE id=%s) FOR UPDATE",
                    (job["version_id"],),
                )
                c.execute("SELECT id FROM ingestion_jobs WHERE id=%s FOR UPDATE", (job["id"],))
                # Rollback/publication failures return to a bounded retry. No exception body is persisted.
                updated = c.execute(
                    """UPDATE ingestion_jobs SET state=%s,error_code='ingestion_failed',
                    available_at=now()+(%s * interval '1 second'),lease_token=NULL,lease_until=NULL
                    WHERE id=%s AND lease_token=%s AND state='running' AND lease_until>clock_timestamp() RETURNING version_id""",
                    (
                        "failed" if job["attempts"] >= MAX_ATTEMPTS else "queued",
                        2 ** job["attempts"],
                        job["id"],
                        job["lease_token"],
                    ),
                ).fetchone()
                if updated:
                    c.execute(
                        "UPDATE document_versions SET state=%s,error_code='ingestion_failed' WHERE id=%s AND state NOT IN ('deleted','superseded')",
                        (
                            "failed" if job["attempts"] >= MAX_ATTEMPTS else "queued",
                            updated["version_id"],
                        ),
                    )
        return True

    def publish(self, job, version, passages, vectors):
        with self.db.connect() as c:
            d = c.execute(
                "SELECT * FROM documents WHERE id=%s FOR UPDATE",
                (version["document_id"],),
            ).fetchone()
            c.execute("SELECT id FROM ingestion_jobs WHERE id=%s FOR UPDATE", (job["id"],))
            live = c.execute(
                """SELECT id FROM ingestion_jobs WHERE id=%s AND lease_token=%s
                AND state='running' AND lease_until>clock_timestamp() FOR UPDATE""",
                (job["id"], job["lease_token"]),
            ).fetchone()
            if not live:
                raise LeaseLost()
            if d["deleted_at"] or d["generation"] != version["generation"]:
                c.execute(
                    "UPDATE ingestion_jobs SET state='cancelled',lease_token=NULL,lease_until=NULL WHERE id=%s",
                    (job["id"],),
                )
                c.execute(
                    "UPDATE document_versions SET state=%s WHERE id=%s",
                    ("deleted" if d["deleted_at"] else "superseded", version["id"]),
                )
                return
            c.execute(
                "DELETE FROM document_passages WHERE version_id=%s", (version["id"],)
            )
            for ordinal, (p, vector) in enumerate(zip(passages, vectors, strict=True)):
                c.execute(
                    """INSERT INTO document_passages(id,version_id,ordinal,line_start,line_end,body,embedding)
                    VALUES (%s,%s,%s,%s,%s,%s,%s::public.vector)""",
                    (
                        uuid5(NAMESPACE_URL, str(version["id"]) + ":" + str(ordinal)),
                        version["id"],
                        ordinal,
                        p["line_start"],
                        p["line_end"],
                        p["body"],
                        str(vector),
                    ),
                )
            if d["active_version"]:
                c.execute(
                    "DELETE FROM document_passages WHERE version_id=%s",
                    (d["active_version"],),
                )
                c.execute(
                    "UPDATE document_versions SET state='superseded' WHERE id=%s",
                    (d["active_version"],),
                )
            c.execute(
                "UPDATE document_versions SET state='ready',error_code=NULL WHERE id=%s",
                (version["id"],),
            )
            c.execute(
                "UPDATE documents SET active_version=%s WHERE id=%s",
                (version["id"], d["id"]),
            )
            # Recheck after inserts: expiry rolls back the entire publication.
            completed = c.execute(
                """UPDATE ingestion_jobs SET state='done',lease_token=NULL,lease_until=NULL,error_code=NULL
                WHERE id=%s AND lease_token=%s AND state='running'
                AND lease_until>clock_timestamp() RETURNING id""",
                (job["id"], job["lease_token"]),
            ).fetchone()
            if not completed:
                raise LeaseLost()
            event(c, d["id"], version["id"], None, "index_published")

    def cleanup(self):
        """Bounded cleanup; original superseded evidence is retained for historical citations."""
        with self.db.connect() as c:
            c.execute("""UPDATE document_versions v SET state='failed',error_code='attempts_exhausted'
                FROM ingestion_jobs j WHERE j.version_id=v.id AND j.state='failed' AND v.state='processing'""")
            c.execute("""UPDATE document_versions v SET state='superseded',error_code='upload_expired' FROM documents d
                WHERE v.document_id=d.id AND v.state='uploading' AND v.created_at<now()-interval '1 hour'""")
            rows = c.execute("""SELECT v.* FROM document_versions v JOIN documents d ON d.id=v.document_id
                WHERE (d.deleted_at IS NOT NULL OR (v.state='superseded' AND NOT EXISTS
                    (SELECT 1 FROM ingestion_jobs j WHERE j.version_id=v.id))) AND v.cleaned_at IS NULL
                ORDER BY v.created_at LIMIT 20""").fetchall()
        for v in rows:
            try:
                self.blobs.delete(v["blob_key"])
            except Exception:
                continue
            with self.db.connect() as c:
                c.execute(
                    "UPDATE document_versions SET cleaned_at=now() WHERE id=%s",
                    (v["id"],),
                )
        return len(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Process durable document jobs; no agent actions."
    )
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    db = Database(Settings())
    db.migrate()
    worker = Worker(db)
    while True:
        worked = worker.run_once()
        worker.cleanup()
        if args.once:
            break
        if not worked:
            time.sleep(2)


if __name__ == "__main__":
    main()
