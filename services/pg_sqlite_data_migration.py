"""SQLite file → PostgreSQL row copy (Alembic 0002 schemas).

Used by test harnesses and operator cutover scripts. Never mutates the SQLite
source file. Production ``erp_data.db`` is only read when explicitly passed as
the source URL/path by an approved cutover script.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

import models  # noqa: F401 — register metadata
from db import Base

_SKIP_COPY_TABLES = frozenset({"alembic_version"})

_FORBIDDEN_SOURCE_FRAGMENTS = (
    "/production/",
    "production.db",
)


class UnsafeSqliteSourceUrlError(ValueError):
    """Raised when a SQLite source URL fails safety checks."""


def validate_sqlite_source_url(url: str, *, allow_erp_data: bool = False) -> str:
    """Allow disposable SQLite file URLs; optionally allow ``erp_data.db`` for cutover."""
    stripped = url.strip()
    if not stripped.startswith("sqlite:"):
        raise UnsafeSqliteSourceUrlError(f"Expected sqlite URL, got {stripped!r}")
    if stripped in ("sqlite://", "sqlite:///:memory:"):
        raise UnsafeSqliteSourceUrlError("Use a SQLite file URL, not memory")
    lowered = stripped.lower()
    if not allow_erp_data and "erp_data.db" in lowered:
        raise UnsafeSqliteSourceUrlError(
            "SQLite source must not reference erp_data.db unless allow_erp_data=True"
        )
    for forbidden in _FORBIDDEN_SOURCE_FRAGMENTS:
        if forbidden in lowered:
            raise UnsafeSqliteSourceUrlError(
                f"SQLite URL must not reference forbidden fragment {forbidden!r}"
            )
    return stripped


def sqlite_url_for_path(db_path: Path) -> str:
    return f"sqlite:///{db_path.as_posix()}"


def _table_names_in_dependency_order(metadata: MetaData) -> list[str]:
    return [table.name for table in metadata.sorted_tables]


def copy_sqlite_rows_to_postgres(*, sqlite_url: str, pg_url: str) -> dict[str, int]:
    """Bulk-copy all ORM tables from SQLite to PostgreSQL."""
    safe_sqlite = validate_sqlite_source_url(sqlite_url, allow_erp_data=True)
    sqlite_path = Path(safe_sqlite.replace("sqlite:///", ""))
    sqlite_engine = create_engine(
        safe_sqlite,
        connect_args={"check_same_thread": False},
    )
    pg_engine = create_engine(pg_url, pool_pre_ping=True, future=True)
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

    if not sqlite_path.exists():
        raise FileNotFoundError(f"SQLite source missing after copy: {sqlite_path}")

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
                text("SELECT pg_get_serial_sequence(:tbl, :col)"),
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


def table_row_counts(session) -> dict[str, int]:
    from sqlalchemy import func

    counts: dict[str, int] = {}
    for table in Base.metadata.sorted_tables:
        name = table.name
        if name.startswith("sqlite_"):
            continue
        counts[name] = session.execute(select(func.count()).select_from(table)).scalar() or 0
    return dict(sorted(counts.items()))
