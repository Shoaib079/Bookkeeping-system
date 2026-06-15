"""P3.9 — contract test for the migrate_schema() retirement plan.

Doc-only guard: verifies the retirement plan exists, carries the required sections,
and pins the invariants (migrate_schema retained now, flag default off, phased
retirement A/B/C, prerequisites, safety rules, PostgreSQL Alembic-only, no retirement
yet). Pure stdlib; no app imports; no DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "P3_9_MIGRATE_SCHEMA_RETIREMENT_PLAN.md"
)

REQUIRED_SECTIONS = (
    "Current state",
    "Retirement prerequisites",
    "Retirement sequence",
    "Safety rules",
    "PostgreSQL future",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Retirement plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Retirement plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Retirement plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_migrate_schema_retained_now(doc_text):
    lowered = doc_text.lower()
    assert "migrate_schema" in lowered and "retained" in lowered, (
        "Plan must state migrate_schema is retained now"
    )
    assert "not removed" in lowered, "Plan must state migrate_schema is not removed"


def test_flag_default_off(doc_text):
    lowered = doc_text.lower()
    assert "flag default off" in lowered or "default off" in lowered, (
        "Plan must state the flag defaults off"
    )
    assert "erp_alembic_authoritative" in lowered, "Plan must name the flag"


def test_prerequisites_listed(doc_text):
    lowered = doc_text.lower()
    assert "bake-in completed" in lowered, "Prerequisites must include bake-in completed"
    assert "smoke tests passed" in lowered, "Prerequisites must include smoke tests passed"
    assert "stamped" in lowered, "Prerequisites must require production DBs stamped"
    assert "no unstamped legacy" in lowered, "Prerequisites must require no unstamped legacy DBs"
    assert "schema equivalence" in lowered, "Prerequisites must require schema equivalence proven"
    assert "rollback tested" in lowered, "Prerequisites must require rollback tested"


def test_phased_retirement_sequence(doc_text):
    lowered = doc_text.lower()
    assert "phase a" in lowered, "Sequence must include Phase A"
    assert "phase b" in lowered, "Sequence must include Phase B"
    assert "phase c" in lowered, "Sequence must include Phase C"
    assert "stop calling" in lowered or "stop invoking" in lowered, (
        "Phase A must stop calling migrate_schema at startup"
    )
    assert "deprecat" in lowered, "Phase B must deprecate the function"
    assert "warning" in lowered or "warn" in lowered, "Phase B must emit warnings if used"
    assert "major release" in lowered, "Phase C must remove in a future major release"


def test_phase_a_keeps_function(doc_text):
    lowered = doc_text.lower()
    assert "keep the function" in lowered or "keep it" in lowered, (
        "Phase A must keep the function in the codebase"
    )


def test_safety_rules(doc_text):
    lowered = doc_text.lower()
    assert "never delete accounting" in lowered, "Safety must never delete accounting data"
    assert "backup before migration" in lowered, "Safety must require backup before migration"
    assert "fail closed on schema mismatch" in lowered, (
        "Safety must fail closed on schema mismatch"
    )


def test_postgresql_alembic_only(doc_text):
    lowered = doc_text.lower()
    assert "postgresql never uses" in lowered and "migrate_schema" in lowered, (
        "Plan must state PostgreSQL never uses migrate_schema"
    )
    assert "alembic-only" in lowered, "Plan must state an Alembic-only PG path"


def test_no_retirement_yet(doc_text):
    lowered = doc_text.lower()
    assert "no retirement performed" in lowered or "no retirement yet" in lowered, (
        "Plan must state no retirement performed yet"
    )
    assert "planned, not executed" in lowered or "not executed" in lowered, (
        "Plan must state the retirement is planned, not executed"
    )


def test_no_runtime_change(doc_text):
    lowered = doc_text.lower()
    assert "no runtime change" in lowered, "Plan must state no runtime change"
    assert "untouched" in lowered, "Plan must state app.py is untouched"
