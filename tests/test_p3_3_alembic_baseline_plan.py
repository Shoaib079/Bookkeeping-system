"""P3.3 — contract test for the Alembic baseline plan document.

Doc-only guard: verifies the plan exists, carries the required sections, and pins
the safety invariants (no migration yet, migrate_schema stays authoritative,
baseline as 0001, safe stamping, Float→Decimal excluded, no blind autogenerate,
backup/rollback rules). No DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P3_3_ALEMBIC_BASELINE_PLAN.md"

REQUIRED_SECTIONS = (
    'What "baseline" means',
    "Baseline strategy",
    "Cutover rules",
    "Migration generation rules",
    "Rollback strategy",
    "Baseline validation plan",
    "No-change decisions",
    "Recommended P3.4 tasks",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Baseline plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Baseline plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Baseline plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_states_no_migration_generated_yet(doc_text):
    assert "no migration has been generated yet" in doc_text.lower(), (
        "Plan must state no migration revision has been generated yet"
    )


def test_states_migrate_schema_remains_active(doc_text):
    lowered = doc_text.lower()
    assert "migrate_schema" in lowered and "authoritative" in lowered, (
        "Plan must state migrate_schema remains authoritative/active for now"
    )


def test_states_baseline_as_0001(doc_text):
    lowered = doc_text.lower()
    assert "0001" in lowered and "baseline" in lowered, (
        "Plan must baseline the current schema as revision 0001"
    )


def test_states_existing_sqlite_dbs_stamped_safely(doc_text):
    lowered = doc_text.lower()
    assert "stamp" in lowered, "Plan must describe stamping existing SQLite DBs"
    assert (
        "without any destructive migration" in lowered
        or "non-destructive" in lowered
        or "no destructive migration" in lowered
    ), "Plan must state existing SQLite DBs are stamped without destructive migration"


def test_states_float_decimal_excluded(doc_text):
    lowered = doc_text.lower()
    assert "float" in lowered and "decimal" in lowered and "exclud" in lowered, (
        "Plan must state Float → Decimal is excluded"
    )


def test_states_no_blind_autogenerate(doc_text):
    assert "no blind autogenerate" in doc_text.lower(), (
        "Plan must forbid blind autogenerate"
    )
    assert "manually review" in doc_text.lower(), (
        "Plan must require manual review of generated revisions"
    )


def test_states_backup_rollback_rules(doc_text):
    lowered = doc_text.lower()
    assert "backup" in lowered and "rollback" in lowered, (
        "Plan must include backup/rollback rules"
    )
    assert "pg_dump" in lowered, "Plan must mention pg_dump for PostgreSQL rollback"
    assert "never delete accounting rows" in lowered, (
        "Plan must preserve the never-delete-accounting-rows policy"
    )
