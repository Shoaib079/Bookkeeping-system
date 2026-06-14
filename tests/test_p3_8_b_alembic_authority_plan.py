"""P3.8-B — contract test for the Alembic authority cutover design.

Doc-only guard: verifies the authority plan exists, carries the required sections,
defines the feature flag, and pins the safety invariants (migrate_schema remains the
default now, Alembic future authority only, backup requirement, rollback requirement,
no destructive migration, retirement criteria). No DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P3_8_B_ALEMBIC_AUTHORITY_PLAN.md"

REQUIRED_SECTIONS = (
    "Feature flag design",
    "Startup decision matrix",
    "Migration flow",
    "Safety rules",
    "Rollback",
    "Test strategy",
    "Retirement criteria",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Authority plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Authority plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Authority plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_feature_flag_defined(doc_text):
    lowered = doc_text.lower()
    assert "erp_alembic_authoritative" in lowered, (
        "Plan must define the ERP_ALEMBIC_AUTHORITATIVE feature flag"
    )
    assert "erp_alembic_authoritative=0" in lowered, "Plan must document the default value 0"
    assert "erp_alembic_authoritative=1" in lowered, "Plan must document the future value 1"


def test_migrate_schema_remains_default_now(doc_text):
    lowered = doc_text.lower()
    assert "migrate_schema" in lowered, "Plan must reference migrate_schema"
    assert "default" in lowered and "authoritative now" in lowered, (
        "Plan must state migrate_schema remains the default and authoritative now"
    )


def test_alembic_future_authority_only(doc_text):
    lowered = doc_text.lower()
    assert "authoritative" in lowered and "future" in lowered and "slice" in lowered, (
        "Plan must state Alembic becomes authoritative only in a future approved slice"
    )


def test_says_no_runtime_change_yet(doc_text):
    assert "no runtime change yet" in doc_text.lower(), (
        "Plan must state no runtime change yet"
    )


def test_decision_matrix_states(doc_text):
    lowered = doc_text.lower()
    assert "new / empty db" in lowered or "new empty db" in lowered or "new db" in lowered, (
        "Decision matrix must address a new/empty DB"
    )
    assert "stamped" in lowered, "Decision matrix must address a stamped DB"
    assert "unstamped" in lowered, "Decision matrix must address an unstamped legacy DB"
    assert "ahead" in lowered, "Decision matrix must address an ahead-of-code DB"


def test_fail_closed_on_ambiguity(doc_text):
    assert "fail closed" in doc_text.lower(), (
        "Plan must fail closed on ambiguity"
    )


def test_backup_requirement(doc_text):
    lowered = doc_text.lower()
    assert "backup" in lowered, "Plan must require a backup"
    assert "without backup" in lowered, (
        "Plan must forbid auto-upgrade on user data without backup"
    )


def test_rollback_requirement(doc_text):
    lowered = doc_text.lower()
    assert "rollback" in lowered, "Plan must include a rollback"
    assert "restore the backup" in lowered or "restore backup" in lowered, (
        "Rollback must restore the backup"
    )
    assert "disable the flag" in lowered or "disable flag" in lowered, (
        "Rollback must disable the flag"
    )


def test_no_destructive_migration(doc_text):
    assert "no destructive migration" in doc_text.lower(), (
        "Plan must forbid destructive migrations"
    )


def test_never_delete_accounting_rows(doc_text):
    assert "never delete accounting rows" in doc_text.lower(), (
        "Plan must preserve the never-delete-accounting-rows policy"
    )


def test_retirement_criteria_present(doc_text):
    lowered = doc_text.lower()
    assert "bake-in" in lowered, "Retirement criteria must include a bake-in period"
    assert "no legacy" in lowered, "Retirement criteria must require no legacy DBs"
    assert "parity" in lowered, "Retirement criteria must require PG parity"
