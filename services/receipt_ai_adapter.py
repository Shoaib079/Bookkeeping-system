"""RECEIPT-AI-01-IMPL-2/3a — bridge Receipt AI suggestions into ExpenseDraft pipeline.

ReceiptExtraction → DraftSuggestion → ExpenseDraftInput → ExpenseDraft (+ optional
DraftAttachment). **Draft only** — never submit, approve, or post.

No Streamlit, no OCR, no AI API, no JournalEntry, no ExpenseRecord.
"""

from __future__ import annotations

import datetime
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from models import DraftAttachment, ExpenseDraft, Vendor
from registry.service import get_setting
from services import receipt_ai as rcpt
from services import receipt_suggestion_capture as rsc
from services import receipt_learning_prefill as rlp
from services import staff_capture as sc
from sqlalchemy.orm import Session

RECEIPT_CAPTURE_SETTING = "receipt_ai.capture_enabled"

# Re-export for callers building suggestions before persistence.
DraftSuggestion = rcpt.DraftSuggestion
CreateSuggestion = rcpt.CreateSuggestion
PAYMENT_PREFILL_THRESHOLD = rcpt.PAYMENT_PREFILL_THRESHOLD
ManualPaymentMethod = Literal["Cash", "Card", "Unknown"]


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
    learned_prefill_applied: bool = False

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
            "learned_prefill_applied": self.learned_prefill_applied,
            "ok": self.ok,
        }


def resolve_receipt_capture_vendor(
    *,
    vendor_text: str = "",
    use_sample_extraction: bool = False,
    attachment_name: str | None = None,
    sample_text: str | None = None,
    default_currency: str = "TRY",
) -> str:
    """Vendor text for learning lookup — manual entry or sample filename parse."""
    if use_sample_extraction and attachment_name:
        extraction = rcpt.extract_receipt_with(
            rcpt.fake_receipt_extractor,
            filename=attachment_name,
            text=sample_text,
            default_currency=default_currency,
        )
        return (extraction.vendor_text or vendor_text or "").strip()
    return (vendor_text or "").strip()


def get_learned_receipt_suggestion(
    session: Session,
    company_id: int,
    vendor_signature: str | None,
    **kwargs: Any,
) -> rlp.LearnedReceiptSuggestion | None:
    """Re-export — learned prefill helper for Receipt Capture."""
    return rlp.get_learned_receipt_suggestion(
        session, company_id, vendor_signature, **kwargs
    )


def _apply_learned_capture_prefill(
    session: Session,
    company_id: int,
    vendor_text: str,
    *,
    tx_category_id: int | None,
    tx_subcategory_id: int | None,
) -> tuple[int | None, int | None, bool]:
    learned = rlp.get_learned_receipt_suggestion(session, company_id, vendor_text)
    cat, sub = rlp.apply_learned_category_prefill(
        learned,
        tx_category_id=tx_category_id,
        tx_subcategory_id=tx_subcategory_id,
    )
    applied = learned is not None and (
        (tx_category_id is None and cat is not None)
        or (tx_subcategory_id is None and sub is not None)
    )
    return cat, sub, applied


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


def is_receipt_capture_enabled(session: Session, company_id: int) -> bool:
    """Company feature flag — controls Receipt capture visibility only."""
    return bool(get_setting(session, RECEIPT_CAPTURE_SETTING, company_id=company_id))


def _vendor_exists(session: Session, company_id: int, vendor_text: str | None) -> bool:
    signature = rcpt.normalize_vendor_signature(vendor_text)
    if not signature:
        return False
    rows = (
        session.query(Vendor.name)
        .filter(Vendor.company_id == company_id, Vendor.is_active.is_(True))
        .all()
    )
    return any(rcpt.normalize_vendor_signature(name) == signature for (name,) in rows)


