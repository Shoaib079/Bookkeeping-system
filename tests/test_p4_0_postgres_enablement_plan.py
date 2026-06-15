"""P4.0 — contract test for the PostgreSQL production enablement plan.

Doc-only guard: verifies the enablement plan exists, carries the required sections,
and pins the invariants (SQLite stays runtime, Alembic-only PG path, no migrate_schema
on PG, test-DB-first with ERP_TEST_POSTGRES_URL safety, schema equivalence + dual-run
parity, Float unchanged, do-not-proceed criteria, no runtime switch). Pure stdlib;
no app imports; no DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P4_0_POSTGRES_ENABLEMENT_PLAN.md"

REQUIRED_SECTIONS = (
    "Current state",
    "PostgreSQL prerequisites",
    "Validation sequence",
    "Known limitations",
    "Production cutover",
    "Do-not-proceed criteria",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Enablement plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Enablement plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Enablement plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_sqlite_remains_runtime(doc_text):
    lowered = doc_text.lower()
    assert "sqlite remains the runtime" in lowered, "Plan must keep SQLite as the runtime DB"
    assert "database_url" in lowered and "unchanged" in lowered, (
        "Plan must state DATABASE_URL is unchanged"
    )


def test_alembic_only_pg_path(doc_text):
    lowered = doc_text.lower()
    assert "alembic-only" in lowered, "Plan must state an Alembic-only PG path"
    assert "no migrate_schema on pg" in lowered or (
        "migrate_schema" in lowered and "pg" in lowered and "never run" in lowered
    ), "Plan must state migrate_schema never runs on PG"


def test_driver_choice(doc_text):
    lowered = doc_text.lower()
    assert "psycopg" in lowered, "Plan must specify the psycopg driver"
    assert "optional" in lowered, "Driver must be an optional dependency"


def test_test_db_first_and_env_safety(doc_text):
    lowered = doc_text.lower()
    assert "test db only first" in lowered or "test-db-first" in lowered or "test db only" in lowered, (
        "Plan must validate test DB first"
    )
    assert "erp_test_postgres_url" in lowered, "Plan must reference ERP_TEST_POSTGRES_URL"
    assert "skip" in lowered, "PG tests must skip when the test URL is unset"
    assert "never touch production first" in lowered, "Plan must never touch production first"


def test_equivalence_and_parity(doc_text):
    lowered = doc_text.lower()
    assert "schema equivalence" in lowered, "Plan must require schema equivalence"
    assert "dual-run parity" in lowered, "Plan must require dual-run parity"
    assert "alembic upgrade head" in lowered, "Plan must use alembic upgrade head on empty PG"


def test_backup_restore(doc_text):
    lowered = doc_text.lower()
    assert "pg_dump" in lowered and "pg_restore" in lowered, (
        "Plan must define a pg_dump/pg_restore backup/restore plan"
    )


def test_known_limitations(doc_text):
    lowered = doc_text.lower()
    assert "float" in lowered and "unchanged" in lowered, "Float money must remain unchanged"
    assert "naive datetime" in lowered, "Naive datetimes must be noted"
    assert "case-sensitiv" in lowered, "Case-sensitivity difference must be noted"
    assert "performance" in lowered and "later" in lowered, "Performance/index checks are later"


def test_production_cutover_later(doc_text):
    lowered = doc_text.lower()
    assert "fresh pg db via alembic" in lowered, "Cutover must create a fresh PG DB via Alembic"
    assert "separate project" in lowered, "Data migration must be a separate project"
    assert "verify balances" in lowered, "Cutover must verify balances/reports"
    assert "rollback" in lowered, "Cutover must have a rollback plan"


def test_do_not_proceed_criteria(doc_text):
    lowered = doc_text.lower()
    assert "schema mismatch" in lowered, "Do-not-proceed must include schema mismatch"
    assert "parity mismatch" in lowered, "Do-not-proceed must include parity mismatch"
    assert "missing indexes" in lowered, "Do-not-proceed must include missing indexes/constraints"
    assert "money rounding difference" in lowered, "Do-not-proceed must include money rounding difference"
    assert "report difference" in lowered, "Do-not-proceed must include report difference"
    assert "accounting mismatch" in lowered, "Do-not-proceed must include any accounting mismatch"


def test_no_runtime_switch(doc_text):
    lowered = doc_text.lower()
    assert "no runtime switch" in lowered, "Plan must state no runtime switch"
    assert "planned, not executed" in lowered or "not executed" in lowered, (
        "Plan must state enablement is planned, not executed"
    )
    assert "float → decimal" in lowered or "float to decimal" in lowered or "no `float → decimal`" in lowered, (
        "Plan must state no Float to Decimal conversion"
    )
