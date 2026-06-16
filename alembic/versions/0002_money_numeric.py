"""MD-05-IMPL-1 — Float money columns → Numeric(19,2/4/8).

Schema-only revision: alters column types per ``alembic/money_numeric_columns.py``.
Does **not** switch ``models.py`` (MD-05-IMPL-2). Quantization of existing values
(ROUND_HALF_UP) is MD-05-IMPL-3.

**Not applied to production.** Apply only via flag-gated, backup-first cutover.
Rollback: restore from backup — downgrade is lossy.

See ``docs/MONEY_DECIMAL_05_NUMERIC_MIGRATION_PLAN.md``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from money_numeric_columns import grouped_by_table, iter_alter_targets

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _numeric_type(scale: int) -> sa.Numeric:
    return sa.Numeric(19, scale)


def _upgrade_postgresql() -> None:
    for table, column, scale in iter_alter_targets():
        op.alter_column(
            table,
            column,
            existing_type=sa.Float(),
            type_=_numeric_type(scale),
            postgresql_using=f"{column}::numeric(19,{scale})",
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
