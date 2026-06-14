"""FASTAPI-P2.5 — void records via existing posting kernels (Streamlit-free)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from sqlalchemy.orm import Session

from models import (
    BankTransaction,
    ExpenseRecord,
    JournalEntry,
    Payable,
    Purchase,
    Sale,
)
from services import audit as audit_svc
from services import commit_modes
from services import posting as posting_svc
from services.commit_modes import VOID_CASCADE_FAMILY
from services.posting import purchase_ref_type
from services.unit_of_work import boundary_commit_scope

# Pinned EN transactional strings — must match registry/locales/transactional.py.
VOID_REASON_REQUIRED_MSG = "Void reason is required."
INVALID_TARGET_TYPE_MSG = "Unsupported void target type: {target_type}"
NOT_FOUND_OR_VOIDED_MSG = "Record not found or is already voided."

SALE_VOIDED_MSG = "Sale {invoice} voided. Reversing journal posted."
EXPENSE_VOIDED_MSG = "Expense voided. Reversing journal posted."
PURCHASE_VOIDED_MSG = "Purchase voided. Reversing journal posted."
PAYABLE_VOIDED_MSG = "Payable voided. Reversing journals posted."
BANK_VOIDED_MSG = "Bank transaction voided. GL reversed and balance restored."

SUPPORTED_VOID_TARGETS = frozenset(
    {"Sale", "ExpenseRecord", "Purchase", "Payable", "BankTransaction"}
)

_REVERSAL_REF_TYPES: dict[str, tuple[str, ...]] = {
    "Sale": ("CashSale", "CardSale", "CreditSale", "ReceivablePayment"),
    "ExpenseRecord": ("Expense",),
    "Purchase": (),  # resolved per record
    "Payable": ("PayableCreation", "PayablePayment"),
    "BankTransaction": ("BankDeposit", "BankWithdrawal", "BankTransfer"),
}


@dataclass(frozen=True, slots=True)
class VoidWriteResult:
    target_type: str
    target_id: int
    reversal_journal_entry_id: int | None
    message: str


def _validate_void_reason(reason: str | None) -> str:
    cleaned = (reason or "").strip()
    if not cleaned:
        raise ValueError(VOID_REASON_REQUIRED_MSG)
    return cleaned


def _entity_company_id(session: Session, target_type: str, target_id: int) -> int | None:
    loaders: dict[str, Callable[[Session, int], object | None]] = {
        "Sale": lambda s, i: s.get(Sale, i),
        "ExpenseRecord": lambda s, i: s.get(ExpenseRecord, i),
        "Purchase": lambda s, i: s.get(Purchase, i),
        "Payable": lambda s, i: s.get(Payable, i),
        "BankTransaction": lambda s, i: s.get(BankTransaction, i),
    }
    obj = loaders[target_type](session, target_id)
    if obj is None:
        return None
    return getattr(obj, "company_id", None)


def _latest_reversal_je_id(
    session: Session,
    *,
    company_id: int,
    reference_types: tuple[str, ...],
    target_id: int,
) -> int | None:
    orig_ids = []
    for ref_type in reference_types:
        rows = (
            session.query(JournalEntry.id)
            .filter_by(
                reference_type=ref_type,
                reference_id=target_id,
                company_id=company_id,
            )
            .all()
        )
        orig_ids.extend(row[0] for row in rows)
    if not orig_ids:
        return None
    rev = (
        session.query(JournalEntry)
        .filter(
            JournalEntry.reference_type == "Reversal",
            JournalEntry.reference_id.in_(orig_ids),
            JournalEntry.company_id == company_id,
        )
        .order_by(JournalEntry.id.desc())
        .first()
    )
    return rev.id if rev else None


def _void_kernel(
    session: Session,
    *,
    target_type: str,
    target_id: int,
    reason: str,
    company_id: int,
) -> bool:
    if target_type == "Sale":
        return posting_svc.void_sale(
            session, target_id, reason, company_id=company_id
        )
    if target_type == "ExpenseRecord":
        return posting_svc.void_expense(
            session, target_id, reason, company_id=company_id
        )
    if target_type == "Purchase":
        return posting_svc.void_purchase(
            session, target_id, reason, company_id=company_id
        )
    if target_type == "Payable":
        return posting_svc.void_payable(
            session, target_id, reason, company_id=company_id
        )
    if target_type == "BankTransaction":
        return posting_svc.void_bank_transaction(
            session, target_id, reason, company_id=company_id
        )
    raise ValueError(INVALID_TARGET_TYPE_MSG.format(target_type=target_type))


def _audit_entity_type(target_type: str) -> str:
    return {
        "Sale": audit_svc.ENTITY_SALE,
        "ExpenseRecord": audit_svc.ENTITY_EXPENSE_RECORD,
        "Purchase": audit_svc.ENTITY_PURCHASE,
        "Payable": audit_svc.ENTITY_PAYABLE,
        "BankTransaction": audit_svc.ENTITY_BANK_TRANSACTION,
    }[target_type]


def _audit_description(target_type: str, target_id: int, reason: str) -> str:
    labels = {
        "Sale": f"Voided Sale #{target_id}: {reason}",
        "ExpenseRecord": f"Voided Expense #{target_id}: {reason}",
        "Purchase": f"Voided Purchase #{target_id}: {reason}",
        "Payable": f"Voided Payable #{target_id}: {reason}",
        "BankTransaction": f"Voided Bank Transaction #{target_id}: {reason}",
    }
    return labels[target_type]


def _success_message(
    session: Session,
    *,
    target_type: str,
    target_id: int,
) -> str:
    if target_type == "Sale":
        sale = session.get(Sale, target_id)
        invoice = sale.invoice_number if sale else str(target_id)
        return SALE_VOIDED_MSG.format(invoice=invoice)
    if target_type == "ExpenseRecord":
        return EXPENSE_VOIDED_MSG
    if target_type == "Purchase":
        return PURCHASE_VOIDED_MSG
    if target_type == "Payable":
        return PAYABLE_VOIDED_MSG
    return BANK_VOIDED_MSG


def _reversal_ref_types(
    session: Session,
    *,
    target_type: str,
    target_id: int,
) -> tuple[str, ...]:
    if target_type == "Purchase":
        purchase = session.get(Purchase, target_id)
        if purchase is None:
            return ()
        return (purchase_ref_type(purchase.purchase_type),)
    return _REVERSAL_REF_TYPES[target_type]


def void_record(
    session: Session,
    *,
    company_id: int,
    performed_by: str | None,
    target_type: str,
    target_id: int,
    reason: str,
) -> VoidWriteResult:
    """Void one supported record — mirrors app void shims + audit in boundary scope."""
    cleaned_reason = _validate_void_reason(reason)
    if target_type not in SUPPORTED_VOID_TARGETS:
        raise ValueError(INVALID_TARGET_TYPE_MSG.format(target_type=target_type))

    entity_cid = _entity_company_id(session, target_type, target_id)
    if entity_cid is None or entity_cid != company_id:
        raise ValueError(NOT_FOUND_OR_VOIDED_MSG)

    entity_audit_type = _audit_entity_type(target_type)
    audit_desc = _audit_description(target_type, target_id, cleaned_reason)

    if commit_modes.is_boundary_mode(VOID_CASCADE_FAMILY):
        with boundary_commit_scope(session, VOID_CASCADE_FAMILY):
            ok = _void_kernel(
                session,
                target_type=target_type,
                target_id=target_id,
                reason=cleaned_reason,
                company_id=company_id,
            )
            if not ok:
                raise ValueError(NOT_FOUND_OR_VOIDED_MSG)
            audit_svc.record_audit(
                session,
                action=audit_svc.ACTION_VOID,
                entity_type=entity_audit_type,
                entity_id=target_id,
                description=audit_desc,
                performed_by=performed_by,
                company_id=company_id,
            )
    else:
        ok = _void_kernel(
            session,
            target_type=target_type,
            target_id=target_id,
            reason=cleaned_reason,
            company_id=company_id,
        )
        if not ok:
            raise ValueError(NOT_FOUND_OR_VOIDED_MSG)
        audit_svc.record_audit(
            session,
            action=audit_svc.ACTION_VOID,
            entity_type=entity_audit_type,
            entity_id=target_id,
            description=audit_desc,
            performed_by=performed_by,
            company_id=company_id,
        )

    reversal_id = _latest_reversal_je_id(
        session,
        company_id=company_id,
        reference_types=_reversal_ref_types(
            session, target_type=target_type, target_id=target_id
        ),
        target_id=target_id,
    )
    return VoidWriteResult(
        target_type=target_type,
        target_id=target_id,
        reversal_journal_entry_id=reversal_id,
        message=_success_message(
            session, target_type=target_type, target_id=target_id
        ),
    )
