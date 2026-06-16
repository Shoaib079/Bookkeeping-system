"""FASTAPI-P0.2-C — read-only general ledger DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import ChartOfAccounts, JournalEntry, JournalEntryLine
from services.money import line_money, money_to_float
from services.read_balances import calculate_account_balance

_ASSET_EXPENSE_TYPES = frozenset({"Asset", "Expense"})


def _balance_delta(account_type: str, debit: float, credit: float) -> float:
    if account_type in _ASSET_EXPENSE_TYPES:
        return (debit or 0) - (credit or 0)
    return (credit or 0) - (debit or 0)


@dataclass(frozen=True, slots=True)
class LedgerRow:
    date: datetime.date
    reference: str | None
    description: str
    debit: float
    credit: float
    running_balance: float
    account_id: int
    account_code: str
    account_name: str
    journal_entry_id: int
    company_id: int
    journal_entry_line_id: int


@dataclass(frozen=True, slots=True)
class LedgerFilters:
    account_id: int
    start_date: datetime.date | None
    end_date: datetime.date | None
    search_keyword: str | None


@dataclass(frozen=True, slots=True)
class LedgerPage:
    rows: tuple[LedgerRow, ...]
    filters: LedgerFilters
    opening_balance: float
    closing_balance: float
    row_count: int
    total_debit: float
    total_credit: float
    account_type: str
    current_balance: float


def _query_ledger_lines(
    session: Session,
    *,
    company_id: int,
    account_id: int,
):
    return (
        session.query(JournalEntryLine)
        .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
        .filter(
            JournalEntryLine.account_id == account_id,
            JournalEntry.company_id == company_id,
        )
        .order_by(JournalEntry.entry_date, JournalEntry.id)
        .all()
    )


def _matches_search(
    *,
    keyword: str | None,
    description: str,
    reference: str | None,
) -> bool:
    if not keyword:
        return True
    needle = keyword.casefold()
    haystacks = (description or "", reference or "")
    return any(needle in h.casefold() for h in haystacks)


def compute_ledger_page(
    session: Session,
    *,
    company_id: int,
    account_id: int,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
    search_keyword: str | None = None,
) -> LedgerPage:
    account = session.get(ChartOfAccounts, account_id)
    if account is None or account.company_id != company_id:
        filters = LedgerFilters(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            search_keyword=search_keyword,
        )
        return LedgerPage(
            rows=(),
            filters=filters,
            opening_balance=0.0,
            closing_balance=0.0,
            row_count=0,
            total_debit=0.0,
            total_credit=0.0,
            account_type="",
            current_balance=0.0,
        )

    all_lines = _query_ledger_lines(
        session, company_id=company_id, account_id=account_id,
    )

    opening_balance = 0.0
    if start_date is not None:
        for line in all_lines:
            entry = line.journal_entry
            if entry is None:
                entry = session.get(JournalEntry, line.journal_entry_id)
            if entry is None or entry.entry_date >= start_date:
                continue
            opening_balance += _balance_delta(
                account.account_type, line_money(line.debit), line_money(line.credit),
            )

    rows: list[LedgerRow] = []
    running_balance = opening_balance
    total_debit = 0.0
    total_credit = 0.0

    for line in all_lines:
        entry = line.journal_entry
        if entry is None:
            entry = session.get(JournalEntry, line.journal_entry_id)
        if entry is None:
            continue
        if start_date is not None and entry.entry_date < start_date:
            continue
        if end_date is not None and entry.entry_date > end_date:
            continue
        if not _matches_search(
            keyword=search_keyword,
            description=entry.description,
            reference=entry.reference_type,
        ):
            continue

        debit = line_money(line.debit)
        credit = line_money(line.credit)
        running_balance += _balance_delta(account.account_type, debit, credit)
        total_debit += debit
        total_credit += credit
        rows.append(
            LedgerRow(
                date=entry.entry_date,
                reference=entry.reference_type,
                description=entry.description,
                debit=debit,
                credit=credit,
                running_balance=running_balance,
                account_id=account.id,
                account_code=account.account_code,
                account_name=account.account_name,
                journal_entry_id=entry.id,
                company_id=company_id,
                journal_entry_line_id=line.id,
            )
        )

    current_balance = calculate_account_balance(
        session, account, company_id=company_id,
    )
    closing_balance = running_balance if rows else opening_balance

    filters = LedgerFilters(
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        search_keyword=search_keyword,
    )
    return LedgerPage(
        rows=tuple(rows),
        filters=filters,
        opening_balance=opening_balance,
        closing_balance=closing_balance,
        row_count=len(rows),
        total_debit=total_debit,
        total_credit=total_credit,
        account_type=account.account_type,
        current_balance=current_balance,
    )
