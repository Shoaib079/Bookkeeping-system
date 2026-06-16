"""FASTAPI-P0.2-E — read-only receivables and payables DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from models import Payable, Sale, Vendor
from services.money import money_to_float

AgingBuckets = dict[str, float]


def get_aging_summary(records, amount_field: str, due_date_field: str) -> AgingBuckets:
    """AR/AP aging buckets (same logic as legacy app.get_aging_summary)."""
    today = datetime.date.today()
    buckets: AgingBuckets = {
        "Current": 0.0,
        "1-30 Days": 0.0,
        "31-60 Days": 0.0,
        "61-90 Days": 0.0,
        "90+ Days": 0.0,
    }
    for record in records:
        due_date = getattr(record, due_date_field)
        amount = money_to_float(getattr(record, amount_field) or 0)
        if not due_date:
            buckets["Current"] += amount
            continue
        age = (today - due_date).days
        if age < 0:
            buckets["Current"] += amount
        elif age <= 30:
            buckets["1-30 Days"] += amount
        elif age <= 60:
            buckets["31-60 Days"] += amount
        elif age <= 90:
            buckets["61-90 Days"] += amount
        else:
            buckets["90+ Days"] += amount
    return buckets


def payable_balance(record) -> float:
    """Outstanding balance on a payable (legacy _payable_balance)."""
    paid_amt = money_to_float(record.paid_amount)
    return max(round(money_to_float(record.amount) - paid_amt, 2), 0.0)


def payable_status(record) -> str:
    """Paid / Partial / Open from payable fields."""
    bal = payable_balance(record)
    if record.paid or bal <= 0:
        return "Paid"
    if money_to_float(record.paid_amount) > 0:
        return "Partial"
    return "Open"


@dataclass(frozen=True, slots=True)
class ReceivableRow:
    id: int
    invoice_number: str
    customer_name: str
    date: datetime.date
    due_date: datetime.date | None
    amount: float
    paid_amount: float
    balance: float
    status: str
    description: str
    currency: str | None
    company_id: int | None


@dataclass(frozen=True, slots=True)
class ReceivablesFilters:
    search_keyword: str | None
    customer_filter: str
    status_filter: str


@dataclass(frozen=True, slots=True)
class ReceivablesPage:
    rows: tuple[ReceivableRow, ...]
    filters: ReceivablesFilters
    outstanding: float
    overdue: float
    open_count: int
    showing_count: int
    aging: AgingBuckets


@dataclass(frozen=True, slots=True)
class PayableRow:
    id: int
    date: datetime.date
    vendor_id: int
    vendor_name: str
    invoice_amount: float
    paid_amount: float
    balance: float
    due_date: datetime.date
    status: str
    source: str
    is_void: bool
    paid: bool
    description: str
    company_id: int | None


@dataclass(frozen=True, slots=True)
class PayablesFilters:
    search_keyword: str | None
    vendor_filter: str
    paid_filter: str
    show_voided: bool


@dataclass(frozen=True, slots=True)
class PayablesPage:
    rows: tuple[PayableRow, ...]
    filters: PayablesFilters
    total_outstanding: float
    overdue: float
    showing_count: int
    aging: AgingBuckets


def _matches_search(keyword: str | None, *haystacks: str) -> bool:
    if not keyword:
        return True
    needle = keyword.casefold()
    return any(needle in (h or "").casefold() for h in haystacks)


def _sale_to_row(sale: Sale) -> ReceivableRow:
    return ReceivableRow(
        id=sale.id,
        invoice_number=sale.invoice_number,
        customer_name=sale.customer_name,
        date=sale.date,
        due_date=sale.due_date,
        amount=money_to_float(sale.amount),
        paid_amount=money_to_float(sale.paid_amount),
        balance=money_to_float(sale.balance),
        status=sale.status,
        description=sale.description or "",
        currency=sale.currency,
        company_id=sale.company_id,
    )


def compute_receivables_page(
    session: Session,
    *,
    company_id: int,
    search_keyword: str | None = None,
    customer_filter: str = "all",
    status_filter: str = "all",
) -> ReceivablesPage:
    credit_sales = (
        session.query(Sale)
        .filter(
            Sale.company_id == company_id,
            Sale.sale_type == "Credit",
            Sale.is_void == False,  # noqa: E712
        )
        .order_by(Sale.date.desc())
        .all()
    )

    rows: list[ReceivableRow] = []
    for sale in credit_sales:
        if not _matches_search(
            search_keyword,
            sale.customer_name,
            sale.invoice_number,
            sale.description or "",
        ):
            continue
        if customer_filter != "all" and sale.customer_name != customer_filter:
            continue
        if status_filter != "all" and sale.status != status_filter:
            continue
        rows.append(_sale_to_row(sale))

    open_rows = [r for r in rows if r.status != "Paid"]
    outstanding = sum(r.balance for r in open_rows)
    overdue = sum(r.balance for r in rows if r.status == "Overdue")
    aging: AgingBuckets = {
        "Current": 0.0,
        "1-30 Days": 0.0,
        "31-60 Days": 0.0,
        "61-90 Days": 0.0,
        "90+ Days": 0.0,
    }
    if open_rows:
        open_sales = [s for s in credit_sales if s.id in {r.id for r in open_rows}]
        aging = get_aging_summary(open_sales, "balance", "due_date")

    filters = ReceivablesFilters(
        search_keyword=search_keyword,
        customer_filter=customer_filter,
        status_filter=status_filter,
    )
    return ReceivablesPage(
        rows=tuple(rows),
        filters=filters,
        outstanding=outstanding,
        overdue=overdue,
        open_count=len(open_rows),
        showing_count=len(rows),
        aging=aging,
    )


def _vendor_name(session: Session, vendor_id: int, *, unknown: str = "Unknown") -> str:
    vendor = session.get(Vendor, vendor_id)
    return vendor.name if vendor else unknown


def compute_payables_page(
    session: Session,
    *,
    company_id: int,
    search_keyword: str | None = None,
    vendor_filter: str = "all",
    paid_filter: str = "all",
    show_voided: bool = False,
    unknown_vendor_label: str = "Unknown",
) -> PayablesPage:
    all_payables = (
        session.query(Payable)
        .filter(Payable.company_id == company_id)
        .order_by(Payable.date.desc())
        .all()
    )

    rows: list[PayableRow] = []
    open_for_aging: list[Payable] = []
    today = datetime.date.today()

    for record in all_payables:
        if record.is_void and not show_voided:
            continue
        vname = _vendor_name(session, record.vendor_id, unknown=unknown_vendor_label)
        if not _matches_search(search_keyword, vname, record.description or ""):
            continue
        if vendor_filter != "all" and vname != vendor_filter:
            continue
        status = payable_status(record)
        if paid_filter != "all" and status != paid_filter:
            continue

        bal = payable_balance(record)
        display_status = "VOID" if record.is_void else status
        rows.append(
            PayableRow(
                id=record.id,
                date=record.date,
                vendor_id=record.vendor_id,
                vendor_name=vname,
                invoice_amount=money_to_float(record.amount),
                paid_amount=money_to_float(record.paid_amount),
                balance=bal,
                due_date=record.due_date,
                status=display_status,
                source=f"PUR#{record.purchase_id}" if record.purchase_id else "Manual",
                is_void=record.is_void,
                paid=record.paid,
                description=record.description or "",
                company_id=record.company_id,
            )
        )
        if not record.is_void and not record.paid:
            open_for_aging.append(record)

    total_outstanding = sum(
        r.balance for r in rows if not r.is_void and not r.paid
    )
    overdue = sum(
        r.balance
        for r in rows
        if not r.is_void and not r.paid and r.due_date < today
    )
    aging: AgingBuckets = {
        "Current": 0.0,
        "1-30 Days": 0.0,
        "31-60 Days": 0.0,
        "61-90 Days": 0.0,
        "90+ Days": 0.0,
    }
    if open_for_aging:
        aging = get_aging_summary(open_for_aging, "amount", "due_date")

    filters = PayablesFilters(
        search_keyword=search_keyword,
        vendor_filter=vendor_filter,
        paid_filter=paid_filter,
        show_voided=show_voided,
    )
    return PayablesPage(
        rows=tuple(rows),
        filters=filters,
        total_outstanding=total_outstanding,
        overdue=overdue,
        showing_count=len(rows),
        aging=aging,
    )


def receivables_page_to_export_rows(page: ReceivablesPage) -> list[dict[str, Any]]:
    return [
        {
            "id": r.id,
            "invoice_number": r.invoice_number,
            "customer_name": r.customer_name,
            "date": r.date,
            "due_date": r.due_date,
            "amount": r.amount,
            "paid_amount": r.paid_amount,
            "balance": r.balance,
            "status": r.status,
        }
        for r in page.rows
    ]


def payables_page_to_table_rows(page: PayablesPage) -> list[dict[str, Any]]:
    return [
        {
            "ID": r.id,
            "Date": r.date,
            "Vendor": r.vendor_name,
            "Invoice Amount": r.invoice_amount,
            "Paid": r.paid_amount,
            "Balance": r.balance,
            "Due Date": r.due_date,
            "Status": r.status,
            "Source": r.source,
        }
        for r in page.rows
    ]
