#!/usr/bin/env python3
"""Operator script — SQLite → PostgreSQL production cutover (data migrate + verify).

Requires env gates documented in docs/POSTGRES_PRODUCTION_CUTOVER.md.
Does not modify the SQLite source file (read-only). Preserves backup path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

if "streamlit" not in sys.modules:
    from unittest.mock import MagicMock

    sys.modules["streamlit"] = MagicMock(session_state={})

import app  # noqa: F401

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from paths import DB_PATH, get_database_url
from postgres_utils import bootstrap_postgres_via_alembic, postgres_alembic_head_revision
from services.pg_sqlite_data_migration import copy_sqlite_rows_to_postgres, sqlite_url_for_path
from services.postgres_cutover_schema import ensure_pg_stamped_at_head, inspect_pg_alembic_state
from services.postgres_cutover_verify import (
    compare_sqlite_postgres_parity,
    company_isolation_check,
)
from services.postgres_runtime_cutover import (
    BACKUP_PATH_ENV_VAR,
    RUNTIME_CUTOVER_APPROVAL_PHRASE,
    RUNTIME_URL_ENV_VAR,
    evaluate_runtime_cutover,
    validate_postgres_runtime_url,
)
from tests.md05_migration_smoke_utils import make_sqlite_file_engine, run_alembic_upgrade


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mask_url(url: str) -> str:
    if "@" in url:
        scheme, rest = url.split("://", 1)
        creds, host = rest.split("@", 1)
        return f"{scheme}://***@{host}"
    return url


def _ensure_sqlite_at_head(sqlite_path: Path) -> str:
    sqlite_url = sqlite_url_for_path(sqlite_path)
    engine = make_sqlite_file_engine(sqlite_path)
    with engine.connect() as conn:
        rev = None
        if conn.dialect.has_table(conn, "alembic_version"):
            rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    engine.dispose()
    if rev == "0001":
        run_alembic_upgrade(sqlite_url, "0002")
    elif rev != "0002":
        print(f"WARN: unexpected alembic revision {rev!r}; proceeding without upgrade", file=sys.stderr)
    return sqlite_url


def main() -> int:
    parser = argparse.ArgumentParser(description="SQLite → PostgreSQL production cutover")
    parser.add_argument(
        "--sqlite-source",
        type=Path,
        default=DB_PATH,
        help="SQLite source file (read-only; default erp_data.db)",
    )
    parser.add_argument(
        "--skip-pg-bootstrap",
        action="store_true",
        help="Assume PG schema already at Alembic head (0002)",
    )
    args = parser.parse_args()

    evaluation = evaluate_runtime_cutover()
    if evaluation.blocked_reason:
        print(f"ERROR: cutover gates blocked — {evaluation.blocked_reason}", file=sys.stderr)
        return 1

    pg_url = evaluation.runtime_url
    if not pg_url:
        print(f"ERROR: {RUNTIME_URL_ENV_VAR} not set or invalid", file=sys.stderr)
        return 1
    pg_url = validate_postgres_runtime_url(pg_url)

    sqlite_path = args.sqlite_source.expanduser().resolve()
    if not sqlite_path.is_file():
        print(f"ERROR: SQLite source missing: {sqlite_path}", file=sys.stderr)
        return 1

    backup_path = Path(evaluation.backup_path or "")
    if not backup_path.is_file():
        print(f"ERROR: backup missing at {BACKUP_PATH_ENV_VAR}", file=sys.stderr)
        return 1

    prod_hash_before = _sha256(DB_PATH) if DB_PATH.is_file() else None
    source_hash = _sha256(sqlite_path)

    sqlite_url = _ensure_sqlite_at_head(sqlite_path)
    sqlite_engine = make_sqlite_file_engine(sqlite_path)
    SqliteSession = sessionmaker(bind=sqlite_engine)

    if args.skip_pg_bootstrap:
        from sqlalchemy import create_engine

        pg_engine = create_engine(pg_url, pool_pre_ping=True)
    else:
        pg_engine = bootstrap_postgres_via_alembic(pg_url)

    assert postgres_alembic_head_revision(pg_engine) == "0002"

    try:
        alembic_before = inspect_pg_alembic_state(pg_engine)
        copy_counts = copy_sqlite_rows_to_postgres(sqlite_url=sqlite_url, pg_url=pg_url)
        stamp_result = ensure_pg_stamped_at_head(pg_url, allow_execute=True)
        alembic_after = inspect_pg_alembic_state(pg_engine)
        with SqliteSession() as sqlite_session, sessionmaker(bind=pg_engine)() as pg_session:
            parity = compare_sqlite_postgres_parity(
                sqlite_session=sqlite_session,
                pg_session=pg_session,
            )
            isolation = company_isolation_check(pg_session)
    finally:
        sqlite_engine.dispose()
        pg_engine.dispose()

    prod_hash_after = _sha256(DB_PATH) if DB_PATH.is_file() else None

    out = {
        "sqlite_source_path": str(sqlite_path),
        "sqlite_source_hash": source_hash,
        "backup_path": str(backup_path),
        "backup_hash": _sha256(backup_path),
        "postgresql_url_masked": _mask_url(pg_url),
        "production_erp_data_touched": prod_hash_before != prod_hash_after,
        "production_hash_before_after": [prod_hash_before, prod_hash_after],
        "approval_phrase": RUNTIME_CUTOVER_APPROVAL_PHRASE,
        "tables_copied": copy_counts,
        "row_count_mismatches": parity["row_count_mismatches"],
        "trial_balance_mismatches": parity["trial_balance_mismatches"],
        "report_mismatches": parity["report_mismatches"],
        "company_isolation": isolation,
        "companies": parity["companies"],
        "parity_ok": parity["parity_ok"] and isolation["company_isolation_ok"],
        "alembic_before": {
            "has_table": alembic_before.has_alembic_version_table,
            "revision": alembic_before.current_revision,
        },
        "alembic_after": {
            "has_table": alembic_after.has_alembic_version_table,
            "revision": alembic_after.current_revision,
        },
        "alembic_stamp": {
            "success": stamp_result.success,
            "message": stamp_result.message,
            "executed": stamp_result.executed,
        },
        "runtime_database_url_after_gate": get_database_url(),
    }
    print(json.dumps(out, indent=2, default=str))
    return 0 if out["parity_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
