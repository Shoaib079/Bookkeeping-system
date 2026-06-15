"""FASTAPI-P0.2-A — read-only GL balance helpers with explicit company_id."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import ChartOfAccounts, JournalEntry, JournalEntryLine

_ASSET_EXPENSE_TYPES = frozenset({"Asset", "Expense"})

_LIQUID_EPOCH = datetime.date(2000, 1, 1)

_CASH_ACCOUNT_CODES = frozenset({"1000", "1001", "1002", "1003"})
_BANK_ACCOUNT_CODES = frozenset({"1010", "1011", "1012", "1013"})
_LIQUID_ACCOUNT_CODES = _CASH_ACCOUNT_CODES | _BANK_ACCOUNT_CODES
_EXCLUDED_LIQUID_CODES = frozenset({"1150", "2110"})

_CODE_DEFAULT_CURRENCY: dict[str, str] = {
    "1000": "TRY",
    "1001": "USD",
    "1002": "EUR",
    "1003": "GBP",
    "1010": "TRY",
    "1011": "USD",
    "1012": "EUR",
    "1013": "GBP",
}


@dataclass(frozen=True, slots=True)
class LiquidPosition:
    as_of: datetime.date
    cash_by_currency: dict[str, float]
    bank_by_currency: dict[str, float]
    total_by_currency: dict[str, float]


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


def _liquid_currency_bucket(account: ChartOfAccounts) -> str:
    if account.currency:
        return account.currency
    return _CODE_DEFAULT_CURRENCY.get(account.account_code, "—")


def _accumulate_liquid_balances(
    session: Session,
    accounts: list[ChartOfAccounts],
    *,
    family_codes: frozenset[str],
    as_of: datetime.date,
    company_id: int,
) -> dict[str, float]:
    totals: dict[str, float] = {}
    for acct in accounts:
        if acct.account_code not in family_codes:
            continue
        if acct.account_code in _EXCLUDED_LIQUID_CODES:
            continue
        bal = round(
            calculate_account_balance_for_period(
                session,
                acct,
                _LIQUID_EPOCH,
                as_of,
                company_id=company_id,
            ),
            2,
        )
        bucket = _liquid_currency_bucket(acct)
        totals[bucket] = round(totals.get(bucket, 0.0) + bal, 2)
    return totals


def compute_liquid_position(
    session: Session,
    *,
    company_id: int,
    as_of: datetime.date,
) -> LiquidPosition:
    """GL cash-in-hand (1000–1003) and bank (1010–1013) balances as-of a date.

    Excludes Card Sales Clearing (1150) and Credit Card Payable (2110).
    Company-scoped; balances derived from journal lines only.
    """
    accounts = (
        session.query(ChartOfAccounts)
        .filter_by(company_id=company_id, is_active=True)
        .filter(ChartOfAccounts.account_code.in_(_LIQUID_ACCOUNT_CODES))
        .order_by(ChartOfAccounts.account_code)
        .all()
    )

    cash_by_currency = _accumulate_liquid_balances(
        session,
        accounts,
        family_codes=_CASH_ACCOUNT_CODES,
        as_of=as_of,
        company_id=company_id,
    )
    bank_by_currency = _accumulate_liquid_balances(
        session,
        accounts,
        family_codes=_BANK_ACCOUNT_CODES,
        as_of=as_of,
        company_id=company_id,
    )

    total_by_currency: dict[str, float] = {}
    for ccy in sorted(set(cash_by_currency) | set(bank_by_currency)):
        total_by_currency[ccy] = round(
            cash_by_currency.get(ccy, 0.0) + bank_by_currency.get(ccy, 0.0),
            2,
        )

    return LiquidPosition(
        as_of=as_of,
        cash_by_currency=cash_by_currency,
        bank_by_currency=bank_by_currency,
        total_by_currency=total_by_currency,
    )
