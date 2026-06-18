"""PRODUCTION-HARDENING-01-PH04 — COMMIT_MODE_* operator rollout contract.

Machine-readable mirror of
``docs/PRODUCTION_HARDENING_01_PH04_COMMIT_MODE_ROLLOUT_AUDIT.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

PH04_CONTRACT_DOC: Final[str] = (
    "docs/PRODUCTION_HARDENING_01_PH04_COMMIT_MODE_ROLLOUT_AUDIT.md"
)
PH04_SLICE_ID: Final[str] = "PRODUCTION-HARDENING-01-PH04"
PH04_TAG: Final[str] = "production-hardening-01-ph04-commit-mode-rollout"
PH04_ROLLOUT_TEST: Final[str] = (
    "tests/test_production_hardening_01_ph04_commit_mode_rollout.py"
)
COMMIT_MODES_MODULE: Final[str] = "services/commit_modes.py"
COMMIT_BOUNDARY_CONTRACT: Final[str] = "registry/commit_boundary_contract.py"

ENV_PREFIX: Final[str] = "COMMIT_MODE_"
VALID_BOUNDARY_VALUE: Final[str] = "boundary"
VALID_INTERNAL_VALUE: Final[str] = "internal"


def commit_mode_env_var(family: str) -> str:
    """Operator env key for a posting family (e.g. ``COMMIT_MODE_POST_CASH_SALE``)."""
    return f"{ENV_PREFIX}{family.upper()}"


@dataclass(frozen=True, slots=True)
class RolloutFamilySpec:
    tier: int
    family: str
    characterization_test: str
    write_module: str | None


# Safest-first rollout order (matches P0.5d sequencing + commit_boundary_contract).
ROLLOUT_FAMILIES: tuple[RolloutFamilySpec, ...] = (
    RolloutFamilySpec(1, "post_cash_sale", "tests/test_fastapi_p0_commit_ownership_cash_sale.py", "services/write_sales.py"),
    RolloutFamilySpec(2, "post_expense", "tests/test_fastapi_p0_commit_ownership_expense.py", "services/write_expenses.py"),
    RolloutFamilySpec(3, "post_purchase", "tests/test_fastapi_p0_commit_ownership_purchase_payable.py", "services/write_purchases.py"),
    RolloutFamilySpec(3, "post_payable_payment", "tests/test_fastapi_p0_commit_ownership_purchase_payable.py", None),
    RolloutFamilySpec(4, "post_receivable_payment", "tests/test_fastapi_p0_commit_ownership_receivable_payment.py", "services/write_receivable_payments.py"),
    RolloutFamilySpec(4, "bank_transaction", "tests/test_fastapi_p0_commit_ownership_banking.py", "services/write_banking.py"),
    RolloutFamilySpec(5, "post_partner_movement", "tests/test_fastapi_p0_commit_ownership_movements.py", "services/write_partner_worker.py"),
    RolloutFamilySpec(5, "post_worker_movement", "tests/test_fastapi_p0_commit_ownership_movements.py", "services/write_partner_worker.py"),
    RolloutFamilySpec(5, "post_equity_movement", "tests/test_fastapi_p0_commit_ownership_movements.py", "services/write_partner_worker.py"),
    RolloutFamilySpec(6, "profit_allocation", "tests/test_fastapi_p0_commit_ownership_close_allocation.py", "services/write_closing.py"),
    RolloutFamilySpec(6, "period_close", "tests/test_fastapi_p0_commit_ownership_close_allocation.py", "services/write_closing.py"),
    RolloutFamilySpec(6, "year_end_close", "tests/test_fastapi_p0_commit_ownership_close_allocation.py", "services/write_closing.py"),
    RolloutFamilySpec(7, "reconciliation", "tests/test_fastapi_p0_commit_ownership_reconciliation.py", "services/write_reconciliation.py"),
    RolloutFamilySpec(8, "void_cascade", "tests/test_fastapi_p0_commit_ownership_voids.py", "services/write_voids.py"),
)

OPERATOR_PREFLIGHT_CHECKLIST: tuple[str, ...] = (
    "pytest tests/",
    "Family P0 characterization test green",
    "Optional PG boundary matrix green",
    "Flip one",
    "Re-run full pytest after each family flip",
    "Rollback:",
    "Never flip production without operator sign-off",
)

OPERATOR_STAGING_EXAMPLE: tuple[str, ...] = (
    "COMMIT_MODE_POST_CASH_SALE=boundary",
    "COMMIT_MODE_POST_EXPENSE=boundary",
)

# Frozen for PH-04 audit tests (do not mutate).
PH04_DEFERRED_ITEMS: tuple[str, ...] = (
    "PRODUCTION-HARDENING-05",
    "production operator sign-off",
    "TD-PS-03",
    "CI optional_postgres job",
)
