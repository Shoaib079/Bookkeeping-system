"""FASTAPI-REACT-32 — read-only journal entries list DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session, joinedload

from models import ChartOfAccounts, JournalEntry, JournalEntryLine
from services.money import line_money, money_to_float


@dataclass(frozen=True, slots=True)
class JournalEntryLineListRow:
    id: int
    account_id: int
    account_code: str
    account_name: str
    debit: float
    credit: float
    company_id: int


@dataclass(frozen=True, slots=True)
class JournalEntryListRow:
    id: int
    entry_date: datetime.date
    description: str
    reference_type: str | None
    reference_id: int | None
    total_debit: float
    total_credit: float
    company_id: int
    lines: tuple[JournalEntryLineListRow, ...]


@dataclass(frozen=True, slots=True)
class JournalEntriesListPage:
    rows: tuple[JournalEntryListRow, ...]
    row_count: int


def _line_row(line: JournalEntryLine, account: ChartOfAccounts | None) -> JournalEntryLineListRow:
    debit = money_to_float(line_money(line.debit))
    credit = money_to_float(line_money(line.credit))
    return JournalEntryLineListRow(
        id=line.id,
        account_id=line.account_id,
        account_code=account.account_code if account else "",
        account_name=account.account_name if account else "Unknown",
        debit=debit,
        credit=credit,
        company_id=line.company_id or 0,
    )


def compute_journal_entries_list(
    session: Session,
    *,
    company_id: int,
) -> JournalEntriesListPage:
    entries = (
        session.query(JournalEntry)
        .options(
            joinedload(JournalEntry.lines).joinedload(JournalEntryLine.account),
        )
        .filter(JournalEntry.company_id == company_id)
        .order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc())
        .all()
    )
    rows: list[JournalEntryListRow] = []
    for entry in entries:
        line_rows = tuple(
            _line_row(line, line.account)
            for line in sorted(entry.lines, key=lambda row: row.id)
        )
        total_debit = sum(line.debit for line in line_rows)
        total_credit = sum(line.credit for line in line_rows)
        rows.append(
            JournalEntryListRow(
                id=entry.id,
                entry_date=entry.entry_date,
                description=entry.description or "",
                reference_type=entry.reference_type,
                reference_id=entry.reference_id,
                total_debit=total_debit,
                total_credit=total_credit,
                company_id=company_id,
                lines=line_rows,
            )
        )
    return JournalEntriesListPage(rows=tuple(rows), row_count=len(rows))
