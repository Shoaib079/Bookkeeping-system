"""P3.8-D — contract test for the flag-aware startup decision plan.

Doc-only guard: verifies the decision plan exists, carries the required sections,
names every action, and pins the decision matrix + safety invariants (flag-off runs
migrate_schema, at_head verify_only, unstamped legacy require_stamp, behind_head needs
backup+confirmation, ahead_of_code fail_closed, PostgreSQL never uses migrate_schema,
the decision function never executes migrations, startup wiring is future).
No DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P3_8_D_STARTUP_DECISION_PLAN.md"

REQUIRED_SECTIONS = (
    "Inputs",
    "Outputs",
    "Decision matrix",
    "Safety rules",
    "Future implementation boundaries",
)

ACTION_NAMES = (
    "run_migrate_schema",
    "verify_only",
    "alembic_upgrade_head",
    "require_stamp",
    "fail_closed",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Startup decision plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Startup decision plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Startup decision plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


@pytest.mark.parametrize("action", ACTION_NAMES)
def test_all_action_names_present(doc_text, action):
    assert action in doc_text, f"Missing action name: {action}"


def test_output_fields_present(doc_text):
    lowered = doc_text.lower()
    for field in ("blocks_startup", "requires_backup", "requires_confirmation", "message"):
        assert field in lowered, f"Missing output field: {field}"


def test_flag_off_runs_migrate_schema(doc_text):
    lowered = doc_text.lower()
    assert "flag" in lowered and "off" in lowered and "run_migrate_schema" in lowered, (
        "Plan must map flag-off to run_migrate_schema"
    )


def test_flag_on_at_head_verify_only(doc_text):
    lowered = doc_text.lower()
    assert "at_head" in lowered and "verify_only" in lowered, (
        "Plan must map flag-on at_head to verify_only"
    )


def test_unstamped_legacy_require_stamp(doc_text):
    lowered = doc_text.lower()
    assert "unstamped" in lowered and "require_stamp" in lowered, (
        "Plan must map unstamped legacy to require_stamp"
    )
    assert "never auto-upgrade" in lowered or "not auto-upgrade" in lowered or "never auto upgrade" in lowered, (
        "Unstamped legacy must not be auto-upgraded"
    )


def test_behind_head_requires_backup_and_confirmation(doc_text):
    lowered = doc_text.lower()
    assert "behind_head" in lowered, "Plan must address behind_head"
    assert "backup" in lowered and "confirmation" in lowered, (
        "behind_head must require backup + confirmation"
    )


def test_ahead_of_code_fail_closed(doc_text):
    lowered = doc_text.lower()
    assert "ahead_of_code" in lowered and "fail_closed" in lowered, (
        "Plan must map ahead_of_code to fail_closed"
    )


def test_unknown_ambiguous_fail_closed(doc_text):
    lowered = doc_text.lower()
    assert ("unknown" in lowered or "ambiguous" in lowered) and "fail_closed" in lowered, (
        "Plan must map unknown/ambiguous to fail_closed"
    )


def test_postgresql_never_uses_migrate_schema(doc_text):
    lowered = doc_text.lower()
    assert "postgresql never uses" in lowered and "migrate_schema" in lowered, (
        "Plan must state PostgreSQL never uses migrate_schema"
    )


def test_decision_function_does_not_execute_migrations(doc_text):
    lowered = doc_text.lower()
    assert "no migration execution in the decision function" in lowered or (
        "never executes a migration" in lowered
    ), "Plan must state the decision function executes no migrations"


def test_startup_wiring_is_future(doc_text):
    lowered = doc_text.lower()
    assert "startup wiring later" in lowered or "startup wiring is" in lowered, (
        "Plan must state startup wiring is a future slice"
    )
    assert "not wired" in lowered, "Plan must state the flag is not wired yet"


def test_fail_safe_default(doc_text):
    assert "fail-safe default" in doc_text.lower(), (
        "Plan must state a fail-safe default"
    )


def test_no_runtime_change_yet(doc_text):
    assert "no runtime change yet" in doc_text.lower(), (
        "Plan must state no runtime change yet"
    )
