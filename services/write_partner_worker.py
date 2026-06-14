"""FASTAPI-P2.6 — partner and worker movement writes via existing posting kernels."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import (
    BankAccount,
    BankTransaction,
    JournalEntry,
    Partner,
    PartnerMovement,
    Worker,
    WorkerMovement,
)
from services import audit as audit_svc
from services import commit_modes
from services import posting as posting_svc
from services.commit_modes import POST_PARTNER_MOVEMENT_FAMILY, POST_WORKER_MOVEMENT_FAMILY
from services.unit_of_work import boundary_commit_scope

# Pinned kernel strings — must match services/posting.py.
INVALID_AMOUNT_MSG = "Amount must be greater than zero."
PARTNER_NOT_FOUND_MSG = "Partner not found or inactive."
WORKER_NOT_FOUND_MSG = "Worker not found or inactive."
BANK_NOT_FOUND_MSG = "Bank account not found."
UNKNOWN_MOVEMENT_MSG = "Unknown movement type: {movement_type}"

PARTNER_MOVEMENT_TYPES = frozenset(
    {
        "CapitalContribution",
        "Drawing",
        "Salary",
        "Advance",
        "Repayment",
        "AdvanceOffset",
    }
)
WORKER_MOVEMENT_TYPES = frozenset({"Salary", "Advance", "Repayment"})

_PARTNER_REF_TYPES = {
    "CapitalContribution": "PartnerCapital",
    "Drawing": "PartnerDrawing",
    "Salary": "PartnerSalary",
    "Advance": "PartnerAdvance",
    "Repayment": "PartnerRepayment",
    "AdvanceOffset": "PartnerAdvanceOffset",
}
_WORKER_REF_TYPES = {
    "Salary": "WorkerSalary",
    "Advance": "WorkerAdvance",
    "Repayment": "WorkerRepayment",
}


@dataclass(frozen=True, slots=True)
class PartnerMovementWriteResult:
    movement_id: int
    journal_entry_id: int
    message: str


@dataclass(frozen=True, slots=True)
class WorkerPaymentWriteResult:
    payment_id: int
    journal_entry_id: int
    message: str


def _resolve_partner(session: Session, *, company_id: int, partner_id: int) -> Partner:
    partner = session.get(Partner, partner_id)
    if (
        partner is None
        or not partner.is_active
        or partner.company_id != company_id
    ):
        raise ValueError(PARTNER_NOT_FOUND_MSG)
    return partner


def _resolve_worker(session: Session, *, company_id: int, worker_id: int) -> Worker:
    worker = session.get(Worker, worker_id)
    if worker is None or not worker.is_active or worker.company_id != company_id:
        raise ValueError(WORKER_NOT_FOUND_MSG)
    return worker


def _resolve_bank_account(
    session: Session,
    *,
    company_id: int,
    bank_account_id: int | None,
    required: bool,
) -> int | None:
    if bank_account_id is None:
        if required:
            raise ValueError("Bank account is required for this movement type.")
        return None
    ba = (
        session.query(BankAccount)
        .filter_by(id=bank_account_id, company_id=company_id, is_active=True)
        .first()
    )
    if ba is None:
        raise ValueError(BANK_NOT_FOUND_MSG)
    return ba.id


def _movement_journal_entry(
    session: Session,
    *,
    reference_type: str,
    movement_id: int,
    company_id: int,
) -> JournalEntry:
    entry = (
        session.query(JournalEntry)
        .filter_by(
            reference_type=reference_type,
            reference_id=movement_id,
            company_id=company_id,
        )
        .order_by(JournalEntry.id.desc())
        .first()
    )
    if entry is None:
        raise ValueError("Journal entry was not created.")
    return entry


def _stamp_company_on_movement(session: Session, movement, company_id: int) -> None:
    """P2-HARDEN-01a — wrapper-side company stamp parity for API sessions.

    The kernel-created PartnerMovement and the partner/worker movement BankTransaction
    rows do not set company_id (Streamlit relies on the SessionLocal before_flush hook,
    which is a no-op on API sessions). Stamp them from the explicit request company when
    still NULL. No accounting/audit change — only the company_id column on these rows.
    """
    if movement is None:
        return
    if movement.company_id is None:
        movement.company_id = company_id
    btxn_id = getattr(movement, "bank_transaction_id", None)
    if btxn_id is not None:
        btxn = session.get(BankTransaction, btxn_id)
        if btxn is not None and btxn.company_id is None:
            btxn.company_id = company_id


def _partner_audit_description(
    movement_type: str, partner_name: str, amount: float
) -> str:
    return f"{movement_type}: {partner_name} — {amount:,.2f}"


def _worker_audit_description(
    movement_type: str, worker_name: str, amount: float
) -> str:
    return f"{movement_type}: {worker_name} — {amount:,.2f}"


def post_partner_movement_record(
    session: Session,
    *,
    company_id: int,
    performed_by: str | None,
    created_by_id: int | None,
    partner_id: int,
    movement_type: str,
    amount: float,
    entry_date: datetime.date,
    bank_account_id: int | None = None,
    notes: str | None = None,
) -> PartnerMovementWriteResult:
    """Post one partner movement — mirrors app post_partner_movement shim + audit."""
    if movement_type not in PARTNER_MOVEMENT_TYPES:
        raise ValueError(UNKNOWN_MOVEMENT_MSG.format(movement_type=movement_type))

    partner = _resolve_partner(session, company_id=company_id, partner_id=partner_id)
    needs_bank = movement_type != "AdvanceOffset"
    resolved_bank_id = _resolve_bank_account(
        session,
        company_id=company_id,
        bank_account_id=bank_account_id,
        required=needs_bank,
    )

    def _run() -> int:
        movement_id, err = posting_svc.post_partner_movement(
            session,
            partner_id,
            movement_type,
            amount,
            entry_date,
            bank_account_id=resolved_bank_id,
            notes=notes,
            created_by_id=created_by_id,
            company_id=company_id,
        )
        if err:
            raise ValueError(err)
        _stamp_company_on_movement(
            session, session.get(PartnerMovement, movement_id), company_id
        )
        audit_svc.record_audit(
            session,
            action=audit_svc.ACTION_CREATE,
            entity_type=audit_svc.ENTITY_PARTNER_MOVEMENT,
            entity_id=movement_id,
            description=_partner_audit_description(
                movement_type, partner.name, amount
            ),
            performed_by=performed_by,
            company_id=company_id,
        )
        return movement_id

    if commit_modes.is_boundary_mode(POST_PARTNER_MOVEMENT_FAMILY):
        with boundary_commit_scope(session, POST_PARTNER_MOVEMENT_FAMILY):
            movement_id = _run()
    else:
        movement_id = _run()

    entry = _movement_journal_entry(
        session,
        reference_type=_PARTNER_REF_TYPES[movement_type],
        movement_id=movement_id,
        company_id=company_id,
    )
    movement = session.get(PartnerMovement, movement_id)
    display_amount = movement.amount if movement is not None else amount
    message = _partner_audit_description(
        movement_type, partner.name, display_amount
    )
    return PartnerMovementWriteResult(
        movement_id=movement_id,
        journal_entry_id=entry.id,
        message=message,
    )


def post_worker_payment_record(
    session: Session,
    *,
    company_id: int,
    performed_by: str | None,
    created_by_id: int | None,
    worker_id: int,
    movement_type: str,
    entry_date: datetime.date,
    bank_account_id: int,
    amount: float | None = None,
    gross_salary: float | None = None,
    deductions: float | None = None,
    advance_recovery: float | None = None,
    pay_period: str | None = None,
    notes: str | None = None,
) -> WorkerPaymentWriteResult:
    """Post one worker movement — mirrors app post_worker_movement shim + audit."""
    if movement_type not in WORKER_MOVEMENT_TYPES:
        raise ValueError(UNKNOWN_MOVEMENT_MSG.format(movement_type=movement_type))

    worker = _resolve_worker(session, company_id=company_id, worker_id=worker_id)
    resolved_bank_id = _resolve_bank_account(
        session,
        company_id=company_id,
        bank_account_id=bank_account_id,
        required=True,
    )

    def _run() -> tuple[int, float]:
        movement_id, err = posting_svc.post_worker_movement(
            session,
            worker_id,
            movement_type,
            entry_date,
            bank_account_id=resolved_bank_id,
            amount=amount,
            gross_salary=gross_salary,
            deductions=deductions,
            advance_recovery=advance_recovery,
            pay_period=pay_period,
            notes=notes,
            created_by_id=created_by_id,
            company_id=company_id,
        )
        if err:
            raise ValueError(err)
        movement = session.get(WorkerMovement, movement_id)
        mv_amount = movement.amount if movement is not None else (amount or 0.0)
        _stamp_company_on_movement(session, movement, company_id)
        audit_desc = _worker_audit_description(
            movement_type, worker.name, mv_amount
        )
        audit_svc.record_audit(
            session,
            action=audit_svc.ACTION_CREATE,
            entity_type=audit_svc.ENTITY_WORKER_MOVEMENT,
            entity_id=movement_id,
            description=audit_desc,
            performed_by=performed_by,
            company_id=company_id,
        )
        return movement_id, mv_amount

    if commit_modes.is_boundary_mode(POST_WORKER_MOVEMENT_FAMILY):
        with boundary_commit_scope(session, POST_WORKER_MOVEMENT_FAMILY):
            movement_id, mv_amount = _run()
    else:
        movement_id, mv_amount = _run()

    entry = _movement_journal_entry(
        session,
        reference_type=_WORKER_REF_TYPES[movement_type],
        movement_id=movement_id,
        company_id=company_id,
    )
    message = _worker_audit_description(movement_type, worker.name, mv_amount)
    return WorkerPaymentWriteResult(
        payment_id=movement_id,
        journal_entry_id=entry.id,
        message=message,
    )
