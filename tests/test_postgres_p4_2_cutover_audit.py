"""POSTGRES-P4.2 — contract test for the PG production cutover readiness audit.

Doc-only guard: verifies the audit exists, returns a NOT-READY verdict, lists the two
hard blockers (Alembic authority + Money-Decimal NUMERIC), the status of the ten
checks, required tests/slices, cutover checklist, rollback, and the no-change
invariants. Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "POSTGRES_P4_2_CUTOVER_AUDIT.md"

REQUIRED_SECTIONS = (
    "Verdict",
    "Status check",
    "Blocker list",
    "Nice-to-have list",
    "Required tests",
    "Required implementation slices",
    "Cutover checklist",
    "Rollback plan",
    "ROADMAP.md update recommendation",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"P4.2 audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"P4.2 audit doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "P4.2 audit doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_verdict_not_ready(doc_text):
    assert "not ready" in doc_text.lower(), "Verdict must be NOT READY"


def test_two_hard_blockers(doc_text):
    low = doc_text.lower()
    assert "alembic" in low and "not yet authoritative" in low, "Blocker 1: Alembic authority"
    assert "migrate_schema" in low and ("invalid on" in low or "cannot run on" in low), (
        "migrate_schema is SQLite-only / invalid on PG"
    )
    assert "money-decimal" in low or "numeric" in low, "Blocker 2: Money-Decimal NUMERIC"
    assert "0 `numeric`" in low or "0 numeric" in low or "still float" in low, (
        "Models still Float (0 Numeric)"
    )
    assert "0002" in doc_text, "No 0002 revision yet"


def test_status_checks(doc_text):
    low = doc_text.lower()
    assert "sqlite is production runtime" in low or "sqlite is production" in low, "SQLite runtime"
    assert "engine-agnostic" in low, "FastAPI/services engine-agnostic"
    assert "h03 deferred" in low or "h03" in low and "deferred" in low, "P2-HARDEN H03 deferred"
    assert "p4_1" in low or "p4.1" in low, "P4.1 local validation referenced"


def test_float_on_pg_not_recommended(doc_text):
    low = doc_text.lower()
    assert "float-on-pg" in low or "float on pg" in low, "Must address the Float-on-PG option"
    assert "not recommended" in low, "Float-on-PG swap is not recommended"
    assert "arithmetically" in low, "Note Float-on-PG is arithmetically safe (P3.1 R4)"


def test_required_tests(doc_text):
    low = doc_text.lower()
    assert "dual-run parity" in low, "Dual-run parity required"
    assert "golden vectors" in low and "decimal" in low, "Golden vectors under Decimal"
    assert "constraint preservation" in low, "Constraint preservation"


def test_mandatory_order(doc_text):
    low = doc_text.lower()
    assert "mandatory order" in low, "ROADMAP must state the mandatory order"
    assert "bake-in" in low, "P3.8 bake-in in the order"
    assert "data migration" in low, "Data migration project in the order"


def test_rollback_keeps_sqlite(doc_text):
    low = doc_text.lower()
    assert "keep sqlite" in low or "sqlite as the rollback target" in low, (
        "Rollback keeps SQLite as the target"
    )
    assert "revert" in low and "database_url" in low, "Rollback reverts DATABASE_URL"
    assert "never hand-edit accounting" in low, "Never hand-edit accounting tables"


def test_no_change_statement(doc_text):
    low = doc_text.lower()
    assert "audit only" in low, "Must state audit-only"
    assert "no runtime db switch" in low, "No runtime DB switch"
    assert "no feature flag flipped" in low, "No feature flag flipped"
    assert "no alembic change" in low, "No Alembic change"
