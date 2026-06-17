"""FASTAPI-REACT-05 — frozen React bootstrap contract.

Machine-readable mirror of ``docs/FASTAPI_REACT_05_REACT_BOOTSTRAP_AUDIT.md``.
"""

from __future__ import annotations

from typing import Final

CONTRACT_DOC: Final[str] = "docs/FASTAPI_REACT_05_REACT_BOOTSTRAP_AUDIT.md"
EXPORT_SCRIPT: Final[str] = "scripts/export_react_bootstrap_assets.py"
DESIGN_CONTRACT: Final[str] = "ui/react_design_contract.py"
NAV_CONTRACT_DOC: Final[str] = "docs/NAV_ARCH_REACT_ROUTE_CONTRACT.md"

FRONTEND_ROOT: Final[str] = "frontend"
PACKAGE_JSON: Final[str] = "frontend/package.json"

REQUIRED_FRONTEND_FILES: tuple[str, ...] = (
    "frontend/package.json",
    "frontend/vite.config.ts",
    "frontend/index.html",
    "frontend/src/main.tsx",
    "frontend/src/App.tsx",
    "frontend/src/theme/ThemeProvider.tsx",
    "frontend/src/routes/AppRouter.tsx",
    "frontend/src/layouts/DesktopShell.tsx",
    "frontend/src/layouts/MobileShell.tsx",
    "frontend/src/layouts/AppShell.tsx",
    "frontend/src/lib/api/client.ts",
    "frontend/src/generated/design-tokens.json",
    "frontend/src/generated/routes.json",
)

REQUIRED_PACKAGE_DEPS: tuple[str, ...] = (
    "react",
    "react-dom",
    "react-router-dom",
)

FORBIDDEN_FRONTEND_PATTERNS: tuple[str, ...] = (
    "create_journal_entry",
    "post_cash_sale",
    "services/posting",
    "streamlit",
)

DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-06",
    "TD-PS-01",
)
