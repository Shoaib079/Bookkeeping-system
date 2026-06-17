"""FASTAPI-REACT-24 — read-only open credit sales list DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import Sale
from services.money import money_to_float


@dataclass(frozen=True, slots=True)
class ReceivableSaleListRow:
    id: int
    invoice_number: str
    customer_name: str
    date: datetime.date
    due_date: datetime.date | None
    balance: float
    status: str
    currency: str | None
    company_id: int


@dataclass(frozen=True, slots=True)
class ReceivableSalesListPage:
    rows: tuple[ReceivableSaleListRow, ...]
    row_count: int


def compute_receivable_sales_list(
    session: Session,
    *,
    company_id: int,
    open_only: bool = True,
) -> ReceivableSalesListPage:
    query = (
        session.query(Sale)
        .filter(
            Sale.company_id == company_id,
            Sale.sale_type == "Credit",
            Sale.is_void == False,  # noqa: E712
        )
        .order_by(Sale.date.desc(), Sale.id.desc())
    )
    if open_only:
        query = query.filter(Sale.balance > 0)
    rows = tuple(
        ReceivableSaleListRow(
            id=sale.id,
            invoice_number=sale.invoice_number,
            customer_name=sale.customer_name,
            date=sale.date,
            due_date=sale.due_date,
            balance=money_to_float(sale.balance),
            status=sale.status,
            currency=sale.currency,
            company_id=company_id,
        )
        for sale in query.all()
    )
    return ReceivableSalesListPage(rows=rows, row_count=len(rows))
