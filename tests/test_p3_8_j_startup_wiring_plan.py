"""P3.8-J — contract test for the flag-gated startup wiring plan.

Doc-only guard: verifies the wiring plan exists, carries the required sections, and
pins the startup branch behavior + safety invariants (flag-off unchanged, flag-on
behavior matrix, runner/gate required, no raw alembic in app.py, no startup wiring
yet, rollback disables the flag). No DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P3_8_J_STARTUP_WIRING_PLAN.md"

REQUIRED_SECTIONS = (
    "Startup sequence with flag off",
    "Startup sequence with flag on",
    "App wiring location",
    "Error handling",
    "Tests for implementation",
    "Rollback",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Wiring plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Wiring plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Wiring plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_flag_off_unchanged(doc_text):
    lowered = doc_text.lower()
    assert "flag off" in lowered and "unchanged" in lowered, (
        "Plan must keep flag-off behavior unchanged"
    )
    assert "migrate_schema" in lowered and "runs first" in lowered, (
        "Flag-off path must run migrate_schema first"
    )


def test_flag_on_behavior_matrix(doc_text):
    lowered = doc_text.lower()
    assert "at_head" in lowered and "skip" in lowered and "verify_only" in lowered, (
        "Matrix must cover at_head -> skip migrate_schema / verify_only"
    )
    assert "new / empty db" in lowered or "new empty db" in lowered, (
        "Matrix must cover new/empty DB"
    )
    assert "upgrade head" in lowered, "Matrix must cover upgrade head for empty DB"
    assert "unstamped legacy" in lowered and "block" in lowered, (
        "Matrix must block on unstamped legacy"
    )
    assert "behind_head" in lowered, "Matrix must cover behind_head"
    assert "ahead_of_code" in lowered and "fail closed" in lowered, (
        "Matrix must fail closed on ahead_of_code"
    )
    assert "unknown" in lowered, "Matrix must cover unknown/ambiguous"


def test_runner_and_gate_required(doc_text):
    lowered = doc_text.lower()
    assert "runner" in lowered, "Plan must require the safe Alembic runner (P3.8-H)"
    assert "gate" in lowered, "Plan must require the migration safety gate (P3.8-I)"
    assert "p3.8-h" in lowered and "p3.8-i" in lowered, (
        "Plan must reference the P3.8-H runner and P3.8-I gate"
    )


def test_no_raw_alembic_in_app(doc_text):
    lowered = doc_text.lower()
    assert "no raw alembic calls in `app.py`" in lowered or "no raw alembic calls in app.py" in lowered, (
        "Plan must forbid raw alembic calls in app.py"
    )


def test_wiring_location_referenced(doc_text):
    lowered = doc_text.lower()
    assert "_boot_session" in lowered, "Plan must reference the _boot_session startup location"
    assert "_run_schema_startup" in lowered, (
        "Plan must name the dispatcher that replaces the migrate_schema+diagnostic pair"
    )


def test_no_silent_fallback_when_flag_on(doc_text):
    assert "no silent fallback when flag on" in doc_text.lower(), (
        "Plan must forbid silent fallback to migrate_schema when flag on"
    )


def test_no_production_action_without_backup_confirmation(doc_text):
    lowered = doc_text.lower()
    assert "no production db action without backup/confirmation" in lowered or (
        "backup" in lowered and "confirmation" in lowered
    ), "Plan must forbid populated-DB action without backup/confirmation"


def test_no_startup_wiring_yet(doc_text):
    lowered = doc_text.lower()
    assert "no startup wiring yet" in lowered, "Plan must state no startup wiring yet"
    assert "not implemented" in lowered, "Plan must state the wiring is not implemented"


def test_rollback_disables_flag(doc_text):
    lowered = doc_text.lower()
    assert "disable the flag" in lowered or "disable flag" in lowered, (
        "Rollback must disable the flag"
    )
    assert "restore the backup" in lowered or "restore backup" in lowered, (
        "Rollback must restore the backup"
    )
    assert "migrate_schema" in lowered and "retained" in lowered, (
        "Rollback must retain migrate_schema"
    )
