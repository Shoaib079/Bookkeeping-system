"""FASTAPI-REACT-48 — read-only recurring expense templates and drafts."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import RecurringExpenseDraft, RecurringExpenseTemplate

_HISTORY_STATUSES = frozenset({"posted", "skipped", "auto_skipped", "postponed"})
_HISTORY_LIMIT = 200


@dataclass(frozen=True, slots=True)
class RecurringExpenseTemplateRow:
    id: int
    name: str
    category: str
    amount: Decimal
    frequency: str
    next_due_date: datetime.date
    is_active: bool
    pending_count: int
    company_id: int


@dataclass(frozen=True, slots=True)
class RecurringExpenseDraftRow:
    id: int
    template_id: int
    template_name: str
    due_date: datetime.date
    category: str
    amount: Decimal
    payment_method: str
    status: str
    actioned_at: datetime.date | None
    note: str | None
    company_id: int


@dataclass(frozen=True, slots=True)
class RecurringExpensesPage:
    templates: tuple[RecurringExpenseTemplateRow, ...]
    pending_drafts: tuple[RecurringExpenseDraftRow, ...]
    draft_history: tuple[RecurringExpenseDraftRow, ...]
    template_count: int
    pending_count: int
    history_count: int
    company_id: int


def _draft_note(draft: RecurringExpenseDraft) -> str | None:
    if draft.skip_reason:
        return draft.skip_reason[:80]
    if draft.postponed_to:
        return f"→ {draft.postponed_to.isoformat()}"
    return None


def _draft_row(
    draft: RecurringExpenseDraft,
    *,
    template_name: str,
    company_id: int,
) -> RecurringExpenseDraftRow:
    return RecurringExpenseDraftRow(
        id=draft.id,
        template_id=draft.template_id,
        template_name=template_name,
        due_date=draft.due_date,
        category=draft.category,
        amount=draft.amount,
        payment_method=draft.payment_method,
        status=draft.status,
        actioned_at=draft.actioned_at,
        note=_draft_note(draft),
        company_id=company_id,
    )


def compute_recurring_expenses_page(
    session: Session,
    *,
    company_id: int,
) -> RecurringExpensesPage:
    today = datetime.date.today()
    templates = (
        session.query(RecurringExpenseTemplate)
        .filter(RecurringExpenseTemplate.company_id == company_id)
        .order_by(
            RecurringExpenseTemplate.is_active.desc(),
            RecurringExpenseTemplate.next_due_date,
        )
        .all()
    )
    template_names = {template.id: template.name for template in templates}
    pending_counts = {
        template_id: count
        for template_id, count in session.query(
            RecurringExpenseDraft.template_id,
            func.count(RecurringExpenseDraft.id),
        )
        .filter(
            RecurringExpenseDraft.company_id == company_id,
            RecurringExpenseDraft.status == "pending",
        )
        .group_by(RecurringExpenseDraft.template_id)
        .all()
    }
    template_rows = tuple(
        RecurringExpenseTemplateRow(
            id=template.id,
            name=template.name,
            category=template.category,
            amount=template.amount,
            frequency=template.frequency,
            next_due_date=template.next_due_date,
            is_active=bool(template.is_active),
            pending_count=int(pending_counts.get(template.id, 0)),
            company_id=company_id,
        )
        for template in templates
    )

    pending_drafts = (
        session.query(RecurringExpenseDraft)
        .filter(
            RecurringExpenseDraft.company_id == company_id,
            RecurringExpenseDraft.status == "pending",
            RecurringExpenseDraft.due_date <= today,
        )
        .order_by(RecurringExpenseDraft.due_date)
        .all()
    )
    pending_rows = tuple(
        _draft_row(
            draft,
            template_name=template_names.get(draft.template_id, "—"),
            company_id=company_id,
        )
        for draft in pending_drafts
    )

    history_drafts = (
        session.query(RecurringExpenseDraft)
        .filter(
            RecurringExpenseDraft.company_id == company_id,
            RecurringExpenseDraft.status.in_(sorted(_HISTORY_STATUSES)),
        )
        .order_by(RecurringExpenseDraft.due_date.desc())
        .limit(_HISTORY_LIMIT)
        .all()
    )
    history_rows = tuple(
        _draft_row(
            draft,
            template_name=template_names.get(draft.template_id, "—"),
            company_id=company_id,
        )
        for draft in history_drafts
    )

    return RecurringExpensesPage(
        templates=template_rows,
        pending_drafts=pending_rows,
        draft_history=history_rows,
        template_count=len(template_rows),
        pending_count=len(pending_rows),
        history_count=len(history_rows),
        company_id=company_id,
    )
