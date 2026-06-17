"""FASTAPI-P0.2-G — read-only transaction history DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import (
    BankAccount,
    BankTransaction,
    ExpenseRecord,
    Payable,
    Purchase,
    Sale,
    TransactionCategory,
    TransactionSubcategory,
    User,
    Vendor,
)

_BANKING_TYPE_LABEL = "Banking"
_FILTER_ALL = "all"


@dataclass(frozen=True, slots=True)
class TransactionHistoryRow:
    date: datetime.date
    type: str
    reference: str
    party: str
    category: str
    subcategory: str
    amount: float
    currency: str
    method: str
    description: str
    status: str
    created_by: str
    source_type: str
    source_id: int
    company_id: int


@dataclass(frozen=True, slots=True)
class TransactionHistoryFilters:
    start_date: datetime.date
    end_date: datetime.date
    search_keyword: str | None
    type_filter: str
    show_voided: bool


@dataclass(frozen=True, slots=True)
class TransactionHistoryPage:
    rows: tuple[TransactionHistoryRow, ...]
    filters: TransactionHistoryFilters
    row_count: int


def _load_cat_lookup(
    session: Session,
    *,
    company_id: int,
) -> tuple[dict[int, str], dict[int, str]]:
    cats = (
        session.query(TransactionCategory)
        .filter(TransactionCategory.company_id == company_id)
        .all()
    )
    subcats = (
        session.query(TransactionSubcategory)
        .filter(TransactionSubcategory.company_id == company_id)
        .all()
    )
    return {c.id: c.name for c in cats}, {s.id: s.name for s in subcats}


def _load_user_lookup(session: Session) -> dict[int, str]:
    return {u.id: (u.display_name or u.username) for u in session.query(User).all()}


def _created_by_display(user_lkp: dict[int, str], source) -> str:
    created_by_id = getattr(source, "created_by_id", None)
    return user_lkp.get(created_by_id, "—")


def _matches_keyword(
    kw: str,
    *,
    party: str = "",
    description: str = "",
    txn_type: str = "",
    method: str = "",
    reference: str = "",
    amount: float | None = None,
) -> bool:
    if not kw:
        return True
    kw_l = kw.lower()
    parts: list[str] = [party, description, txn_type, method, reference]
    if amount is not None:
        parts.extend(
            (
                f"{amount:.2f}",
                f"{amount:,.2f}",
                str(int(amount)) if amount == int(amount) else "",
            )
        )
    haystack = " ".join(p for p in parts if p).lower()
    return kw_l in haystack


def _is_all(value: str, *, filter_all_label: str) -> bool:
    return value in {_FILTER_ALL, filter_all_label}


def _collect_rows(
    session: Session,
    *,
    company_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    keyword: str,
    type_filter: str,
    method_filter: str,
    cat_filter: str,
    subcat_filter: str,
    show_voided: bool,
    currency: str,
    cat_names_lkp: dict[int, str],
    subcat_names_lkp: dict[int, str],
    user_lkp: dict[int, str],
    filter_all_label: str,
) -> list[tuple[TransactionHistoryRow, object]]:
    rows: list[tuple[TransactionHistoryRow, object]] = []

    if _is_all(type_filter, filter_all_label=filter_all_label) or type_filter == "Sale":
        query = (
            session.query(Sale)
            .filter(
                Sale.company_id == company_id,
                Sale.date.between(start_date, end_date),
            )
        )
        if not show_voided:
            query = query.filter(Sale.is_void == False)  # noqa: E712
        for sale in query.order_by(Sale.date.desc()).all():
            amount = float(sale.amount or 0)
            if not _matches_keyword(
                keyword,
                party=sale.customer_name,
                description=sale.description or "",
                txn_type=sale.sale_type + " Sale",
                method=sale.sale_type,
                reference=sale.invoice_number,
                amount=amount,
            ):
                continue
            cat_label = cat_names_lkp.get(sale.tx_category_id, "")
            sub_label = subcat_names_lkp.get(sale.tx_subcategory_id, "")
            if not _is_all(cat_filter, filter_all_label=filter_all_label) and cat_label != cat_filter:
                continue
            if not _is_all(subcat_filter, filter_all_label=filter_all_label) and sub_label != subcat_filter:
                continue
            row = TransactionHistoryRow(
                date=sale.date,
                type=sale.sale_type + " Sale",
                reference=sale.invoice_number,
                party=sale.customer_name,
                category=cat_label,
                subcategory=sub_label,
                amount=amount,
                currency=currency,
                method=sale.sale_type,
                description=sale.description or "",
                status="VOID" if sale.is_void else sale.status,
                created_by=_created_by_display(user_lkp, sale),
                source_type="Sale",
                source_id=sale.id,
                company_id=company_id,
            )
            rows.append((row, sale))

    if _is_all(type_filter, filter_all_label=filter_all_label) or type_filter == "Expense":
        query = (
            session.query(ExpenseRecord)
            .filter(
                ExpenseRecord.company_id == company_id,
                ExpenseRecord.date.between(start_date, end_date),
            )
        )
        if not show_voided:
            query = query.filter(ExpenseRecord.is_void == False)  # noqa: E712
        for expense in query.order_by(ExpenseRecord.date.desc()).all():
            if not _is_all(method_filter, filter_all_label=filter_all_label) and (
                expense.payment_method or ""
            ).lower() != method_filter.lower():
                continue
            amount = float(expense.amount or 0)
            if not _matches_keyword(
                keyword,
                party=expense.employee_name or "",
                description=expense.description or "",
                txn_type=expense.expense_type or "Expense",
                method=expense.payment_method or "",
                reference=expense.category or "",
                amount=amount,
            ):
                continue
            cat_label = cat_names_lkp.get(expense.tx_category_id, "")
            sub_label = subcat_names_lkp.get(expense.tx_subcategory_id, "")
            if not _is_all(cat_filter, filter_all_label=filter_all_label) and cat_label != cat_filter:
                continue
            if not _is_all(subcat_filter, filter_all_label=filter_all_label) and sub_label != subcat_filter:
                continue
            row = TransactionHistoryRow(
                date=expense.date,
                type=expense.expense_type or "Expense",
                reference=expense.category or "",
                party=expense.employee_name or "",
                category=cat_label,
                subcategory=sub_label,
                amount=amount,
                currency=currency,
                method=expense.payment_method or "",
                description=expense.description or "",
                status="VOID" if expense.is_void else "Recorded",
                created_by=_created_by_display(user_lkp, expense),
                source_type="ExpenseRecord",
                source_id=expense.id,
                company_id=company_id,
            )
            rows.append((row, expense))

    if _is_all(type_filter, filter_all_label=filter_all_label) or type_filter == "Purchase":
        query = (
            session.query(Purchase)
            .filter(
                Purchase.company_id == company_id,
                Purchase.date.between(start_date, end_date),
            )
        )
        if not show_voided:
            query = query.filter(Purchase.is_void == False)  # noqa: E712
        for purchase in query.order_by(Purchase.date.desc()).all():
            vendor = session.get(Vendor, purchase.vendor_id)
            vendor_name = vendor.name if vendor else ""
            amount = float(purchase.amount or 0)
            if not _matches_keyword(
                keyword,
                party=vendor_name,
                description=purchase.description or "",
                txn_type="Purchase",
                method=purchase.purchase_type or "Credit",
                reference=f"PUR#{purchase.id}",
                amount=amount,
            ):
                continue
            cat_label = cat_names_lkp.get(purchase.tx_category_id, "")
            sub_label = subcat_names_lkp.get(purchase.tx_subcategory_id, "")
            if not _is_all(cat_filter, filter_all_label=filter_all_label) and cat_label != cat_filter:
                continue
            if not _is_all(subcat_filter, filter_all_label=filter_all_label) and sub_label != subcat_filter:
                continue
            row = TransactionHistoryRow(
                date=purchase.date,
                type="Purchase",
                reference=f"PUR#{purchase.id}",
                party=vendor_name,
                category=cat_label,
                subcategory=sub_label,
                amount=amount,
                currency=currency,
                method=purchase.purchase_type or "Credit",
                description=purchase.description or "",
                status="VOID" if purchase.is_void else "Active",
                created_by=_created_by_display(user_lkp, purchase),
                source_type="Purchase",
                source_id=purchase.id,
                company_id=company_id,
            )
            rows.append((row, purchase))

    if _is_all(type_filter, filter_all_label=filter_all_label) or type_filter == _BANKING_TYPE_LABEL:
        query = (
            session.query(BankTransaction)
            .filter(
                BankTransaction.company_id == company_id,
                BankTransaction.date.between(start_date, end_date),
            )
        )
        if not show_voided:
            query = query.filter(BankTransaction.is_void == False)  # noqa: E712
        for txn in query.order_by(BankTransaction.date.desc()).all():
            account = session.get(BankAccount, txn.account_id)
            amount = float(txn.amount or 0)
            if not _matches_keyword(
                keyword,
                party=account.name if account else "",
                description=txn.description or "",
                txn_type="Bank " + txn.type.title(),
                method="Bank",
                reference=f"TXN#{txn.id}",
                amount=amount,
            ):
                continue
            if not _is_all(cat_filter, filter_all_label=filter_all_label):
                continue
            row = TransactionHistoryRow(
                date=txn.date,
                type="Bank " + txn.type.title(),
                reference=f"TXN#{txn.id}",
                party=account.name if account else "",
                category="",
                subcategory="",
                amount=amount,
                currency=currency,
                method="Bank",
                description=txn.description or "",
                status="VOID" if txn.is_void else "Active",
                created_by="—",
                source_type="BankTransaction",
                source_id=txn.id,
                company_id=company_id,
            )
            rows.append((row, txn))

    if _is_all(type_filter, filter_all_label=filter_all_label) or type_filter == "Payable":
        query = (
            session.query(Payable)
            .filter(
                Payable.company_id == company_id,
                Payable.date.between(start_date, end_date),
            )
        )
        if not show_voided:
            query = query.filter(Payable.is_void == False)  # noqa: E712
        for payable in query.order_by(Payable.date.desc()).all():
            vendor = session.get(Vendor, payable.vendor_id)
            vendor_name = vendor.name if vendor else ""
            amount = float(payable.amount or 0)
            if not _matches_keyword(
                keyword,
                party=vendor_name,
                description=payable.description or "",
                txn_type="Payable",
                method=payable.payment_method or "Credit",
                reference=f"PAY#{payable.id}",
                amount=amount,
            ):
                continue
            if not _is_all(cat_filter, filter_all_label=filter_all_label):
                continue
            row = TransactionHistoryRow(
                date=payable.date,
                type="Payable",
                reference=f"PAY#{payable.id}",
                party=vendor_name,
                category="",
                subcategory="",
                amount=amount,
                currency=currency,
                method=payable.payment_method or "Credit",
                description=payable.description or "",
                status=(
                    "VOID"
                    if payable.is_void
                    else ("Paid" if payable.paid else "Open")
                ),
                created_by="—",
                source_type="Payable",
                source_id=payable.id,
                company_id=company_id,
            )
            rows.append((row, payable))

    rows.sort(key=lambda item: item[0].date, reverse=True)
    return rows


def fetch_filtered_rows_with_sources(
    session: Session,
    *,
    company_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    keyword: str,
    type_filter: str,
    method_filter: str,
    cat_filter: str,
    subcat_filter: str,
    show_voided: bool,
    currency: str,
    cat_names_lkp: dict[int, str],
    subcat_names_lkp: dict[int, str],
    user_lkp: dict[int, str],
    filter_all_label: str,
) -> list[tuple[dict, str, object]]:
    """Streamlit-compatible row tuples (display dict, source type, ORM object)."""
    collected = _collect_rows(
        session,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        type_filter=type_filter,
        method_filter=method_filter,
        cat_filter=cat_filter,
        subcat_filter=subcat_filter,
        show_voided=show_voided,
        currency=currency,
        cat_names_lkp=cat_names_lkp,
        subcat_names_lkp=subcat_names_lkp,
        user_lkp=user_lkp,
        filter_all_label=filter_all_label,
    )
    return [
        (
            {
                "Date": row.date,
                "Type": row.type,
                "Reference": row.reference,
                "Party": row.party,
                "Category": row.category,
                "Subcategory": row.subcategory,
                "Amount": row.amount,
                "Currency": row.currency,
                "Method": row.method,
                "Description": row.description,
                "Status": row.status,
                "Created By": row.created_by,
            },
            row.source_type,
            source,
        )
        for row, source in collected
    ]


def compute_transaction_history_page(
    session: Session,
    *,
    company_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    search_keyword: str | None = None,
    type_filter: str = _FILTER_ALL,
    show_voided: bool = False,
    currency: str = "USD",
) -> TransactionHistoryPage:
    cat_names_lkp, subcat_names_lkp = _load_cat_lookup(session, company_id=company_id)
    user_lkp = _load_user_lookup(session)
    collected = _collect_rows(
        session,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        keyword=(search_keyword or "").strip(),
        type_filter=type_filter,
        method_filter=_FILTER_ALL,
        cat_filter=_FILTER_ALL,
        subcat_filter=_FILTER_ALL,
        show_voided=show_voided,
        currency=currency,
        cat_names_lkp=cat_names_lkp,
        subcat_names_lkp=subcat_names_lkp,
        user_lkp=user_lkp,
        filter_all_label=_FILTER_ALL,
    )
    rows = tuple(row for row, _source in collected)
    filters = TransactionHistoryFilters(
        start_date=start_date,
        end_date=end_date,
        search_keyword=search_keyword,
        type_filter=type_filter,
        show_voided=show_voided,
    )
    return TransactionHistoryPage(rows=rows, filters=filters, row_count=len(rows))
