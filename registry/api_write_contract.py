"""FASTAPI-REACT-02 — frozen API write route contract (explicit company_id).

Machine-readable mirror of ``docs/FASTAPI_REACT_02_API_WRITE_HARDENING_AUDIT.md``.
Routes pass ``company_id`` from ``require_company_write_access`` into ``services/write_*``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

CONTRACT_DOC: Final[str] = "docs/FASTAPI_REACT_02_API_WRITE_HARDENING_AUDIT.md"
P2_HARDEN_CLOSURE_DOC: Final[str] = "docs/P2_HARDEN_01_AUDIT_CLOSURE.md"

COMPANY_HEADER: Final[str] = "X-Company-Id"
COMPANY_MISSING_MARKER: Final[str] = "active_company_id"

WRITE_ROUTE_FILES: tuple[str, ...] = (
    "api/routes/sales.py",
    "api/routes/expenses.py",
    "api/routes/purchases.py",
    "api/routes/receivable_payments.py",
    "api/routes/voids.py",
    "api/routes/partner_movements.py",
    "api/routes/worker_payments.py",
    "api/routes/bank_transactions.py",
    "api/routes/reconciliation.py",
    "api/routes/closing.py",
)

WRITE_SERVICE_MODULES: tuple[str, ...] = (
    "services/write_sales.py",
    "services/write_expenses.py",
    "services/write_purchases.py",
    "services/write_receivable_payments.py",
    "services/write_voids.py",
    "services/write_banking.py",
    "services/write_partner_worker.py",
    "services/write_reconciliation.py",
    "services/write_closing.py",
)


@dataclass(frozen=True, slots=True)
class ApiWriteEndpointSpec:
    route_file: str
    handler: str
    permission: str
    service_module: str
    service_call: str


API_WRITE_ENDPOINTS: tuple[ApiWriteEndpointSpec, ...] = (
    ApiWriteEndpointSpec(
        "api/routes/sales.py", "post_sale", "create_transaction",
        "services/write_sales.py", "create_and_post_sale",
    ),
    ApiWriteEndpointSpec(
        "api/routes/expenses.py", "post_expense", "create_transaction",
        "services/write_expenses.py", "create_and_post_expense",
    ),
    ApiWriteEndpointSpec(
        "api/routes/purchases.py", "post_purchase", "create_transaction",
        "services/write_purchases.py", "create_and_post_purchase",
    ),
    ApiWriteEndpointSpec(
        "api/routes/receivable_payments.py", "post_receivable_payment",
        "create_transaction", "services/write_receivable_payments.py",
        "record_receivable_payment",
    ),
    ApiWriteEndpointSpec(
        "api/routes/voids.py", "post_void", "void_transaction",
        "services/write_voids.py", "void_record",
    ),
    ApiWriteEndpointSpec(
        "api/routes/partner_movements.py", "post_partner_movement",
        "post_partner_movement", "services/write_partner_worker.py",
        "post_partner_movement_record",
    ),
    ApiWriteEndpointSpec(
        "api/routes/worker_payments.py", "post_worker_payment",
        "post_worker_movement", "services/write_partner_worker.py",
        "post_worker_payment_record",
    ),
    ApiWriteEndpointSpec(
        "api/routes/bank_transactions.py", "post_bank_transaction",
        "manage_banking", "services/write_banking.py",
        "create_manual_bank_transaction",
    ),
    ApiWriteEndpointSpec(
        "api/routes/reconciliation.py", "post_reconciliation_match",
        "import_bank_statement", "services/write_reconciliation.py",
        "match_statement_row",
    ),
    ApiWriteEndpointSpec(
        "api/routes/reconciliation.py", "post_reconciliation_unmatch",
        "import_bank_statement", "services/write_reconciliation.py",
        "unmatch_statement_row",
    ),
    ApiWriteEndpointSpec(
        "api/routes/closing.py", "post_close_period", "close_fiscal_period",
        "services/write_closing.py", "close_period",
    ),
    ApiWriteEndpointSpec(
        "api/routes/closing.py", "post_profit_allocation", "allocate_profit",
        "services/write_closing.py", "allocate",
    ),
    ApiWriteEndpointSpec(
        "api/routes/closing.py", "post_void_allocation", "void_profit_allocation",
        "services/write_closing.py", "void_allocation",
    ),
)

CORE_INVARIANTS: tuple[str, ...] = (
    "No GET commits",
    "JWT RequestContext",
    "X-Company-Id",
    "Never trust company_id from request body",
    "Never delete accounting records",
    "Void → reverse → audit",
)

DEFERRED_GAP_IDS: tuple[str, ...] = (
    "TD-PS-01",
    "TD-PS-03",
    "TD-POSTING-06",
)
