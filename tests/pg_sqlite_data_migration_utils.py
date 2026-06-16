"""POSTGRES-CUTOVER-PREP — test-only SQLite → PostgreSQL data copy helpers.

Copies row data from an ephemeral Alembic-built SQLite file DB into a disposable
PostgreSQL test DB (also Alembic-built). Never touches ``paths.DATABASE_URL`` or
production ``erp_data.db``.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import models  # noqa: F401 — register metadata
from db import Base
from postgres_utils import (
    bootstrap_postgres_via_alembic,
    drop_all_pg_objects,
    validate_test_postgres_url,
)
from tests.md05_migration_smoke_utils import (
    MoneySnapshot,
    capture_money_snapshot,
    make_sqlite_file_engine,
    run_alembic_upgrade,
    seed_smoke_tenant,
    session_for_url,
)

_FORBIDDEN_SQLITE_FRAGMENTS = (
    "erp_data.db",
    "/production/",
    "production.db",
)


class UnsafeSqliteTestUrlError(ValueError):
    """Raised when a SQLite URL fails test-only safety checks."""


def validate_sqlite_test_url(url: str) -> str:
    """Allow only disposable SQLite file URLs (reject production ``erp_data.db``)."""
    stripped = url.strip()
    if not stripped.startswith("sqlite:"):
        raise UnsafeSqliteTestUrlError(f"Expected sqlite URL, got {stripped!r}")
    lowered = stripped.lower()
    for forbidden in _FORBIDDEN_SQLITE_FRAGMENTS:
        if forbidden in lowered:
            raise UnsafeSqliteTestUrlError(
                f"SQLite URL must not reference production path fragment {forbidden!r}"
            )
    if stripped in ("sqlite://", "sqlite:///:memory:"):
        raise UnsafeSqliteTestUrlError("Use a disposable SQLite file URL, not memory")
    return stripped


def build_seeded_sqlite_at_head(db_path: Path) -> str:
    """Alembic 0001→0002 on a temp file DB with MD-05 smoke tenant."""
    database_url = f"sqlite:///{db_path.as_posix()}"
    validate_sqlite_test_url(database_url)
    run_alembic_upgrade(database_url, "0001")
    with session_for_url(database_url) as session:
        seed_smoke_tenant(session)
    run_alembic_upgrade(database_url, "0002")
    return database_url


def _table_names_in_dependency_order(metadata: MetaData) -> list[str]:
    return [table.name for table in metadata.sorted_tables]


_SKIP_COPY_TABLES = frozenset({"alembic_version"})


def copy_sqlite_rows_to_postgres(*, sqlite_url: str, pg_url: str) -> dict[str, int]:
    """Bulk-copy all ORM tables from SQLite to PostgreSQL (test DBs only)."""
    safe_sqlite = validate_sqlite_test_url(sqlite_url)
    safe_pg = validate_test_postgres_url(pg_url)

    sqlite_engine = make_sqlite_file_engine(Path(safe_sqlite.replace("sqlite:///", "")))
    pg_engine = create_engine(safe_pg, pool_pre_ping=True, future=True)
    row_counts: dict[str, int] = {}

    try:
        with pg_engine.begin() as pg_conn:
            pg_conn.execute(text("SET session_replication_role = 'replica'"))

        sqlite_session = sessionmaker(bind=sqlite_engine)()
        pg_session = sessionmaker(bind=pg_engine)()
        try:
            for table_name in _table_names_in_dependency_order(Base.metadata):
                if table_name in _SKIP_COPY_TABLES:
                    continue
                table = Base.metadata.tables[table_name]
                rows = sqlite_session.execute(select(table)).mappings().all()
                if not rows:
                    row_counts[table_name] = 0
                    continue
                pg_session.execute(table.insert(), [dict(row) for row in rows])
                row_counts[table_name] = len(rows)
            pg_session.commit()
        finally:
            sqlite_session.close()
            pg_session.close()

        _reset_pg_sequences(pg_engine)
        with pg_engine.begin() as pg_conn:
            pg_conn.execute(text("SET session_replication_role = 'origin'"))
    finally:
        sqlite_engine.dispose()
        pg_engine.dispose()

    return row_counts


def _reset_pg_sequences(engine: Engine) -> None:
    """Advance serial/identity sequences after explicit-id inserts."""
    insp = inspect(engine)
    with engine.begin() as conn:
        for table_name in insp.get_table_names():
            pk_cols = insp.get_pk_constraint(table_name).get("constrained_columns") or []
            if len(pk_cols) != 1:
                continue
            pk_col = pk_cols[0]
            default = conn.execute(
                text(
                    "SELECT pg_get_serial_sequence(:tbl, :col)"
                ),
                {"tbl": table_name, "col": pk_col},
            ).scalar_one_or_none()
            if not default:
                continue
            conn.execute(
                text(
                    f'SELECT setval(:seq, COALESCE((SELECT MAX("{pk_col}") FROM "{table_name}"), 1))'
                ),
                {"seq": default},
            )


def money_snapshots_equal(left: MoneySnapshot, right: MoneySnapshot) -> bool:
    return asdict(left) == asdict(right)


def snapshot_dict(snapshot: MoneySnapshot) -> dict[str, float]:
    return asdict(snapshot)


def migrate_smoke_sqlite_to_postgres(
    *,
    sqlite_path: Path,
    pg_url: str,
) -> tuple[dict[str, Any], dict[str, float], dict[str, float]]:
    """Build seeded SQLite, copy to Alembic PG, return counts + before/after snapshots."""
    sqlite_url = build_seeded_sqlite_at_head(sqlite_path)
    with session_for_url(sqlite_url) as session:
        before = capture_money_snapshot(session)

    pg_engine = bootstrap_postgres_via_alembic(pg_url)
    try:
        counts = copy_sqlite_rows_to_postgres(sqlite_url=sqlite_url, pg_url=pg_url)
        pg_session = sessionmaker(bind=pg_engine)()
        try:
            after = capture_money_snapshot(pg_session)
        finally:
            pg_session.close()
    finally:
        drop_all_pg_objects(pg_engine)
        pg_engine.dispose()

    return counts, snapshot_dict(before), snapshot_dict(after)
