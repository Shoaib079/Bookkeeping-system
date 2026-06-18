"""FASTAPI-REACT-08 — frozen first React write page contract.

Machine-readable mirror of ``docs/FASTAPI_REACT_08_REACT_WRITE_AUDIT.md``.
"""

from __future__ import annotations

from typing import Final

CONTRACT_DOC: Final[str] = "docs/FASTAPI_REACT_08_REACT_WRITE_AUDIT.md"
PAGES_CONTRACT: Final[str] = "registry/react_pages_contract.py"
WRITE_API_CONTRACT: Final[str] = "registry/api_write_contract.py"
BOUNDARY_CONTRACT: Final[str] = "registry/pg_boundary_contract.py"

READ_PAGES_FLAG_ENV: Final[str] = "VITE_ERP_REACT_PAGES"
WRITE_SALES_FLAG_ENV: Final[str] = "VITE_ERP_REACT_WRITE_SALES"
WRITE_EXPENSES_FLAG_ENV: Final[str] = "VITE_ERP_REACT_WRITE_EXPENSES"
WRITE_VOIDS_FLAG_ENV: Final[str] = "VITE_ERP_REACT_WRITE_VOIDS"
WRITE_PURCHASES_FLAG_ENV: Final[str] = "VITE_ERP_REACT_WRITE_PURCHASES"
WRITE_RECEIVABLE_PAYMENTS_FLAG_ENV: Final[str] = "VITE_ERP_REACT_WRITE_RECEIVABLE_PAYMENTS"
WRITE_BANKING_FLAG_ENV: Final[str] = "VITE_ERP_REACT_WRITE_BANKING"
WRITE_PARTNER_WORKER_FLAG_ENV: Final[str] = "VITE_ERP_REACT_WRITE_PARTNER_WORKER"
WRITE_RECONCILIATION_FLAG_ENV: Final[str] = "VITE_ERP_REACT_WRITE_RECONCILIATION"
WRITE_CLOSING_FLAG_ENV: Final[str] = "VITE_ERP_REACT_WRITE_CLOSING"
API_WRITE_SALES_ENV: Final[str] = "ERP_API_WRITE_SALES"
API_WRITE_EXPENSES_ENV: Final[str] = "ERP_API_WRITE_EXPENSES"
API_WRITE_VOIDS_ENV: Final[str] = "ERP_API_WRITE_VOIDS"
API_WRITE_PURCHASES_ENV: Final[str] = "ERP_API_WRITE_PURCHASES"
API_WRITE_RECEIVABLE_PAYMENTS_ENV: Final[str] = "ERP_API_WRITE_RECEIVABLE_PAYMENTS"
API_WRITE_BANKING_ENV: Final[str] = "ERP_API_WRITE_BANKING"
API_WRITE_PARTNER_WORKER_ENV: Final[str] = "ERP_API_WRITE_PARTNER_WORKER"
API_WRITE_RECONCILIATION_ENV: Final[str] = "ERP_API_WRITE_RECONCILIATION"
API_WRITE_CLOSING_ENV: Final[str] = "ERP_API_WRITE_CLOSING"

# (react_path, page_component, page_key)
WRITE_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/transactions/new", "NewTransactionPage", "new_transaction"),
)

WRITE_API_PATHS: tuple[str, ...] = (
    "/api/v1/sales",
)

EXPENSE_WRITE_API_PATHS: tuple[str, ...] = (
    "/api/v1/expenses",
)

VOID_WRITE_API_PATHS: tuple[str, ...] = (
    "/api/v1/voids",
)

PURCHASE_WRITE_API_PATHS: tuple[str, ...] = (
    "/api/v1/purchases",
)

RECEIVABLE_PAYMENT_WRITE_API_PATHS: tuple[str, ...] = (
    "/api/v1/receivable-payments",
)

BANK_TRANSACTION_WRITE_API_PATHS: tuple[str, ...] = (
    "/api/v1/bank-transactions",
)

PARTNER_MOVEMENT_WRITE_API_PATHS: tuple[str, ...] = (
    "/api/v1/partner-movements",
)

WORKER_PAYMENT_WRITE_API_PATHS: tuple[str, ...] = (
    "/api/v1/worker-payments",
)

RECONCILIATION_WRITE_API_PATHS: tuple[str, ...] = (
    "/api/v1/reconciliation/match",
    "/api/v1/reconciliation/unmatch",
)

