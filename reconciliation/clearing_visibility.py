"""BANKING-UX-02 P2 — Card Sales Clearing visibility (read-only)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Callable

from models import JournalEntry, JournalEntryLine, Sale

_TOLERANCE = 0.01
_UNSETTLED_DATE_MIN = datetime.date(2000, 1, 1)
_UNSETTLED_DATE_MAX = datetime.date(2100, 12, 31)


@dataclass
class ClearingVisibilitySnapshot:
    current_clearing_balance: float
    unsettled_card_sales_total: float
    settlements_posted_total: float
    remaining_clearing: float
    reconciliation_mismatch: bool


def _sum_clearing_debits_card_sales(
    session,
    company_id: int,
    clearing_account_id: int,
) -> float:
    """Total card-sale debits posted to Card Sales Clearing."""
    rows = (
        session.query(JournalEntryLine.debit)
        .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
        .join(Sale, Sale.id == JournalEntry.reference_id)
        .filter(
            JournalEntry.company_id == company_id,
            JournalEntry.reference_type == "CardSale",
            JournalEntryLine.account_id == clearing_account_id,
            Sale.is_void == False,  # noqa: E712
        )
        .all()
    )
    return round(sum((d or 0) for (d,) in rows), 2)


def _sum_clearing_settlement_credits(
    session,
    company_id: int,
    clearing_account_id: int,
) -> float:
    """Total settlement credits posted against Card Sales Clearing."""
    rows = (
        session.query(JournalEntryLine.credit)
        .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
        .filter(
            JournalEntry.company_id == company_id,
            JournalEntry.reference_type == "BankStmtSettlement",
            JournalEntryLine.account_id == clearing_account_id,
        )
        .all()
    )
    return round(sum((c or 0) for (c,) in rows), 2)


def compute_clearing_visibility(
    session,
    company_id: int,
    *,
    clearing_account_id: int,
    current_clearing_balance: float,
    get_unsettled_card_sales: Callable[..., list[dict[str, Any]]],
    get_account_by_name: Callable[..., Any],
) -> ClearingVisibilitySnapshot:
    """Read-only clearing visibility for account 1150."""
    unsettled = get_unsettled_card_sales(
        session,
        company_id,
        date_from=_UNSETTLED_DATE_MIN,
        date_to=_UNSETTLED_DATE_MAX,
        get_account_by_name=get_account_by_name,
    )
    unsettled_total = round(sum(c["amount"] for c in unsettled), 2)
    settlements_posted = _sum_clearing_settlement_credits(
        session, company_id, clearing_account_id
    )
    total_card_sales = _sum_clearing_debits_card_sales(
        session, company_id, clearing_account_id
    )
    current = round(float(current_clearing_balance), 2)
    remaining = round(total_card_sales - settlements_posted, 2)
    reconciliation_mismatch = abs(remaining - current) > _TOLERANCE

    return ClearingVisibilitySnapshot(
        current_clearing_balance=current,
        unsettled_card_sales_total=unsettled_total,
        settlements_posted_total=settlements_posted,
        remaining_clearing=remaining,
        reconciliation_mismatch=reconciliation_mismatch,
    )
