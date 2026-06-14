"""FASTAPI-P1.2 — read-only API application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.openapi_tags import OPENAPI_TAGS
from api.routes import banking, ledger, partners, payables, receivables, reports
from services.permissions import PermissionDenied

_API_DESCRIPTION = """\
Read-only ERP API (P1.x). All business routes require dev/test headers:

- ``X-User-Id`` (required) — actor user id
- ``X-Company-Id`` (required for company-scoped routes) — active company
- ``X-Role`` (optional) — membership role override for tests

**Error contract:** 401 missing user · 400 missing company · 403 membership/permission · 404 not found · 422 validation

No write endpoints; GET handlers do not commit the database session.
"""


def create_app() -> FastAPI:
    """Construct the read-only FastAPI application."""
    app = FastAPI(
        title="Streamlit Accounting ERP API",
        version="1.2.0",
        description=_API_DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
    )

    @app.get(
        "/health",
        tags=["health"],
        summary="Health check",
        description="Returns ``{\"status\": \"ok\"}`` when the API process is running.",
    )
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(reports.router, prefix="/api/v1/reports")
    app.include_router(ledger.router, prefix="/api/v1/ledger")
    app.include_router(receivables.router, prefix="/api/v1/receivables")
    app.include_router(payables.router, prefix="/api/v1/payables")
    app.include_router(partners.router, prefix="/api/v1/partners")
    app.include_router(banking.router, prefix="/api/v1/banking")

    @app.exception_handler(PermissionDenied)
    async def _permission_denied_handler(_request, exc: PermissionDenied):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(_request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    return app
