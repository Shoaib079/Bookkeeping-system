"""P3.9-A — contract test for migrate_schema() retirement readiness audit.

Doc-only guard. Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P3_9_A_AUDIT.md"
PLAN_PATH = Path(__file__).resolve().parents[1] / "docs" / "P3_9_MIGRATE_SCHEMA_RETIREMENT_PLAN.md"

REQUIRED_SECTIONS = (
    "Verdict",
    "P3.9 §2 prerequisite checklist",
    "Current runtime behavior",
    "Remaining callers",
    "Gap analysis",
    "PostgreSQL implications",
    "Required implementation slices",
    "Rollback",
    "ROADMAP update recommendation",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"P3.9-A audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


def test_retirement_plan_prerequisite_exists():
    assert PLAN_PATH.exists()


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text: str, section: str):
    assert section.lower() in doc_text.lower(), f"Missing section: {section!r}"


def test_verdict_not_ready_to_remove(doc_text: str):
    low = doc_text.lower()
    assert "not ready to remove" in low
    assert "phase a" in low and "p3.8-n" in low


def test_phase_b_and_c_not_started(doc_text: str):
    low = doc_text.lower()
    assert "phase b" in low and "not started" in low
    assert "phase c" in low


def test_prerequisites_reference_p3_8_slices(doc_text: str):
    low = doc_text.lower()
    assert "p3.8-l-exec" in low or "l-exec" in low
    assert "p3.8-l-tests" in low or "l-tests" in low
    assert "schema equivalence" in low


def test_explicit_opt_out_legacy_path(doc_text: str):
    low = doc_text.lower()
    assert "=0" in low or "false" in low
    assert "migrate_schema" in low


def test_postgresql_never_migrate_schema(doc_text: str):
    low = doc_text.lower()
    assert "postgresql" in low or "pg" in low
    assert "alembic" in low


def test_next_slices_sequenced(doc_text: str):
    low = doc_text.lower()
    assert "p3.9-b" in low
    assert "p3.9-c" in low


def test_no_change_statement(doc_text: str):
    low = doc_text.lower()
    assert "audit only" in low
    assert "no" in low and "removal" in low
