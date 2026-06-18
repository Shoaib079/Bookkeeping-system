"""PRODUCTION-HARDENING-01-PH03 — PostgreSQL matrix execution contract.

Machine-readable mirror of
``docs/PRODUCTION_HARDENING_01_PH03_PG_MATRIX_EXECUTION_AUDIT.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

PH03_CONTRACT_DOC: Final[str] = (
    "docs/PRODUCTION_HARDENING_01_PH03_PG_MATRIX_EXECUTION_AUDIT.md"
)
PH03_SLICE_ID: Final[str] = "PRODUCTION-HARDENING-01-PH03"
PH03_TAG: Final[str] = "production-hardening-01-ph03-pg-matrix-execution"
PH03_MATRIX_TEST: Final[str] = (
    "tests/test_production_hardening_01_ph03_pg_matrix_execution.py"
)
PH03_LEGACY_MATRIX_TEST: Final[str] = (
    "tests/test_fastapi_react_07_pg_boundary_matrix.py"
)

POSTGRES_OPTIONAL_ENV: Final[str] = "ERP_TEST_POSTGRES_URL"
POSTGRES_OPTIONAL_DOC: Final[str] = "docs/POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md"
POSTGRES_OPERATOR_DOC: Final[str] = "docs/P4_1_LOCAL_POSTGRES_VALIDATION.md"

OPTIONAL_POSTGRES_MARKER: Final[str] = "optional_postgres"


@dataclass(frozen=True, slots=True)
class PgBoundaryFlowSpec:
    flow_id: str
    family: str
    write_path: str
    test_file: str


PG_BOUNDARY_MATRIX_FLOWS: tuple[PgBoundaryFlowSpec, ...] = (
    PgBoundaryFlowSpec(
        "boundary_cash_sale",
        "post_cash_sale",
        "write_sales.create_and_post_sale",
        PH03_LEGACY_MATRIX_TEST,
    ),
    PgBoundaryFlowSpec(
        "boundary_void_sale",
        "void_cascade",
        "write_voids.void_record",
        PH03_LEGACY_MATRIX_TEST,
    ),
    PgBoundaryFlowSpec(
        "boundary_bank_deposit",
        "bank_transaction",
        "write_banking.create_manual_bank_transaction",
        PH03_MATRIX_TEST,
    ),
    PgBoundaryFlowSpec(
        "boundary_equity_contribution",
        "post_equity_movement",
        "post_capital_contribution + audit",
        PH03_MATRIX_TEST,
    ),
)

OPTIONAL_POSTGRES_TEST_FILES: tuple[str, ...] = (
    "tests/test_fastapi_react_07_pg_boundary_matrix.py",
    PH03_MATRIX_TEST,
    "tests/test_p3_2_dual_run_parity.py",
    "tests/test_pg_build_dual_run_parity.py",
    "tests/test_p3_2_postgres_fixture.py",
    "tests/test_postgres_runtime_cutover_prep.py",
    "tests/test_postgres_production_cutover_smoke.py",
    "tests/test_postgres_cutover_schema_stamp.py",
    "tests/test_money_decimal_05_impl4_migration_smoke.py",
    "tests/test_dashboard_decimal_trend.py",
    "tests/test_app_column_exists_pg_compat.py",
)

STREAMLIT_LAUNCH_CHECKLIST: tuple[tuple[str, str], ...] = (
    ("Core ERP + accounting engine", "Ready"),
    ("Full SQLite pytest suite", "Required"),
    ("PostgreSQL runtime cutover", "Testing"),
    ("React / FastAPI API-write cutover", "Not required"),
)

API_WRITE_LAUNCH_CHECKLIST: tuple[tuple[str, str], ...] = (
    ("P0 commit characterization (all 14 families)", "Complete"),
    ("P2 API boundary commit count (9 write suites)", "Complete"),
    ("Optional PG boundary matrix", "Partial"),
    ("Per-route `ERP_API_WRITE_*` flags", "Operator"),
    ("VITE_ERP_REACT_PAGES=1", "Operator"),
    ("`COMMIT_MODE_*=boundary` production flip", "Operator"),
    ("TD-PS-03 route-layer DTO cleanup", "Deferred"),
)

# Frozen for PH-03 audit tests (do not mutate).
PH03_DEFERRED_ITEMS: tuple[str, ...] = (
    "PRODUCTION-HARDENING-04",
    "PRODUCTION-HARDENING-05",
    "production COMMIT_MODE_* flip",
    "TD-PS-03",
    "CI optional_postgres job",
)
