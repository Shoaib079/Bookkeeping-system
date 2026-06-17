"""FASTAPI-REACT-04 — commit boundary characterization contract (TD-PS-01).

Maps posting families to dual-run characterization tests. Production flip stays
``internal`` until operator-approved ``COMMIT_MODE_*`` rollout (FR-05+).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from services import commit_modes as cm

CONTRACT_DOC: Final[str] = "docs/FASTAPI_REACT_04_READ_API_BOUNDARY_AUDIT.md"
SCAFFOLD_TEST: Final[str] = "tests/test_fastapi_p0_commit_ownership_scaffold.py"

BOUNDARY_READY_WRITE_MODULES: tuple[str, ...] = (
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
class CommitFamilySpec:
    family: str
    characterization_test: str


COMMIT_FAMILY_CHARACTERIZATION: tuple[CommitFamilySpec, ...] = (
    CommitFamilySpec(cm.POST_CASH_SALE_FAMILY, "tests/test_fastapi_p0_commit_ownership_cash_sale.py"),
    CommitFamilySpec(cm.POST_EXPENSE_FAMILY, "tests/test_fastapi_p0_commit_ownership_expense.py"),
    CommitFamilySpec(
        cm.POST_PURCHASE_FAMILY,
        "tests/test_fastapi_p0_commit_ownership_purchase_payable.py",
    ),
    CommitFamilySpec(
        cm.POST_PAYABLE_PAYMENT_FAMILY,
        "tests/test_fastapi_p0_commit_ownership_purchase_payable.py",
    ),
    CommitFamilySpec(
        cm.POST_RECEIVABLE_PAYMENT_FAMILY,
        "tests/test_fastapi_p0_commit_ownership_receivable_payment.py",
    ),
    CommitFamilySpec(
        cm.POST_BANK_TRANSACTION_FAMILY,
        "tests/test_fastapi_p0_commit_ownership_scaffold.py",
    ),
    CommitFamilySpec(
        cm.POST_PARTNER_MOVEMENT_FAMILY,
        "tests/test_fastapi_p0_commit_ownership_movements.py",
    ),
    CommitFamilySpec(
        cm.POST_WORKER_MOVEMENT_FAMILY,
        "tests/test_fastapi_p0_commit_ownership_movements.py",
    ),
    CommitFamilySpec(
        cm.POST_EQUITY_MOVEMENT_FAMILY,
        "tests/test_fastapi_p0_commit_ownership_scaffold.py",
    ),
    CommitFamilySpec(
        cm.PROFIT_ALLOCATION_FAMILY,
        "tests/test_fastapi_p0_commit_ownership_close_allocation.py",
    ),
    CommitFamilySpec(
        cm.PERIOD_CLOSE_FAMILY,
        "tests/test_fastapi_p0_commit_ownership_close_allocation.py",
    ),
    CommitFamilySpec(
        cm.YEAR_END_CLOSE_FAMILY,
        "tests/test_fastapi_p0_commit_ownership_close_allocation.py",
    ),
    CommitFamilySpec(
        cm.RECONCILIATION_FAMILY,
        "tests/test_fastapi_p0_commit_ownership_reconciliation.py",
    ),
    CommitFamilySpec(
        cm.VOID_CASCADE_FAMILY,
        "tests/test_fastapi_p0_commit_ownership_voids.py",
    ),
)

ALL_BOUNDARY_FAMILIES: tuple[str, ...] = tuple(spec.family for spec in COMMIT_FAMILY_CHARACTERIZATION)
