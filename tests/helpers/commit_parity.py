"""FASTAPI-P0.5d-S0 — dual-run persisted-state parity helpers (test-only)."""

from __future__ import annotations

from typing import Any, Callable

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from services.money import line_money, money_to_float

# Tables commonly touched by posting flows (extend per family in later slices).
DEFAULT_TABLES: tuple[type, ...] = (
    models.JournalEntry,
    models.JournalEntryLine,
    models.AuditLog,
    models.Sale,
    models.ExpenseRecord,
    models.ChartOfAccounts,
    models.BankTransaction,
    models.BankAccount,
)

EXPENSE_TABLES: tuple[type, ...] = (
    models.JournalEntry,
    models.JournalEntryLine,
    models.AuditLog,
    models.ExpenseRecord,
    models.ChartOfAccounts,
    models.BankTransaction,
    models.BankAccount,
)

PURCHASE_PAYABLE_TABLES: tuple[type, ...] = (
    models.JournalEntry,
    models.JournalEntryLine,
    models.AuditLog,
    models.Purchase,
    models.Payable,
    models.Vendor,
    models.ChartOfAccounts,
    models.BankTransaction,
    models.BankAccount,
)

RECEIVABLE_PAYMENT_TABLES: tuple[type, ...] = (
    models.JournalEntry,
    models.JournalEntryLine,
    models.AuditLog,
    models.Sale,
    models.ChartOfAccounts,
    models.BankTransaction,
    models.BankAccount,
)

MOVEMENT_TABLES: tuple[type, ...] = (
    models.JournalEntry,
    models.JournalEntryLine,
    models.AuditLog,
    models.Partner,
    models.PartnerMovement,
    models.Worker,
    models.WorkerMovement,
    models.ChartOfAccounts,
    models.BankTransaction,
    models.BankAccount,
)

CLOSE_ALLOCATION_TABLES: tuple[type, ...] = (
    models.JournalEntry,
    models.JournalEntryLine,
    models.AuditLog,
    models.FiscalPeriod,
    models.PartnerProfitAllocation,
    models.PartnerProfitAllocationLine,
    models.Partner,
    models.YearEndClose,
    models.ChartOfAccounts,
)

RECONCILIATION_TABLES: tuple[type, ...] = (
    models.JournalEntry,
    models.JournalEntryLine,
    models.AuditLog,
    models.BankStatementRow,
    models.BankStatementImport,
    models.BankTransaction,
    models.BankAccount,
    models.ChartOfAccounts,
    models.ExpenseRecord,
)

