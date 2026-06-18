"""PRODUCTION-HARDENING-01 — frozen production hardening contract.

Machine-readable mirror of ``docs/PRODUCTION_HARDENING_01_PH01_REGISTER_CLEANUP_AUDIT.md``
and subsequent PH slice audits.
"""

from __future__ import annotations

from typing import Final

EPIC_ID: Final[str] = "PRODUCTION-HARDENING-01"
EPIC_STATUS: Final[str] = "complete"

PH01_CONTRACT_DOC: Final[str] = (
    "docs/PRODUCTION_HARDENING_01_PH01_REGISTER_CLEANUP_AUDIT.md"
)
PH01_SLICE_ID: Final[str] = "PRODUCTION-HARDENING-01-PH01"
PH01_TAG: Final[str] = "production-hardening-01-ph01-register-cleanup"

# Stale global deferred pointers removed in PH-01 (superseded work).
PH01_STALE_GLOBAL_DEFERRED_REMOVED: tuple[str, ...] = (
    "FASTAPI-REACT-42",
    "React write pages",
)

# ROADMAP epic-table gaps closed in PH-01.
PH01_ROADMAP_EPIC_ROWS_ADDED: tuple[str, ...] = (
    "FASTAPI-REACT-13",
    "FASTAPI-REACT-14",
    "FASTAPI-REACT-15",
    "FASTAPI-REACT-16",
)

PH01_STATUS_REGISTER_KEYS: tuple[str, ...] = (
    "React migration",
    "FastAPI foundation",
    EPIC_ID,
)

# Frozen for PH-01 audit tests (do not mutate).
PH01_DEFERRED_ITEMS: tuple[str, ...] = (
    "PRODUCTION-HARDENING-02",
    "PRODUCTION-HARDENING-03",
    "PRODUCTION-HARDENING-04",
    "PRODUCTION-HARDENING-05",
    "production COMMIT_MODE_* flip",
)

EPIC_SLICES: tuple[tuple[str, str, str], ...] = (
    (
        "PRODUCTION-HARDENING-01-PH01",
        "ROADMAP + stale contract deferred cleanup",
        "complete",
    ),
    (
        "PRODUCTION-HARDENING-01-PH02",
        "bank_transaction + equity_movement commit characterization",
        "complete",
    ),
    (
        "PRODUCTION-HARDENING-01-PH03",
        "PostgreSQL matrix execution audit + launch checklist",
        "complete",
    ),
    (
        "PRODUCTION-HARDENING-01-PH04",
        "COMMIT_MODE_* operator rollout characterization",
        "complete",
    ),
    (
        "PRODUCTION-HARDENING-01-PH05",
        "Launch-readiness verification gate + epic closure",
        "complete",
    ),
)

PH05_CONTRACT_DOC: Final[str] = (
    "docs/PRODUCTION_HARDENING_01_PH05_LAUNCH_READINESS_AUDIT.md"
)
PH05_SLICE_ID: Final[str] = "PRODUCTION-HARDENING-01-PH05"
PH05_TAG: Final[str] = "production-hardening-01-ph05-launch-readiness"
PH05_GATE_CONTRACT: Final[str] = "registry/launch_readiness_gate_contract.py"

# Frozen for PH-05 audit tests (do not mutate).
PH05_DEFERRED_ITEMS: tuple[str, ...] = (
    "TD-PS-03",
    "CI optional_postgres job",
    "production operator sign-off",
)

PH04_CONTRACT_DOC: Final[str] = (
    "docs/PRODUCTION_HARDENING_01_PH04_COMMIT_MODE_ROLLOUT_AUDIT.md"
)
PH04_SLICE_ID: Final[str] = "PRODUCTION-HARDENING-01-PH04"
PH04_TAG: Final[str] = "production-hardening-01-ph04-commit-mode-rollout"
PH04_ROLLOUT_CONTRACT: Final[str] = "registry/commit_mode_rollout_contract.py"

# Frozen for PH-04 audit tests (do not mutate).
PH04_DEFERRED_ITEMS: tuple[str, ...] = (
    "PRODUCTION-HARDENING-05",
    "production operator sign-off",
    "TD-PS-03",
    "CI optional_postgres job",
)

PH02_CONTRACT_DOC: Final[str] = (
    "docs/PRODUCTION_HARDENING_01_PH02_COMMIT_CHARACTERIZATION_AUDIT.md"
)
PH02_SLICE_ID: Final[str] = "PRODUCTION-HARDENING-01-PH02"
PH02_TAG: Final[str] = "production-hardening-01-ph02-commit-characterization"

PH02_CHARACTERIZATION_TESTS: tuple[str, ...] = (
    "tests/test_fastapi_p0_commit_ownership_banking.py",
    "tests/test_fastapi_p0_commit_ownership_movements.py",
)

PH02_BOUNDARY_FAMILIES: tuple[str, ...] = (
    "bank_transaction",
    "post_equity_movement",
)

# Frozen for PH-02 audit tests (do not mutate).
PH02_DEFERRED_ITEMS: tuple[str, ...] = (
    "PRODUCTION-HARDENING-03",
    "PRODUCTION-HARDENING-04",
    "PRODUCTION-HARDENING-05",
    "bank_transaction PG matrix",
    "equity_movement PG matrix",
    "production COMMIT_MODE_* flip",
)

PH03_CONTRACT_DOC: Final[str] = (
    "docs/PRODUCTION_HARDENING_01_PH03_PG_MATRIX_EXECUTION_AUDIT.md"
)
PH03_SLICE_ID: Final[str] = "PRODUCTION-HARDENING-01-PH03"
PH03_TAG: Final[str] = "production-hardening-01-ph03-pg-matrix-execution"
PH03_MATRIX_CONTRACT: Final[str] = "registry/pg_matrix_execution_contract.py"

# Frozen for PH-03 audit tests (do not mutate).
PH03_DEFERRED_ITEMS: tuple[str, ...] = (
    "PRODUCTION-HARDENING-04",
    "PRODUCTION-HARDENING-05",
    "production COMMIT_MODE_* flip",
    "TD-PS-03",
    "CI optional_postgres job",
)
