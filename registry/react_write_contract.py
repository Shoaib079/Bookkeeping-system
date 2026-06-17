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
API_WRITE_SALES_ENV: Final[str] = "ERP_API_WRITE_SALES"
API_WRITE_EXPENSES_ENV: Final[str] = "ERP_API_WRITE_EXPENSES"

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

WRITE_CLIENT_MODULE: Final[str] = "frontend/src/lib/api/writeClient.ts"
P2_SALES_WRITE_TEST: Final[str] = "tests/test_fastapi_p2_sales_write.py"
P2_EXPENSE_WRITE_TEST: Final[str] = "tests/test_fastapi_p2_expense_write.py"

REQUIRED_FRONTEND_FILES: tuple[str, ...] = (
    "frontend/src/config/featureFlags.ts",
    "frontend/src/lib/api/writeClient.ts",
    "frontend/src/pages/NewTransactionPage.tsx",
)

# FR-08 cash only; FR-09 cash expense; FR-10 adds Card/Credit + Bank.
ALLOWED_SALE_PAYMENT_METHODS: tuple[str, ...] = ("Cash", "Card", "Credit")
ALLOWED_EXPENSE_PAYMENT_METHODS: tuple[str, ...] = ("Cash", "Bank")

SALE_PAYMENT_OPTIONAL_FIELDS: tuple[str, ...] = (
    "customer_name",
    "card_bank_account_id",
)

EXPENSE_PAYMENT_OPTIONAL_FIELDS: tuple[str, ...] = (
    "bank_account_id",
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

DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-11",
    "void write page",
    "purchase write page",
    "production COMMIT_MODE_* flip",
)
