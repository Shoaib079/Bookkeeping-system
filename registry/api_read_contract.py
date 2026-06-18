"""FASTAPI-REACT-04 — frozen read API contract (OpenAPI + error mapping).

Machine-readable mirror of ``docs/FASTAPI_REACT_04_READ_API_BOUNDARY_AUDIT.md``.
"""

from __future__ import annotations

from typing import Final

CONTRACT_DOC: Final[str] = "docs/FASTAPI_REACT_04_READ_API_BOUNDARY_AUDIT.md"
P1_CONTRACT_TEST: Final[str] = "tests/test_fastapi_p1_api_contract.py"
P1_READ_TEST: Final[str] = "tests/test_fastapi_p1_read_endpoints.py"

# Stable GET read spine (OpenAPI paths).
READ_API_PATHS: tuple[str, ...] = (
    "/health",
    "/auth/login",
    "/auth/me",
    "/auth/companies",
    "/api/v1/reports/profit-loss",
    "/api/v1/reports/balance-sheet",
    "/api/v1/reports/cash-flow",
    "/api/v1/reports/trial-balance",
    "/api/v1/transactions",
    "/api/v1/ledger",
    "/api/v1/chart-of-accounts",
    "/api/v1/receivables",
    "/api/v1/receivable-sales",
    "/api/v1/sales",
    "/api/v1/expenses",
    "/api/v1/purchases",
    "/api/v1/payables",
    "/api/v1/partners",
    "/api/v1/bank-accounts",
    "/api/v1/bank-statement-rows",
    "/api/v1/fiscal-periods",
    "/api/v1/journal-entries",
    "/api/v1/vendors",
    "/api/v1/customers",
    "/api/v1/profit-allocations",
    "/api/v1/workers",
    "/api/v1/partners/{partner_id}/statement",
    "/api/v1/banking/readiness",
)

READ_API_TAGS: tuple[str, ...] = (
    "health",
    "auth",
    "reports",
    "transactions",
    "ledger",
    "chart-of-accounts",
    "receivables",
    "receivable-sales",
    "sales",
    "expenses",
    "purchases",
    "payables",
    "partners",
    "bank-accounts",
    "bank-statement-rows",
    "fiscal-periods",
    "journal-entries",
    "vendors",
    "customers",
    "profit-allocations",
    "workers",
    "banking",
)

ERROR_CONTRACT_MARKERS: tuple[str, ...] = (
    "401 missing/invalid bearer",
    "400 missing company",
    "403 membership/permission",
    "404 not found",
    "422 validation",
)

HTTP_ERROR_MARKERS: tuple[str, ...] = (
    "active_company_id",
    "require_company_membership",
)

READ_SERVICE_MODULES: tuple[str, ...] = (
    "services/read_reports.py",
    "services/read_trial_balance.py",
    "services/read_transaction_history.py",
    "services/read_ledger.py",
    "services/read_ar_ap.py",
    "services/read_coa.py",
    "services/read_partners.py",
    "services/read_bank_accounts.py",
    "services/read_bank_statement_rows.py",
    "services/read_fiscal_periods.py",
    "services/read_journal_entries.py",
    "services/read_vendors.py",
    "services/read_customers.py",
    "services/read_receivable_sales.py",
    "services/read_sales.py",
    "services/read_expenses.py",
    "services/read_purchases.py",
    "services/read_profit_allocations.py",
    "services/read_workers.py",
    "services/read_partner_statement.py",
    "services/read_balances.py",
    "services/read_reconciliation.py",
)

SERIALIZATION_MODULE: Final[str] = "api/serialization.py"

DEFERRED_GAP_IDS: tuple[str, ...] = (
    "TD-PS-01",
    "TD-PS-03",
)