CLOSING_WRITE_API_PATHS: tuple[str, ...] = (
    "/api/v1/periods/",
    "/api/v1/profit-allocations",
)

VOID_TARGET_TYPES: tuple[str, ...] = (
    "Sale",
    "ExpenseRecord",
    "Purchase",
    "Payable",
    "BankTransaction",
)

WRITE_CLIENT_MODULE: Final[str] = "frontend/src/lib/api/writeClient.ts"
P2_SALES_WRITE_TEST: Final[str] = "tests/test_fastapi_p2_sales_write.py"
P2_EXPENSE_WRITE_TEST: Final[str] = "tests/test_fastapi_p2_expense_write.py"
P2_VOID_WRITE_TEST: Final[str] = "tests/test_fastapi_p2_void_write.py"
P2_PURCHASE_WRITE_TEST: Final[str] = "tests/test_fastapi_p2_purchase_write.py"
P2_RECEIVABLE_PAYMENT_WRITE_TEST: Final[str] = (
    "tests/test_fastapi_p2_receivable_payment_write.py"
)
P2_BANKING_WRITE_TEST: Final[str] = "tests/test_fastapi_p2_banking_write.py"
P2_PARTNER_WORKER_WRITE_TEST: Final[str] = "tests/test_fastapi_p2_partner_worker_write.py"
P2_RECONCILIATION_WRITE_TEST: Final[str] = "tests/test_fastapi_p2_reconciliation_write.py"
P2_CLOSING_WRITE_TEST: Final[str] = "tests/test_fastapi_p2_closing_write.py"

BANK_ACCOUNTS_LIST_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/bank-accounts",
)

WORKERS_LIST_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/workers",
)

PARTNERS_LIST_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/partners",
)

BANK_STATEMENT_ROWS_LIST_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/bank-statement-rows",
)

FISCAL_PERIODS_LIST_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/fiscal-periods",
)

VENDORS_LIST_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/vendors",
)

RECEIVABLE_SALES_LIST_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/receivable-sales",
)

PROFIT_ALLOCATIONS_LIST_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/profit-allocations",
)

WRITE_PICKER_READ_API_PATHS: tuple[str, ...] = (
    *BANK_ACCOUNTS_LIST_READ_API_PATHS,
    *WORKERS_LIST_READ_API_PATHS,
    *PARTNERS_LIST_READ_API_PATHS,
    *BANK_STATEMENT_ROWS_LIST_READ_API_PATHS,
    *FISCAL_PERIODS_LIST_READ_API_PATHS,
    *VENDORS_LIST_READ_API_PATHS,
    *RECEIVABLE_SALES_LIST_READ_API_PATHS,
    *PROFIT_ALLOCATIONS_LIST_READ_API_PATHS,
)

WRITE_PICKER_FRONTEND_FILES: tuple[str, ...] = (
    "frontend/src/components/BankAccountPicker.tsx",
    "frontend/src/components/WorkerPicker.tsx",
    "frontend/src/components/PartnerPicker.tsx",
    "frontend/src/components/StatementRowPicker.tsx",
    "frontend/src/components/FiscalPeriodPicker.tsx",
    "frontend/src/components/VendorPicker.tsx",
    "frontend/src/components/CoaAccountPicker.tsx",
    "frontend/src/components/ReceivableSalePicker.tsx",
    "frontend/src/components/ProfitAllocationPicker.tsx",
)

REQUIRED_FRONTEND_FILES: tuple[str, ...] = (
    "frontend/src/config/featureFlags.ts",
    "frontend/src/lib/api/writeClient.ts",
    "frontend/src/pages/NewTransactionPage.tsx",
    *WRITE_PICKER_FRONTEND_FILES,
)

