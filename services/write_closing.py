"""FASTAPI-P2.9 — period close / profit allocation / allocation void via posting kernels.

Streamlit-free wrapper mirroring the app.py shims (kernel call + audit row), with
boundary commit ownership and explicit company scoping. Accounting behavior and the
pinned audit strings are preserved verbatim from the app shims.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import FiscalPeriod, JournalEntry, Partner, PartnerProfitAllocation
from services import audit as audit_svc
from services import commit_modes
from services import posting as posting_svc
from services.commit_modes import (
    PERIOD_CLOSE_FAMILY,
    PROFIT_ALLOCATION_FAMILY,
    VOID_CASCADE_FAMILY,
)
from services.posting import _get_period_net_income_from_je
from services.unit_of_work import boundary_commit_scope

# Pinned not-found strings — mirror kernel/shim contract and avoid leaking
# cross-company existence (same string for missing / closed / other-company).
PERIOD_NOT_FOUND_OR_CLOSED_MSG = "Period not found or already closed."
FISCAL_PERIOD_NOT_FOUND_MSG = "Fiscal period not found."
ALLOCATION_NOT_FOUND_OR_VOIDED_MSG = "Allocation not found or already voided."


@dataclass(frozen=True, slots=True)
class PeriodCloseWriteResult:
    period_id: int
    journal_entry_id: int
    message: str


@dataclass(frozen=True, slots=True)
class ProfitAllocationWriteResult:
    allocation_id: int
    journal_entry_id: int | None
    message: str


@dataclass(frozen=True, slots=True)
class AllocationVoidWriteResult:
    allocation_id: int
    reversal_journal_entry_id: int | None
    message: str


def _active_partner_count(session: Session, company_id: int) -> int:
    return (
        session.query(Partner)
        .filter(Partner.is_active == True, Partner.company_id == company_id)  # noqa: E712
        .count()
    )


def _latest_reversal_je_id(
    session: Session, *, company_id: int, original_je_id: int | None
) -> int | None:
    if original_je_id is None:
        return None
    rev = (
        session.query(JournalEntry)
        .filter(
            JournalEntry.reference_type == "Reversal",
            JournalEntry.reference_id == original_je_id,
            JournalEntry.company_id == company_id,
        )
        .order_by(JournalEntry.id.desc())
        .first()
    )
    return rev.id if rev else None


def close_period(
    session: Session,
    *,
    company_id: int,
    performed_by: str | None,
    period_id: int,
) -> PeriodCloseWriteResult:
    """Close a fiscal period — mirrors app close_fiscal_period shim in a boundary scope."""
    period = session.get(FiscalPeriod, period_id)
    if period is None or period.company_id != company_id:
        raise ValueError(PERIOD_NOT_FOUND_OR_CLOSED_MSG)
    period_name = period.name

    def _run():
        je = posting_svc.close_fiscal_period(session, period_id, company_id=company_id)
        period_obj = session.get(FiscalPeriod, period_id)
        net_income = _get_period_net_income_from_je(
            session, period_obj, company_id=company_id
        )
        audit_svc.record_audit(
            session,
            action=audit_svc.ACTION_PERIOD_CLOSE,
            entity_type=audit_svc.ENTITY_FISCAL_PERIOD,
            entity_id=period_id,
            description=(
                f"Closed period '{period_obj.name}' "
                f"({period_obj.start_date}–{period_obj.end_date}). "
                f"Net income: ${net_income:,.2f}. Closing JE #{je.id}."
            ),
            performed_by=performed_by,
            company_id=company_id,
            commit_family=PERIOD_CLOSE_FAMILY,
        )
        return je

    if commit_modes.is_boundary_mode(PERIOD_CLOSE_FAMILY):
        with boundary_commit_scope(session, PERIOD_CLOSE_FAMILY):
            je = _run()
    else:
        je = _run()

    return PeriodCloseWriteResult(
        period_id=period_id,
        journal_entry_id=je.id,
        message=f"Period '{period_name}' closed. Closing journal #{je.id} posted.",
    )


def allocate(
    session: Session,
    *,
    company_id: int,
    performed_by: str | None,
    allocated_by_id: int,
    period_id: int,
    notes: str | None = None,
) -> ProfitAllocationWriteResult:
    """Allocate a closed period's net income — mirrors app allocate shim in a boundary scope."""
    period = session.get(FiscalPeriod, period_id)
    if period is None or period.company_id != company_id:
        raise ValueError(FISCAL_PERIOD_NOT_FOUND_MSG)
    period_name = period.name

    def _run():
        alloc_id, err = posting_svc.allocate_profit_to_partners(
            session, period_id, allocated_by_id, notes=notes, company_id=company_id
        )
        if err:
            raise ValueError(err)
        allocation = session.get(PartnerProfitAllocation, alloc_id)
        # Parity with the Streamlit before_flush stamp hook (absent on API sessions):
        # the kernel's duplicate-allocation guard filters PartnerProfitAllocation.company_id,
        # so the row must carry company_id for that guard to catch a second allocation.
        if allocation.company_id is None:
            allocation.company_id = company_id
        partner_count = _active_partner_count(session, company_id)
        audit_svc.record_audit(
            session,
            action=audit_svc.ACTION_PROFIT_ALLOCATION,
            entity_type=audit_svc.ENTITY_PARTNER_PROFIT_ALLOCATION,
            entity_id=alloc_id,
            description=(
                f"Allocated {period_name}: net "
                f"{allocation.total_net_income:,.2f} → {partner_count} partners"
            ),
            performed_by=performed_by,
            company_id=company_id,
            commit_family=PROFIT_ALLOCATION_FAMILY,
        )
        return alloc_id, allocation.journal_entry_id

    if commit_modes.is_boundary_mode(PROFIT_ALLOCATION_FAMILY):
        with boundary_commit_scope(session, PROFIT_ALLOCATION_FAMILY):
            alloc_id, je_id = _run()
    else:
        alloc_id, je_id = _run()

    return ProfitAllocationWriteResult(
        allocation_id=alloc_id,
        journal_entry_id=je_id,
        message=f"Profit allocated for period '{period_name}'.",
    )


