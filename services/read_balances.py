"""FASTAPI-P0.2-A — read-only GL balance helpers with explicit company_id."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models import JournalEntry, JournalEntryLine

_ASSET_EXPENSE_TYPES = frozenset({"Asset", "Expense"})


def _net_balance_for_lines(account, lines) -> float:
    if account.account_type in _ASSET_EXPENSE_TYPES:
        return sum((line.debit or 0) - (line.credit or 0) for line in lines)
    return sum((line.credit or 0) - (line.debit or 0) for line in lines)


def calculate_account_balance_for_period(
    session: Session,
    account,
    start_date,
    end_date,
    exclude_refs=None,
    *,
    company_id: int | None,
) -> float:
    """Calculate an account's net balance from journal entries within a date range."""
    q = (
        session.query(JournalEntryLine)
        .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
        .filter(
            JournalEntryLine.account_id == account.id,
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
        )
    )
    if company_id is not None:
        q = q.filter(JournalEntry.company_id == company_id)
    if exclude_refs:
        q = q.filter(~JournalEntry.reference_type.in_(exclude_refs))
    return _net_balance_for_lines(account, q.all())


def calculate_account_balance(
    session: Session,
    account,
    *,
    company_id: int | None,
) -> float:
    """Calculate an account's all-time net balance from journal entries."""
    if company_id is not None:
        q = (
            session.query(JournalEntryLine)
            .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
            .filter(
                JournalEntryLine.account_id == account.id,
                JournalEntry.company_id == company_id,
            )
        )
    else:
        q = session.query(JournalEntryLine).filter_by(account_id=account.id)
    return _net_balance_for_lines(account, q.all())
