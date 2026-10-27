import hmac
import logging
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response

from .config import Settings
from .contracts import (
    Edit,
    Login,
    RequisitionData,
    Transition,
    IssuePurchaseOrder,
    ProposePurchaseOrder,
    ProposalDecision,
    RecordReceipt,
    CaptureInvoice,
    ReviewInvoice,
)
from .database import Database
from .identity import COOKIE, authenticate, login, seed_users
from .workflow import command, get_record, view, get_purchase_order


def create_app(settings=None):
    settings = settings or Settings()
    db = Database(settings)

    @asynccontextmanager
    async def lifespan(app):
        db.migrate()
        seed_users(db)
        yield

    app = FastAPI(title="Harbor procurement API", version="0.1.0", lifespan=lifespan)
    app.state.db, app.state.settings = db, settings

    @app.middleware("http")
    async def boundary(request, call_next):
        request.state.request_id = str(uuid4())
        origin = request.headers.get("origin")
        if (
            request.method not in ("GET", "HEAD", "OPTIONS")
            and origin
            and origin not in settings.allowed_origins
        ):
            return JSONResponse(
                {
                    "detail": "Origin is not allowed",
                    "request_id": request.state.request_id,
                },
                status_code=403,
            )
        try:
            response = await call_next(request)
        except Exception as error:
            logging.getLogger("harbor").error(
                "request_id=%s error_type=%s",
                request.state.request_id,
                type(error).__name__,
            )
            response = JSONResponse(
                {
                    "detail": "The request could not be completed",
                    "request_id": request.state.request_id,
                },
                status_code=500,
            )
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        return JSONResponse(
            {"detail": error.detail, "request_id": request.state.request_id},
            status_code=error.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return JSONResponse(
            {
                "detail": "Please check the highlighted fields",
                "fields": [
                    {"loc": list(e["loc"]), "message": e["msg"]} for e in error.errors()
                ],
                "request_id": request.state.request_id,
            },
            status_code=422,
        )

    def identity(request: Request):
        return authenticate(db, settings, request.cookies.get(COOKIE))

    def actor(request: Request, auth=Depends(identity)):
        user, claims = auth
        if request.method not in ("GET", "HEAD") and not hmac.compare_digest(
            request.headers.get("X-CSRF-Token", ""), claims["csrf"]
        ):
            raise HTTPException(403, "Invalid CSRF token; sign in again")
        return user

    def command_key(idempotency_key: str = Header(min_length=8, max_length=100)):
        return idempotency_key

    @app.get("/api/v1/health")
    def health():
        with db.connect() as connection:
            connection.execute("SELECT 1")
        return {"status": "ok", "version": "0.1.0"}

    @app.post("/api/v1/auth/login")
    def sign_in(data: Login):
        token, result = login(db, settings, data.username, data.password)
        response = JSONResponse(result)
        response.set_cookie(
            COOKIE,
            token,
            httponly=True,
            secure=settings.secure_cookie,
            samesite="lax",
            path="/api",
            max_age=settings.session_seconds,
        )
        return response

    @app.get("/api/v1/auth/me")
    def me(auth=Depends(identity)):
        user, claims = auth
        return {"user": user, "csrf_token": claims["csrf"]}

    @app.post("/api/v1/auth/logout", status_code=204)
    def sign_out(user=Depends(actor), auth=Depends(identity)):
        with db.connect() as connection:
            connection.execute(
                "UPDATE sessions SET revoked=true WHERE id=%s", (auth[1]["jti"],)
            )
        response = Response(status_code=204)
        response.delete_cookie(COOKIE, path="/api")
        return response

    @app.get("/api/v1/requisitions")
    def register(user=Depends(actor)):
        with db.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM requisitions WHERE owner_id=%s OR (%s != 'requester' AND status != 'draft') ORDER BY number DESC",
                (user["id"], user["role"]),
            ).fetchall()
            return {"items": [view(connection, row) for row in rows]}

    @app.get("/api/v1/requisitions/{id}")
    def detail(id: UUID, user=Depends(actor)):
        with db.connect() as connection:
            return view(connection, get_record(connection, id, user))

    @app.post("/api/v1/requisitions", status_code=201)
    def create(data: RequisitionData, user=Depends(actor), key=Depends(command_key)):
        return command(db, user, key, "create", data.model_dump(mode="json"))

    @app.put("/api/v1/requisitions/{id}")
    def edit(id: UUID, data: Edit, user=Depends(actor), key=Depends(command_key)):
        return command(db, user, key, "edit", data.model_dump(mode="json"), id)

    # Explicit routes keep the public contract and OpenAPI action schemas clear.
    @app.post("/api/v1/requisitions/{id}/submit")
    def submit(
        id: UUID, data: Transition, user=Depends(actor), key=Depends(command_key)
    ):
        return command(db, user, key, "submit", data.model_dump(mode="json"), id)

    @app.post("/api/v1/requisitions/{id}/approve")
    def approve(
        id: UUID, data: Transition, user=Depends(actor), key=Depends(command_key)
    ):
        return command(db, user, key, "approve", data.model_dump(mode="json"), id)

    @app.post("/api/v1/requisitions/{id}/return")
    def return_for_changes(
        id: UUID, data: Transition, user=Depends(actor), key=Depends(command_key)
    ):
        return command(db, user, key, "return", data.model_dump(mode="json"), id)

    @app.post("/api/v1/requisitions/{id}/purchase-order", status_code=201)
    def issue_purchase_order(
        id: UUID,
        data: IssuePurchaseOrder,
        user=Depends(actor),
        key=Depends(command_key),
    ):
        return command(db, user, key, "issue_po", data.model_dump(mode="json"), id)

    @app.post("/api/v1/requisitions/{id}/po-proposals", status_code=201)
    def propose_po(
        id: UUID,
        data: ProposePurchaseOrder,
        user=Depends(actor),
        key=Depends(command_key),
    ):
        return command(db, user, key, "propose_po", data.model_dump(mode="json"), id)

    @app.post("/api/v1/requisitions/{id}/po-proposals/approve")
    def approve_po(
        id: UUID, data: ProposalDecision, user=Depends(actor), key=Depends(command_key)
    ):
        return command(db, user, key, "approve_po", data.model_dump(mode="json"), id)

    @app.post("/api/v1/requisitions/{id}/po-proposals/return")
    def return_po(
        id: UUID, data: ProposalDecision, user=Depends(actor), key=Depends(command_key)
    ):
        return command(db, user, key, "return_po", data.model_dump(mode="json"), id)

    @app.post("/api/v1/requisitions/{id}/po-proposals/issue")
    def issue_po_revision(
        id: UUID, data: ProposalDecision, user=Depends(actor), key=Depends(command_key)
    ):
        return command(
            db, user, key, "issue_po_revision", data.model_dump(mode="json"), id
        )

    @app.post("/api/v1/requisitions/{id}/receipts", status_code=201)
    def receive(
        id: UUID, data: RecordReceipt, user=Depends(actor), key=Depends(command_key)
    ):
        return command(db, user, key, "receive", data.model_dump(mode="json"), id)

    @app.post("/api/v1/requisitions/{id}/invoices", status_code=201)
    def capture_invoice(
        id: UUID, data: CaptureInvoice, user=Depends(actor), key=Depends(command_key)
    ):
        return command(
            db, user, key, "capture_invoice", data.model_dump(mode="json"), id
        )

    @app.post("/api/v1/requisitions/{id}/invoices/review")
    def review_invoice(
        id: UUID, data: ReviewInvoice, user=Depends(actor), key=Depends(command_key)
    ):
        return command(
            db, user, key, "review_invoice", data.model_dump(mode="json"), id
        )

    @app.get("/api/v1/purchase-orders/{id}")
    def purchase_order(id: UUID, user=Depends(actor)):
        with db.connect() as connection:
            return get_purchase_order(connection, id, user)

    return app
