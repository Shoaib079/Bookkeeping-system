"""FASTAPI-REACT-06 — frozen first React pages contract.

Machine-readable mirror of ``docs/FASTAPI_REACT_06_REACT_PAGES_AUDIT.md``.
"""

from __future__ import annotations

from typing import Final

CONTRACT_DOC: Final[str] = "docs/FASTAPI_REACT_06_REACT_PAGES_AUDIT.md"
BOOTSTRAP_CONTRACT: Final[str] = "registry/react_bootstrap_contract.py"
READ_CONTRACT: Final[str] = "registry/api_read_contract.py"

# Operator / build-time gate — default off; PlaceholderPage remains for gated routes.
FEATURE_FLAG_ENV: Final[str] = "ERP_REACT_PAGES"
VITE_FEATURE_FLAG_ENV: Final[str] = "VITE_ERP_REACT_PAGES"

# (react_path, page_component, page_key)
REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/", "HomePage", "home"),
    ("/books/general-ledger", "LedgerPage", "ledger"),
    ("/reports/balance-sheet", "BalanceSheetPage", "balance_sheet"),
    ("/receivables", "ReceivablesPage", "receivables"),
    ("/payables", "PayablesPage", "payables"),
    ("/partners", "PartnerStatementPage", "partners"),
    ("/banking", "BankingReadinessPage", "banking"),
    ("/reports", "ReportsPage", "reports"),
    ("/reports/profit-loss", "ProfitLossPage", "profit_loss"),
)

HOME_READ_API_PATHS: tuple[str, ...] = (
    "/auth/me",
    "/auth/companies",
    "/api/v1/reports/profit-loss",
)

LEDGER_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/ledger",
)

BALANCE_SHEET_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/reports/balance-sheet",
)

RECEIVABLES_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/receivables",
)

PAYABLES_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/payables",
)

PARTNER_STATEMENT_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/partners/{partner_id}/statement",
)

BANKING_READINESS_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/banking/readiness",
)

REPORTS_HUB_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/reports/profit-loss",
)

PROFIT_LOSS_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/reports/profit-loss",
)

REQUIRED_FRONTEND_FILES: tuple[str, ...] = (
    "frontend/src/config/featureFlags.ts",
    "frontend/src/lib/api/session.ts",
    "frontend/src/lib/api/types.ts",
    "frontend/src/pages/HomePage.tsx",
    "frontend/src/pages/LedgerPage.tsx",
    "frontend/src/pages/BalanceSheetPage.tsx",
    "frontend/src/pages/ReceivablesPage.tsx",
    "frontend/src/pages/PayablesPage.tsx",
    "frontend/src/pages/PartnerStatementPage.tsx",
    "frontend/src/pages/BankingReadinessPage.tsx",
    "frontend/src/pages/ReportsPage.tsx",
    "frontend/src/pages/ProfitLossPage.tsx",
    "frontend/src/components/ReadApiSetup.tsx",
)

FORBIDDEN_FRONTEND_PATTERNS: tuple[str, ...] = (
    "create_journal_entry",
    "post_cash_sale",
    "services/posting",
    "streamlit",
    "apiPut",
    "apiDelete",
)

# Frozen for FR-06 audit tests (do not mutate).
FR06_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/", "HomePage", "home"),
    ("/books/general-ledger", "LedgerPage", "ledger"),
)

FR06_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-17",
    "TD-PS-01",
    "chart-of-accounts picker",
)

# Frozen for FR-17 audit tests (do not mutate).
FR17_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/reports/balance-sheet", "BalanceSheetPage", "balance_sheet"),
    ("/receivables", "ReceivablesPage", "receivables"),
    ("/payables", "PayablesPage", "payables"),
)

FR17_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-18",
    "partner statement page",
    "banking readiness page",
    "chart-of-accounts picker",
)

# Frozen for FR-18 audit tests (do not mutate).
FR18_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-19",
    "chart-of-accounts picker",
    "partner picker",
    "transaction ledger read page",
)

FR18_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/partners", "PartnerStatementPage", "partners"),
    ("/banking", "BankingReadinessPage", "banking"),
)

DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-20",
    "transaction ledger read page",
    "cash flow read page",
    "chart-of-accounts picker",
)

# Frozen for FR-19 audit tests (do not mutate).
FR19_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/reports", "ReportsPage", "reports"),
    ("/reports/profit-loss", "ProfitLossPage", "profit_loss"),
)
