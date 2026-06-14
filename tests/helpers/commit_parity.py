"""FASTAPI-P0.5d-S0 — dual-run persisted-state parity helpers (test-only)."""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

import models

# Tables commonly touched by posting flows (extend per family in later slices).
DEFAULT_TABLES: tuple[type, ...] = (
    models.JournalEntry,
    models.JournalEntryLine,
    models.AuditLog,
    models.Sale,
    models.ChartOfAccounts,
    models.BankTransaction,
    models.BankAccount,
)


def table_row_counts(session: Session, tables: tuple[type, ...] = DEFAULT_TABLES) -> dict[str, int]:
    """Serializable row counts keyed by table name."""
    return {table.__tablename__: session.query(func.count()).select_from(table).scalar() or 0 for table in tables}


def journal_line_tuples(session: Session) -> list[tuple[int | None, int, float, float]]:
    """Ordered JE line tuples for GL parity comparison."""
    lines = (
        session.query(models.JournalEntryLine)
        .order_by(
            models.JournalEntryLine.journal_entry_id,
            models.JournalEntryLine.id,
        )
        .all()
    )
    return [(ln.journal_entry_id, ln.account_id, ln.debit or 0.0, ln.credit or 0.0) for ln in lines]


def sale_row_tuples(session: Session) -> list[tuple]:
    sales = session.query(models.Sale).order_by(models.Sale.id).all()
    return [
        (
            s.id,
            s.invoice_number,
            s.customer_name,
            s.amount,
            s.sale_type,
            s.paid_amount,
            s.balance,
            s.status,
            str(s.date),
            s.company_id,
        )
        for s in sales
    ]


def audit_row_tuples(session: Session) -> list[tuple]:
    rows = session.query(models.AuditLog).order_by(models.AuditLog.id).all()
    return [
        (
            r.action,
            r.entity_type,
            r.entity_id,
            r.description,
            r.performed_by,
            r.company_id,
        )
        for r in rows
    ]


def persisted_state_snapshot(
    session: Session,
    *,
    tables: tuple[type, ...] = DEFAULT_TABLES,
    include_journal_lines: bool = True,
    include_sale_rows: bool = True,
    include_audit_rows: bool = True,
) -> dict[str, Any]:
    """Compact persisted-state fingerprint for internal vs boundary dual-run."""
    snap: dict[str, Any] = {"counts": table_row_counts(session, tables)}
    if include_journal_lines:
        snap["journal_lines"] = journal_line_tuples(session)
    if include_sale_rows:
        snap["sales"] = sale_row_tuples(session)
    if include_audit_rows:
        snap["audit_rows"] = audit_row_tuples(session)
    return snap


def assert_persisted_state_equal(left: dict[str, Any], right: dict[str, Any]) -> None:
    assert left == right


def dual_run_parity(
    *,
    session_factory: Callable[[], Session],
    internal_runner: Callable[[Session], None],
    boundary_runner: Callable[[Session], None],
    tables: tuple[type, ...] = DEFAULT_TABLES,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the same flow twice on isolated sessions; return both snapshots.

    ``session_factory`` must return a fresh DB each call (e.g. new :memory:
    engine). Callers assert equality — used by future family flip tests only.
    """
    internal_session = session_factory()
    try:
        internal_runner(internal_session)
        internal_snap = persisted_state_snapshot(internal_session, tables=tables)
    finally:
        internal_session.close()

    boundary_session = session_factory()
    try:
        boundary_runner(boundary_session)
        boundary_snap = persisted_state_snapshot(boundary_session, tables=tables)
    finally:
        boundary_session.close()

    return internal_snap, boundary_snap
