"""P3.8-L-BAKEIN — contract test for the Alembic authority bake-in audit.

Doc-only guard: verifies the audit exists, carries the required outputs (verdict, flow,
decision matrix, callers, SQLite-only findings, missing tests, bake-in definition,
rollback, PG implications, slices, exact retirement condition, ROADMAP rec), and pins
the conclusion. Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P3_8_L_BAKEIN_AUDIT.md"

REQUIRED_SECTIONS = (
    "Verdict",
    "Exact startup flow",
    "Decision matrix",
    "Remaining callers of `migrate_schema()`",
    "SQLite-only logic",
    "Missing characterization tests",
    'What "bake-in" actually means',
    "Rollback if authority is enabled",
    "PostgreSQL implications",
    "Required implementation slices",
    "Required conclusion",
    "ROADMAP update recommendation",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"P3.8-L audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"P3.8-L audit doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "P3.8-L audit doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_verdict_machinery_complete_not_retired(doc_text):
    low = doc_text.lower()
    assert "not ready to retire" in low, "Verdict must be NOT READY to retire migrate_schema"
    assert "machinery is complete" in low or "machinery is **complete" in low or "complete and wired" in low, (
        "Verdict must note the machinery is complete and wired"
    )


def test_flow_and_wiring(doc_text):
    low = doc_text.lower()
    assert "prepare_schema_startup_authoritative" in low, "Must cite the pre-session prepare fn"
    assert "run_schema_startup_in_session" in low, "Must cite the in-session run fn"
    assert "26447" in doc_text or "26449" in doc_text, "Must anchor the app.py call site"


def test_decision_matrix_states(doc_text):
    low = doc_text.lower()
    assert "flag off" in low and "migrate_schema" in low and "authoritative" in low, (
        "Flag-off keeps migrate_schema authoritative"
    )
    assert "verify_only" in low and "skip" in low, "Flag-on at_head skips migrate_schema"
    assert "new" in low and ("upgrade" in low), "Flag-on new-empty upgrades"
    assert "fail_closed" in low, "Flag-on ahead/unknown fails closed"


def test_single_caller(doc_text):
    low = doc_text.lower()
    assert "exactly one runtime caller" in low or "one runtime caller" in low, (
        "Must state migrate_schema has a single runtime caller"
    )


def test_sqlite_only(doc_text):
    low = doc_text.lower()
    assert "add column" in low and "sqlite" in low, "Must note ALTER ADD COLUMN / SQLite-only"
    assert "invalid on postgresql" in low or "invalid on pg" in low or "never run on postgresql" in low, (
        "migrate_schema must never run on PostgreSQL"
    )


def test_missing_tests_listed(doc_text):
    low = doc_text.lower()
    assert "schema-equivalence" in low or "schema equivalence" in low, "Equivalence gate test"
    assert "single-caller guard" in low, "Single-caller guard test"
    assert "never runs on postgresql" in low or "never on postgresql" in low or "never-on-pg" in low, (
        "Never-on-PG test"
    )


def test_bakein_definition(doc_text):
    low = doc_text.lower()
    assert "defined window" in low, "Bake-in is over a defined window"
    assert "no schema drift" in low, "Bake-in observes no schema drift"
    assert "not a code change" in low or "not* a code change" in low or "evidence collection" in low, (
        "Bake-in is operational, not a code change"
    )


def test_rollback_flag_off(doc_text):
    low = doc_text.lower()
    assert "disable the flag" in low and "migrate_schema" in low, (
        "Rollback = disable the flag, migrate_schema runs again"
    )
    assert "no schema change" in low, "Rollback needs no schema change"


def test_exact_condition(doc_text):
    low = doc_text.lower()
    assert "default" in low and "flip" in low, "Condition includes the default flip (P3.8-N)"
    assert "stamped at head" in low, "Condition requires all DBs stamped at head"
    assert "p3.9" in low, "Retirement removal is P3.9"
    assert "never" in low and "postgresql" in low, "migrate_schema never runs on PostgreSQL"


def test_no_change_statement(doc_text):
    low = doc_text.lower()
    assert "audit only" in low, "Must state audit-only"
    assert "no feature-flag change" in low or "no feature flag change" in low, "No flag change"
    assert "no runtime db switch" in low, "No runtime DB switch"
    assert "no alembic change" in low, "No Alembic change"
