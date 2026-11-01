from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from . import documents
from .document_adapters import MAX_BYTES


def install_document_routes(app, db, actor, command_key):
    @app.get("/api/v1/documents")
    def list_documents(user=Depends(actor)):
        with db.connect() as c:
            ids = c.execute(
                "SELECT id FROM documents WHERE deleted_at IS NULL ORDER BY created_at DESC LIMIT 100"
            ).fetchall()
            return {"items": [documents.detail(c, row["id"]) for row in ids]}

    @app.get("/api/v1/documents/search")
    def search_documents(
        q: str = Query(min_length=2, max_length=500), user=Depends(actor)
    ):
        return documents.search(db, app.state.document_embeddings, q)

    async def receive(
        request, user, key, filename, title, document_id=None, expected_generation=None
    ):
        documents.buyer(user)
        content = bytearray()
        async for part in request.stream():
            if len(content) + len(part) > MAX_BYTES:
                raise HTTPException(413, "Document exceeds 64 KiB")
            content.extend(part)
        return await run_in_threadpool(
            documents.upload,
            db,
            app.state.document_blobs,
            user,
            key,
            filename,
            title,
            bytes(content),
            document_id,
            expected_generation,
        )

    @app.post("/api/v1/documents", status_code=202)
    async def upload_document(
        request: Request,
        filename: str = Query(max_length=160),
        title: str = Query(max_length=150),
        user=Depends(actor),
        key=Depends(command_key),
    ):
        return await receive(request, user, key, filename, title)

    @app.post("/api/v1/documents/{document_id}/versions", status_code=202)
    async def replace_document(
        document_id: UUID,
        request: Request,
        filename: str = Query(max_length=160),
        title: str = Query(max_length=150),
        expected_generation: int = Query(ge=1),
        user=Depends(actor),
        key=Depends(command_key),
    ):
        return await receive(
            request, user, key, filename, title, document_id, expected_generation
        )

    @app.get("/api/v1/documents/{document_id}")
    def get_document(document_id: UUID, user=Depends(actor)):
        with db.connect() as c:
            return documents.detail(c, document_id)

    @app.get("/api/v1/documents/{document_id}/versions/{version_id}/source")
    def get_source(document_id: UUID, version_id: UUID, user=Depends(actor)):
        with db.connect() as c:
            documents.detail(c, document_id)
            v = c.execute(
                "SELECT * FROM document_versions WHERE id=%s AND document_id=%s AND cleaned_at IS NULL",
                (version_id, document_id),
            ).fetchone()
            if not v or v["state"] in ("uploading", "deleted"):
                raise HTTPException(404, "Source not found")
        try:
            content = app.state.document_blobs.get(v["blob_key"])
        except Exception:
            raise HTTPException(503, "Source storage unavailable") from None
        # Recheck after external I/O: a deletion must not return a now-hidden source.
        with db.connect() as c:
            documents.detail(c, document_id)
        return Response(
            content,
            media_type="text/plain",
            headers={"Content-Disposition": 'attachment; filename="source.txt"'},
        )

    @app.delete("/api/v1/documents/{document_id}", status_code=204)
    def delete_document(
        document_id: UUID, expected_generation: int = Query(ge=1), user=Depends(actor)
    ):
        documents.remove(db, user, document_id, expected_generation)
        return Response(status_code=204)

    @app.post("/api/v1/documents/{document_id}/retry")
    def retry_document(document_id: UUID, user=Depends(actor)):
        return documents.retry(db, user, document_id)
