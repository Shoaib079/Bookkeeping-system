"""MONEY-DECIMAL-05 — contract test for the Numeric migration plan.

Doc-only guard: verifies the plan exists, carries all seven required outputs, pins the
2/4/8-dp classification, the new-0002 / never-edit-0001 strategy, the SQLite-exactness
caveat, the risk/test plans, the do-not-touch list, and the no-change invariants. Pure
stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "MONEY_DECIMAL_05_NUMERIC_MIGRATION_PLAN.md"
)

REQUIRED_SECTIONS = (
    "Column classification",
    "Migration plan",
    "Risk list",
    "Test plan",
    "Safe implementation slices",
    "Do-not-touch list",
    "ROADMAP update recommendation",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"MD-05 plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"MD-05 plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "MD-05 plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_precision_tiers(doc_text):
    for tier in ("Numeric(19, 2)", "Numeric(19, 4)", "Numeric(19, 8)"):
        assert tier in doc_text, f"Classification must include {tier}"


def test_tier_targets(doc_text):
    low = doc_text.lower()
    assert "amount_native" in low or "native_amount" in low, "4dp tier = native FX amounts"
    assert "fx_rate" in low, "8dp tier = fx_rate"
    assert "debit" in low and "credit" in low, "2dp tier = GL debit/credit"


def test_quantity_percentage_remain_float(doc_text):
    low = doc_text.lower()
    assert "remain" in low and "float" in low, "Some columns remain Float"
    assert "quantity" in low and "min_stock" in low, "Quantities remain Float"
    assert "profit_share_pct" in low or "share_pct" in low, "Percentages remain Float"


def test_new_0002_never_edit_0001(doc_text):
    low = doc_text.lower()
    assert "0002" in doc_text, "Must create revision 0002"
    assert "never edit" in low and "0001" in doc_text, "Must never edit 0001_baseline"


def test_pg_direct_sqlite_batch(doc_text):
    low = doc_text.lower()
    assert "alter column" in low and "numeric" in low, "PG direct ALTER COLUMN TYPE NUMERIC"
    assert "batch_alter_table" in low or "batch alter" in low, "SQLite batch alter / rebuild"
    assert "using" in low, "PG conversion via USING clause"


def test_sqlite_exactness_caveat(doc_text):
    low = doc_text.lower()
    assert "no true decimal" in low or "no real decimal" in low, (
        "Must state SQLite has no true decimal type"
    )
    assert "postgresql" in low and "exact" in low, "Exactness lands on PostgreSQL"


def test_risk_quantization_and_rollback(doc_text):
    low = doc_text.lower()
    assert "quantiz" in low and "round_half_up" in low, "Quantization risk (ROUND_HALF_UP)"
    assert "restore-from-backup" in low or "restore backup" in low or "restore from backup" in low, (
        "Rollback = restore from backup"
    )
    assert "golden vector" in low, "Golden vectors are the guard"


def test_test_plan(doc_text):
    low = doc_text.lower()
    assert "sqlite migration smoke" in low or "sqlite smoke" in low, "SQLite smoke test"
    assert "erp_test_postgres_url" in low, "Optional PG migration test"
    assert "reports" in low and ("to the cent" in low or "match" in low), "Reports must still match"
    assert "constraint preservation" in low, "Constraint preservation test"


def test_slices_not_implemented(doc_text):
    low = doc_text.lower()
    assert "do not implement" in low, "Slices must be marked do-not-implement"
    for s in ("md-05-impl-1", "md-05-impl-5"):
        assert s in low, f"Slices must include {s}"


def test_cutover_reuses_p38(doc_text):
    low = doc_text.lower()
    assert "p3.8" in low, "Cutover must reuse the P3.8 flag-gated machinery"
    assert "backup" in low and "confirmation" in low, "Backup + owner confirmation gates"
    assert "dual-run parity" in low, "PG dual-run parity gate"


def test_no_change_statement(doc_text):
    low = doc_text.lower()
    assert "audit" in low and "planning only" in low, "Must state audit/planning only"
    assert "no production code" in low, "No production code"
    assert "no `models.py`" in low or "no models.py" in low, "No models.py change"
    assert "no postgresql runtime switch" in low, "No PG runtime switch"
