"""RECEIPT-AI-02-IMPL-2 — capture original receipt suggestion at draft creation.

Stores what the AI/manual/sample extractor suggested **before** later user edits.
Enables future correction-learning (suggested X vs approved Y). Does **not** call
the learning service in this slice.

No Streamlit, no posting, no OCR/AI API.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from typing import Any, Literal

from models import ReceiptDraftSuggestion
from services import receipt_ai as rcpt
from sqlalchemy.orm import Session

SuggestionSource = Literal["manual", "sample_extractor", "ocr"]


@dataclass(frozen=True)
class CaptureSuggestionResult:
    captured: bool
    record_id: int | None = None
    skip_reason: str = ""

    @property
    def ok(self) -> bool:
        return self.captured and self.record_id is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "captured": self.captured,
            "record_id": self.record_id,
            "skip_reason": self.skip_reason,
            "ok": self.ok,
        }


@dataclass(frozen=True)
class CapturedSuggestionView:
    id: int
    company_id: int
    draft_id: int
    attachment_sha256: str | None
    vendor_signature: str | None
    vendor_text: str | None
    suggested_category_id: int | None
    suggested_subcategory_id: int | None
    suggested_payment_method: str | None
    suggested_payment_confidence: float | None
    suggested_payment_evidence: tuple[str, ...]
    suggested_items: tuple[dict[str, Any], ...]
    extraction_confidence: float | None
    raw_text: str | None
    source: str
    created_by_id: int
    created_at: datetime.datetime
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "draft_id": self.draft_id,
            "attachment_sha256": self.attachment_sha256,
            "vendor_signature": self.vendor_signature,
            "vendor_text": self.vendor_text,
            "suggested_category_id": self.suggested_category_id,
            "suggested_subcategory_id": self.suggested_subcategory_id,
            "suggested_payment_method": self.suggested_payment_method,
            "suggested_payment_confidence": self.suggested_payment_confidence,
            "suggested_payment_evidence": list(self.suggested_payment_evidence),
            "suggested_items": list(self.suggested_items),
            "extraction_confidence": self.extraction_confidence,
            "raw_text": self.raw_text,
            "source": self.source,
            "created_by_id": self.created_by_id,
            "created_at": self.created_at.isoformat(),
            "snapshot": self.snapshot,
        }


def _suggested_items_from_suggestion(
    suggestion: rcpt.DraftSuggestion,
) -> list[dict[str, Any]]:
    items = [
        c.to_dict() for c in suggestion.create_suggestions if c.kind == "item"
    ]
    return items


def build_snapshot(
    suggestion: rcpt.DraftSuggestion,
    *,
    vendor_text: str | None = None,
    raw_text: str | None = None,
    source: SuggestionSource,
) -> dict[str, Any]:
    """Serializable snapshot of the original suggestion at capture time."""
    return {
        "suggestion": suggestion.to_dict(),
        "vendor_text": vendor_text,
        "raw_text": raw_text,
        "source": source,
    }


def _row_to_view(row: ReceiptDraftSuggestion) -> CapturedSuggestionView:
    evidence = json.loads(row.suggested_payment_evidence_json or "[]")
    items = json.loads(row.suggested_items_json or "[]")
    snapshot = json.loads(row.snapshot_json or "{}")
    return CapturedSuggestionView(
        id=row.id,
        company_id=row.company_id,
        draft_id=row.draft_id,
        attachment_sha256=row.attachment_sha256,
        vendor_signature=row.vendor_signature,
        vendor_text=row.vendor_text,
        suggested_category_id=row.suggested_category_id,
        suggested_subcategory_id=row.suggested_subcategory_id,
        suggested_payment_method=row.suggested_payment_method,
        suggested_payment_confidence=row.suggested_payment_confidence,
        suggested_payment_evidence=tuple(evidence),
        suggested_items=tuple(items),
        extraction_confidence=row.extraction_confidence,
        raw_text=row.raw_text,
        source=row.source,
        created_by_id=row.created_by_id,
        created_at=row.created_at,
        snapshot=snapshot,
    )


def get_captured_suggestion(
    session: Session,
    company_id: int,
    draft_id: int,
) -> CapturedSuggestionView | None:
    row = (
        session.query(ReceiptDraftSuggestion)
        .filter(
            ReceiptDraftSuggestion.company_id == company_id,
            ReceiptDraftSuggestion.draft_id == draft_id,
        )
        .first()
    )
    return _row_to_view(row) if row else None


def capture_draft_suggestion(
    session: Session,
    company_id: int,
    draft_id: int,
    suggestion: rcpt.DraftSuggestion,
    *,
    created_by_id: int,
    source: SuggestionSource,
    attachment_sha256: str | None = None,
    vendor_text: str | None = None,
    raw_text: str | None = None,
    allow_replace: bool = False,
) -> CaptureSuggestionResult:
    """Persist the original suggestion once per draft. Never learns or posts."""
    existing = (
        session.query(ReceiptDraftSuggestion)
        .filter(
            ReceiptDraftSuggestion.company_id == company_id,
            ReceiptDraftSuggestion.draft_id == draft_id,
        )
        .first()
    )
    if existing is not None and not allow_replace:
        return CaptureSuggestionResult(
            captured=False,
            record_id=existing.id,
            skip_reason="suggestion already captured for draft",
        )

    snapshot = build_snapshot(
        suggestion,
        vendor_text=vendor_text,
        raw_text=raw_text,
        source=source,
    )
    now = datetime.datetime.now()
    row = ReceiptDraftSuggestion(
        company_id=company_id,
        draft_id=draft_id,
        attachment_sha256=attachment_sha256,
        vendor_signature=suggestion.vendor_signature,
        vendor_text=(vendor_text or suggestion.description or "").strip() or None,
        suggested_category_id=suggestion.tx_category_id,
        suggested_subcategory_id=suggestion.tx_subcategory_id,
        suggested_payment_method=suggestion.payment_method,
        suggested_payment_confidence=suggestion.payment_confidence,
        suggested_payment_evidence_json=json.dumps(list(suggestion.payment_evidence)),
        suggested_items_json=json.dumps(_suggested_items_from_suggestion(suggestion)),
        extraction_confidence=suggestion.extraction_confidence,
        raw_text=raw_text,
        source=source,
        snapshot_json=json.dumps(snapshot),
        created_by_id=created_by_id,
        created_at=now,
    )
    if existing is not None and allow_replace:
        session.delete(existing)
        session.flush()
    session.add(row)
    session.flush()
    session.commit()
    return CaptureSuggestionResult(captured=True, record_id=row.id)
