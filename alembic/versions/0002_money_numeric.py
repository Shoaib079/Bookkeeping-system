"""MD-05-IMPL-1 — Float money columns → Numeric(19,2/4/8).

Schema-only revision: alters column types per ``alembic/money_numeric_columns.py``.
Does **not** switch ``models.py`` (MD-05-IMPL-2). Quantization of existing values
(ROUND_HALF_UP) is MD-05-IMPL-3 ✅ — PG USING ``ROUND(col::numeric, scale)``.

**Not applied to production.** Apply only via flag-gated, backup-first cutover.
Rollback: restore from backup — downgrade is lossy.

See ``docs/MONEY_DECIMAL_05_NUMERIC_MIGRATION_PLAN.md``.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

from money_numeric_columns import grouped_by_table, iter_alter_targets

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _numeric_type(scale: int) -> sa.Numeric:
    return sa.Numeric(19, scale)


_INDEX_TABLE_RE = re.compile(r"\bON\s+(\w+)\s*\(", re.IGNORECASE)
_INDEX_NAME_RE = re.compile(r"INDEX\s+(\w+)\s+ON", re.IGNORECASE)


def _0001_supplemental_index_sql() -> tuple[str, ...]:
    """Load supplemental index DDL authored in revision 0001."""
    path = Path(__file__).with_name("0001_baseline.py")
    spec = importlib.util.spec_from_file_location("alembic_0001_baseline", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod._SUPPLEMENTAL_INDEX_SQL


def _table_for_index_ddl(ddl: str) -> str:
    match = _INDEX_TABLE_RE.search(ddl)
    return match.group(1) if match else ""


def _index_name_for_ddl(ddl: str) -> str | None:
    match = _INDEX_NAME_RE.search(ddl)
    return match.group(1) if match else None


def _reapply_sqlite_supplemental_indexes() -> None:
    """SQLite ``batch_alter_table`` rebuilds drop 0001 supplemental indexes — restore them."""
    bind = op.get_bind()
    altered_tables = set(grouped_by_table().keys())
    for ddl in _0001_supplemental_index_sql():
        if _table_for_index_ddl(ddl) not in altered_tables:
            continue
        index_name = _index_name_for_ddl(ddl)
        if index_name:
            bind.execute(text(f'DROP INDEX IF EXISTS "{index_name}"'))
        bind.execute(text(ddl))


def _upgrade_postgresql() -> None:
    for table, column, scale in iter_alter_targets():
        op.alter_column(
            table,
            column,
            existing_type=sa.Float(),
            type_=_numeric_type(scale),
            postgresql_using=f"ROUND({column}::numeric, {scale})",
        )


def _upgrade_sqlite_batch() -> None:
    for table, columns in grouped_by_table().items():
        with op.batch_alter_table(table) as batch_op:
            for column, scale in columns:
                batch_op.alter_column(
                    column,
                    existing_type=sa.Float(),
                    type_=_numeric_type(scale),
                )
    _reapply_sqlite_supplemental_indexes()


def _downgrade_postgresql() -> None:
    for table, column, scale in iter_alter_targets():
        op.alter_column(
            table,
            column,
            existing_type=_numeric_type(scale),
            type_=sa.Float(),
            postgresql_using=f"{column}::double precision",
        )


def _downgrade_sqlite_batch() -> None:
    for table, columns in grouped_by_table().items():
        with op.batch_alter_table(table) as batch_op:
            for column, scale in columns:
                batch_op.alter_column(
                    column,
                    existing_type=_numeric_type(scale),
                    type_=sa.Float(),
                )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _upgrade_postgresql()
    else:
        _upgrade_sqlite_batch()


def downgrade() -> None:
    """Lossy — prefer restore-from-backup for production rollback."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _downgrade_postgresql()
    else:
        _downgrade_sqlite_batch()
