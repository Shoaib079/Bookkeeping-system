"""FASTAPI-P2.3 — create and post purchases (Streamlit-free, mirrors Add Transaction purchase path)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import (
    BankAccount,
    BankTransaction,
    JournalEntry,
    Payable,
    Purchase,
    TransactionCategory,
    TransactionSubcategory,
    Vendor,
)
from reconciliation.company_card import apply_account_balance_delta
from services import audit as audit_svc
from services import commit_modes
from services import posting as posting_svc
from services.money import money_to_float
from services.commit_modes import POST_PURCHASE_FAMILY
from services.posting import purchase_ref_type
from services.unit_of_work import boundary_commit_scope

# Pinned EN transactional strings — must match registry/locales/transactional.py.
INVALID_AMOUNT_MSG = "❌ Please enter a valid amount greater than zero."
CATEGORY_REQUIRED_MSG = "Select a category before saving"
SUBCATEGORY_REQUIRED_MSG = "Select a subcategory for this category"
VENDOR_REQUIRED_MSG = "Select a vendor before saving a purchase."
VENDOR_NOT_FOUND_MSG = "Vendor not found."
BANK_NOT_SELECTED_MSG = "No bank account selected."
PURCHASE_RECORDED_MSG = "Purchase recorded (PUR#{id})."
PURCHASE_RECORDED_PAYABLE_MSG = "Purchase recorded (PUR#{id}) — Payable created."

PURCHASE_PAYMENT_METHODS = frozenset({"Cash", "Bank", "Credit"})
_PURCHASE_TYPE_LABEL = "Purchase"
_DEFAULT_GL_DEBIT = "Inventory"


@dataclass(frozen=True, slots=True)
class PurchaseWriteResult:
    purchase_id: int
    payable_id: int | None
    journal_entry_id: int | None
    message: str


def _pay_method_not_allowed_error(method: str) -> str:
    return (
        f'Payment method "{method}" is not valid for {_PURCHASE_TYPE_LABEL}. '
        "A valid method has been selected — review and save again."
    )


def validate_purchase_amount(amount: float | None) -> None:
    if amount is None or amount <= 0:
        raise ValueError(INVALID_AMOUNT_MSG)


def validate_purchase_payment_method(payment_method: str) -> None:
    if payment_method not in PURCHASE_PAYMENT_METHODS:
        raise ValueError(_pay_method_not_allowed_error(payment_method or ""))


def _resolve_vendor(
    session: Session,
    company_id: int,
    *,
    vendor_id: int | None,
    vendor_name: str | None,
) -> Vendor:
    if vendor_id is not None:
        vendor = session.get(Vendor, vendor_id)
        if vendor is None or vendor.company_id != company_id or not vendor.is_active:
            raise ValueError(VENDOR_NOT_FOUND_MSG)
        return vendor
    name = (vendor_name or "").strip()
    if not name:
        raise ValueError(VENDOR_REQUIRED_MSG)
    vendor = (
        session.query(Vendor)
        .filter_by(company_id=company_id, name=name, is_active=True)
        .first()
    )
    if vendor is None:
        raise ValueError(VENDOR_NOT_FOUND_MSG)
    return vendor


def _resolve_category(
    session: Session,
    company_id: int,
    *,
    category_id: int | None,
    category_name: str | None,
) -> TransactionCategory:
    if category_id is not None:
        cat = session.get(TransactionCategory, category_id)
        if (
            cat is None
            or cat.company_id != company_id
            or cat.transaction_type != "Purchase"
            or not cat.is_active
        ):
            raise ValueError(CATEGORY_REQUIRED_MSG)
        return cat
    name = (category_name or "").strip()
    if not name:
        raise ValueError(CATEGORY_REQUIRED_MSG)
    cat = (
        session.query(TransactionCategory)
        .filter_by(
            company_id=company_id,
            transaction_type="Purchase",
            name=name,
            is_active=True,
        )
        .first()
    )
    if cat is None:
        raise ValueError(CATEGORY_REQUIRED_MSG)
    return cat


def _resolve_subcategory(
    session: Session,
    company_id: int,
    cat: TransactionCategory,
    *,
    subcategory_id: int | None,
    subcategory_name: str | None,
) -> TransactionSubcategory | None:
    subcats = (
        session.query(TransactionSubcategory)
        .filter_by(category_id=cat.id, is_active=True)
        .order_by(TransactionSubcategory.name)
        .all()
    )
    if not subcats:
        return None

    if subcategory_id is not None:
        sub = session.get(TransactionSubcategory, subcategory_id)
        if (
            sub is None
            or sub.company_id != company_id
            or sub.category_id != cat.id
            or not sub.is_active
        ):
            raise ValueError(SUBCATEGORY_REQUIRED_MSG)
        return sub

    name = (subcategory_name or "").strip()
    if name:
        sub = next((s for s in subcats if s.name == name), None)
        if sub is None:
            raise ValueError(SUBCATEGORY_REQUIRED_MSG)
        return sub

    return subcats[0]


def _journal_entry_for_purchase(
    session: Session,
    *,
    purchase_id: int,
    payment_method: str,
    company_id: int,
) -> JournalEntry | None:
    ref_type = purchase_ref_type(payment_method)
    return (
        session.query(JournalEntry)
        .filter_by(
            reference_type=ref_type,
            reference_id=purchase_id,
            company_id=company_id,
        )
        .order_by(JournalEntry.id.desc())
        .first()
    )


def _record_bank_withdrawal(
    session: Session,
    *,
    bank_account_id: int,
    company_id: int,
    amount: float,
    entry_date: datetime.date,
    description: str,
) -> None:
    if amount <= 0:
        return
    ba = (
        session.query(BankAccount)
        .filter_by(id=bank_account_id, company_id=company_id, is_active=True)
        .first()
    )
    if ba is None:
        return
    apply_account_balance_delta(ba, "withdrawal", amount)
    session.add(
        BankTransaction(
            account_id=ba.id,
            date=entry_date,
            amount=amount,
            type="withdrawal",
            description=description,
            company_id=company_id,
        )
    )
    session.add(ba)


def _post_purchase_flow(
    session: Session,
    record: Purchase,
    *,
    gl_debit: str,
    payment_method: str,
    company_id: int,
    notes: str,
    vendor_id: int,
    bank_account_id: int | None,
    performed_by: str | None,
    currency: str,
    amount: float,
    entry_date: datetime.date,
) -> int | None:
    """Post GL, payable/bank subledger, and audit (boundary flush or internal commits)."""
    posting_svc.post_purchase(
        session,
        record.id,
        amount,
        entry_date,
        payment_method,
        gl_debit,
        currency=currency,
        fx_rate=record.fx_rate,
        company_id=company_id,
    )

    payable_id: int | None = None

    if payment_method == "Credit":
        payable = Payable(
            date=entry_date,
            vendor_id=vendor_id,
            amount=amount,
            due_date=entry_date + datetime.timedelta(days=30),
            paid=False,
            description=f"From Purchase #{record.id}: {notes.strip()}",
            expense_category=gl_debit,
            purchase_id=record.id,
            company_id=company_id,
        )
        session.add(payable)
        session.flush()
        payable_id = payable.id
        audit_desc = f"PUR#{record.id} · {amount:,.2f} {currency} — payable created"
    else:
        if payment_method == "Bank" and bank_account_id is not None:
            _record_bank_withdrawal(
                session,
                bank_account_id=bank_account_id,
                company_id=company_id,
                amount=amount,
                entry_date=entry_date,
                description=f"Purchase PUR#{record.id}",
            )
        audit_desc = f"PUR#{record.id} · {amount:,.2f} {currency}"

    audit_svc.record_audit(
        session,
        action=audit_svc.ACTION_CREATE,
        entity_type="Purchase",
        entity_id=record.id,
        description=audit_desc,
        performed_by=performed_by,
        company_id=company_id,
    )
    return payable_id


def create_and_post_purchase(
    session: Session,
    *,
    company_id: int,
    user_id: int | None,
    performed_by: str | None,
    entry_date: datetime.date,
    amount: float,
    currency: str,
    payment_method: str,
    notes: str = "",
    vendor_id: int | None = None,
    vendor_name: str | None = None,
    category_id: int | None = None,
    category_name: str | None = None,
    subcategory_id: int | None = None,
    subcategory_name: str | None = None,
    bank_account_id: int | None = None,
    fx_rate: float = 1.0,
) -> PurchaseWriteResult:
    """Persist and post one purchase — mirrors Add Transaction purchase save (Cash/Bank/Credit)."""
    validate_purchase_amount(amount)
    validate_purchase_payment_method(payment_method)

    vendor = _resolve_vendor(
        session,
        company_id,
        vendor_id=vendor_id,
        vendor_name=vendor_name,
    )
    cat = _resolve_category(
        session,
        company_id,
        category_id=category_id,
        category_name=category_name,
    )
    sub = _resolve_subcategory(
        session,
        company_id,
        cat,
        subcategory_id=subcategory_id,
        subcategory_name=subcategory_name,
    )
    gl_debit = cat.name or _DEFAULT_GL_DEBIT

    if payment_method == "Bank":
        if bank_account_id is None:
            has_bank = (
                session.query(BankAccount)
                .filter_by(company_id=company_id, is_active=True, kind="bank")
                .count()
                > 0
            )
            if has_bank:
                raise ValueError(BANK_NOT_SELECTED_MSG)

    native = money_to_float(amount * fx_rate) if fx_rate and fx_rate != 1.0 else amount
    record = Purchase(
        date=entry_date,
        vendor_id=vendor.id,
        amount=amount,
        description=(notes or "").strip(),
        purchase_type=payment_method,
        gl_debit=gl_debit,
        tx_category_id=cat.id,
        tx_subcategory_id=sub.id if sub else None,
        created_by_id=user_id,
        currency=currency,
        fx_rate=fx_rate,
        native_amount=native,
        company_id=company_id,
    )

    payable_id: int | None = None

    if commit_modes.is_boundary_mode(POST_PURCHASE_FAMILY):
        try:
            with boundary_commit_scope(session, POST_PURCHASE_FAMILY):
                session.add(record)
                session.flush()
                payable_id = _post_purchase_flow(
                    session,
                    record,
                    gl_debit=gl_debit,
                    payment_method=payment_method,
                    company_id=company_id,
                    notes=notes,
                    vendor_id=vendor.id,
                    bank_account_id=bank_account_id,
                    performed_by=performed_by,
                    currency=currency,
                    amount=amount,
                    entry_date=entry_date,
                )
        except ValueError:
            raise
    else:
        session.add(record)
        session.commit()
        try:
            posting_svc.post_purchase(
                session,
                record.id,
                amount,
                entry_date,
                payment_method,
                gl_debit,
                currency=currency,
                fx_rate=fx_rate,
                company_id=company_id,
            )
        except ValueError as exc:
            session.rollback()
            raise ValueError(str(exc)) from exc
        if payment_method == "Credit":
            payable = Payable(
                date=entry_date,
                vendor_id=vendor.id,
                amount=amount,
                due_date=entry_date + datetime.timedelta(days=30),
                paid=False,
                description=f"From Purchase #{record.id}: {notes.strip()}",
                expense_category=gl_debit,
                purchase_id=record.id,
                company_id=company_id,
            )
            session.add(payable)
            session.commit()
            payable_id = payable.id
            audit_desc = (
                f"PUR#{record.id} · {amount:,.2f} {currency} — payable created"
            )
        else:
            if payment_method == "Bank" and bank_account_id is not None:
                _record_bank_withdrawal(
                    session,
                    bank_account_id=bank_account_id,
                    company_id=company_id,
                    amount=amount,
                    entry_date=entry_date,
                    description=f"Purchase PUR#{record.id}",
                )
                session.commit()
            audit_desc = f"PUR#{record.id} · {amount:,.2f} {currency}"
        audit_svc.record_audit(
            session,
            action=audit_svc.ACTION_CREATE,
            entity_type="Purchase",
            entity_id=record.id,
            description=audit_desc,
            performed_by=performed_by,
            company_id=company_id,
        )

    entry = _journal_entry_for_purchase(
        session,
        purchase_id=record.id,
        payment_method=payment_method,
        company_id=company_id,
    )
    if payment_method == "Credit":
        message = PURCHASE_RECORDED_PAYABLE_MSG.format(id=record.id)
    else:
        message = PURCHASE_RECORDED_MSG.format(id=record.id)

    return PurchaseWriteResult(
        purchase_id=record.id,
        payable_id=payable_id,
        journal_entry_id=entry.id if entry else None,
        message=message,
    )
