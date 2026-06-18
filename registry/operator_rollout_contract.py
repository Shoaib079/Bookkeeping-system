"""Operator rollout contract — post PH-05 staging flag sequence.

Machine-readable mirror of operator rollout audit docs under ``docs/OPERATOR_ROLLOUT_*``.
Follows PH-03/PH-04 runbooks; does not change accounting, GL, or posting math.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

ROLLOUT_AUTHORITY_DOC: Final[str] = (
    "docs/PRODUCTION_HARDENING_01_PH05_LAUNCH_READINESS_AUDIT.md"
)
STAGING_CONFIG_DIR: Final[str] = "config/staging"
STAGING_FRONTEND_ENV: Final[str] = "config/staging/frontend.env.example"
STAGING_API_ENV: Final[str] = "config/staging/api.env.example"
STAGING_README: Final[str] = "config/staging/README.md"

LAUNCH_GATE_CONTRACT: Final[str] = "registry/launch_readiness_gate_contract.py"
COMMIT_ROLLOUT_CONTRACT: Final[str] = "registry/commit_mode_rollout_contract.py"
PG_MATRIX_CONTRACT: Final[str] = "registry/pg_matrix_execution_contract.py"
REACT_PAGES_CONTRACT: Final[str] = "registry/react_pages_contract.py"
REACT_WRITE_CONTRACT: Final[str] = "registry/react_write_contract.py"


@dataclass(frozen=True, slots=True)
class OperatorRolloutStage:
    stage_id: str
    tag: str
    audit_doc: str
    gate_test: str
    staging_env_keys: tuple[str, ...]
    pytest_gate_commands: tuple[str, ...]


# Approved staging sequence (Operator Rollout Readiness Audit § Suggested staging sequence).
ROLLOUT_STAGES: tuple[OperatorRolloutStage, ...] = (
    OperatorRolloutStage(
        "OPERATOR-ROLLOUT-OR01",
        "operator-rollout-or01-react-read-staging",
        "docs/OPERATOR_ROLLOUT_OR01_REACT_READ_STAGING.md",
        "tests/test_operator_rollout_or01_react_read_staging.py",
        ("VITE_ERP_REACT_PAGES=1",),
        (
            "pytest tests/test_operator_rollout_or01_react_read_staging.py -q",
            "pytest tests/test_fastapi_react_06_react_pages.py -q",
            "pytest tests/ -q",
        ),
    ),
    OperatorRolloutStage(
        "OPERATOR-ROLLOUT-OR02",
        "operator-rollout-or02-pg-matrix-staging",
        "docs/OPERATOR_ROLLOUT_OR02_PG_MATRIX_STAGING.md",
        "tests/test_operator_rollout_or02_pg_matrix_staging.py",
        ("ERP_TEST_POSTGRES_URL",),
        (
            "pytest tests/test_fastapi_react_07_pg_boundary_matrix.py",
            "tests/test_production_hardening_01_ph03_pg_matrix_execution.py",
            "-m optional_postgres -q",
        ),
    ),
    OperatorRolloutStage(
        "OPERATOR-ROLLOUT-OR03",
        "operator-rollout-or03-api-write-sales-staging",
        "docs/OPERATOR_ROLLOUT_OR03_API_WRITE_SALES_STAGING.md",
        "tests/test_operator_rollout_or03_api_write_sales_staging.py",
        ("ERP_API_WRITE_SALES=1", "VITE_ERP_REACT_WRITE_SALES=1"),
        (
            "pytest tests/test_fastapi_p2_sales_write.py -q",
            "pytest tests/test_fastapi_react_08_react_write.py -q",
            "pytest tests/ -q",
        ),
    ),
    OperatorRolloutStage(
        "OPERATOR-ROLLOUT-OR04",
        "operator-rollout-or04-commit-mode-cash-sale-staging",
        "docs/OPERATOR_ROLLOUT_OR04_COMMIT_MODE_CASH_SALE_STAGING.md",
        "tests/test_operator_rollout_or04_commit_mode_cash_sale_staging.py",
        ("COMMIT_MODE_POST_CASH_SALE=boundary",),
        (
            "pytest tests/test_fastapi_p0_commit_ownership_cash_sale.py -q",
            "pytest tests/ -q",
        ),
    ),
    OperatorRolloutStage(
        "OPERATOR-ROLLOUT-OR05",
        "operator-rollout-or05-commit-mode-expense-staging",
        "docs/OPERATOR_ROLLOUT_OR05_COMMIT_MODE_EXPENSE_STAGING.md",
        "tests/test_operator_rollout_or05_commit_mode_expense_staging.py",
        ("COMMIT_MODE_POST_EXPENSE=boundary",),
        (
            "pytest tests/test_fastapi_p0_commit_ownership_expense.py -q",
            "pytest tests/ -q",
        ),
    ),
    OperatorRolloutStage(
        "OPERATOR-ROLLOUT-OR06",
        "operator-rollout-or06-commit-mode-purchase-staging",
        "docs/OPERATOR_ROLLOUT_OR06_COMMIT_MODE_PURCHASE_STAGING.md",
        "tests/test_operator_rollout_or06_commit_mode_purchase_staging.py",
        (
            "COMMIT_MODE_POST_PURCHASE=boundary",
            "COMMIT_MODE_POST_PAYABLE_PAYMENT=boundary",
        ),
        (
            "pytest tests/test_fastapi_p0_commit_ownership_purchase_payable.py -q",
            "pytest tests/ -q",
        ),
    ),
    OperatorRolloutStage(
        "OPERATOR-ROLLOUT-OR07",
        "operator-rollout-or07-commit-mode-receivable-bank-staging",
        "docs/OPERATOR_ROLLOUT_OR07_COMMIT_MODE_RECEIVABLE_BANK_STAGING.md",
        "tests/test_operator_rollout_or07_commit_mode_receivable_bank_staging.py",
        (
            "COMMIT_MODE_POST_RECEIVABLE_PAYMENT=boundary",
            "COMMIT_MODE_BANK_TRANSACTION=boundary",
        ),
        (
            "pytest tests/test_fastapi_p0_commit_ownership_receivable_payment.py -q",
            "pytest tests/test_fastapi_p0_commit_ownership_banking.py -q",
            "pytest tests/ -q",
        ),
    ),
    OperatorRolloutStage(
        "OPERATOR-ROLLOUT-OR08",
        "operator-rollout-or08-commit-mode-movements-staging",
        "docs/OPERATOR_ROLLOUT_OR08_COMMIT_MODE_MOVEMENTS_STAGING.md",
        "tests/test_operator_rollout_or08_commit_mode_movements_staging.py",
        (
            "COMMIT_MODE_POST_PARTNER_MOVEMENT=boundary",
            "COMMIT_MODE_POST_WORKER_MOVEMENT=boundary",
            "COMMIT_MODE_POST_EQUITY_MOVEMENT=boundary",
        ),
        ("pytest tests/test_fastapi_p0_commit_ownership_movements.py -q", "pytest tests/ -q"),
    ),
    OperatorRolloutStage(
        "OPERATOR-ROLLOUT-OR09",
        "operator-rollout-or09-commit-mode-closing-staging",
        "docs/OPERATOR_ROLLOUT_OR09_COMMIT_MODE_CLOSING_STAGING.md",
        "tests/test_operator_rollout_or09_commit_mode_closing_staging.py",
        (
            "COMMIT_MODE_PROFIT_ALLOCATION=boundary",
            "COMMIT_MODE_PERIOD_CLOSE=boundary",
            "COMMIT_MODE_YEAR_END_CLOSE=boundary",
        ),
        (
            "pytest tests/test_fastapi_p0_commit_ownership_close_allocation.py -q",
            "pytest tests/ -q",
        ),
    ),
    OperatorRolloutStage(
        "OPERATOR-ROLLOUT-OR10",
        "operator-rollout-or10-commit-mode-reconciliation-staging",
        "docs/OPERATOR_ROLLOUT_OR10_COMMIT_MODE_RECONCILIATION_STAGING.md",
        "tests/test_operator_rollout_or10_commit_mode_reconciliation_staging.py",
        ("COMMIT_MODE_RECONCILIATION=boundary",),
        (
            "pytest tests/test_fastapi_p0_commit_ownership_reconciliation.py -q",
            "pytest tests/ -q",
        ),
    ),
    OperatorRolloutStage(
        "OPERATOR-ROLLOUT-OR11",
        "operator-rollout-or11-commit-mode-void-staging",
        "docs/OPERATOR_ROLLOUT_OR11_COMMIT_MODE_VOID_STAGING.md",
        "tests/test_operator_rollout_or11_commit_mode_void_staging.py",
        ("COMMIT_MODE_VOID_CASCADE=boundary",),
        ("pytest tests/test_fastapi_p0_commit_ownership_voids.py -q", "pytest tests/ -q"),
    ),
)

# Frozen for OR-01 audit tests (do not mutate).
OR01_DEFERRED_ITEMS: tuple[str, ...] = (
    "OPERATOR-ROLLOUT-OR02",
    "production operator sign-off",
    "production COMMIT_MODE_* flip",
)

# Frozen for OR-02 audit tests (do not mutate).
OR02_DEFERRED_ITEMS: tuple[str, ...] = (
    "OPERATOR-ROLLOUT-OR03",
    "production operator sign-off",
    "production COMMIT_MODE_* flip",
)

# Frozen for OR-03 audit tests (do not mutate).
OR03_DEFERRED_ITEMS: tuple[str, ...] = (
    "OPERATOR-ROLLOUT-OR04",
    "production operator sign-off",
    "production COMMIT_MODE_* flip",
)

OR03_WRITE_FLAGS_ENABLED: tuple[str, ...] = (
    "VITE_ERP_REACT_WRITE_SALES=1",
    "ERP_API_WRITE_SALES=1",
)

# Frozen for OR-04 audit tests (do not mutate).
OR04_DEFERRED_ITEMS: tuple[str, ...] = (
    "OPERATOR-ROLLOUT-OR05",
    "production operator sign-off",
    "production COMMIT_MODE_* flip",
)

OR04_COMMIT_MODE_ENABLED: tuple[str, ...] = ("COMMIT_MODE_POST_CASH_SALE=boundary",)

OR04_P0_GATE_TEST: Final[str] = (
    "tests/test_fastapi_p0_commit_ownership_cash_sale.py"
)

# Frozen for OR-04 audit tests (do not mutate).
OR04_STILL_COMMENTED_COMMIT_MODES: tuple[str, ...] = (
    "COMMIT_MODE_POST_EXPENSE",
    "COMMIT_MODE_POST_PURCHASE",
    "COMMIT_MODE_POST_PAYABLE_PAYMENT",
    "COMMIT_MODE_POST_RECEIVABLE_PAYMENT",
    "COMMIT_MODE_BANK_TRANSACTION",
    "COMMIT_MODE_POST_PARTNER_MOVEMENT",
    "COMMIT_MODE_POST_WORKER_MOVEMENT",
    "COMMIT_MODE_POST_EQUITY_MOVEMENT",
    "COMMIT_MODE_PROFIT_ALLOCATION",
    "COMMIT_MODE_PERIOD_CLOSE",
    "COMMIT_MODE_YEAR_END_CLOSE",
    "COMMIT_MODE_RECONCILIATION",
    "COMMIT_MODE_VOID_CASCADE",
)

# Frozen for OR-05 audit tests (do not mutate).
OR05_DEFERRED_ITEMS: tuple[str, ...] = (
    "OPERATOR-ROLLOUT-OR06",
    "production operator sign-off",
    "production COMMIT_MODE_* flip",
)

OR05_COMMIT_MODE_ENABLED: tuple[str, ...] = ("COMMIT_MODE_POST_EXPENSE=boundary",)

OR05_CUMULATIVE_COMMIT_MODES_ENABLED: tuple[str, ...] = (
    "COMMIT_MODE_POST_CASH_SALE=boundary",
    "COMMIT_MODE_POST_EXPENSE=boundary",
)

OR05_P0_GATE_TEST: Final[str] = (
    "tests/test_fastapi_p0_commit_ownership_expense.py"
)

OR05_STILL_COMMENTED_COMMIT_MODES: tuple[str, ...] = (
    "COMMIT_MODE_POST_PURCHASE",
    "COMMIT_MODE_POST_PAYABLE_PAYMENT",
    "COMMIT_MODE_POST_RECEIVABLE_PAYMENT",
    "COMMIT_MODE_BANK_TRANSACTION",
    "COMMIT_MODE_POST_PARTNER_MOVEMENT",
    "COMMIT_MODE_POST_WORKER_MOVEMENT",
    "COMMIT_MODE_POST_EQUITY_MOVEMENT",
    "COMMIT_MODE_PROFIT_ALLOCATION",
    "COMMIT_MODE_PERIOD_CLOSE",
    "COMMIT_MODE_YEAR_END_CLOSE",
    "COMMIT_MODE_RECONCILIATION",
    "COMMIT_MODE_VOID_CASCADE",
)

# Frozen for OR-06 audit tests (do not mutate).
OR06_DEFERRED_ITEMS: tuple[str, ...] = (
    "OPERATOR-ROLLOUT-OR07",
    "production operator sign-off",
    "production COMMIT_MODE_* flip",
)

OR06_CUMULATIVE_COMMIT_MODES_ENABLED: tuple[str, ...] = (
    "COMMIT_MODE_POST_CASH_SALE=boundary",
    "COMMIT_MODE_POST_EXPENSE=boundary",
    "COMMIT_MODE_POST_PURCHASE=boundary",
    "COMMIT_MODE_POST_PAYABLE_PAYMENT=boundary",
)

OR06_P0_GATE_TEST: Final[str] = (
    "tests/test_fastapi_p0_commit_ownership_purchase_payable.py"
)

OR06_STILL_COMMENTED_COMMIT_MODES: tuple[str, ...] = (
    "COMMIT_MODE_POST_RECEIVABLE_PAYMENT",
    "COMMIT_MODE_BANK_TRANSACTION",
    "COMMIT_MODE_POST_PARTNER_MOVEMENT",
    "COMMIT_MODE_POST_WORKER_MOVEMENT",
    "COMMIT_MODE_POST_EQUITY_MOVEMENT",
    "COMMIT_MODE_PROFIT_ALLOCATION",
    "COMMIT_MODE_PERIOD_CLOSE",
    "COMMIT_MODE_YEAR_END_CLOSE",
    "COMMIT_MODE_RECONCILIATION",
    "COMMIT_MODE_VOID_CASCADE",
)

OR07_DEFERRED_ITEMS: tuple[str, ...] = (
    "OPERATOR-ROLLOUT-OR08",
    "production operator sign-off",
    "production COMMIT_MODE_* flip",
)

OR07_CUMULATIVE_COMMIT_MODES_ENABLED: tuple[str, ...] = (
    *OR06_CUMULATIVE_COMMIT_MODES_ENABLED,
    "COMMIT_MODE_POST_RECEIVABLE_PAYMENT=boundary",
    "COMMIT_MODE_BANK_TRANSACTION=boundary",
)

OR07_P0_GATE_TESTS: tuple[str, ...] = (
    "tests/test_fastapi_p0_commit_ownership_receivable_payment.py",
    "tests/test_fastapi_p0_commit_ownership_banking.py",
)

OR07_STILL_COMMENTED_COMMIT_MODES: tuple[str, ...] = (
    "COMMIT_MODE_POST_PARTNER_MOVEMENT",
    "COMMIT_MODE_POST_WORKER_MOVEMENT",
    "COMMIT_MODE_POST_EQUITY_MOVEMENT",
    "COMMIT_MODE_PROFIT_ALLOCATION",
    "COMMIT_MODE_PERIOD_CLOSE",
    "COMMIT_MODE_YEAR_END_CLOSE",
    "COMMIT_MODE_RECONCILIATION",
    "COMMIT_MODE_VOID_CASCADE",
)

OR08_DEFERRED_ITEMS: tuple[str, ...] = (
    "OPERATOR-ROLLOUT-OR09",
    "production operator sign-off",
    "production COMMIT_MODE_* flip",
)

OR08_CUMULATIVE_COMMIT_MODES_ENABLED: tuple[str, ...] = (
    *OR07_CUMULATIVE_COMMIT_MODES_ENABLED,
    "COMMIT_MODE_POST_PARTNER_MOVEMENT=boundary",
    "COMMIT_MODE_POST_WORKER_MOVEMENT=boundary",
    "COMMIT_MODE_POST_EQUITY_MOVEMENT=boundary",
)

OR08_P0_GATE_TEST: Final[str] = (
    "tests/test_fastapi_p0_commit_ownership_movements.py"
)

OR08_STILL_COMMENTED_COMMIT_MODES: tuple[str, ...] = (
    "COMMIT_MODE_PROFIT_ALLOCATION",
    "COMMIT_MODE_PERIOD_CLOSE",
    "COMMIT_MODE_YEAR_END_CLOSE",
    "COMMIT_MODE_RECONCILIATION",
    "COMMIT_MODE_VOID_CASCADE",
)

OR09_DEFERRED_ITEMS: tuple[str, ...] = (
    "OPERATOR-ROLLOUT-OR10",
    "production operator sign-off",
    "production COMMIT_MODE_* flip",
)

OR09_CUMULATIVE_COMMIT_MODES_ENABLED: tuple[str, ...] = (
    *OR08_CUMULATIVE_COMMIT_MODES_ENABLED,
    "COMMIT_MODE_PROFIT_ALLOCATION=boundary",
    "COMMIT_MODE_PERIOD_CLOSE=boundary",
    "COMMIT_MODE_YEAR_END_CLOSE=boundary",
)

OR09_P0_GATE_TEST: Final[str] = (
    "tests/test_fastapi_p0_commit_ownership_close_allocation.py"
)

OR09_STILL_COMMENTED_COMMIT_MODES: tuple[str, ...] = (
    "COMMIT_MODE_RECONCILIATION",
    "COMMIT_MODE_VOID_CASCADE",
)

OR10_DEFERRED_ITEMS: tuple[str, ...] = (
    "OPERATOR-ROLLOUT-OR11",
    "production operator sign-off",
    "production COMMIT_MODE_* flip",
)

OR10_CUMULATIVE_COMMIT_MODES_ENABLED: tuple[str, ...] = (
    *OR09_CUMULATIVE_COMMIT_MODES_ENABLED,
    "COMMIT_MODE_RECONCILIATION=boundary",
)

OR10_P0_GATE_TEST: Final[str] = (
    "tests/test_fastapi_p0_commit_ownership_reconciliation.py"
)

OR10_STILL_COMMENTED_COMMIT_MODES: tuple[str, ...] = ("COMMIT_MODE_VOID_CASCADE",)

OR11_DEFERRED_ITEMS: tuple[str, ...] = (
    "production operator sign-off",
    "production COMMIT_MODE_* flip",
)

OR11_CUMULATIVE_COMMIT_MODES_ENABLED: tuple[str, ...] = (
    *OR10_CUMULATIVE_COMMIT_MODES_ENABLED,
    "COMMIT_MODE_VOID_CASCADE=boundary",
)

OR11_P0_GATE_TEST: Final[str] = "tests/test_fastapi_p0_commit_ownership_voids.py"

OR11_STILL_COMMENTED_COMMIT_MODES: tuple[str, ...] = ()
