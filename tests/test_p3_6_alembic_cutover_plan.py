"""P3.6 — contract test for the Alembic cutover plan.

Doc-only guard: verifies the cutover plan exists, carries the required sections, and
pins the safety invariants (no runtime change yet, migrate_schema active now,
Alembic authoritative only in a future approved slice, stamped/unstamped/new DB
handling, backup/rollback, PostgreSQL path, no automatic destructive migration).
No DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P3_6_ALEMBIC_CUTOVER_PLAN.md"

REQUIRED_SECTIONS = (
    "Current state",
    "Cutover target",
    "Startup behavior plan",
    "Safety rules",
    "Rollback strategy",
    "Test plan",
    "Future PostgreSQL path",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Cutover plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Cutover plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Cutover plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_says_no_runtime_change_yet(doc_text):
    assert "no runtime change yet" in doc_text.lower(), (
        "Plan must state no runtime change yet"
    )


def test_migrate_schema_remains_active_now(doc_text):
    lowered = doc_text.lower()
    assert "migrate_schema" in lowered and "authoritative now" in lowered, (
        "Plan must state migrate_schema remains active/authoritative now"
    )


def test_alembic_authoritative_only_in_future_slice(doc_text):
    lowered = doc_text.lower()
    assert "authoritative" in lowered and "future" in lowered and "slice" in lowered, (
        "Plan must state Alembic becomes authoritative only in a future approved slice"
    )


def test_mentions_stamped_db(doc_text):
    assert "stamped db" in doc_text.lower(), "Plan must address stamped DB startup"


def test_mentions_unstamped_db(doc_text):
    assert "unstamped" in doc_text.lower(), "Plan must address unstamped legacy DB"


def test_mentions_new_db(doc_text):
    lowered = doc_text.lower()
    assert "new / empty db" in lowered or "new empty db" in lowered or "new db" in lowered, (
        "Plan must address new/empty DB startup"
    )


def test_mentions_backup_and_rollback(doc_text):
    lowered = doc_text.lower()
    assert "backup" in lowered, "Plan must mention backup"
    assert "rollback" in lowered, "Plan must mention rollback"
    assert "restore the backup" in lowered or "restore backup" in lowered, (
        "Rollback must restore the backup"
    )


def test_mentions_postgresql_path(doc_text):
    assert "postgresql" in doc_text.lower(), "Plan must include the PostgreSQL path"


def test_no_automatic_destructive_migration(doc_text):
    lowered = doc_text.lower()
    assert "no destructive migration" in lowered, (
        "Plan must forbid destructive migrations"
    )
    assert "without backup" in lowered, (
        "Plan must forbid automatic upgrade on user data without backup"
    )


def test_never_delete_accounting_rows(doc_text):
    assert "never delete accounting rows" in doc_text.lower(), (
        "Plan must preserve the never-delete-accounting-rows policy"
    )
