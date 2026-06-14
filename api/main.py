"""FASTAPI-P1.0 — read-only API application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from api.routes import ar_ap, banking, ledger, partners, reports
from services.permissions import PermissionDenied


def create_app() -> FastAPI:
    """Construct the read-only FastAPI application."""
    app = FastAPI(
        title="Streamlit Accounting ERP API",
        version="1.0.0",
        description="Read-only API spine (P1.0+). No writes, no commits on GET.",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(reports.router, prefix="/api/v1/reports")
    app.include_router(ledger.router, prefix="/api/v1/ledger")
    app.include_router(ar_ap.router, prefix="/api/v1")
    app.include_router(partners.router, prefix="/api/v1/partners")
    app.include_router(banking.router, prefix="/api/v1/banking")

    @app.exception_handler(PermissionDenied)
    async def _permission_denied_handler(_request, exc: PermissionDenied):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return app
