"""FASTAPI-P1.2 — read-only API application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.openapi_tags import OPENAPI_TAGS
from api.routes import audit_log, auth, bank_accounts, bank_statement_rows, bank_transactions, banking, chart_of_accounts, closing, customers, expenses, expenses_read, fiscal_periods, journal_entries, ledger, opening_balances, partner_movements, partners, payables, profit_allocations, purchases, purchases_read, receivable_payments, receivable_sales, receivables, recon_health, reconciliation, reports, sales, sales_read, transactions, vendors, voids, worker_payments, workers
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
    app.include_router(chart_of_accounts.router, prefix="/api/v1/chart-of-accounts")
    app.include_router(transactions.router, prefix="/api/v1/transactions")
    app.include_router(ledger.router, prefix="/api/v1/ledger")
    app.include_router(receivables.router, prefix="/api/v1/receivables")
    app.include_router(receivable_sales.router, prefix="/api/v1/receivable-sales")
    app.include_router(payables.router, prefix="/api/v1/payables")
    app.include_router(partners.router, prefix="/api/v1/partners")
    app.include_router(bank_accounts.router, prefix="/api/v1/bank-accounts")
    app.include_router(bank_statement_rows.router, prefix="/api/v1/bank-statement-rows")
    app.include_router(fiscal_periods.router, prefix="/api/v1/fiscal-periods")
    app.include_router(journal_entries.router, prefix="/api/v1/journal-entries")
    app.include_router(opening_balances.router, prefix="/api/v1/opening-balances")
    app.include_router(audit_log.router, prefix="/api/v1/audit-log")
    app.include_router(vendors.router, prefix="/api/v1/vendors")
    app.include_router(customers.router, prefix="/api/v1/customers")
    app.include_router(workers.router, prefix="/api/v1/workers")
    app.include_router(banking.router, prefix="/api/v1/banking")
    app.include_router(sales_read.router, prefix="/api/v1/sales")
    app.include_router(sales.router, prefix="/api/v1/sales")
    app.include_router(expenses_read.router, prefix="/api/v1/expenses")
    app.include_router(expenses.router, prefix="/api/v1/expenses")
    app.include_router(purchases_read.router, prefix="/api/v1/purchases")
    app.include_router(purchases.router, prefix="/api/v1/purchases")
    app.include_router(receivable_payments.router, prefix="/api/v1/receivable-payments")
    app.include_router(voids.router, prefix="/api/v1/voids")
    app.include_router(partner_movements.router, prefix="/api/v1/partner-movements")
    app.include_router(worker_payments.router, prefix="/api/v1/worker-payments")
    app.include_router(bank_transactions.router, prefix="/api/v1/bank-transactions")
    app.include_router(reconciliation.router, prefix="/api/v1/reconciliation")
    app.include_router(recon_health.router, prefix="/api/v1/reconciliation")
    app.include_router(closing.router, prefix="/api/v1")
    app.include_router(profit_allocations.router, prefix="/api/v1/profit-allocations")

    @app.exception_handler(PermissionDenied)
    async def _permission_denied_handler(_request, exc: PermissionDenied):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(_request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    return app
