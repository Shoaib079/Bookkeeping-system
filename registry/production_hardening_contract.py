"""PRODUCTION-HARDENING-01 — frozen production hardening contract.

Machine-readable mirror of ``docs/PRODUCTION_HARDENING_01_PH01_REGISTER_CLEANUP_AUDIT.md``
and subsequent PH slice audits.
"""

from __future__ import annotations

from typing import Final

EPIC_ID: Final[str] = "PRODUCTION-HARDENING-01"

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
        "planned",
    ),
    (
        "PRODUCTION-HARDENING-01-PH03",
        "PostgreSQL matrix execution audit + launch checklist",
        "planned",
    ),
    (
        "PRODUCTION-HARDENING-01-PH04",
        "COMMIT_MODE_* operator rollout characterization",
        "planned",
    ),
    (
        "PRODUCTION-HARDENING-01-PH05",
        "Launch-readiness verification gate + epic closure",
        "planned",
    ),
)
