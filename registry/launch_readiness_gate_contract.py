"""PRODUCTION-HARDENING-01-PH05 — launch-readiness verification gate contract.

Machine-readable mirror of
``docs/PRODUCTION_HARDENING_01_PH05_LAUNCH_READINESS_AUDIT.md``.
"""

from __future__ import annotations

from typing import Final

PH05_CONTRACT_DOC: Final[str] = (
    "docs/PRODUCTION_HARDENING_01_PH05_LAUNCH_READINESS_AUDIT.md"
)
PH05_SLICE_ID: Final[str] = "PRODUCTION-HARDENING-01-PH05"
PH05_TAG: Final[str] = "production-hardening-01-ph05-launch-readiness"
PH05_GATE_TEST: Final[str] = (
    "tests/test_production_hardening_01_ph05_launch_readiness.py"
)

EPIC_ID: Final[str] = "PRODUCTION-HARDENING-01"
EPIC_STATUS: Final[str] = "complete"

EPIC_SLICE_AUDITS: tuple[tuple[str, str, str], ...] = (
    (
        "PRODUCTION-HARDENING-01-PH01",
        "docs/PRODUCTION_HARDENING_01_PH01_REGISTER_CLEANUP_AUDIT.md",
        "production-hardening-01-ph01-register-cleanup",
    ),
    (
        "PRODUCTION-HARDENING-01-PH02",
        "docs/PRODUCTION_HARDENING_01_PH02_COMMIT_CHARACTERIZATION_AUDIT.md",
        "production-hardening-01-ph02-commit-characterization",
    ),
    (
        "PRODUCTION-HARDENING-01-PH03",
        "docs/PRODUCTION_HARDENING_01_PH03_PG_MATRIX_EXECUTION_AUDIT.md",
        "production-hardening-01-ph03-pg-matrix-execution",
    ),
    (
        "PRODUCTION-HARDENING-01-PH04",
        "docs/PRODUCTION_HARDENING_01_PH04_COMMIT_MODE_ROLLOUT_AUDIT.md",
        "production-hardening-01-ph04-commit-mode-rollout",
    ),
    (
        "PRODUCTION-HARDENING-01-PH05",
        PH05_CONTRACT_DOC,
        PH05_TAG,
    ),
)

EPIC_SLICE_TESTS: tuple[str, ...] = (
    "tests/test_production_hardening_01_ph01_register_cleanup.py",
    "tests/test_production_hardening_01_ph02_commit_characterization.py",
    "tests/test_production_hardening_01_ph03_pg_matrix_execution.py",
    "tests/test_production_hardening_01_ph04_commit_mode_rollout.py",
    PH05_GATE_TEST,
)

SUPPORTING_CONTRACTS: tuple[str, ...] = (
    "registry/production_hardening_contract.py",
    "registry/pg_matrix_execution_contract.py",
    "registry/commit_mode_rollout_contract.py",
    "registry/commit_boundary_contract.py",
    "registry/pg_boundary_contract.py",
)

VERIFICATION_GATE_COMMANDS: tuple[str, ...] = (
    "pytest tests/test_production_hardening_01_ph01_register_cleanup.py",
    "pytest tests/test_production_hardening_01_ph02_commit_characterization.py",
    "pytest tests/test_production_hardening_01_ph03_pg_matrix_execution.py",
    "pytest tests/test_production_hardening_01_ph04_commit_mode_rollout.py",
    "pytest tests/test_production_hardening_01_ph05_launch_readiness.py",
    "pytest tests/",
)

STREAMLIT_LAUNCH_VERDICT: Final[str] = "0 launch blockers"
API_WRITE_LAUNCH_VERDICT: Final[str] = "operator deferrals only"

POST_EPIC_OPERATOR_DEFERRALS: tuple[str, ...] = (
    "Per-route ERP_API_WRITE_* flags",
    "VITE_ERP_REACT_PAGES=1",
    "COMMIT_MODE_*=boundary production flip",
    "production operator sign-off",
    "ERP_TEST_POSTGRES_URL PG matrix green on staging",
)

POST_EPIC_INTENTIONAL_DEFERRALS: tuple[str, ...] = (
    "TD-PS-03",
    "CI optional_postgres job",
)

# Frozen for PH-05 audit tests (do not mutate).
PH05_DEFERRED_ITEMS: tuple[str, ...] = (
    "TD-PS-03",
    "CI optional_postgres job",
    "production operator sign-off",
)
