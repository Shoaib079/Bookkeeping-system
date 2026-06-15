"""RECEIPT-AI-02-IMPL-1/3/4 — pure receipt learning service (injected store).

Learns vendor→category/subcategory/payment, item→product, and source→document_type
mappings from **approved + posted** drafts only. Payment suggestions are advisory;
void reversals decrement reinforcement via :func:`record_void_reversal`.

Persistent storage: :mod:`services.receipt_learning_store` (``receipt_learning_map``).

No Streamlit, no auto-post, no OCR/AI API.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from services.receipt_ai import normalize_vendor_signature

SignatureType = Literal[
    "vendor_category",
    "vendor_subcategory",
    "vendor_payment",
    "item_product",
    "source_format",
]

ConfidenceTier = Literal["manual", "prefill", "auto_post_eligible", "trusted"]

TIER_MANUAL: ConfidenceTier = "manual"
TIER_PREFILL: ConfidenceTier = "prefill"
TIER_AUTO_POST_ELIGIBLE: ConfidenceTier = "auto_post_eligible"
TIER_TRUSTED: ConfidenceTier = "trusted"

AUTO_POST_MIN_APPROVALS = 3
TRUSTED_MIN_APPROVALS = 5

_NEVER_LEARN_CATEGORY_TOKENS: frozenset[str] = frozenset(
    {
        "payroll",
        "salary",
        "salaries",
        "tax",
        "taxes",
        "vat",
        "withholding",
        "bank transfer",
        "bank_transfer",
        "transfer fee",
    }
)
_LARGE_AMOUNT_THRESHOLD = 100_000.0
_MIN_APPROVALS_TO_SURFACE = 1


@dataclass(frozen=True)
class LearningRecord:
    company_id: int
    signature_type: SignatureType
    signature_key: str
    target_value: str
    approval_count: int = 0
    correction_count: int = 0
    last_approved_at: datetime.datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "signature_type": self.signature_type,
            "signature_key": self.signature_key,
            "target_value": self.target_value,
            "approval_count": self.approval_count,
            "correction_count": self.correction_count,
            "last_approved_at": (
                self.last_approved_at.isoformat() if self.last_approved_at else None
            ),
        }


@dataclass(frozen=True)
class ApprovalLearningEvent:
    """Input for learning — must represent an approved, posted draft."""

    company_id: int
    vendor_signature: str | None
    expense_record_id: int | None
    tx_category_id: int | None = None
    tx_subcategory_id: int | None = None
    payment_method: str | None = None
    category_name: str | None = None
    amount: float | None = None
    is_voided: bool = False
    item_texts: tuple[str, ...] = field(default_factory=tuple)
    product_ids: tuple[int | None, ...] = field(default_factory=tuple)
    source_signature: str | None = None
    document_type: str | None = None
    approved_at: datetime.datetime | None = None
    voided_at: datetime.datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "vendor_signature": self.vendor_signature,
            "expense_record_id": self.expense_record_id,
            "tx_category_id": self.tx_category_id,
            "tx_subcategory_id": self.tx_subcategory_id,
            "payment_method": self.payment_method,
            "category_name": self.category_name,
            "amount": self.amount,
            "is_voided": self.is_voided,
            "item_texts": list(self.item_texts),
            "product_ids": list(self.product_ids),
            "source_signature": self.source_signature,
            "document_type": self.document_type,
            "approved_at": (
                self.approved_at.isoformat() if self.approved_at else None
            ),
            "voided_at": (
                self.voided_at.isoformat() if self.voided_at else None
            ),
        }


@dataclass(frozen=True)
class RecordApprovalResult:
    learned: bool
    skip_reason: str = ""
    records_written: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "learned": self.learned,
            "skip_reason": self.skip_reason,
            "records_written": self.records_written,
            "ok": self.learned,
        }


@dataclass(frozen=True)
class RecordVoidReversalResult:
    reconciled: bool
    skip_reason: str = ""
    records_updated: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "reconciled": self.reconciled,
            "skip_reason": self.skip_reason,
            "records_updated": self.records_updated,
            "ok": self.reconciled,
        }


@dataclass(frozen=True)
class PostedDraftLearningContext:
    """Build learning events from posted draft + expense record (no DB import)."""

    company_id: int
    expense_record_id: int
    vendor_signature: str | None
    tx_category_id: int | None = None
    tx_subcategory_id: int | None = None
    payment_method: str | None = None
    category_name: str | None = None
    amount: float | None = None
    expense_record_is_void: bool = False
    item_texts: tuple[str, ...] = field(default_factory=tuple)
    product_ids: tuple[int | None, ...] = field(default_factory=tuple)
    source_signature: str | None = None
    document_type: str | None = None
    approved_at: datetime.datetime | None = None
    voided_at: datetime.datetime | None = None


@dataclass(frozen=True)
class MappingSuggestion:
    target_value: str
    confidence: float
    tier: ConfidenceTier
    approval_count: int
    advisory_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_value": self.target_value,
            "confidence": self.confidence,
            "tier": self.tier,
            "approval_count": self.approval_count,
            "advisory_only": self.advisory_only,
        }


@dataclass(frozen=True)
class VendorLearningSuggestion:
    company_id: int
    vendor_signature: str
    category: MappingSuggestion | None = None
    subcategory: MappingSuggestion | None = None
    payment_method: MappingSuggestion | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "vendor_signature": self.vendor_signature,
            "category": self.category.to_dict() if self.category else None,
            "subcategory": self.subcategory.to_dict() if self.subcategory else None,
            "payment_method": (
                self.payment_method.to_dict() if self.payment_method else None
            ),
        }


class LearningStore(Protocol):
    """Injected persistence seam — in-memory, or :class:`~services.receipt_learning_store.PersistentLearningStore`."""

    def list_for_signature(
        self,
        company_id: int,
        signature_type: SignatureType,
        signature_key: str,
    ) -> tuple[LearningRecord, ...]: ...

    def record_approval_hit(
        self,
        company_id: int,
        signature_type: SignatureType,
        signature_key: str,
        target_value: str,
        *,
        approved_at: datetime.datetime,
    ) -> LearningRecord: ...

    def decrement_approval_hit(
        self,
        company_id: int,
        signature_type: SignatureType,
        signature_key: str,
        target_value: str,
        *,
        voided_at: datetime.datetime,
    ) -> LearningRecord | None: ...


class InMemoryLearningStore:
    """Test/dev store — keyed by company + signature type + key + target."""

    def __init__(self) -> None:
        self._rows: dict[tuple[int, str, str, str], LearningRecord] = {}

    def list_for_signature(
        self,
        company_id: int,
        signature_type: SignatureType,
        signature_key: str,
    ) -> tuple[LearningRecord, ...]:
        prefix = (company_id, signature_type, signature_key)
        return tuple(
            row
            for key, row in self._rows.items()
            if key[:3] == prefix and row.approval_count > 0
        )

    def record_approval_hit(
        self,
        company_id: int,
        signature_type: SignatureType,
        signature_key: str,
        target_value: str,
        *,
        approved_at: datetime.datetime,
    ) -> LearningRecord:
        key = (company_id, signature_type, signature_key, target_value)
        existing = self._rows.get(key)
        if existing is None:
            row = LearningRecord(
                company_id=company_id,
                signature_type=signature_type,
                signature_key=signature_key,
                target_value=target_value,
                approval_count=1,
                last_approved_at=approved_at,
            )
        else:
            row = LearningRecord(
                company_id=company_id,
                signature_type=signature_type,
                signature_key=signature_key,
                target_value=target_value,
                approval_count=existing.approval_count + 1,
                correction_count=existing.correction_count,
                last_approved_at=approved_at,
            )
        self._rows[key] = row
        return row

    def decrement_approval_hit(
        self,
        company_id: int,
        signature_type: SignatureType,
        signature_key: str,
        target_value: str,
        *,
        voided_at: datetime.datetime,
    ) -> LearningRecord | None:
        key = (company_id, signature_type, signature_key, target_value)
        existing = self._rows.get(key)
        if existing is None or existing.approval_count <= 0:
            return None
        row = LearningRecord(
            company_id=company_id,
            signature_type=signature_type,
            signature_key=signature_key,
            target_value=target_value,
            approval_count=existing.approval_count - 1,
            correction_count=existing.correction_count + 1,
            last_approved_at=existing.last_approved_at,
        )
        self._rows[key] = row
        return row

    def all_records(self) -> tuple[LearningRecord, ...]:
        return tuple(self._rows.values())


# ── Pure helpers ──────────────────────────────────────────────────────────────


def _normalized_vendor_key(vendor_text: str | None) -> str | None:
    if not vendor_text or not str(vendor_text).strip():
        return None
    sig = normalize_vendor_signature(vendor_text)
    if not sig or sig == "UNKNOWN":
        return None
    return sig


def _category_is_never_learn(category_name: str | None) -> bool:
    if not category_name:
        return False
    low = category_name.casefold()
    return any(token in low for token in _NEVER_LEARN_CATEGORY_TOKENS)


def should_learn_from_approval(event: ApprovalLearningEvent) -> tuple[bool, str]:
    """Return (ok, skip_reason). Learn only from approved + posted, safe vendors."""
    if event.expense_record_id is None:
        return False, "expense_record_id missing — not posted"
    if event.is_voided:
        return False, "voided posting — use record_void_reversal"
    vendor_key = _normalized_vendor_key(event.vendor_signature)
    if vendor_key is None:
        return False, "blank or unknown vendor signature"
    if _category_is_never_learn(event.category_name):
        return False, "category on never-learn list"
    if event.amount is not None and event.amount > _LARGE_AMOUNT_THRESHOLD:
        return False, "amount exceeds large-outlier threshold"
    if event.payment_method in (None, "", "Unknown"):
        # Still learn category/subcategory; payment mapping skipped separately.
        pass
    return True, ""


def calculate_confidence(
    *,
    approval_count: int,
    total_approvals_for_signature: int,
    approvals_for_target: int,
    correction_count: int = 0,
    recency_factor: float = 1.0,
) -> float:
    """Bounded 0–100 score from count, consistency, recency, correction penalty."""
    if approval_count < 1 or total_approvals_for_signature < 1 or approvals_for_target < 1:
        return 0.0
    consistency = approvals_for_target / total_approvals_for_signature
    base = min(99.0, 40.0 + approval_count * 8.0)
    score = base * consistency * recency_factor
    penalty = min(0.5, correction_count * 0.1)
    score *= 1.0 - penalty
    return max(0.0, min(100.0, round(score, 2)))


def classify_confidence_tier(
    confidence: float,
    approval_count: int,
    *,
    auto_post_min_approvals: int = AUTO_POST_MIN_APPROVALS,
    trusted_min_approvals: int = TRUSTED_MIN_APPROVALS,
) -> ConfidenceTier:
    """<80 manual · 80–95 prefill · >95+N auto-post-eligible · >99 trusted."""
    if confidence >= 99.0 and approval_count >= trusted_min_approvals:
        return TIER_TRUSTED
    if confidence > 95.0 and approval_count >= auto_post_min_approvals:
        return TIER_AUTO_POST_ELIGIBLE
    if confidence >= 80.0:
        return TIER_PREFILL
    return TIER_MANUAL


def _best_mapping(
    records: tuple[LearningRecord, ...],
) -> LearningRecord | None:
    if not records:
        return None
    return max(records, key=lambda r: (r.approval_count, r.last_approved_at or datetime.datetime.min))


def _mapping_suggestion(
    records: tuple[LearningRecord, ...],
    target_record: LearningRecord,
    *,
    advisory_only: bool = False,
) -> MappingSuggestion:
    total = sum(r.approval_count for r in records)
    confidence = calculate_confidence(
        approval_count=target_record.approval_count,
        total_approvals_for_signature=total,
        approvals_for_target=target_record.approval_count,
        correction_count=target_record.correction_count,
    )
    tier = classify_confidence_tier(confidence, target_record.approval_count)
    return MappingSuggestion(
        target_value=target_record.target_value,
        confidence=confidence,
        tier=tier,
        approval_count=target_record.approval_count,
        advisory_only=advisory_only,
    )


def learning_event_from_posted_draft(
    ctx: PostedDraftLearningContext,
) -> ApprovalLearningEvent:
    """Map posted draft + expense record fields to a learning event."""
    return ApprovalLearningEvent(
        company_id=ctx.company_id,
        vendor_signature=ctx.vendor_signature,
        expense_record_id=ctx.expense_record_id,
        tx_category_id=ctx.tx_category_id,
        tx_subcategory_id=ctx.tx_subcategory_id,
        payment_method=ctx.payment_method,
        category_name=ctx.category_name,
        amount=ctx.amount,
        is_voided=ctx.expense_record_is_void,
        item_texts=ctx.item_texts,
        product_ids=ctx.product_ids,
        source_signature=ctx.source_signature,
        document_type=ctx.document_type,
        approved_at=ctx.approved_at,
        voided_at=ctx.voided_at,
    )


def _iter_mapping_targets(
    event: ApprovalLearningEvent,
) -> tuple[tuple[SignatureType, str, str], ...]:
    vendor_key = _normalized_vendor_key(event.vendor_signature)
    if vendor_key is None:
        return ()
    targets: list[tuple[SignatureType, str, str]] = []
    if event.tx_category_id is not None:
        targets.append(("vendor_category", vendor_key, str(event.tx_category_id)))
    if event.tx_subcategory_id is not None:
        targets.append(("vendor_subcategory", vendor_key, str(event.tx_subcategory_id)))
    if event.payment_method and event.payment_method not in ("", "Unknown"):
        targets.append(("vendor_payment", vendor_key, event.payment_method))
    for item_text, product_id in zip(event.item_texts, event.product_ids, strict=False):
        key = (item_text or "").strip().casefold()
        if key and product_id is not None:
            targets.append(("item_product", key, str(product_id)))
    if event.source_signature and event.document_type:
        src_key = normalize_vendor_signature(event.source_signature) or event.source_signature
        targets.append(("source_format", src_key, event.document_type))
    return tuple(targets)


def should_reconcile_void(event: ApprovalLearningEvent) -> tuple[bool, str]:
    """Return (ok, skip_reason). Reconcile only voided posted expenses."""
    if not event.is_voided:
        return False, "not voided"
    if event.expense_record_id is None:
        return False, "expense_record_id missing — not posted"
    vendor_key = _normalized_vendor_key(event.vendor_signature)
    if vendor_key is None:
        return False, "blank or unknown vendor signature"
    if _category_is_never_learn(event.category_name):
        return False, "category on never-learn list"
    if event.amount is not None and event.amount > _LARGE_AMOUNT_THRESHOLD:
        return False, "amount exceeds large-outlier threshold"
    return True, ""


def record_approval(
    store: LearningStore,
    event: ApprovalLearningEvent,
) -> RecordApprovalResult:
    """Increment learned mappings for an approved, posted draft."""
    ok, reason = should_learn_from_approval(event)
    if not ok:
        return RecordApprovalResult(learned=False, skip_reason=reason)

    approved_at = event.approved_at or datetime.datetime.now()
    written = 0
    for signature_type, signature_key, target_value in _iter_mapping_targets(event):
        store.record_approval_hit(
            event.company_id,
            signature_type,
            signature_key,
            target_value,
            approved_at=approved_at,
        )
        written += 1

    return RecordApprovalResult(learned=True, records_written=written)


def record_void_reversal(
    store: LearningStore,
    event: ApprovalLearningEvent,
) -> RecordVoidReversalResult:
    """Decrement learned mappings when a posted expense is voided/reversed."""
    ok, reason = should_reconcile_void(event)
    if not ok:
        return RecordVoidReversalResult(reconciled=False, skip_reason=reason)

    voided_at = event.voided_at or datetime.datetime.now()
    updated = 0
    for signature_type, signature_key, target_value in _iter_mapping_targets(event):
        row = store.decrement_approval_hit(
            event.company_id,
            signature_type,
            signature_key,
            target_value,
            voided_at=voided_at,
        )
        if row is not None:
            updated += 1

    return RecordVoidReversalResult(reconciled=updated > 0, records_updated=updated)


reconcile_voided_receipt_learning = record_void_reversal


def suggest_for_vendor(
    store: LearningStore,
    company_id: int,
    vendor_signature: str,
) -> VendorLearningSuggestion | None:
    """Suggest learned mappings for a vendor signature (company-scoped)."""
    vendor_key = _normalized_vendor_key(vendor_signature)
    if vendor_key is None:
        return None

    cat_records = store.list_for_signature(company_id, "vendor_category", vendor_key)
    sub_records = store.list_for_signature(company_id, "vendor_subcategory", vendor_key)
    pay_records = store.list_for_signature(company_id, "vendor_payment", vendor_key)

    best_cat = _best_mapping(cat_records)
    best_sub = _best_mapping(sub_records)
    best_pay = _best_mapping(pay_records)

    if not any((best_cat, best_sub, best_pay)):
        return None

    return VendorLearningSuggestion(
        company_id=company_id,
        vendor_signature=vendor_key,
        category=(
            _mapping_suggestion(cat_records, best_cat)
            if best_cat and best_cat.approval_count >= _MIN_APPROVALS_TO_SURFACE
            else None
        ),
        subcategory=(
            _mapping_suggestion(sub_records, best_sub)
            if best_sub and best_sub.approval_count >= _MIN_APPROVALS_TO_SURFACE
            else None
        ),
        payment_method=(
            _mapping_suggestion(pay_records, best_pay, advisory_only=True)
            if best_pay and best_pay.approval_count >= _MIN_APPROVALS_TO_SURFACE
            else None
        ),
    )
