"""FASTAPI-REACT-49 — read-only staff expense draft submissions and inbox."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from services import staff_capture as sc_svc


@dataclass(frozen=True, slots=True)
class StaffExpenseDraftsPage:
    my_drafts: tuple[sc_svc.ExpenseDraftView, ...]
    inbox_drafts: tuple[sc_svc.ExpenseDraftView, ...]
    my_draft_count: int
    inbox_count: int
    company_id: int
    user_id: int
    can_submit: bool
    can_approve: bool


def compute_staff_expense_drafts_page(
    session: Session,
    *,
    company_id: int,
    user_id: int,
    can_submit: bool,
    can_approve: bool,
) -> StaffExpenseDraftsPage:
    my_drafts: tuple[sc_svc.ExpenseDraftView, ...] = ()
    if can_submit:
        my_drafts = tuple(
            sc_svc.list_expense_drafts(session, company_id, user_id)
        )

    inbox_drafts: tuple[sc_svc.ExpenseDraftView, ...] = ()
    if can_approve:
        inbox_drafts = tuple(
            sc_svc.list_submitted_expense_drafts(session, company_id, user_id)
        )

    return StaffExpenseDraftsPage(
        my_drafts=my_drafts,
        inbox_drafts=inbox_drafts,
        my_draft_count=len(my_drafts),
        inbox_count=len(inbox_drafts),
        company_id=company_id,
        user_id=user_id,
        can_submit=can_submit,
        can_approve=can_approve,
    )
