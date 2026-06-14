"""FASTAPI-P0.5d — per-family commit ownership mode (TD-PS-01).

All families default to ``internal`` (legacy kernel + audit commit points).
``post_cash_sale`` is the first family that may flip to ``boundary`` behind a flag.
"""

from __future__ import annotations

import os
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

# Slice 1 — first boundary flip candidate (cash sale GL post + paired audit only).
POST_CASH_SALE_FAMILY = "post_cash_sale"

# Slice 2 — expense GL post + paired audit (Add Transaction expense save boundary).
POST_EXPENSE_FAMILY = "post_expense"

# Slice 3 — purchase GL post + payable row + audit (Add Transaction purchase save boundary).
POST_PURCHASE_FAMILY = "post_purchase"

# Slice 3 — payable payment GL post + state + audit (Add Transaction supplier payment boundary).
POST_PAYABLE_PAYMENT_FAMILY = "post_payable_payment"

# Slice 4 — receivable payment GL post + sale state + audit (Add Transaction customer payment boundary).
POST_RECEIVABLE_PAYMENT_FAMILY = "post_receivable_payment"

AUDIT_FAMILY = "audit"


class CommitMode(str, Enum):
    INTERNAL = "internal"
    BOUNDARY = "boundary"


_DEFAULT_MODES: dict[str, CommitMode] = {
    family: CommitMode.INTERNAL for family in (*POSTING_FAMILIES, AUDIT_FAMILY)
}
_DEFAULT_MODES[POST_CASH_SALE_FAMILY] = CommitMode.INTERNAL
_DEFAULT_MODES[POST_EXPENSE_FAMILY] = CommitMode.INTERNAL
_DEFAULT_MODES[POST_PURCHASE_FAMILY] = CommitMode.INTERNAL
_DEFAULT_MODES[POST_PAYABLE_PAYMENT_FAMILY] = CommitMode.INTERNAL
_DEFAULT_MODES[POST_RECEIVABLE_PAYMENT_FAMILY] = CommitMode.INTERNAL

_test_overrides: dict[str, CommitMode] = {}


def _env_commit_mode(family: str) -> CommitMode | None:
    env_val = os.environ.get(f"COMMIT_MODE_{family.upper()}")
    if env_val == CommitMode.BOUNDARY.value:
        return CommitMode.BOUNDARY
    if env_val == CommitMode.INTERNAL.value:
        return CommitMode.INTERNAL
    return None


def get_commit_mode(family: str) -> CommitMode:
    """Return commit mode for a posting/audit family (default: internal)."""
    if family in _test_overrides:
        return _test_overrides[family]
    env_mode = _env_commit_mode(family)
    if env_mode is not None:
        return env_mode
    return _DEFAULT_MODES.get(family, CommitMode.INTERNAL)


def is_boundary_mode(family: str) -> bool:
    return get_commit_mode(family) == CommitMode.BOUNDARY


def set_commit_mode_for_tests(family: str, mode: CommitMode) -> None:
    """Test/config harness hook — flip a family without code changes."""
    _test_overrides[family] = mode


def reset_commit_modes_for_tests() -> None:
    _test_overrides.clear()


__all__ = (
    "AUDIT_FAMILY",
    "CommitMode",
    "POST_CASH_SALE_FAMILY",
    "POST_EXPENSE_FAMILY",
    "POST_PAYABLE_PAYMENT_FAMILY",
    "POST_PURCHASE_FAMILY",
    "POST_RECEIVABLE_PAYMENT_FAMILY",
    "POSTING_FAMILIES",
    "get_commit_mode",
    "is_boundary_mode",
    "reset_commit_modes_for_tests",
    "set_commit_mode_for_tests",
)
