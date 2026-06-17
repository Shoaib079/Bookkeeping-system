"""FASTAPI-REACT-03 — reconciliation boundary contract (no lazy ``import app``).

Machine-readable mirror of ``docs/FASTAPI_REACT_03_RECON_BOUNDARY_AUDIT.md``.
"""

from __future__ import annotations

from typing import Final

CONTRACT_DOC: Final[str] = "docs/FASTAPI_REACT_03_RECON_BOUNDARY_AUDIT.md"

RECON_MODULES: tuple[str, ...] = (
    "reconciliation/match_post.py",
    "reconciliation/company_card.py",
)

FORBIDDEN_PATTERNS: tuple[str, ...] = (
    r"def _app\(",
    r"import app\b",
    r"from app import",
    r"app\.get_account_by_name",
    r"app\.calculate_account_balance",
    r"app\.get_worker_advance_balance",
    r"app\.create_journal_entry",
)

REQUIRED_SERVICE_IMPORTS: tuple[str, ...] = (
    "services.posting",
    "services.banking_balance",
    "services.read_balances",
)

DEFERRED_GAP_IDS: tuple[str, ...] = (
    "TD-PS-01",
    "TD-PS-03",
)

BOUNDARY_READY_MODULES: tuple[str, ...] = (
    "services/write_reconciliation.py",
    "services/write_voids.py",
    "services/write_sales.py",
)