VOID_CASCADE_TABLES: tuple[type, ...] = (
    models.JournalEntry,
    models.JournalEntryLine,
    models.AuditLog,
    models.Sale,
    models.ExpenseRecord,
    models.Purchase,
    models.Payable,
    models.BankTransaction,
    models.BankAccount,
    models.PartnerMovement,
    models.WorkerMovement,
    models.PartnerProfitAllocation,
    models.ChartOfAccounts,
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
    return [(ln.journal_entry_id, ln.account_id, line_money(ln.debit), line_money(ln.credit)) for ln in lines]


def sale_row_tuples(session: Session) -> list[tuple]:
    sales = session.query(models.Sale).order_by(models.Sale.id).all()
    return [
        (
            s.id,
            s.invoice_number,
            s.customer_name,
            money_to_float(s.amount),
            s.sale_type,
            money_to_float(s.paid_amount),
            money_to_float(s.balance),
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


def expense_row_tuples(session: Session) -> list[tuple]:
    rows = session.query(models.ExpenseRecord).order_by(models.ExpenseRecord.id).all()
    return [
        (
            r.id,
            r.expense_type,
            r.category,
            money_to_float(r.amount),
            r.payment_method,
            r.description,
            str(r.date),
            r.company_id,
            r.credit_card_account_id,
        )
        for r in rows
    ]


def bank_txn_row_tuples(session: Session) -> list[tuple]:
    rows = (
        session.query(models.BankTransaction)
        .order_by(models.BankTransaction.id)
        .all()
    )
    return [
        (
            t.id,
            t.account_id,
            money_to_float(t.amount),
            t.type,
            t.description,
            str(t.date),
            t.company_id,
            t.statement_ref,
            t.is_void,
        )
        for t in rows
    ]


def purchase_row_tuples(session: Session) -> list[tuple]:
    rows = session.query(models.Purchase).order_by(models.Purchase.id).all()
    return [
        (
            r.id,
            r.vendor_id,
            money_to_float(r.amount),
            r.purchase_type,
            r.gl_debit,
            r.description,
            str(r.date),
            r.company_id,
            r.credit_card_account_id,
        )
        for r in rows
    ]


def payable_row_tuples(session: Session) -> list[tuple]:
    rows = session.query(models.Payable).order_by(models.Payable.id).all()
    return [
        (
            r.id,
            r.vendor_id,
            money_to_float(r.amount),
            r.paid_amount,
            r.balance,
            r.paid,
            r.purchase_id,
            r.payment_method,
            str(r.date),
            str(r.due_date),
            r.company_id,
            r.credit_card_account_id,
        )
        for r in rows
    ]


def partner_movement_row_tuples(session: Session) -> list[tuple]:
    rows = (
        session.query(models.PartnerMovement)
        .order_by(models.PartnerMovement.id)
        .all()
    )
    return [
        (
            r.id,
            r.partner_id,
            r.movement_type,
            money_to_float(r.amount),
            r.bank_transaction_id,
            r.journal_entry_id,
            str(r.date),
            r.is_void,
            r.company_id,
        )
        for r in rows
    ]


def worker_movement_row_tuples(session: Session) -> list[tuple]:
    rows = (
        session.query(models.WorkerMovement)
        .order_by(models.WorkerMovement.id)
        .all()
    )
    return [
        (
            r.id,
            r.worker_id,
            r.movement_type,
            money_to_float(r.amount),
            r.gross_salary,
            r.deductions,
            r.advance_recovery,
            r.net_paid,
            r.bank_transaction_id,
            r.journal_entry_id,
            str(r.date),
            r.is_void,
            r.company_id,
        )
        for r in rows
    ]


def fiscal_period_row_tuples(session: Session) -> list[tuple]:
    rows = session.query(models.FiscalPeriod).order_by(models.FiscalPeriod.id).all()
    return [
        (
            r.id,
            r.name,
            str(r.start_date),
            str(r.end_date),
            r.is_closed,
            str(r.closed_at) if r.closed_at else None,
            r.closing_je_id,
            r.company_id,
        )
        for r in rows
    ]


def profit_allocation_row_tuples(session: Session) -> list[tuple]:
    rows = (
        session.query(models.PartnerProfitAllocation)
        .order_by(models.PartnerProfitAllocation.id)
        .all()
    )
    return [
        (
            r.id,
            r.fiscal_period_id,
            r.total_net_income,
            r.journal_entry_id,
            r.is_void,
            r.company_id,
        )
        for r in rows
    ]


def profit_allocation_line_tuples(session: Session) -> list[tuple]:
    rows = (
        session.query(models.PartnerProfitAllocationLine)
        .order_by(
            models.PartnerProfitAllocationLine.allocation_id,
            models.PartnerProfitAllocationLine.id,
        )
        .all()
    )
    return [
        (
            r.allocation_id,
            r.partner_id,
            r.share_pct,
            money_to_float(r.amount),
            r.company_id,
        )
        for r in rows
    ]


def year_end_close_row_tuples(session: Session) -> list[tuple]:
    rows = session.query(models.YearEndClose).order_by(models.YearEndClose.id).all()
    return [
        (
            r.id,
            r.fiscal_year,
            str(r.start_date),
            str(r.end_date),
            r.status,
            r.period_count,
            r.allocation_count,
            r.net_income_snapshot,
            r.re_balance_at_close,
            r.is_void,
            r.company_id,
        )
        for r in rows
    ]


def bank_statement_row_tuples(session: Session) -> list[tuple]:
    rows = (
        session.query(models.BankStatementRow)
        .order_by(models.BankStatementRow.id)
        .all()
    )
    return [
        (
            r.id,
            r.bank_statement_import_id,
            r.status,
            r.match_type,
            r.posted_journal_entry_id,
            r.bank_transaction_id,
            money_to_float(r.amount),
            r.vendor_id,
            r.payable_id,
            r.expense_record_id,
            r.partner_movement_id,
            r.worker_movement_id,
            r.clearing_sale_ids_json,
            r.settlement_row_id,
        )
        for r in rows
    ]


def bank_account_row_tuples(session: Session) -> list[tuple]:
    rows = session.query(models.BankAccount).order_by(models.BankAccount.id).all()
    return [
        (
            r.id,
            r.name,
            r.currency,
            r.balance,
            r.company_id,
            r.is_active,
        )
        for r in rows
    ]


def sale_void_row_tuples(session: Session) -> list[tuple]:
    rows = session.query(models.Sale).order_by(models.Sale.id).all()
    return [
        (
            s.id,
            s.is_void,
            s.status,
            str(s.voided_at) if s.voided_at else None,
            s.void_reason,
            s.company_id,
        )
        for s in rows
    ]


def expense_void_row_tuples(session: Session) -> list[tuple]:
    rows = session.query(models.ExpenseRecord).order_by(models.ExpenseRecord.id).all()
    return [
        (
            r.id,
            r.is_void,
            str(r.voided_at) if r.voided_at else None,
            r.void_reason,
            r.company_id,
        )
        for r in rows
    ]


def purchase_void_row_tuples(session: Session) -> list[tuple]:
    rows = session.query(models.Purchase).order_by(models.Purchase.id).all()
    return [
        (
            r.id,
            r.is_void,
            str(r.voided_at) if r.voided_at else None,
            r.void_reason,
            r.purchase_type,
            r.company_id,
        )
        for r in rows
    ]


def payable_void_row_tuples(session: Session) -> list[tuple]:
    rows = session.query(models.Payable).order_by(models.Payable.id).all()
    return [
        (
            r.id,
            r.is_void,
            r.paid,
            str(r.voided_at) if r.voided_at else None,
            r.void_reason,
            r.purchase_id,
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
    include_expense_rows: bool = False,
    include_bank_txn_rows: bool = False,
    include_purchase_rows: bool = False,
    include_payable_rows: bool = False,
    include_partner_movement_rows: bool = False,
    include_worker_movement_rows: bool = False,
    include_fiscal_period_rows: bool = False,
    include_profit_allocation_rows: bool = False,
    include_profit_allocation_lines: bool = False,
    include_year_end_close_rows: bool = False,
    include_bank_statement_rows: bool = False,
    include_bank_account_rows: bool = False,
    include_sale_void_rows: bool = False,
    include_expense_void_rows: bool = False,
    include_purchase_void_rows: bool = False,
    include_payable_void_rows: bool = False,
    include_audit_rows: bool = True,
) -> dict[str, Any]:
    """Compact persisted-state fingerprint for internal vs boundary dual-run."""
    snap: dict[str, Any] = {"counts": table_row_counts(session, tables)}
    if include_journal_lines:
        snap["journal_lines"] = journal_line_tuples(session)
    if include_sale_rows:
        snap["sales"] = sale_row_tuples(session)
    if include_expense_rows:
        snap["expenses"] = expense_row_tuples(session)
    if include_bank_txn_rows:
        snap["bank_txns"] = bank_txn_row_tuples(session)
    if include_purchase_rows:
        snap["purchases"] = purchase_row_tuples(session)
    if include_payable_rows:
        snap["payables"] = payable_row_tuples(session)
    if include_partner_movement_rows:
        snap["partner_movements"] = partner_movement_row_tuples(session)
    if include_worker_movement_rows:
        snap["worker_movements"] = worker_movement_row_tuples(session)
    if include_fiscal_period_rows:
        snap["fiscal_periods"] = fiscal_period_row_tuples(session)
    if include_profit_allocation_rows:
        snap["profit_allocations"] = profit_allocation_row_tuples(session)
    if include_profit_allocation_lines:
        snap["profit_allocation_lines"] = profit_allocation_line_tuples(session)
    if include_year_end_close_rows:
        snap["year_end_closes"] = year_end_close_row_tuples(session)
    if include_bank_statement_rows:
        snap["bank_statement_rows"] = bank_statement_row_tuples(session)
    if include_bank_account_rows:
        snap["bank_accounts"] = bank_account_row_tuples(session)
    if include_sale_void_rows:
        snap["sale_void_rows"] = sale_void_row_tuples(session)
    if include_expense_void_rows:
        snap["expense_void_rows"] = expense_void_row_tuples(session)
    if include_purchase_void_rows:
        snap["purchase_void_rows"] = purchase_void_row_tuples(session)
    if include_payable_void_rows:
        snap["payable_void_rows"] = payable_void_row_tuples(session)
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
    snapshot_kwargs: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the same flow twice on isolated sessions; return both snapshots.

    ``session_factory`` must return a fresh DB each call (e.g. new :memory:
    engine). Callers assert equality — used by future family flip tests only.
    """
    snap_kw = snapshot_kwargs or {}
    internal_session = session_factory()
    try:
        internal_runner(internal_session)
        internal_snap = persisted_state_snapshot(
            internal_session, tables=tables, **snap_kw
        )
    finally:
        internal_session.close()

    boundary_session = session_factory()
    try:
        boundary_runner(boundary_session)
        boundary_snap = persisted_state_snapshot(
            boundary_session, tables=tables, **snap_kw
        )
    finally:
        boundary_session.close()

    return internal_snap, boundary_snap
