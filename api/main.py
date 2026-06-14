"""FASTAPI-P1.0 — read-only API application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from api.routes import reports
from services.permissions import PermissionDenied


def create_app() -> FastAPI:
    """Construct the read-only FastAPI application."""
    app = FastAPI(
        title="Streamlit Accounting ERP API",
        version="1.0.0",
        description="Read-only API spine (P1.0). No writes, no commits on GET.",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(reports.router, prefix="/api/v1/reports")

    @app.exception_handler(PermissionDenied)
    async def _permission_denied_handler(_request, exc: PermissionDenied):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return app
