"""P3.8-G — contract test for the flag-gated Alembic behavior plan.

Doc-only guard: verifies the behavior plan exists, carries the required sections,
and pins the first-slice branch behavior + safety invariants (flag-off unchanged,
at_head skips migrate_schema, new empty DB upgrade head, unstamped legacy blocks,
behind_head needs backup/confirmation, ahead_of_code/unknown fail closed, no
production auto-upgrade, no automatic stamp, migrate_schema retained, rollback
disables the flag, execution sequence present). No DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P3_8_G_FLAG_GATED_BEHAVIOR_PLAN.md"

REQUIRED_SECTIONS = (
    "Scope of first behavior slice",
    "What is explicitly NOT included",
    "Required helpers before wiring",
    "Test matrix",
    "Safety and rollback",
    "Execution sequence",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Behavior plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Behavior plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Behavior plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_flag_off_unchanged(doc_text):
    lowered = doc_text.lower()
    assert "flag off" in lowered and "unchanged" in lowered and "migrate_schema" in lowered, (
        "Plan must keep flag-off behavior unchanged (migrate_schema)"
    )


def test_flag_on_at_head_skips_migrate_schema(doc_text):
    lowered = doc_text.lower()
    assert "at_head" in lowered and "skip" in lowered and "migrate_schema" in lowered, (
        "Plan must skip migrate_schema for flag-on at_head"
    )
    assert "verify_only" in lowered, "at_head must be verify_only"


def test_new_db_upgrade_head_allowed(doc_text):
    lowered = doc_text.lower()
    assert "upgrade head" in lowered, "Plan must allow alembic upgrade head"
    assert "empty" in lowered, "upgrade head must be restricted to an empty DB"


def test_unstamped_legacy_blocks(doc_text):
    lowered = doc_text.lower()
    assert "unstamped legacy" in lowered and "block" in lowered, (
        "Plan must block on unstamped legacy DB"
    )
    assert "stamp instruction" in lowered, "Unstamped legacy block must give stamp instructions"


def test_behind_head_requires_backup_confirmation(doc_text):
    lowered = doc_text.lower()
    assert "behind_head" in lowered, "Plan must address behind_head"
    assert "backup" in lowered and "confirmation" in lowered, (
        "behind_head must require backup + confirmation"
    )


def test_ahead_of_code_and_unknown_fail_closed(doc_text):
    lowered = doc_text.lower()
    assert "ahead_of_code" in lowered and "fail closed" in lowered, (
        "ahead_of_code must fail closed"
    )
    assert "unknown" in lowered, "Plan must address unknown/ambiguous"


def test_no_production_auto_upgrade(doc_text):
    lowered = doc_text.lower()
    assert "no production auto-upgrade" in lowered, (
        "Plan must exclude production auto-upgrade of a populated DB"
    )


def test_no_automatic_stamp(doc_text):
    lowered = doc_text.lower()
    assert "no automatic stamp" in lowered, "Plan must exclude automatic stamp of a legacy DB"


def test_migrate_schema_retained(doc_text):
    lowered = doc_text.lower()
    assert "migrate_schema" in lowered and "retained" in lowered, (
        "Plan must retain migrate_schema()"
    )


def test_rollback_disables_flag(doc_text):
    lowered = doc_text.lower()
    assert "disable the flag" in lowered or "disable flag" in lowered, (
        "Rollback must disable the flag"
    )
    assert "restore the backup" in lowered or "restore backup" in lowered, (
        "Rollback must restore the backup"
    )


def test_never_edit_accounting_tables(doc_text):
    assert "never edit accounting tables manually" in doc_text.lower(), (
        "Plan must forbid manual accounting-table edits"
    )


def test_execution_sequence_present(doc_text):
    lowered = doc_text.lower()
    for phase in ("p3.8-h", "p3.8-i", "p3.8-j", "p3.8-k"):
        assert phase in lowered, f"Execution sequence must include {phase}"


def test_no_runtime_change_yet(doc_text):
    assert "no runtime change yet" in doc_text.lower(), (
        "Plan must state no runtime change yet"
    )
