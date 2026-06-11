"""Unsettled card sales in Card Sales Clearing — Phase 18-MVP-3."""

from __future__ import annotations

import datetime
import json
from typing import Any, Callable

from models import BankStatementImport, BankStatementRow, JournalEntry, Sale

UNSETTLED_DATE_MIN = datetime.date(2000, 1, 1)
_UNSETTLED_DATE_MAX = datetime.date(2100, 12, 31)


def _settled_sale_ids(session, company_id: int) -> set[int]:
    settled: set[int] = set()
    rows = (
        session.query(BankStatementRow)
        .join(BankStatementImport)
        .filter(
            BankStatementImport.company_id == company_id,
            BankStatementRow.status == "posted",
            BankStatementRow.match_type == "deposit_clearing",
            BankStatementRow.clearing_sale_ids_json.isnot(None),
        )
        .all()
    )
    for row in rows:
        try:
            settled.update(json.loads(row.clearing_sale_ids_json or "[]"))
        except json.JSONDecodeError:
            continue
    return settled


def get_unsettled_card_sales(
    session,
    company_id: int,
    *,
    date_from: datetime.date,
    date_to: datetime.date,
    get_account_by_name,
) -> list[dict[str, Any]]:
    """Card sales posted to Card Sales Clearing not yet matched to a bank deposit."""
    clearing_acct = get_account_by_name(session, "Card Sales Clearing")
    if not clearing_acct:
        return []

    settled = _settled_sale_ids(session, company_id)
    sales = (
        session.query(Sale)
        .filter(
            Sale.company_id == company_id,
            Sale.sale_type == "Card",
            Sale.is_void == False,  # noqa: E712
            Sale.date >= date_from,
            Sale.date <= date_to,
        )
        .order_by(Sale.date, Sale.id)
        .all()
    )

    out: list[dict[str, Any]] = []
    for sale in sales:
        if sale.id in settled:
            continue
        je = (
            session.query(JournalEntry)
            .filter_by(
                company_id=company_id,
                reference_type="CardSale",
                reference_id=sale.id,
            )
            .first()
        )
        if not je:
            continue
        clearing_debit = sum(
            (ln.debit or 0)
            for ln in je.lines
            if ln.account_id == clearing_acct.id
        )
        if clearing_debit <= 0:
            continue
        out.append(
            {
                "sale_id": sale.id,
                "date": sale.date,
                "amount": round(float(sale.amount), 2),
                "invoice": sale.invoice_number,
                "customer": sale.customer_name,
            }
        )
    return out


def fetch_unsettled_card_sales_for_visibility(
    session,
    company_id: int,
    *,
    get_unsettled_card_sales: Callable[..., list[dict[str, Any]]],
    get_account_by_name: Callable[..., Any],
) -> list[dict[str, Any]]:
    """Wide-date unsettled card sales — shared by P2 visibility and P3 list."""
    return get_unsettled_card_sales(
        session,
        company_id,
        date_from=UNSETTLED_DATE_MIN,
        date_to=_UNSETTLED_DATE_MAX,
        get_account_by_name=get_account_by_name,
    )
