"""FASTAPI-P1.2 — read-only API application factory."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.openapi_tags import OPENAPI_TAGS
from api.routes import auth, bank_transactions, banking, closing, expenses, ledger, partner_movements, partners, payables, purchases, receivable_payments, receivables, reconciliation, reports, sales, voids, worker_payments
from services.permissions import PermissionDenied

_API_DESCRIPTION = """\
ERP API (P1.x reads, P2.x writes). Business routes require:

- ``Authorization: Bearer <access_token>`` — identity from JWT (DB-verified)
- ``X-Company-Id`` (required for company-scoped routes) — active company selection

Membership role and permissions are resolved from the database per request.
Set ``ERP_API_DEV_HEADERS=1`` only for explicit test/dev fallback to legacy headers.

**Error contract:** 401 missing/invalid bearer · 400 missing company · 403 membership/permission · 404 not found · 422 validation

GET handlers do not commit the database session. Write endpoints (e.g. ``POST /api/v1/sales``,
``POST /api/v1/expenses``) require feature flags such as ``ERP_API_WRITE_SALES=1`` /
``ERP_API_WRITE_EXPENSES=1`` / ``ERP_API_WRITE_PURCHASES=1`` /
``ERP_API_WRITE_RECEIVABLE_PAYMENTS=1`` / ``ERP_API_WRITE_VOIDS=1`` /
``ERP_API_WRITE_PARTNER_WORKER=1`` / ``ERP_API_WRITE_BANKING=1`` / ``ERP_API_WRITE_RECONCILIATION=1``.
"""


def create_app() -> FastAPI:
    """Construct the read-only FastAPI application."""
    app = FastAPI(
        title="Streamlit Accounting ERP API",
        version="1.4.7",
        description=_API_DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
    )

    allowed_origins = [
        o.strip()
        for o in os.getenv("ERP_CORS_ORIGINS", "").split(",")
        if o.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "X-Company-Id"],
    )

    @app.get(
        "/health",
        tags=["health"],
        summary="Health check",
        description="Returns ``{\"status\": \"ok\"}`` when the API process is running.",
    )
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router, prefix="/auth")
    app.include_router(reports.router, prefix="/api/v1/reports")
    app.include_router(ledger.router, prefix="/api/v1/ledger")
    app.include_router(receivables.router, prefix="/api/v1/receivables")
    app.include_router(payables.router, prefix="/api/v1/payables")
    app.include_router(partners.router, prefix="/api/v1/partners")
    app.include_router(banking.router, prefix="/api/v1/banking")
    app.include_router(sales.router, prefix="/api/v1/sales")
    app.include_router(expenses.router, prefix="/api/v1/expenses")
    app.include_router(purchases.router, prefix="/api/v1/purchases")
    app.include_router(receivable_payments.router, prefix="/api/v1/receivable-payments")
    app.include_router(voids.router, prefix="/api/v1/voids")
    app.include_router(partner_movements.router, prefix="/api/v1/partner-movements")
    app.include_router(worker_payments.router, prefix="/api/v1/worker-payments")
    app.include_router(bank_transactions.router, prefix="/api/v1/bank-transactions")
    app.include_router(reconciliation.router, prefix="/api/v1/reconciliation")
    app.include_router(closing.router, prefix="/api/v1")

    @app.exception_handler(PermissionDenied)
    async def _permission_denied_handler(_request, exc: PermissionDenied):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(_request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    return app
