"""FASTAPI-P2.1 — create and post sales (Streamlit-free, mirrors Add Transaction sale path)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import BankAccount, BankTransaction, Customer, JournalEntry, Sale
from reconciliation.company_card import apply_account_balance_delta
from services import audit as audit_svc
from services import commit_modes
from services import posting as posting_svc
from services.commit_modes import POST_CASH_SALE_FAMILY
from services.money import money_to_float, persist_money
from services.unit_of_work import boundary_commit_scope

# Pinned EN transactional strings — must match registry/locales/transactional.py.
INVALID_AMOUNT_MSG = "❌ Please enter a valid amount greater than zero."
CREDIT_CUSTOMER_MSG = "Enter a customer name for on-account (credit) sales."
SALE_RECORDED_MSG = "Sale recorded — Invoice {invoice}"

SALE_PAYMENT_METHODS = frozenset({"Cash", "Card", "Credit"})
_SALE_TYPE_LABEL = "Sale"

_REF_TYPE_BY_SALE_TYPE = {
    "Cash": "CashSale",
    "Card": "CardSale",
    "Credit": "CreditSale",
}


@dataclass(frozen=True, slots=True)
class SaleWriteResult:
    sale_id: int
    journal_entry_id: int | None
    invoice_number: str
    message: str


def _pay_method_not_allowed_error(method: str) -> str:
    return (
        f'Payment method "{method}" is not valid for {_SALE_TYPE_LABEL}. '
        "A valid method has been selected — review and save again."
    )


def validate_sale_amount(amount: float | None) -> None:
    if amount is None or amount <= 0:
        raise ValueError(INVALID_AMOUNT_MSG)


def validate_sale_payment_method(payment_method: str) -> None:
    if payment_method not in SALE_PAYMENT_METHODS:
        raise ValueError(_pay_method_not_allowed_error(payment_method or ""))


def validate_credit_sale_customer(customer_name: str | None) -> None:
    """Credit (on-account) sales need a real customer — not blank or walk-in default."""
    name = (customer_name or "").strip()
    if not name or name == "Walk-in Customer":
        raise ValueError(CREDIT_CUSTOMER_MSG)


def _journal_entry_for_sale(
    session: Session,
    *,
    sale_id: int,
    reference_type: str,
    company_id: int,
) -> JournalEntry | None:
    return (
        session.query(JournalEntry)
        .filter_by(
            reference_type=reference_type,
            reference_id=sale_id,
            company_id=company_id,
        )
        .order_by(JournalEntry.id.desc())
        .first()
    )


def create_and_post_sale(
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
    customer_name: str | None = None,
    card_bank_account_id: int | None = None,
    fx_rate: float = 1.0,
) -> SaleWriteResult:
    """Persist and post one sale — mirrors ``app._at_save`` sale branch for Add Transaction."""
    validate_sale_amount(amount)
    validate_sale_payment_method(payment_method)
    if payment_method == "Credit":
        validate_credit_sale_customer(customer_name)

    sale_type = payment_method
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    inv_num = f"INV-{ts}"
    cname = (customer_name or "").strip() or "Walk-in Customer"
    cust_obj = (
        session.query(Customer)
        .filter_by(name=cname, company_id=company_id, is_active=True)
        .first()
    )

    native = money_to_float(amount * fx_rate) if fx_rate and fx_rate != 1.0 else amount
    record = Sale(
        date=entry_date,
        invoice_number=inv_num,
        customer_name=cname,
        description=(notes or "").strip(),
        amount=amount,
        sale_type=sale_type,
        paid_amount=amount if sale_type != "Credit" else 0.0,
        balance=0.0 if sale_type != "Credit" else amount,
        due_date=entry_date if sale_type != "Credit" else entry_date + datetime.timedelta(days=30),
        status="Paid" if sale_type != "Credit" else "Open",
        created_by_id=user_id,
        customer_id=cust_obj.id if cust_obj else None,
        currency=currency,
        fx_rate=fx_rate,
        native_amount=native,
        company_id=company_id,
    )
    session.add(record)
    session.commit()

    audit_desc = f"Sale {inv_num} · {amount:,.2f} {currency}"
    audit_logged = False

    if sale_type == "Card":
        posting_svc.post_card_sale(
            session,
            record.id,
            amount,
            entry_date,
            currency=currency,
            fx_rate=fx_rate,
            company_id=company_id,
        )
        if not posting_svc.card_settlement_on(session, company_id) and card_bank_account_id:
            card_ba = (
                session.query(BankAccount)
                .filter_by(id=card_bank_account_id, company_id=company_id, is_active=True)
                .first()
            )
            if card_ba:
                apply_account_balance_delta(card_ba, "deposit", amount)
                session.add(
                    BankTransaction(
                        account_id=card_ba.id,
                        date=entry_date,
                        amount=persist_money(amount),
                        type="deposit",
                        description=f"Card Sale {inv_num}",
                        company_id=company_id,
                    )
                )
                session.commit()
    elif sale_type == "Cash":
        if commit_modes.is_boundary_mode(POST_CASH_SALE_FAMILY):
            with boundary_commit_scope(session, POST_CASH_SALE_FAMILY):
                posting_svc.post_cash_sale(
                    session,
                    record.id,
                    amount,
                    entry_date,
                    currency=currency,
                    fx_rate=fx_rate,
                    company_id=company_id,
                )
                audit_svc.record_audit(
                    session,
                    action=audit_svc.ACTION_CREATE,
                    entity_type=audit_svc.ENTITY_SALE,
                    entity_id=record.id,
                    description=audit_desc,
                    performed_by=performed_by,
                    company_id=company_id,
                )
                audit_logged = True
        else:
            posting_svc.post_cash_sale(
                session,
                record.id,
                amount,
                entry_date,
                currency=currency,
                fx_rate=fx_rate,
                company_id=company_id,
            )
    else:
        posting_svc.post_credit_sale(
            session,
            record.id,
            amount,
            entry_date,
            currency=currency,
            fx_rate=fx_rate,
            company_id=company_id,
        )

    if not audit_logged:
        audit_svc.record_audit(
            session,
            action=audit_svc.ACTION_CREATE,
            entity_type=audit_svc.ENTITY_SALE,
            entity_id=record.id,
            description=audit_desc,
            performed_by=performed_by,
            company_id=company_id,
        )

    ref_type = _REF_TYPE_BY_SALE_TYPE[sale_type]
    entry = _journal_entry_for_sale(
        session,
        sale_id=record.id,
        reference_type=ref_type,
        company_id=company_id,
    )
    return SaleWriteResult(
        sale_id=record.id,
        journal_entry_id=entry.id if entry else None,
        invoice_number=inv_num,
        message=SALE_RECORDED_MSG.format(invoice=inv_num),
    )