def void_allocation(
    session: Session,
    *,
    company_id: int,
    performed_by: str | None,
    voider_id: int,
    allocation_id: int,
    reason: str,
) -> AllocationVoidWriteResult:
    """Void a profit allocation — mirrors app void_profit_allocation shim in a boundary scope."""
    allocation = session.get(PartnerProfitAllocation, allocation_id)
    if allocation is None or allocation.is_void:
        raise ValueError(ALLOCATION_NOT_FOUND_OR_VOIDED_MSG)
    period = session.get(FiscalPeriod, allocation.fiscal_period_id)
    if period is None or period.company_id != company_id:
        raise ValueError(ALLOCATION_NOT_FOUND_OR_VOIDED_MSG)
    fiscal_period_id = allocation.fiscal_period_id
    original_je_id = allocation.journal_entry_id

    def _run():
        err = posting_svc.void_profit_allocation(
            session, allocation_id, voider_id, reason, company_id=company_id
        )
        if err:
            raise ValueError(err)
        audit_svc.record_audit(
            session,
            action=audit_svc.ACTION_VOID,
            entity_type=audit_svc.ENTITY_PARTNER_PROFIT_ALLOCATION,
            entity_id=allocation_id,
            description=f"Voided profit allocation for period #{fiscal_period_id} — {reason}",
            performed_by=performed_by,
            company_id=company_id,
            commit_family=VOID_CASCADE_FAMILY,
        )

    if commit_modes.is_boundary_mode(VOID_CASCADE_FAMILY):
        with boundary_commit_scope(session, VOID_CASCADE_FAMILY):
            _run()
    else:
        _run()

    reversal_id = _latest_reversal_je_id(
        session, company_id=company_id, original_je_id=original_je_id
    )
    return AllocationVoidWriteResult(
        allocation_id=allocation_id,
        reversal_journal_entry_id=reversal_id,
        message="Profit allocation voided. Reversing journal posted.",
    )