def build_draft_suggestion_from_extraction(
    session: Session,
    company_id: int,
    extraction: rcpt.ReceiptExtraction,
    *,
    tx_category_id: int | None = None,
    tx_subcategory_id: int | None = None,
) -> rcpt.DraftSuggestion:
    """Map an extraction to a draft suggestion with company-scoped vendor lookup."""
    return rcpt.map_extraction_to_draft_suggestion(
        extraction,
        existing_tx_category_id=tx_category_id,
        existing_tx_subcategory_id=tx_subcategory_id,
        vendor_exists=_vendor_exists(session, company_id, extraction.vendor_text),
    )


def build_manual_draft_suggestion(
    session: Session,
    company_id: int,
    *,
    vendor_text: str,
    receipt_date: datetime.date,
    total_amount: float,
    currency: str,
    payment_method: ManualPaymentMethod,
    tx_category_id: int | None = None,
    tx_subcategory_id: int | None = None,
) -> rcpt.DraftSuggestion:
    """Manual/fake-extractor path — user-entered fields, no OCR/AI."""
    if payment_method == "Cash":
        pay_method = rcpt.PAYMENT_CASH
        pay_confidence = 1.0
    elif payment_method == "Card":
        pay_method = rcpt.PAYMENT_CARD
        pay_confidence = 1.0
    else:
        pay_method = rcpt.PAYMENT_UNKNOWN
        pay_confidence = 0.0

    extraction = rcpt.ReceiptExtraction(
        vendor_text=(vendor_text or "").strip() or None,
        receipt_date=receipt_date,
        total_amount=total_amount,
        currency=(currency or "").strip() or None,
        confidence=1.0,
        payment_method=pay_method,
        payment_confidence=pay_confidence,
    )
    return rcpt.map_extraction_to_draft_suggestion(
        extraction,
        existing_tx_category_id=tx_category_id,
        existing_tx_subcategory_id=tx_subcategory_id,
        vendor_exists=_vendor_exists(session, company_id, vendor_text),
    )


