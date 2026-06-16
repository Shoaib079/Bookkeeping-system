"""MD-05-IMPL-1 — contract tests for Alembic revision 0002_money_numeric.

Verifies authored migration metadata, MD-05 column classification, and ephemeral
SQLite upgrade 0001→0002 on an empty database. Does not touch production
``erp_data.db`` or switch ``models.py``.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine

from money_numeric_columns import (
    FLOAT_REMAIN,
    NUMERIC_19_2,
    NUMERIC_19_4,
    NUMERIC_19_8,
    iter_alter_targets,
    scale_for,
)
from p3_schema_equivalence_utils import BASELINE_0001_PATH

ROOT = Path(__file__).resolve().parents[1]
REVISION_0002_PATH = ROOT / "alembic" / "versions" / "0002_money_numeric.py"
CLASSIFICATION_PATH = ROOT / "money_numeric_columns.py"
PRODUCTION_DB = ROOT / "erp_data.db"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def baseline_0001_sha256() -> str:
    return _sha256(BASELINE_0001_PATH)


@pytest.fixture(scope="module")
def revision_source() -> str:
    assert REVISION_0002_PATH.exists(), f"Missing revision: {REVISION_0002_PATH}"
    return REVISION_0002_PATH.read_text(encoding="utf-8")


def _model_float_columns() -> set[tuple[str, str]]:
    import re

    src = (ROOT / "models.py").read_text(encoding="utf-8")
    table: str | None = None
    cols: set[tuple[str, str]] = set()
    for line in src.splitlines():
        m_tab = re.search(r"""__tablename__\s*=\s*["'](\w+)["']""", line)
        if m_tab:
            table = m_tab.group(1)
        m_col = re.search(r"(\w+)\s*=\s*Column\(Float", line)
        if m_col and table:
            cols.add((table, m_col.group(1)))
    return cols


def _make_memory_engine() -> Engine:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
        if engine.dialect.name != "sqlite":
            return
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


def _column_type_name(engine: Engine, table: str, column: str) -> str:
    with engine.connect() as conn:
        rows = conn.execute(text(f'PRAGMA table_info("{table}")')).fetchall()
    for row in rows:
        if row[1] == column:
            return str(row[2]).upper()
    raise KeyError(f"{table}.{column} not found")


def test_0002_revision_file_exists():
    assert REVISION_0002_PATH.name == "0002_money_numeric.py"
    assert REVISION_0002_PATH.stat().st_size > 500


def test_revision_metadata(revision_source):
    assert 'revision = "0002"' in revision_source
    assert 'down_revision = "0001"' in revision_source
    assert "money_numeric_columns" in revision_source


def test_0001_baseline_untouched(baseline_0001_sha256):
    baseline_src = BASELINE_0001_PATH.read_text(encoding="utf-8")
    lowered = baseline_src.lower()
    assert "numeric(" not in lowered
    assert "alter_column" not in lowered
    assert 'revision = "0001"' in baseline_src
    assert baseline_0001_sha256 == _sha256(BASELINE_0001_PATH)


def test_classification_module_exists():
    assert CLASSIFICATION_PATH.exists()
    assert CLASSIFICATION_PATH.stat().st_size > 1000


def _model_numeric_columns() -> set[tuple[str, str]]:
    src = (ROOT / "models.py").read_text(encoding="utf-8")
    table: str | None = None
    cols: set[tuple[str, str]] = set()
    for line in src.splitlines():
        m_tab = re.search(r"""__tablename__\s*=\s*["'](\w+)["']""", line)
        if m_tab:
            table = m_tab.group(1)
        m_col = re.search(r"(\w+)\s*=\s*Column\(NUMERIC_", line)
        if m_col and table:
            cols.add((table, m_col.group(1)))
    return cols


def test_classification_covers_all_model_numeric_columns():
    model_cols = _model_numeric_columns()
    classified = NUMERIC_19_2 | NUMERIC_19_4 | NUMERIC_19_8
    assert len(model_cols) == 88
    assert classified == model_cols


def test_model_float_columns_are_float_remain_only():
    model_float = _model_float_columns()
    assert len(model_float) == 11
    assert model_float == FLOAT_REMAIN


def test_no_overlap_between_tiers():
    pairs = [
        (NUMERIC_19_2, NUMERIC_19_4),
        (NUMERIC_19_2, NUMERIC_19_8),
        (NUMERIC_19_2, FLOAT_REMAIN),
        (NUMERIC_19_4, NUMERIC_19_8),
        (NUMERIC_19_4, FLOAT_REMAIN),
        (NUMERIC_19_8, FLOAT_REMAIN),
    ]
    for left, right in pairs:
        assert not (left & right), f"overlap: {left & right}"


def test_tier_counts():
    assert len(NUMERIC_19_2) == 80
    assert len(NUMERIC_19_4) == 5
    assert len(NUMERIC_19_8) == 3
    assert len(FLOAT_REMAIN) == 11
    assert len(list(iter_alter_targets())) == 88


@pytest.mark.parametrize("table,column", sorted(NUMERIC_19_4))
def test_native_columns_numeric_19_4(table, column):
    assert scale_for(table, column) == 4


@pytest.mark.parametrize("table,column", sorted(NUMERIC_19_8))
def test_fx_rate_columns_numeric_19_8(table, column):
    assert scale_for(table, column) == 8


@pytest.mark.parametrize("table,column", sorted(FLOAT_REMAIN))
def test_quantity_percentage_remain_float(table, column):
    assert scale_for(table, column) is None


def test_money_columns_target_numeric_19_2(revision_source):
    for table, column in sorted(NUMERIC_19_2):
        assert f'("{table}", "{column}")' in CLASSIFICATION_PATH.read_text(encoding="utf-8")
    assert "Numeric(19, 2)" in revision_source or "Numeric(19," in revision_source


def test_upgrade_alters_no_float_remain_columns(revision_source):
    for table, column in FLOAT_REMAIN:
        pattern = rf"alter_column\(\s*[\n\s]*{table!r},\s*[\n\s]*{column!r}"
        assert re.search(pattern, revision_source) is None


def test_ephemeral_sqlite_upgrade_0001_to_0002(tmp_path):
    alembic_bin = shutil.which("alembic")
    if not alembic_bin:
        pytest.skip("alembic CLI not on PATH")

    db_path = tmp_path / "md05_impl1_empty.db"
    database_url = f"sqlite:///{db_path.as_posix()}"
    env = {**os.environ, "DATABASE_URL": database_url}
    for target in ("0001", "0002"):
        result = subprocess.run(
            [alembic_bin, "upgrade", target],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr or result.stdout

    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    try:
        with engine.connect() as conn:
            rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert rev == "0002"

        for table, column in sorted(NUMERIC_19_2 | NUMERIC_19_4 | NUMERIC_19_8):
            type_name = _column_type_name(engine, table, column)
            assert "NUM" in type_name or "DEC" in type_name, (
                f"{table}.{column} expected Numeric affinity, got {type_name!r}"
            )

        for table, column in sorted(FLOAT_REMAIN):
            type_name = _column_type_name(engine, table, column)
            assert type_name == "FLOAT", f"{table}.{column} should remain FLOAT, got {type_name!r}"

        insp = inspect(engine)
        assert insp.has_table("journal_entries")
        assert insp.has_table("sales")
    finally:
        engine.dispose()


def test_production_db_not_used_by_harness():
    assert "erp_data.db" not in REVISION_0002_PATH.read_text(encoding="utf-8")
    assert not str(PRODUCTION_DB).startswith("/tmp")


def test_models_use_numeric_for_money_columns():
    models_src = (ROOT / "models.py").read_text(encoding="utf-8")
    assert "NUMERIC_MONEY = Numeric(19, 2, asdecimal=True)" in models_src
    assert "NUMERIC_FX = Numeric(19, 4, asdecimal=True)" in models_src
    assert "NUMERIC_RATE = Numeric(19, 8, asdecimal=True)" in models_src
    assert models_src.count("Column(NUMERIC_MONEY") >= 80
    assert models_src.count("Column(Float") == 11
