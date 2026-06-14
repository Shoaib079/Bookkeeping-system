"""P3.4-E — contract test for the Alembic baseline acceptance & stamp plan.

Doc-only guard: verifies the stamp plan exists, carries the required sections, and
pins the safety invariants (no stamp yet, backup-first, alembic_version-only,
no upgrade, migrate_schema stays active, restore-from-backup rollback, no manual
accounting edits). No DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P3_4_E_BASELINE_STAMP_PLAN.md"

REQUIRED_SECTIONS = (
    "Preconditions before stamping",
    "Backup procedure",
    "Dry-run / verification procedure",
    "Stamp procedure",
    "Post-stamp verification",
    "Rollback procedure",
    "Cutover boundary",
    "Operator checklist",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Stamp plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Stamp plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Stamp plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_says_no_stamp_yet(doc_text):
    assert "no database has been stamped yet" in doc_text.lower(), (
        "Plan must state no DB has been stamped yet"
    )


def test_mentions_backup(doc_text):
    assert "backup" in doc_text.lower(), "Plan must describe a backup"


def test_mentions_erp_data_db(doc_text):
    assert "erp_data.db" in doc_text.lower(), "Plan must reference erp_data.db"


def test_mentions_alembic_stamp_0001(doc_text):
    assert "alembic stamp 0001" in doc_text.lower(), "Plan must specify 'alembic stamp 0001'"


def test_stamp_writes_alembic_version_only(doc_text):
    lowered = doc_text.lower()
    assert "alembic_version" in lowered, "Plan must reference the alembic_version table"
    assert "no schema ddl" in lowered or "no ddl" in lowered, (
        "Plan must state stamp issues no schema DDL"
    )


def test_says_no_alembic_upgrade(doc_text):
    assert "do not run `alembic upgrade`" in doc_text.lower() or "do not run alembic upgrade" in doc_text.lower(), (
        "Plan must forbid alembic upgrade"
    )


def test_says_migrate_schema_remains_active(doc_text):
    lowered = doc_text.lower()
    assert "migrate_schema" in lowered and "active" in lowered, (
        "Plan must state migrate_schema remains active"
    )


def test_rollback_restores_backup(doc_text):
    lowered = doc_text.lower()
    assert "restore the backup" in lowered or "restore backup" in lowered or "restore-from-backup" in lowered, (
        "Plan rollback must restore the backup"
    )


def test_no_manual_accounting_table_edits(doc_text):
    assert "do not manually edit accounting tables" in doc_text.lower(), (
        "Plan must forbid manual accounting-table edits"
    )
