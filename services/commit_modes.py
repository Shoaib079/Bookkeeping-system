"""FASTAPI-P0.5d-S0 — per-family commit ownership mode (scaffolding only).

All families default to ``internal`` (legacy kernel + audit commit points).
Boundary mode is reserved for future family-by-family flips (TD-PS-01).
"""

from __future__ import annotations

from enum import Enum

# Sequencing order from FASTAPI_P0_5D_COMMIT_OWNERSHIP_PLAN.md §4 (safest → riskiest).
POSTING_FAMILIES: tuple[str, ...] = (
    "sale",
    "expense",
    "purchase_payable",
    "receivable_payment",
    "bank_transaction",
    "partner_worker_equity",
    "profit_allocation",
    "period_year_end_close",
    "reconciliation",
    "void",
)

AUDIT_FAMILY = "audit"


class CommitMode(str, Enum):
    INTERNAL = "internal"
    BOUNDARY = "boundary"


_DEFAULT_MODES: dict[str, CommitMode] = {
    family: CommitMode.INTERNAL for family in (*POSTING_FAMILIES, AUDIT_FAMILY)
}

# Test-only overrides — not read by posting/audit paths in P0.5d-S0.
_test_overrides: dict[str, CommitMode] = {}


def get_commit_mode(family: str) -> CommitMode:
    """Return commit mode for a posting/audit family (default: internal)."""
    if family in _test_overrides:
        return _test_overrides[family]
    return _DEFAULT_MODES.get(family, CommitMode.INTERNAL)


def is_boundary_mode(family: str) -> bool:
    return get_commit_mode(family) == CommitMode.BOUNDARY


def set_commit_mode_for_tests(family: str, mode: CommitMode) -> None:
    """Test harness hook — production paths do not call this in P0.5d-S0."""
    _test_overrides[family] = mode


def reset_commit_modes_for_tests() -> None:
    _test_overrides.clear()


__all__ = (
    "AUDIT_FAMILY",
    "CommitMode",
    "POSTING_FAMILIES",
    "get_commit_mode",
    "is_boundary_mode",
    "reset_commit_modes_for_tests",
    "set_commit_mode_for_tests",
)
