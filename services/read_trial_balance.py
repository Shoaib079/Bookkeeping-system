"""FASTAPI-REACT-33 — read-only trial balance DTOs and compute."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import ChartOfAccounts, JournalEntry, JournalEntryLine
from services.money import money_to_float
from services.read_balances import calculate_account_balance

_ASSET_EXPENSE_TYPES = frozenset({"Asset", "Expense"})


@dataclass(frozen=True, slots=True)
class TrialBalanceRow:
    account_code: str
    account_name: str
    account_type: str
    debit: float
    credit: float


@dataclass(frozen=True, slots=True)
class TrialBalanceStatement:
    rows: tuple[TrialBalanceRow, ...]
    total_debit: float
    total_credit: float
    gl_total_debit: float
    gl_total_credit: float
    gl_balanced: bool
    gl_difference: float
    row_count: int


def _trial_balance_columns(
    account: ChartOfAccounts,
    balance: float,
) -> tuple[float, float]:
    if account.account_type in _ASSET_EXPENSE_TYPES:
        if balance >= 0:
            return balance, 0.0
        return 0.0, abs(balance)
    if balance >= 0:
        return 0.0, balance
    return abs(balance), 0.0


def compute_trial_balance(
    session: Session,
    *,
    company_id: int,
) -> TrialBalanceStatement:
    accounts = (
        session.query(ChartOfAccounts)
        .filter_by(company_id=company_id, is_active=True)
        .order_by(ChartOfAccounts.account_code)
        .all()
    )

    rows: list[TrialBalanceRow] = []
    total_debit = 0.0
    total_credit = 0.0
    for account in accounts:
        balance = money_to_float(
            calculate_account_balance(session, account, company_id=company_id)
        )
        debit, credit = _trial_balance_columns(account, balance)
        rows.append(
            TrialBalanceRow(
                account_code=account.account_code,
                account_name=account.account_name,
                account_type=account.account_type,
                debit=debit,
                credit=credit,
            )
        )
        total_debit += debit
        total_credit += credit

    gl_total_debit = money_to_float(
        session.query(func.sum(JournalEntryLine.debit))
        .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
        .filter(JournalEntry.company_id == company_id)
        .scalar()
        or 0
    )
    gl_total_credit = money_to_float(
        session.query(func.sum(JournalEntryLine.credit))
        .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
        .filter(JournalEntry.company_id == company_id)
        .scalar()
        or 0
    )
    gl_difference = abs(gl_total_debit - gl_total_credit)
    gl_balanced = gl_difference < 0.01

    return TrialBalanceStatement(
        rows=tuple(rows),
        total_debit=total_debit,
        total_credit=total_credit,
        gl_total_debit=gl_total_debit,
        gl_total_credit=gl_total_credit,
        gl_balanced=gl_balanced,
        gl_difference=gl_difference,
        row_count=len(rows),
    )
