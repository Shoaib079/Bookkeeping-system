"""POSTGRES-CUTOVER-PREP — test-only SQLite → PostgreSQL data copy helpers.

Thin wrapper over ``services.pg_sqlite_data_migration`` with stricter test-only
SQLite URL validation. Never touches production ``erp_data.db`` unless explicitly
allowed by operator cutover scripts in ``services/``.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from postgres_utils import (
    bootstrap_postgres_via_alembic,
    drop_all_pg_objects,
    validate_test_postgres_url,
)
from services.pg_sqlite_data_migration import (
    copy_sqlite_rows_to_postgres as _copy_sqlite_rows_to_postgres,
)
from tests.md05_migration_smoke_utils import (
    MoneySnapshot,
    capture_money_snapshot,
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


def copy_sqlite_rows_to_postgres(*, sqlite_url: str, pg_url: str) -> dict[str, int]:
    safe_sqlite = validate_sqlite_test_url(sqlite_url)
    safe_pg = validate_test_postgres_url(pg_url)
    return _copy_sqlite_rows_to_postgres(sqlite_url=safe_sqlite, pg_url=safe_pg)


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
