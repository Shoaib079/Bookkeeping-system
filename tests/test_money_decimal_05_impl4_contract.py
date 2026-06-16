"""MD-05-IMPL-4 — static contracts for migration smoke slice."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVISION_0002_PATH = ROOT / "alembic" / "versions" / "0002_money_numeric.py"
IMPL4_DOC = ROOT / "docs" / "MONEY_DECIMAL_05_IMPL_4.md"
UTILS_PATH = ROOT / "tests" / "md05_migration_smoke_utils.py"


def test_impl4_doc_and_harness_exist():
    assert IMPL4_DOC.exists()
    assert UTILS_PATH.exists()
    assert (ROOT / "tests" / "test_money_decimal_05_impl4_migration_smoke.py").exists()


def test_0002_sqlite_reapplies_supplemental_indexes():
    src = REVISION_0002_PATH.read_text(encoding="utf-8")
    assert "_reapply_sqlite_supplemental_indexes" in src
    assert "_0001_supplemental_index_sql" in src
    assert "_reapply_sqlite_supplemental_indexes()" in src
