"""RECEIPT-AI-01-IMPL-2 — bridge Receipt AI suggestions into ExpenseDraft pipeline.

ReceiptExtraction → DraftSuggestion → ExpenseDraftInput → ExpenseDraft (+ optional
DraftAttachment). **Draft only** — never submit, approve, or post.

No Streamlit, no OCR, no AI API, no JournalEntry, no ExpenseRecord.
"""

from __future__ import annotations

import datetime
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from models import DraftAttachment, ExpenseDraft
from services import receipt_ai as rcpt
from services import staff_capture as sc
from sqlalchemy.orm import Session

# Re-export for callers building suggestions before persistence.
DraftSuggestion = rcpt.DraftSuggestion
CreateSuggestion = rcpt.CreateSuggestion
PAYMENT_PREFILL_THRESHOLD = rcpt.PAYMENT_PREFILL_THRESHOLD


@dataclass(frozen=True)
class ReceiptDraftResult:
    """Outcome of bridging a suggestion into a persisted expense draft."""

    draft_id: int | None
    error: str = ""
    attachment_id: int | None = None
    duplicate_attachment: bool = False
    payment_prefilled: bool = False
    user_must_choose_payment: bool = False
    create_suggestions: tuple[rcpt.CreateSuggestion, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.draft_id is not None and not self.error

    def to_dict(self) -> dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "error": self.error,
            "attachment_id": self.attachment_id,
            "duplicate_attachment": self.duplicate_attachment,
            "payment_prefilled": self.payment_prefilled,
            "user_must_choose_payment": self.user_must_choose_payment,
            "create_suggestions": [c.to_dict() for c in self.create_suggestions],
            "warnings": list(self.warnings),
            "ok": self.ok,
        }


def suggestion_to_expense_draft_input(
    suggestion: rcpt.DraftSuggestion,
    *,
    default_currency: str = "USD",
    fallback_date: datetime.date | None = None,
) -> sc.ExpenseDraftInput:
    """Map a :class:`DraftSuggestion` onto :class:`ExpenseDraftInput` (pure)."""
    draft_date = suggestion.date or fallback_date or datetime.date.today()
    amount = float(suggestion.amount) if suggestion.amount is not None else 0.0
    currency = (suggestion.currency or default_currency).strip()

    if suggestion.payment_prefilled and suggestion.payment_method in ("Cash", "Card"):
        payment_method = suggestion.payment_method
    elif suggestion.user_must_choose_payment:
        payment_method = "Unknown"
    else:
        payment_method = "Cash"

    return sc.ExpenseDraftInput(
        date=draft_date,
        amount=amount,
        currency=currency,
        payment_method=payment_method,
        tx_category_id=suggestion.tx_category_id,
        tx_subcategory_id=suggestion.tx_subcategory_id,
        description=(suggestion.description or "").strip(),
    )


def _company_attachment_hashes(session: Session, company_id: int) -> list[str]:
    rows = (
        session.query(DraftAttachment.sha256)
        .filter(DraftAttachment.company_id == company_id)
        .all()
    )
    return [row[0] for row in rows]


def create_expense_draft_from_suggestion(
    session: Session,
    company_id: int,
    actor_id: int,
    suggestion: rcpt.DraftSuggestion,
    *,
    uploads_root: Path | None = None,
    file_bytes: bytes | None = None,
    attachment_name: str = "receipt",
    attachment_mime: str | None = None,
    default_currency: str = "USD",
    fallback_date: datetime.date | None = None,
    performed_by: str | None = None,
) -> ReceiptDraftResult:
    """Persist an expense draft (status ``draft``) from a receipt suggestion.

    Never submits, approves, or posts. Optional receipt bytes attach via
    :func:`staff_capture.add_draft_attachment` (sha256 dedup, validation, company scope).
    """
    payload = suggestion_to_expense_draft_input(
        suggestion,
        default_currency=default_currency,
        fallback_date=fallback_date,
    )
    created = sc.create_expense_draft(
        session,
        company_id,
        actor_id,
        payload,
        performed_by=performed_by,
    )
    if not created.ok:
        return ReceiptDraftResult(
            draft_id=None,
            error=created.error,
            payment_prefilled=suggestion.payment_prefilled,
            user_must_choose_payment=suggestion.user_must_choose_payment,
            create_suggestions=tuple(suggestion.create_suggestions),
        )

    draft_id = created.record_id
    assert draft_id is not None

    row = (
        session.query(ExpenseDraft)
        .filter(
            ExpenseDraft.id == draft_id,
            ExpenseDraft.company_id == company_id,
        )
        .first()
    )
    if row is None or row.status != "draft":
        return ReceiptDraftResult(
            draft_id=draft_id,
            error="Draft was not created in draft status.",
            payment_prefilled=suggestion.payment_prefilled,
            user_must_choose_payment=suggestion.user_must_choose_payment,
            create_suggestions=tuple(suggestion.create_suggestions),
        )

    attachment_id: int | None = None
    duplicate_attachment = False
    warnings: list[str] = list(created.warnings)

    if file_bytes is not None:
        if uploads_root is None:
            return ReceiptDraftResult(
                draft_id=draft_id,
                error="uploads_root is required when file_bytes is provided.",
                payment_prefilled=suggestion.payment_prefilled,
                user_must_choose_payment=suggestion.user_must_choose_payment,
                create_suggestions=tuple(suggestion.create_suggestions),
            )
        digest = hashlib.sha256(file_bytes).hexdigest()
        if rcpt.detect_duplicate_by_sha256(digest, _company_attachment_hashes(session, company_id)):
            duplicate_attachment = True
            warnings.append("duplicate_attachment")
        else:
            mime = attachment_mime or sc.sniff_mime(file_bytes)
            if mime is None:
                return ReceiptDraftResult(
                    draft_id=draft_id,
                    error="Unsupported attachment file type.",
                    payment_prefilled=suggestion.payment_prefilled,
                    user_must_choose_payment=suggestion.user_must_choose_payment,
                    create_suggestions=tuple(suggestion.create_suggestions),
                    warnings=tuple(warnings),
                )
            attached = sc.add_draft_attachment(
                session,
                company_id,
                sc.EXPENSE_DRAFT_TYPE,
                draft_id,
                actor_id,
                file_bytes=file_bytes,
                original_name=attachment_name,
                mime_type=mime,
                uploads_root=uploads_root,
                performed_by=performed_by,
            )
            if not attached.ok:
                return ReceiptDraftResult(
                    draft_id=draft_id,
                    error=attached.error,
                    payment_prefilled=suggestion.payment_prefilled,
                    user_must_choose_payment=suggestion.user_must_choose_payment,
                    create_suggestions=tuple(suggestion.create_suggestions),
                    warnings=tuple(warnings),
                )
            attachment_id = attached.record_id

    return ReceiptDraftResult(
        draft_id=draft_id,
        attachment_id=attachment_id,
        duplicate_attachment=duplicate_attachment,
        payment_prefilled=suggestion.payment_prefilled,
        user_must_choose_payment=suggestion.user_must_choose_payment,
        create_suggestions=tuple(suggestion.create_suggestions),
        warnings=tuple(warnings),
    )
