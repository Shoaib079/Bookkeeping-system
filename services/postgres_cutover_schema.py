"""PostgreSQL cutover schema — verify Alembic head schema and stamp safely."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from services.alembic_runner import AlembicCommandResult, get_current_revision, run_stamp
from services.schema_version import resolve_head_revision

_HEAD_REVISION = "0002"
_NUMERIC_MONEY_PROBE = ("journal_entry_lines", "debit")


@dataclass(frozen=True, slots=True)
class PgAlembicState:
    has_alembic_version_table: bool
    current_revision: str | None
    head_revision: str
    companies_count: int
    journal_entry_lines_count: int


@dataclass(frozen=True, slots=True)
class PgSchemaVerifyResult:
    ok: bool
    message: str


def inspect_pg_alembic_state(engine: Engine) -> PgAlembicState:
    head = resolve_head_revision() or _HEAD_REVISION
    with engine.connect() as conn:
        insp = inspect(conn)
        has_av = insp.has_table("alembic_version")
        rev: str | None = None
        if has_av:
            rows = conn.execute(text("SELECT version_num FROM alembic_version")).fetchall()
            if len(rows) == 1:
                rev = str(rows[0][0])
        companies = 0
        jel = 0
        if insp.has_table("companies"):
            companies = conn.execute(text('SELECT COUNT(*) FROM "companies"')).scalar() or 0
        if insp.has_table("journal_entry_lines"):
            jel = conn.execute(text('SELECT COUNT(*) FROM "journal_entry_lines"')).scalar() or 0
    return PgAlembicState(
        has_alembic_version_table=has_av,
        current_revision=rev,
        head_revision=head,
        companies_count=int(companies),
        journal_entry_lines_count=int(jel),
    )


def verify_pg_schema_matches_head(engine: Engine, *, head_revision: str | None = None) -> PgSchemaVerifyResult:
    """Read-only: populated PG looks like Alembic ``0002`` without running migrations."""
    head = head_revision or resolve_head_revision() or _HEAD_REVISION
    state = inspect_pg_alembic_state(engine)
    if state.companies_count == 0 and state.journal_entry_lines_count == 0:
        return PgSchemaVerifyResult(ok=False, message="PostgreSQL database has no application rows.")
    with engine.connect() as conn:
        insp = inspect(conn)
        for table in ("companies", "journal_entries", "journal_entry_lines", "chart_of_accounts"):
            if not insp.has_table(table):
                return PgSchemaVerifyResult(
                    ok=False,
                    message=f"Missing expected table {table!r} for revision {head}.",
                )
        table, column = _NUMERIC_MONEY_PROBE
        cols = insp.get_columns(table)
        col = next((c for c in cols if c["name"] == column), None)
        if col is None:
            return PgSchemaVerifyResult(
                ok=False,
                message=f"Missing column {table}.{column}.",
            )
        col_type = col.get("type")
        prec = getattr(col_type, "precision", None)
        scale = getattr(col_type, "scale", None)
        if prec != 19 or scale != 2:
            return PgSchemaVerifyResult(
                ok=False,
                message=(
                    f"{table}.{column} expected NUMERIC(19,2) for revision {head}, "
                    f"got precision={prec!r} scale={scale!r}."
                ),
            )
    if state.current_revision == head:
        return PgSchemaVerifyResult(ok=True, message=f"Already stamped at head {head}.")
    return PgSchemaVerifyResult(
        ok=True,
        message=f"Schema matches Alembic head {head}; safe to stamp only.",
    )


def ensure_pg_stamped_at_head(
    database_url: str,
    *,
    head_revision: str | None = None,
    allow_execute: bool = True,
) -> AlembicCommandResult:
    """Stamp ``alembic_version`` at head when schema already matches (no DDL/data reload)."""
    from sqlalchemy import create_engine

    head = head_revision or resolve_head_revision() or _HEAD_REVISION
    current = get_current_revision(database_url, allow_production=True)
    if current == head:
        return AlembicCommandResult(
            command="stamp",
            target=head,
            success=True,
            message=f"PostgreSQL already stamped at {head}.",
            dry_run=not allow_execute,
            executed=False,
            argv=(),
        )

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        verify = verify_pg_schema_matches_head(engine, head_revision=head)
        if not verify.ok:
            raise RuntimeError(verify.message)
    finally:
        engine.dispose()

    return run_stamp(
        database_url=database_url,
        revision=head,
        allow_execute=allow_execute,
        allow_production=True,
    )
