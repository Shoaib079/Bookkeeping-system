"""FASTAPI-REACT-29 — read-only purchases list DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import Purchase, Vendor
from services.money import money_to_float


@dataclass(frozen=True, slots=True)
class PurchaseListRow:
    id: int
    date: datetime.date
    vendor_name: str
    purchase_number: str | None
    purchase_type: str
    gl_debit: str
    amount: float
    description: str
    is_void: bool
    currency: str | None
    company_id: int


@dataclass(frozen=True, slots=True)
class PurchasesListPage:
    rows: tuple[PurchaseListRow, ...]
    row_count: int


def compute_purchases_list(
    session: Session,
    *,
    company_id: int,
    show_voided: bool = False,
) -> PurchasesListPage:
    query = (
        session.query(Purchase, Vendor)
        .join(Vendor, Purchase.vendor_id == Vendor.id)
        .filter(Purchase.company_id == company_id)
        .order_by(Purchase.date.desc(), Purchase.id.desc())
    )
    if not show_voided:
        query = query.filter(Purchase.is_void == False)  # noqa: E712
    rows = tuple(
        PurchaseListRow(
            id=purchase.id,
            date=purchase.date,
            vendor_name=vendor.name,
            purchase_number=purchase.purchase_number,
            purchase_type=purchase.purchase_type or "Credit",
            gl_debit=purchase.gl_debit or "Inventory",
            amount=money_to_float(purchase.amount),
            description=purchase.description or "",
            is_void=bool(purchase.is_void),
            currency=purchase.currency,
            company_id=company_id,
        )
        for purchase, vendor in query.all()
    )
    return PurchasesListPage(rows=rows, row_count=len(rows))
