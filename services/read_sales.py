"""FASTAPI-REACT-26 — read-only sales list DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import Sale
from services.money import money_to_float


@dataclass(frozen=True, slots=True)
class SalesListRow:
    id: int
    date: datetime.date
    invoice_number: str
    customer_name: str
    description: str
    amount: float
    sale_type: str
    paid_amount: float
    balance: float
    due_date: datetime.date | None
    status: str
    is_void: bool
    currency: str | None
    company_id: int


@dataclass(frozen=True, slots=True)
class SalesListPage:
    rows: tuple[SalesListRow, ...]
    row_count: int


def compute_sales_list(
    session: Session,
    *,
    company_id: int,
    show_voided: bool = False,
) -> SalesListPage:
    query = (
        session.query(Sale)
        .filter(Sale.company_id == company_id)
        .order_by(Sale.date.desc(), Sale.id.desc())
    )
    if not show_voided:
        query = query.filter(Sale.is_void == False)  # noqa: E712
    rows = tuple(
        SalesListRow(
            id=sale.id,
            date=sale.date,
            invoice_number=sale.invoice_number,
            customer_name=sale.customer_name,
            description=sale.description or "",
            amount=money_to_float(sale.amount),
            sale_type=sale.sale_type,
            paid_amount=money_to_float(sale.paid_amount),
            balance=money_to_float(sale.balance),
            due_date=sale.due_date,
            status=sale.status,
            is_void=bool(sale.is_void),
            currency=sale.currency,
            company_id=company_id,
        )
        for sale in query.all()
    )
    return SalesListPage(rows=rows, row_count=len(rows))