def create_receipt_capture_draft(
    session: Session,
    company_id: int,
    actor_id: int,
    *,
    vendor_text: str = "",
    receipt_date: datetime.date | None = None,
    total_amount: float = 0.0,
    currency: str = "",
    payment_method: ManualPaymentMethod = "Cash",
    tx_category_id: int | None = None,
    tx_subcategory_id: int | None = None,
    uploads_root: Path | None = None,
    file_bytes: bytes | None = None,
    attachment_name: str = "receipt",
    attachment_mime: str | None = None,
    performed_by: str | None = None,
    use_sample_extraction: bool = False,
    sample_text: str | None = None,
    sample_payload: dict[str, Any] | None = None,
) -> ReceiptDraftResult:
    """IMPL-3a/3c/5 entry — manual fields or fake extractor → draft. Never posts."""
    if not is_receipt_capture_enabled(session, company_id):
        return ReceiptDraftResult(
            draft_id=None,
            error="Receipt capture is not enabled for this company.",
        )

    learned_applied = False

    if use_sample_extraction:
        if not attachment_name:
            return ReceiptDraftResult(draft_id=None, error="Filename is required for sample extraction.")
        extraction = rcpt.extract_receipt_with(
            rcpt.fake_receipt_extractor,
            filename=attachment_name,
            text=sample_text,
            payload=sample_payload,
            default_currency=(currency or "TRY").strip() or "TRY",
        )
        if extraction.total_amount is None or extraction.total_amount <= 0:
            return ReceiptDraftResult(
                draft_id=None,
                error="Sample extraction could not determine a valid amount.",
            )
        vendor_for_learn = extraction.vendor_text or vendor_text
        tx_category_id, tx_subcategory_id, learned_applied = _apply_learned_capture_prefill(
            session,
            company_id,
            vendor_for_learn,
            tx_category_id=tx_category_id,
            tx_subcategory_id=tx_subcategory_id,
        )
        suggestion = build_draft_suggestion_from_extraction(
            session,
            company_id,
            extraction,
            tx_category_id=tx_category_id,
            tx_subcategory_id=tx_subcategory_id,
        )
        draft_date = extraction.receipt_date or receipt_date or datetime.date.today()
        draft_currency = (extraction.currency or currency or "TRY").strip()
        return create_expense_draft_from_suggestion(
            session,
            company_id,
            actor_id,
            suggestion,
            uploads_root=uploads_root,
            file_bytes=file_bytes,
            attachment_name=attachment_name,
            attachment_mime=attachment_mime,
            default_currency=draft_currency,
            fallback_date=draft_date,
            performed_by=performed_by,
            capture_original_suggestion=True,
            suggestion_source="sample_extractor",
            vendor_text=extraction.vendor_text or suggestion.description,
            raw_text=extraction.raw_text,
            learned_prefill_applied=learned_applied,
        )

    if total_amount <= 0:
        return ReceiptDraftResult(draft_id=None, error="Amount must be greater than zero.")
    if not (currency or "").strip():
        return ReceiptDraftResult(draft_id=None, error="Currency is required.")
    if receipt_date is None:
        receipt_date = datetime.date.today()

    tx_category_id, tx_subcategory_id, learned_applied = _apply_learned_capture_prefill(
        session,
        company_id,
        vendor_text,
        tx_category_id=tx_category_id,
        tx_subcategory_id=tx_subcategory_id,
    )

    suggestion = build_manual_draft_suggestion(
        session,
        company_id,
        vendor_text=vendor_text,
        receipt_date=receipt_date,
        total_amount=total_amount,
        currency=currency,
        payment_method=payment_method,
        tx_category_id=tx_category_id,
        tx_subcategory_id=tx_subcategory_id,
    )
    return create_expense_draft_from_suggestion(
        session,
        company_id,
        actor_id,
        suggestion,
        uploads_root=uploads_root,
        file_bytes=file_bytes,
        attachment_name=attachment_name,
        attachment_mime=attachment_mime,
        default_currency=currency.strip(),
        fallback_date=receipt_date,
        performed_by=performed_by,
        capture_original_suggestion=True,
        suggestion_source="manual",
        vendor_text=vendor_text or suggestion.description,
        learned_prefill_applied=learned_applied,
    )


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
    capture_original_suggestion: bool = False,
    suggestion_source: rsc.SuggestionSource = "manual",
    vendor_text: str | None = None,
    raw_text: str | None = None,
    learned_prefill_applied: bool = False,
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
    attachment_sha256: str | None = None

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
        attachment_sha256 = digest
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

    if capture_original_suggestion:
        captured = rsc.capture_draft_suggestion(
            session,
            company_id,
            draft_id,
            suggestion,
            created_by_id=actor_id,
            source=suggestion_source,
            attachment_sha256=attachment_sha256,
            vendor_text=vendor_text,
            raw_text=raw_text,
        )
        if not captured.captured and captured.skip_reason != "suggestion already captured for draft":
            return ReceiptDraftResult(
                draft_id=draft_id,
                error=captured.skip_reason or "Failed to capture original suggestion.",
                attachment_id=attachment_id,
                duplicate_attachment=duplicate_attachment,
                payment_prefilled=suggestion.payment_prefilled,
                user_must_choose_payment=suggestion.user_must_choose_payment,
                create_suggestions=tuple(suggestion.create_suggestions),
                warnings=tuple(warnings),
            )

    return ReceiptDraftResult(
        draft_id=draft_id,
        attachment_id=attachment_id,
        duplicate_attachment=duplicate_attachment,
        payment_prefilled=suggestion.payment_prefilled,
        user_must_choose_payment=suggestion.user_must_choose_payment,
        create_suggestions=tuple(suggestion.create_suggestions),
        warnings=tuple(warnings),
        learned_prefill_applied=learned_prefill_applied,
    )