# FR-08 cash only; FR-09 cash expense; FR-10 adds Card/Credit + Bank.
ALLOWED_SALE_PAYMENT_METHODS: tuple[str, ...] = ("Cash", "Card", "Credit")
ALLOWED_EXPENSE_PAYMENT_METHODS: tuple[str, ...] = ("Cash", "Bank")
ALLOWED_PURCHASE_PAYMENT_METHODS: tuple[str, ...] = ("Cash", "Bank", "Credit")
ALLOWED_RECEIVABLE_PAYMENT_METHODS: tuple[str, ...] = ("Cash", "Bank")
ALLOWED_BANK_TRANSACTION_TYPES: tuple[str, ...] = ("deposit", "withdrawal", "transfer")
ALLOWED_PARTNER_MOVEMENT_TYPES: tuple[str, ...] = (
    "CapitalContribution",
    "Drawing",
    "Salary",
    "Advance",
    "Repayment",
    "AdvanceOffset",
)
ALLOWED_WORKER_MOVEMENT_TYPES: tuple[str, ...] = ("Salary", "Advance", "Repayment")
ALLOWED_RECONCILIATION_MATCH_TYPES: tuple[str, ...] = (
    "generic_deposit",
    "bank_charge",
    "deposit_clearing",
    "vendor_outflow",
    "partner",
    "worker",
    "equity",
    "cc_bill_payment",
)
CLOSING_WRITE_ACTIONS: tuple[str, ...] = (
    "close_period",
    "profit_allocation",
    "void_allocation",
)

SALE_PAYMENT_OPTIONAL_FIELDS: tuple[str, ...] = (
    "customer_name",
    "card_bank_account_id",
)

EXPENSE_PAYMENT_OPTIONAL_FIELDS: tuple[str, ...] = (
    "bank_account_id",
)

PURCHASE_PAYMENT_OPTIONAL_FIELDS: tuple[str, ...] = (
    "vendor_name",
    "category_name",
    "subcategory_name",
    "bank_account_id",
)

RECEIVABLE_PAYMENT_OPTIONAL_FIELDS: tuple[str, ...] = (
    "customer_name",
    "bank_account_id",
)

BANK_TRANSACTION_OPTIONAL_FIELDS: tuple[str, ...] = (
    "destination_bank_account_id",
    "currency",
)

PARTNER_MOVEMENT_OPTIONAL_FIELDS: tuple[str, ...] = (
    "bank_account_id",
    "notes",
)

WORKER_PAYMENT_OPTIONAL_FIELDS: tuple[str, ...] = (
    "deductions",
    "advance_recovery",
    "pay_period",
    "notes",
)

RECONCILIATION_MATCH_OPTIONAL_FIELDS: tuple[str, ...] = (
    "credit_account_name",
    "charge_subtype",
)

CLOSING_OPTIONAL_FIELDS: tuple[str, ...] = (
    "notes",
)

FORBIDDEN_FRONTEND_PATTERNS: tuple[str, ...] = (
    "create_journal_entry",
    "post_cash_sale",
    "services/posting",
    "streamlit",
    "apiPut",
    "apiDelete",
    "apiPatch",
)

# apiPost allowed only in WRITE_CLIENT_MODULE (enforced by tests).
WRITE_METHOD_NAME: Final[str] = "apiPost"

# Frozen for FR-08 audit tests (do not mutate).
FR08_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-09",
    "card sale form",
    "credit sale form",
    "expense write page",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-09 audit tests (do not mutate).
FR09_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-10",
    "card sale form",
    "credit sale form",
    "bank expense payment",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-10 audit tests (do not mutate).
FR10_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-11",
    "void write page",
    "purchase write page",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-11 audit tests (do not mutate).
FR11_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-12",
    "purchase write page",
    "receivable payment write",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-12 audit tests (do not mutate).
FR12_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-13",
    "receivable payment write",
    "bank account picker",
    "vendor picker",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-13 audit tests (do not mutate).
FR13_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-14",
    "bank transaction write",
    "receivable sale picker",
    "bank account picker",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-14 audit tests (do not mutate).
FR14_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-15",
    "partner movement write",
    "worker payment write",
    "bank account picker",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-15 audit tests (do not mutate).
FR15_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-16",
    "reconciliation write",
    "closing write",
    "partner picker",
    "worker picker",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-16 audit tests (do not mutate).
FR16_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-17",
    "full match-type payload forms",
    "statement row picker",
    "fiscal period picker",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-21 audit tests (write contract; do not mutate).
FR21_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-22",
    "bank account picker",
    "worker picker",
    "partner picker on write tab",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-22 audit tests (write contract; do not mutate).
FR22_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-23",
    "full match-type payload forms",
    "statement row picker",
    "fiscal period picker",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-23 audit tests (write contract; do not mutate).
FR23_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-24",
    "receivable sale picker",
    "allocation id picker",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-24 audit tests (write contract; do not mutate).
FR24_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-25",
    "production COMMIT_MODE_* flip",
)

DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-35",
    "production COMMIT_MODE_* flip",
)
