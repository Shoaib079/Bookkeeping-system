"""SC-P1 — Staff Capture service layer (expense drafts + attachments).

FastAPI-ready: explicit company_id and user_id, serializable DTOs, no Streamlit dependency.
Approval posts via injected post_fn only.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from models import (
    AuditLog,
    DraftAttachment,
    ExpenseDraft,
    TransactionCategory,
    TransactionSubcategory,
)
from services import user_access as ua
from sqlalchemy.orm import Session

DraftStatus = Literal["draft", "submitted", "approved", "rejected", "returned"]
DraftType = Literal["expense", "salary", "sales_total", "cash_count"]

DRAFT_STATUSES: frozenset[str] = frozenset(
    {"draft", "submitted", "approved", "rejected", "returned"}
)
EDITABLE_STATUSES: frozenset[str] = frozenset({"draft", "returned"})
TERMINAL_STATUSES: frozenset[str] = frozenset({"approved", "rejected"})

EXPENSE_DRAFT_TYPE: DraftType = "expense"
V1_PAYMENT_METHODS: frozenset[str] = frozenset({"Cash"})

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024
MAX_ATTACHMENTS_PER_DRAFT = 5
ALLOWED_ATTACHMENT_MIMES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    }
)

_MIME_TO_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}

# Injected by Streamlit/FastAPI — posting seam stays outside this module.
ExpensePostFn = Callable[[Session, "ExpenseDraftView"], "ExpensePostResult"]


@dataclass(frozen=True)
class ExpenseDraftInput:
    date: datetime.date
    amount: float
    currency: str
    payment_method: str
    tx_category_id: int | None
    tx_subcategory_id: int | None
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "amount": self.amount,
            "currency": self.currency,
            "payment_method": self.payment_method,
            "tx_category_id": self.tx_category_id,
            "tx_subcategory_id": self.tx_subcategory_id,
            "description": self.description,
        }


@dataclass(frozen=True)
class ExpenseDraftView:
    id: int
    company_id: int
    created_by_id: int
    status: str
    created_at: datetime.datetime
    submitted_at: datetime.datetime | None
    submitted_note: str | None
    reviewed_by_id: int | None
    reviewed_at: datetime.datetime | None
    review_note: str | None
    expense_record_id: int | None
    date: datetime.date
    amount: float
    currency: str
    payment_method: str
    tx_category_id: int | None
    tx_subcategory_id: int | None
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "created_by_id": self.created_by_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "submitted_note": self.submitted_note,
            "reviewed_by_id": self.reviewed_by_id,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_note": self.review_note,
            "expense_record_id": self.expense_record_id,
            "date": self.date.isoformat(),
            "amount": self.amount,
            "currency": self.currency,
            "payment_method": self.payment_method,
            "tx_category_id": self.tx_category_id,
            "tx_subcategory_id": self.tx_subcategory_id,
            "description": self.description,
        }


@dataclass(frozen=True)
class DraftAttachmentView:
    id: int
    company_id: int
    uploaded_by_id: int
    created_at: datetime.datetime
    draft_type: str
    draft_id: int
    file_path: str
    original_name: str
    mime: str
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "uploaded_by_id": self.uploaded_by_id,
            "created_at": self.created_at.isoformat(),
            "draft_type": self.draft_type,
            "draft_id": self.draft_id,
            "file_path": self.file_path,
            "original_name": self.original_name,
            "mime": self.mime,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class ExpensePostResult:
    expense_record_id: int | None
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.expense_record_id is not None and not self.error


@dataclass(frozen=True)
class MutationResult:
    record_id: int | None
    error: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.record_id is not None and not self.error

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "error": self.error,
            "warnings": list(self.warnings),
            "ok": self.ok,
        }


# ── Pure helpers ──────────────────────────────────────────────────────────────


def can_transition(current: str, target: str) -> bool:
    """Legal expense-draft status transitions."""
    if current not in DRAFT_STATUSES or target not in DRAFT_STATUSES:
        return False
    if current in TERMINAL_STATUSES:
        return False
    if target == "submitted":
        return current in {"draft", "returned"}
    if target == "approved":
        return current == "submitted"
    if target == "rejected":
        return current == "submitted"
    if target == "returned":
        return current == "submitted"
    if target == "draft":
        return current == "returned"
    return False


def sniff_mime(file_bytes: bytes) -> str | None:
    """Magic-byte MIME sniff — not extension-based."""
    if len(file_bytes) < 4:
        return None
    if file_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if file_bytes[:4] == b"\x89PNG":
        return "image/png"
    if file_bytes[:4] == b"%PDF":
        return "application/pdf"
    if len(file_bytes) >= 12 and file_bytes[:4] == b"RIFF" and file_bytes[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_attachment_bytes(
    file_bytes: bytes,
    *,
    declared_mime: str,
) -> str | None:
    if not file_bytes:
        return "Attachment file is empty."
    if len(file_bytes) > MAX_ATTACHMENT_BYTES:
        return f"Attachment exceeds {MAX_ATTACHMENT_BYTES // (1024 * 1024)} MB limit."
    sniffed = sniff_mime(file_bytes)
    if sniffed is None:
        return "Unsupported file type."
    if sniffed not in ALLOWED_ATTACHMENT_MIMES:
        return "Unsupported file type."
    if declared_mime not in ALLOWED_ATTACHMENT_MIMES:
        return "Unsupported MIME type."
    if sniffed != declared_mime:
        return "File content does not match declared MIME type."
    return None


def validate_expense_payload(
    payload: ExpenseDraftInput,
    *,
    require_amount: bool = True,
) -> str | None:
    if payload.payment_method not in V1_PAYMENT_METHODS:
        return "Only Cash payment method is supported in v1."
    if require_amount and payload.amount <= 0:
        return "Amount must be greater than zero."
    if not (payload.currency or "").strip():
        return "Currency is required."
    return None


# ── DB helpers ────────────────────────────────────────────────────────────────


def _expense_view(row: ExpenseDraft) -> ExpenseDraftView:
    return ExpenseDraftView(
        id=row.id,
        company_id=row.company_id,
        created_by_id=row.created_by_id,
        status=row.status,
        created_at=row.created_at,
        submitted_at=row.submitted_at,
        submitted_note=row.submitted_note,
        reviewed_by_id=row.reviewed_by_id,
        reviewed_at=row.reviewed_at,
        review_note=row.review_note,
        expense_record_id=row.expense_record_id,
        date=row.date,
        amount=row.amount,
        currency=row.currency,
        payment_method=row.payment_method,
        tx_category_id=row.tx_category_id,
        tx_subcategory_id=row.tx_subcategory_id,
        description=row.description or "",
    )


def _attachment_view(row: DraftAttachment) -> DraftAttachmentView:
    return DraftAttachmentView(
        id=row.id,
        company_id=row.company_id,
        uploaded_by_id=row.uploaded_by_id,
        created_at=row.created_at,
        draft_type=row.draft_type,
        draft_id=row.draft_id,
        file_path=row.file_path,
        original_name=row.original_name,
        mime=row.mime,
        size_bytes=row.size_bytes,
        sha256=row.sha256,
    )


def _get_expense_draft_row(
    session: Session,
    company_id: int,
    draft_id: int,
) -> ExpenseDraft | None:
    return (
        session.query(ExpenseDraft)
        .filter(
            ExpenseDraft.id == draft_id,
            ExpenseDraft.company_id == company_id,
        )
        .first()
    )


def _write_audit(
    session: Session,
    *,
    company_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    description: str,
    performed_by: str | None,
) -> None:
    session.add(
        AuditLog(
            timestamp=datetime.datetime.now(),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            performed_by=performed_by,
            company_id=company_id,
        )
    )


def _validate_category_active(
    session: Session,
    company_id: int,
    tx_category_id: int | None,
    tx_subcategory_id: int | None,
) -> str | None:
    if tx_category_id is not None:
        cat = session.get(TransactionCategory, tx_category_id)
        if not cat or cat.company_id != company_id or not cat.is_active:
            return "Transaction category is missing or inactive."
        if cat.transaction_type != "Expense":
            return "Category must be an Expense category."
    if tx_subcategory_id is not None:
        sub = session.get(TransactionSubcategory, tx_subcategory_id)
        if not sub or sub.company_id != company_id or not sub.is_active:
            return "Transaction subcategory is missing or inactive."
        if tx_category_id is not None and sub.category_id != tx_category_id:
            return "Subcategory does not belong to the selected category."
    return None


def _relative_draft_path(company_id: int, ext: str) -> tuple[str, str]:
    """Return (stored_path, disk_relative_under_uploads)."""
    month = datetime.date.today().strftime("%Y-%m")
    name = f"{uuid.uuid4().hex}{ext}"
    disk_rel = f"{company_id}/drafts/{month}/{name}"
    return f"uploads/{disk_rel}", disk_rel


def _sanitize_original_name(name: str) -> str:
    base = Path(name).name
    if ".." in base or base.startswith("/"):
        return "attachment"
    return base[:500] or "attachment"


# ── Public API — expense drafts ───────────────────────────────────────────────


def create_expense_draft(
    session: Session,
    company_id: int,
    actor_id: int,
    payload: ExpenseDraftInput,
    *,
    performed_by: str | None = None,
) -> MutationResult:
    if not ua.has_permission(session, company_id, actor_id, "submit_expense_drafts"):
        return MutationResult(record_id=None, error="Permission denied: submit_expense_drafts.")
    err = validate_expense_payload(payload, require_amount=False)
    if err:
        return MutationResult(record_id=None, error=err)
    now = datetime.datetime.now()
    row = ExpenseDraft(
        company_id=company_id,
        created_by_id=actor_id,
        status="draft",
        created_at=now,
        date=payload.date,
        amount=payload.amount,
        currency=payload.currency.strip(),
        payment_method=payload.payment_method,
        tx_category_id=payload.tx_category_id,
        tx_subcategory_id=payload.tx_subcategory_id,
        description=(payload.description or "").strip(),
    )
    session.add(row)
    session.flush()
    _write_audit(
        session,
        company_id=company_id,
        action="create_expense_draft",
        entity_type="ExpenseDraft",
        entity_id=row.id,
        description=json.dumps({"created_by_id": actor_id}),
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=row.id)


def update_expense_draft(
    session: Session,
    company_id: int,
    draft_id: int,
    actor_id: int,
    payload: ExpenseDraftInput,
    *,
    performed_by: str | None = None,
) -> MutationResult:
    row = _get_expense_draft_row(session, company_id, draft_id)
    if row is None:
        return MutationResult(record_id=None, error="Draft not found.")
    if row.created_by_id != actor_id:
        return MutationResult(record_id=None, error="You may only edit your own drafts.")
    if not ua.has_permission(session, company_id, actor_id, "submit_expense_drafts"):
        return MutationResult(record_id=None, error="Permission denied: submit_expense_drafts.")
    if row.status not in EDITABLE_STATUSES:
        return MutationResult(record_id=None, error=f"Draft in status {row.status!r} cannot be edited.")
    err = validate_expense_payload(payload, require_amount=False)
    if err:
        return MutationResult(record_id=None, error=err)
    row.date = payload.date
    row.amount = payload.amount
    row.currency = payload.currency.strip()
    row.payment_method = payload.payment_method
    row.tx_category_id = payload.tx_category_id
    row.tx_subcategory_id = payload.tx_subcategory_id
    row.description = (payload.description or "").strip()
    session.flush()
    _write_audit(
        session,
        company_id=company_id,
        action="update_expense_draft",
        entity_type="ExpenseDraft",
        entity_id=row.id,
        description=json.dumps({"updated_by_id": actor_id}),
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=row.id)


def submit_expense_draft(
    session: Session,
    company_id: int,
    draft_id: int,
    actor_id: int,
    *,
    submitted_note: str | None = None,
    performed_by: str | None = None,
) -> MutationResult:
    row = _get_expense_draft_row(session, company_id, draft_id)
    if row is None:
        return MutationResult(record_id=None, error="Draft not found.")
    if row.created_by_id != actor_id:
        return MutationResult(record_id=None, error="You may only submit your own drafts.")
    if not ua.has_permission(session, company_id, actor_id, "submit_expense_drafts"):
        return MutationResult(record_id=None, error="Permission denied: submit_expense_drafts.")
    if not can_transition(row.status, "submitted"):
        return MutationResult(record_id=None, error=f"Cannot submit from status {row.status!r}.")
    payload = ExpenseDraftInput(
        date=row.date,
        amount=row.amount,
        currency=row.currency,
        payment_method=row.payment_method,
        tx_category_id=row.tx_category_id,
        tx_subcategory_id=row.tx_subcategory_id,
        description=row.description or "",
    )
    err = validate_expense_payload(payload)
    if err:
        return MutationResult(record_id=None, error=err)
    cat_err = _validate_category_active(
        session, company_id, row.tx_category_id, row.tx_subcategory_id
    )
    if cat_err:
        return MutationResult(record_id=None, error=cat_err)

    warnings: list[str] = []
    att_count = (
        session.query(DraftAttachment)
        .filter(
            DraftAttachment.company_id == company_id,
            DraftAttachment.draft_type == EXPENSE_DRAFT_TYPE,
            DraftAttachment.draft_id == draft_id,
        )
        .count()
    )
    if att_count == 0:
        warnings.append("attachment_recommended")

    now = datetime.datetime.now()
    row.status = "submitted"
    row.submitted_at = now
    row.submitted_note = (submitted_note or "").strip() or None
    row.reviewed_by_id = None
    row.reviewed_at = None
    row.review_note = None
    session.flush()
    _write_audit(
        session,
        company_id=company_id,
        action="submit_expense_draft",
        entity_type="ExpenseDraft",
        entity_id=row.id,
        description=json.dumps({"submitted_by_id": actor_id}),
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=row.id, warnings=tuple(warnings))


def return_expense_draft(
    session: Session,
    company_id: int,
    draft_id: int,
    reviewer_id: int,
    review_note: str,
    *,
    performed_by: str | None = None,
) -> MutationResult:
    if not ua.has_permission(session, company_id, reviewer_id, "approve_expense_drafts"):
        return MutationResult(record_id=None, error="Permission denied: approve_expense_drafts.")
    if not (review_note or "").strip():
        return MutationResult(record_id=None, error="Review note is required when returning a draft.")
    row = _get_expense_draft_row(session, company_id, draft_id)
    if row is None:
        return MutationResult(record_id=None, error="Draft not found.")
    if not can_transition(row.status, "returned"):
        return MutationResult(record_id=None, error=f"Cannot return from status {row.status!r}.")
    now = datetime.datetime.now()
    row.status = "returned"
    row.reviewed_by_id = reviewer_id
    row.reviewed_at = now
    row.review_note = review_note.strip()
    session.flush()
    _write_audit(
        session,
        company_id=company_id,
        action="return_expense_draft",
        entity_type="ExpenseDraft",
        entity_id=row.id,
        description=json.dumps({"reviewer_id": reviewer_id}),
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=row.id)


def reject_expense_draft(
    session: Session,
    company_id: int,
    draft_id: int,
    reviewer_id: int,
    *,
    review_note: str | None = None,
    performed_by: str | None = None,
) -> MutationResult:
    if not ua.has_permission(session, company_id, reviewer_id, "approve_expense_drafts"):
        return MutationResult(record_id=None, error="Permission denied: approve_expense_drafts.")
    row = _get_expense_draft_row(session, company_id, draft_id)
    if row is None:
        return MutationResult(record_id=None, error="Draft not found.")
    if not can_transition(row.status, "rejected"):
        return MutationResult(record_id=None, error=f"Cannot reject from status {row.status!r}.")
    now = datetime.datetime.now()
    row.status = "rejected"
    row.reviewed_by_id = reviewer_id
    row.reviewed_at = now
    row.review_note = (review_note or "").strip() or None
    session.flush()
    _write_audit(
        session,
        company_id=company_id,
        action="reject_expense_draft",
        entity_type="ExpenseDraft",
        entity_id=row.id,
        description=json.dumps({"reviewer_id": reviewer_id}),
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=row.id)


def approve_expense_draft(
    session: Session,
    company_id: int,
    draft_id: int,
    reviewer_id: int,
    *,
    post_fn: ExpensePostFn,
    performed_by: str | None = None,
) -> MutationResult:
    if not ua.has_permission(session, company_id, reviewer_id, "approve_expense_drafts"):
        return MutationResult(record_id=None, error="Permission denied: approve_expense_drafts.")
    row = _get_expense_draft_row(session, company_id, draft_id)
    if row is None:
        return MutationResult(record_id=None, error="Draft not found.")
    if row.created_by_id == reviewer_id:
        return MutationResult(record_id=None, error="You cannot approve your own draft.")
    if row.expense_record_id is not None:
        return MutationResult(record_id=row.expense_record_id)
    if row.status != "submitted":
        return MutationResult(record_id=None, error=f"Cannot approve from status {row.status!r}.")

    payload = ExpenseDraftInput(
        date=row.date,
        amount=row.amount,
        currency=row.currency,
        payment_method=row.payment_method,
        tx_category_id=row.tx_category_id,
        tx_subcategory_id=row.tx_subcategory_id,
        description=row.description or "",
    )
    err = validate_expense_payload(payload)
    if err:
        return MutationResult(record_id=None, error=err)
    cat_err = _validate_category_active(
        session, company_id, row.tx_category_id, row.tx_subcategory_id
    )
    if cat_err:
        return MutationResult(record_id=None, error=cat_err)

    view = _expense_view(row)
    try:
        post_result = post_fn(session, view)
    except ValueError as exc:
        return MutationResult(record_id=None, error=str(exc))
    if not post_result.ok:
        return MutationResult(record_id=None, error=post_result.error or "Posting failed.")

    now = datetime.datetime.now()
    row.expense_record_id = post_result.expense_record_id
    row.status = "approved"
    row.reviewed_by_id = reviewer_id
    row.reviewed_at = now
    session.flush()
    _write_audit(
        session,
        company_id=company_id,
        action="approve_expense_draft",
        entity_type="ExpenseDraft",
        entity_id=row.id,
        description=json.dumps(
            {
                "reviewer_id": reviewer_id,
                "expense_record_id": post_result.expense_record_id,
            }
        ),
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=row.id)


def get_expense_draft(
    session: Session,
    company_id: int,
    draft_id: int,
) -> ExpenseDraftView | None:
    row = _get_expense_draft_row(session, company_id, draft_id)
    return _expense_view(row) if row else None


def list_expense_drafts(
    session: Session,
    company_id: int,
    created_by_id: int,
) -> list[ExpenseDraftView]:
    """Own drafts only — caller supplies created_by_id."""
    rows = (
        session.query(ExpenseDraft)
        .filter(
            ExpenseDraft.company_id == company_id,
            ExpenseDraft.created_by_id == created_by_id,
        )
        .order_by(ExpenseDraft.created_at.desc())
        .all()
    )
    return [_expense_view(r) for r in rows]


def list_submitted_expense_drafts(
    session: Session,
    company_id: int,
    reviewer_id: int,
) -> list[ExpenseDraftView]:
    if not ua.has_permission(session, company_id, reviewer_id, "approve_expense_drafts"):
        return []
    rows = (
        session.query(ExpenseDraft)
        .filter(
            ExpenseDraft.company_id == company_id,
            ExpenseDraft.status == "submitted",
        )
        .order_by(ExpenseDraft.submitted_at.desc())
        .all()
    )
    return [_expense_view(r) for r in rows]


# ── Public API — attachments ──────────────────────────────────────────────────


def add_draft_attachment(
    session: Session,
    company_id: int,
    draft_type: str,
    draft_id: int,
    actor_id: int,
    *,
    file_bytes: bytes,
    original_name: str,
    mime_type: str,
    uploads_root: Path,
    performed_by: str | None = None,
) -> MutationResult:
    if draft_type != EXPENSE_DRAFT_TYPE:
        return MutationResult(record_id=None, error=f"Unsupported draft type: {draft_type}.")
    if not ua.has_permission(session, company_id, actor_id, "upload_receipts"):
        return MutationResult(record_id=None, error="Permission denied: upload_receipts.")
    row = _get_expense_draft_row(session, company_id, draft_id)
    if row is None:
        return MutationResult(record_id=None, error="Draft not found.")
    if row.created_by_id != actor_id:
        return MutationResult(record_id=None, error="You may only attach files to your own drafts.")
    if row.status not in EDITABLE_STATUSES:
        return MutationResult(record_id=None, error="Attachments cannot be added after submission.")

    err = validate_attachment_bytes(file_bytes, declared_mime=mime_type)
    if err:
        return MutationResult(record_id=None, error=err)

    count = (
        session.query(DraftAttachment)
        .filter(
            DraftAttachment.company_id == company_id,
            DraftAttachment.draft_type == draft_type,
            DraftAttachment.draft_id == draft_id,
        )
        .count()
    )
    if count >= MAX_ATTACHMENTS_PER_DRAFT:
        return MutationResult(record_id=None, error="Maximum attachments per draft reached.")

    ext = _MIME_TO_EXT.get(mime_type)
    if not ext:
        return MutationResult(record_id=None, error="Unsupported MIME type.")

    rel_path, disk_rel = _relative_draft_path(company_id, ext)
    abs_path = uploads_root / disk_rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(file_bytes)

    digest = hashlib.sha256(file_bytes).hexdigest()
    att = DraftAttachment(
        company_id=company_id,
        uploaded_by_id=actor_id,
        created_at=datetime.datetime.now(),
        draft_type=draft_type,
        draft_id=draft_id,
        file_path=rel_path,
        original_name=_sanitize_original_name(original_name),
        mime=mime_type,
        size_bytes=len(file_bytes),
        sha256=digest,
    )
    session.add(att)
    session.flush()
    _write_audit(
        session,
        company_id=company_id,
        action="add_draft_attachment",
        entity_type="DraftAttachment",
        entity_id=att.id,
        description=json.dumps(
            {"draft_type": draft_type, "draft_id": draft_id, "uploaded_by_id": actor_id}
        ),
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=att.id)


def list_draft_attachments(
    session: Session,
    company_id: int,
    draft_type: str,
    draft_id: int,
) -> list[DraftAttachmentView]:
    rows = (
        session.query(DraftAttachment)
        .filter(
            DraftAttachment.company_id == company_id,
            DraftAttachment.draft_type == draft_type,
            DraftAttachment.draft_id == draft_id,
        )
        .order_by(DraftAttachment.created_at)
        .all()
    )
    return [_attachment_view(r) for r in rows]
