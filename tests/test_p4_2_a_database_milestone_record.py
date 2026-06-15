"""P4.2-A — contract test for the database milestone record.

Doc-only guard: verifies the milestone record exists and pins test status,
completed P3.x/P4.x milestones, current runtime invariants, and next priorities.
Pure stdlib; no app imports; no DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "P4_2_A_DATABASE_MILESTONE_RECORD.md"
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Milestone record missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Milestone record missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Milestone record is empty"


def test_doc_contains_test_status_pass_count(doc_text):
    assert "3286 passed" in doc_text


def test_doc_sqlite_remains_production_runtime(doc_text):
    assert "SQLite remains production runtime" in doc_text


def test_doc_alembic_behind_feature_flag(doc_text):
    assert "Alembic available behind feature flag" in doc_text


def test_doc_next_priority_nav_ux_02(doc_text):
    assert "NAV-UX-02" in doc_text


def test_doc_next_priority_banking_ux_04(doc_text):
    assert "BANKING-UX-04" in doc_text


def test_doc_next_priority_fastapi_foundation(doc_text):
    assert "FastAPI foundation" in doc_text


def test_doc_next_priority_react_frontend_migration(doc_text):
    assert "React frontend migration" in doc_text


def test_doc_records_completed_milestones(doc_text):
    lowered = doc_text.lower()
    for marker in (
        "p3.4 alembic 0001 baseline",
        "p3.8 authority transition",
        "p4.0 postgresql enablement",
        "p4.1 local postgresql validation",
    ):
        assert marker in lowered, f"Milestone record must mention {marker!r}"


def test_doc_postgres_readiness_test_db_only(doc_text):
    lowered = doc_text.lower()
    assert "test db only" in lowered
    assert "production pg not enabled" in lowered
