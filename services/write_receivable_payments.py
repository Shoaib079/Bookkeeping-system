"""FASTAPI-P2.4 — record receivable payments (Streamlit-free, mirrors Customer Payment path)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import BankAccount, BankTransaction, Customer, JournalEntry, Sale
from reconciliation.company_card import apply_account_balance_delta
from services import audit as audit_svc
from services import commit_modes
from services import posting as posting_svc
from services.commit_modes import POST_RECEIVABLE_PAYMENT_FAMILY
from services.unit_of_work import boundary_commit_scope

# Pinned EN transactional strings — must match registry/locales/transactional.py / posting kernel.
ZERO_PAYMENT_MSG = "Payment amount must be greater than zero."
NOT_CREDIT_SALE_MSG = "Sale not found or is not a credit sale."
BANK_NOT_SELECTED_MSG = "No bank account selected."
CUSTOMER_PAYMENT_MSG = "Payment of {amount:,.2f} recorded against {invoice}."

CUSTOMER_PAYMENT_METHODS = frozenset({"Cash", "Bank"})
_CUSTOMER_PAYMENT_TYPE_LABEL = "Customer Payment"

_REF_TYPE = "ReceivablePayment"


@dataclass(frozen=True, slots=True)
class ReceivablePaymentWriteResult:
    payment_id: int
    journal_entry_id: int
    sale_id: int
    message: str


def _pay_method_not_allowed_error(method: str) -> str:
    return (
        f'Payment method "{method}" is not valid for {_CUSTOMER_PAYMENT_TYPE_LABEL}. '
        "A valid method has been selected — review and save again."
    )


def validate_customer_payment_method(payment_method: str) -> None:
    if payment_method not in CUSTOMER_PAYMENT_METHODS:
        raise ValueError(_pay_method_not_allowed_error(payment_method or ""))


def _resolve_credit_sale(
    session: Session,
    company_id: int,
    sale_id: int,
    *,
    customer_id: int | None = None,
    customer_name: str | None = None,
) -> Sale:
    sale = session.get(Sale, sale_id)
    if (
        sale is None
        or sale.company_id != company_id
        or sale.sale_type != "Credit"
        or sale.is_void
    ):
        raise ValueError(NOT_CREDIT_SALE_MSG)
    if customer_id is not None and sale.customer_id != customer_id:
        raise ValueError(NOT_CREDIT_SALE_MSG)
    if customer_name is not None:
        name = customer_name.strip()
        if name and sale.customer_name != name:
            raise ValueError(NOT_CREDIT_SALE_MSG)
    if customer_id is None and customer_name:
        cust = (
            session.query(Customer)
            .filter_by(company_id=company_id, name=customer_name.strip(), is_active=True)
            .first()
        )
        if cust and sale.customer_id and sale.customer_id != cust.id:
            raise ValueError(NOT_CREDIT_SALE_MSG)
    return sale


def _journal_entry_for_payment(
    session: Session,
    *,
    sale_id: int,
    company_id: int,
) -> JournalEntry | None:
    return (
        session.query(JournalEntry)
        .filter_by(
            reference_type=_REF_TYPE,
            reference_id=sale_id,
            company_id=company_id,
        )
        .order_by(JournalEntry.id.desc())
        .first()
    )


def _record_bank_deposit(
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
    apply_account_balance_delta(ba, "deposit", amount)
    session.add(
        BankTransaction(
            account_id=ba.id,
            date=entry_date,
            amount=amount,
            type="deposit",
            description=description,
            company_id=company_id,
        )
    )
    session.add(ba)


def record_receivable_payment(
    session: Session,
    *,
    company_id: int,
    performed_by: str | None,
    entry_date: datetime.date,
    amount: float,
    currency: str,
    payment_method: str,
    sale_id: int,
    customer_id: int | None = None,
    customer_name: str | None = None,
    bank_account_id: int | None = None,
    payment_fx_rate: float = 1.0,
    notes: str = "",
) -> ReceivablePaymentWriteResult:
    """Record payment against a credit sale — mirrors Add Transaction Customer Payment."""
    validate_customer_payment_method(payment_method)
    sale = _resolve_credit_sale(
        session,
        company_id,
        sale_id,
        customer_id=customer_id,
        customer_name=customer_name,
    )

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

    audit_desc = f"Payment {amount:,.2f} {currency} on {sale.invoice_number}"

    if commit_modes.is_boundary_mode(POST_RECEIVABLE_PAYMENT_FAMILY):
        with boundary_commit_scope(session, POST_RECEIVABLE_PAYMENT_FAMILY):
            err = posting_svc.post_receivable_payment(
                session,
                sale.id,
                amount,
                entry_date,
                payment_method,
                currency=currency,
                payment_fx_rate=payment_fx_rate,
                company_id=company_id,
            )
            if err:
                raise ValueError(err)
            if payment_method == "Bank" and bank_account_id is not None:
                _record_bank_deposit(
                    session,
                    bank_account_id=bank_account_id,
                    company_id=company_id,
                    amount=amount,
                    entry_date=entry_date,
                    description=f"Customer payment {sale.invoice_number}",
                )
            audit_svc.record_audit(
                session,
                action=audit_svc.ACTION_PAYMENT,
                entity_type=audit_svc.ENTITY_SALE,
                entity_id=sale.id,
                description=audit_desc,
                performed_by=performed_by,
                company_id=company_id,
            )
    else:
        err = posting_svc.post_receivable_payment(
            session,
            sale.id,
            amount,
            entry_date,
            payment_method,
            currency=currency,
            payment_fx_rate=payment_fx_rate,
            company_id=company_id,
        )
        if err:
            raise ValueError(err)
        if payment_method == "Bank" and bank_account_id is not None:
            _record_bank_deposit(
                session,
                bank_account_id=bank_account_id,
                company_id=company_id,
                amount=amount,
                entry_date=entry_date,
                description=f"Customer payment {sale.invoice_number}",
            )
            session.commit()
        audit_svc.record_audit(
            session,
            action=audit_svc.ACTION_PAYMENT,
            entity_type=audit_svc.ENTITY_SALE,
            entity_id=sale.id,
            description=audit_desc,
            performed_by=performed_by,
            company_id=company_id,
        )

    entry = _journal_entry_for_payment(session, sale_id=sale.id, company_id=company_id)
    if entry is None:
        raise ValueError("Payment journal entry was not created.")

    message = CUSTOMER_PAYMENT_MSG.format(
        amount=amount,
        invoice=sale.invoice_number,
    )
    return ReceivablePaymentWriteResult(
        payment_id=entry.id,
        journal_entry_id=entry.id,
        sale_id=sale.id,
        message=message,
    )
