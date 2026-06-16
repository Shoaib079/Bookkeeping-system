"""FASTAPI-P2.2 — create and post expenses (Streamlit-free, mirrors Add Transaction expense path)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import BankAccount, BankTransaction, ExpenseRecord, JournalEntry, TransactionCategory, TransactionSubcategory
from reconciliation.company_card import apply_account_balance_delta
from services import audit as audit_svc
from services import commit_modes
from services import posting as posting_svc
from services.money import money_to_float
from services.commit_modes import POST_EXPENSE_FAMILY
from services.unit_of_work import boundary_commit_scope, boundary_depth

# Pinned EN transactional strings — must match registry/locales/transactional.py.
INVALID_AMOUNT_MSG = "❌ Please enter a valid amount greater than zero."
CATEGORY_REQUIRED_MSG = "Select a category before saving"
SUBCATEGORY_REQUIRED_MSG = "Select a subcategory for this category"
BANK_NOT_SELECTED_MSG = "No bank account selected."
EXPENSE_RECORDED_MSG = "{category} expense recorded."

EXPENSE_PAYMENT_METHODS = frozenset({"Cash", "Bank"})
_EXPENSE_TYPE_LABEL = "Expense"

_REF_TYPE = "Expense"


@dataclass(frozen=True, slots=True)
class ExpenseWriteResult:
    expense_id: int
    journal_entry_id: int | None
    message: str


def _pay_method_not_allowed_error(method: str) -> str:
    return (
        f'Payment method "{method}" is not valid for {_EXPENSE_TYPE_LABEL}. '
        "A valid method has been selected — review and save again."
    )


def validate_expense_amount(amount: float | None) -> None:
    if amount is None or amount <= 0:
        raise ValueError(INVALID_AMOUNT_MSG)


def validate_expense_payment_method(payment_method: str) -> None:
    if payment_method not in EXPENSE_PAYMENT_METHODS:
        raise ValueError(_pay_method_not_allowed_error(payment_method or ""))


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
            or cat.transaction_type != "Expense"
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
            transaction_type="Expense",
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
) -> tuple[TransactionSubcategory | None, str | None]:
    subcats = (
        session.query(TransactionSubcategory)
        .filter_by(category_id=cat.id, is_active=True)
        .order_by(TransactionSubcategory.name)
        .all()
    )
    if not subcats:
        return None, None

    if subcategory_id is not None:
        sub = session.get(TransactionSubcategory, subcategory_id)
        if (
            sub is None
            or sub.company_id != company_id
            or sub.category_id != cat.id
            or not sub.is_active
        ):
            raise ValueError(SUBCATEGORY_REQUIRED_MSG)
        return sub, sub.name

    name = (subcategory_name or "").strip()
    if name:
        sub = next((s for s in subcats if s.name == name), None)
        if sub is None:
            raise ValueError(SUBCATEGORY_REQUIRED_MSG)
        return sub, sub.name

    # Mirror Streamlit _at_resolve_submit_subcategory auto-pick.
    return subcats[0], subcats[0].name


def _journal_entry_for_expense(
    session: Session,
    *,
    expense_id: int,
    company_id: int,
) -> JournalEntry | None:
    return (
        session.query(JournalEntry)
        .filter_by(
            reference_type=_REF_TYPE,
            reference_id=expense_id,
            company_id=company_id,
        )
        .order_by(JournalEntry.id.desc())
        .first()
    )


def _save_and_post_expense_record(
    session: Session,
    record: ExpenseRecord,
    *,
    gl_category: str,
    payment_method: str,
    company_id: int,
) -> None:
    """Mirror app._save_and_post_expense_record without Streamlit (Cash/Bank only)."""
    session.add(record)
    session.flush()
    try:
        posting_svc.post_expense(
            session,
            record.id,
            record.amount,
            record.date,
            gl_category,
            payment_method=payment_method,
            currency=record.currency,
            company_id=company_id,
        )
    except ValueError as exc:
        if boundary_depth() > 0:
            raise
        session.rollback()
        raise ValueError(str(exc)) from exc
    if boundary_depth() > 0:
        session.flush()
    else:
        session.commit()


def _record_bank_withdrawal(
    session: Session,
    *,
    bank_account_id: int,
    company_id: int,
    amount: float,
    entry_date: datetime.date,
    description: str,
) -> None:
    """Mirror app._record_named_bank_movement using bank account id."""
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


def create_and_post_expense(
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
    category_id: int | None = None,
    category_name: str | None = None,
    subcategory_id: int | None = None,
    subcategory_name: str | None = None,
    bank_account_id: int | None = None,
    fx_rate: float = 1.0,
) -> ExpenseWriteResult:
    """Persist and post one expense — mirrors Add Transaction expense save (general mode)."""
    validate_expense_amount(amount)
    validate_expense_payment_method(payment_method)

    cat = _resolve_category(
        session,
        company_id,
        category_id=category_id,
        category_name=category_name,
    )
    sub, subcat_name = _resolve_subcategory(
        session,
        company_id,
        cat,
        subcategory_id=subcategory_id,
        subcategory_name=subcategory_name,
    )
    gl_category = subcat_name or cat.name
    expense_type = cat.name

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
    record = ExpenseRecord(
        date=entry_date,
        expense_type=expense_type,
        category=gl_category,
        description=(notes or "").strip(),
        amount=amount,
        payment_method=payment_method,
        gross_salary=amount,
        deductions=0.0,
        net_salary=amount,
        tx_category_id=cat.id,
        tx_subcategory_id=sub.id if sub else None,
        created_by_id=user_id,
        currency=currency,
        fx_rate=fx_rate,
        native_amount=native,
        company_id=company_id,
    )

    audit_desc = f"{expense_type} expense · {amount:,.2f} {currency}"
    success_msg = EXPENSE_RECORDED_MSG.format(category=expense_type)
    audit_logged = False

    if commit_modes.is_boundary_mode(POST_EXPENSE_FAMILY):
        with boundary_commit_scope(session, POST_EXPENSE_FAMILY):
            _save_and_post_expense_record(
                session,
                record,
                gl_category=gl_category,
                payment_method=payment_method,
                company_id=company_id,
            )
            if payment_method == "Bank" and bank_account_id is not None:
                _record_bank_withdrawal(
                    session,
                    bank_account_id=bank_account_id,
                    company_id=company_id,
                    amount=amount,
                    entry_date=entry_date,
                    description=f"Expense EXP#{record.id} — {expense_type}",
                )
            audit_svc.record_audit(
                session,
                action=audit_svc.ACTION_CREATE,
                entity_type=audit_svc.ENTITY_EXPENSE_RECORD,
                entity_id=record.id,
                description=audit_desc,
                performed_by=performed_by,
                company_id=company_id,
            )
            audit_logged = True
    else:
        _save_and_post_expense_record(
            session,
            record,
            gl_category=gl_category,
            payment_method=payment_method,
            company_id=company_id,
        )
        if payment_method == "Bank" and bank_account_id is not None:
            _record_bank_withdrawal(
                session,
                bank_account_id=bank_account_id,
                company_id=company_id,
                amount=amount,
                entry_date=entry_date,
                description=f"Expense EXP#{record.id} — {expense_type}",
            )
            session.commit()
        audit_svc.record_audit(
            session,
            action=audit_svc.ACTION_CREATE,
            entity_type=audit_svc.ENTITY_EXPENSE_RECORD,
            entity_id=record.id,
            description=audit_desc,
            performed_by=performed_by,
            company_id=company_id,
        )
        audit_logged = True

    entry = _journal_entry_for_expense(
        session,
        expense_id=record.id,
        company_id=company_id,
    )
    return ExpenseWriteResult(
        expense_id=record.id,
        journal_entry_id=entry.id if entry else None,
        message=success_msg,
    )
