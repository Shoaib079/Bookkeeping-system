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
)

HOME_READ_API_PATHS: tuple[str, ...] = (
    "/auth/me",
    "/auth/companies",
    "/api/v1/reports/profit-loss",
)

LEDGER_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/ledger",
)

REQUIRED_FRONTEND_FILES: tuple[str, ...] = (
    "frontend/src/config/featureFlags.ts",
    "frontend/src/lib/api/session.ts",
    "frontend/src/lib/api/types.ts",
    "frontend/src/pages/HomePage.tsx",
    "frontend/src/pages/LedgerPage.tsx",
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

DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-14",
    "TD-PS-01",
    "chart-of-accounts picker",
)
