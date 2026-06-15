"""RECEIPT-AI-02-IMPL-5 — learned receipt mapping prefill for Receipt Capture.

Reads company-scoped ``ReceiptLearningMap`` rows via :class:`~services.receipt_learning_store.PersistentLearningStore`
and returns prefill-ready suggestions. Category/subcategory apply only at **prefill+** tiers;
payment is always advisory.

No Streamlit, no auto-post, no posting changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services import receipt_learning as learn
from services.receipt_learning_store import persistent_learning_store
from sqlalchemy.orm import Session

PREFILL_ELIGIBLE_TIERS: frozenset[learn.ConfidenceTier] = frozenset(
    {
        learn.TIER_PREFILL,
        learn.TIER_AUTO_POST_ELIGIBLE,
        learn.TIER_TRUSTED,
    }
)


def tier_allows_prefill(tier: learn.ConfidenceTier | None) -> bool:
    """True when learned mapping may prefill editable fields (≥80% tier)."""
    return tier is not None and tier in PREFILL_ELIGIBLE_TIERS


@dataclass(frozen=True)
class LearnedReceiptSuggestion:
    """Learned prefill view for Receipt Capture."""

    vendor_signature: str | None
    suggested_category_id: int | None = None
    suggested_subcategory_id: int | None = None
    category_confidence: float | None = None
    category_tier: learn.ConfidenceTier | None = None
    prefill_category: bool = False
    prefill_subcategory: bool = False
    suggested_payment_method: str | None = None
    payment_confidence: float | None = None
    payment_tier: learn.ConfidenceTier | None = None
    payment_advisory_only: bool = True
    explanation: str = ""
    evidence: tuple[str, ...] = ()

    @property
    def has_mapping(self) -> bool:
        return any(
            (
                self.suggested_category_id,
                self.suggested_subcategory_id,
                self.suggested_payment_method,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor_signature": self.vendor_signature,
            "suggested_category_id": self.suggested_category_id,
            "suggested_subcategory_id": self.suggested_subcategory_id,
            "category_confidence": self.category_confidence,
            "category_tier": self.category_tier,
            "prefill_category": self.prefill_category,
            "prefill_subcategory": self.prefill_subcategory,
            "suggested_payment_method": self.suggested_payment_method,
            "payment_confidence": self.payment_confidence,
            "payment_tier": self.payment_tier,
            "payment_advisory_only": self.payment_advisory_only,
            "explanation": self.explanation,
            "evidence": list(self.evidence),
            "has_mapping": self.has_mapping,
        }


def _parse_category_id(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_from_vendor_suggestion(
    suggestion: learn.VendorLearningSuggestion,
) -> LearnedReceiptSuggestion:
    evidence: list[str] = []
    cat_id: int | None = None
    cat_conf: float | None = None
    cat_tier: learn.ConfidenceTier | None = None
    prefill_cat = False
    if suggestion.category is not None:
        cat_id = _parse_category_id(suggestion.category.target_value)
        cat_conf = suggestion.category.confidence
        cat_tier = suggestion.category.tier
        prefill_cat = tier_allows_prefill(cat_tier)
        evidence.append(
            f"category:{cat_id} confidence={cat_conf:.1f}% tier={cat_tier} "
            f"approvals={suggestion.category.approval_count}"
        )

    sub_id: int | None = None
    sub_conf: float | None = None
    sub_tier: learn.ConfidenceTier | None = None
    prefill_sub = False
    if suggestion.subcategory is not None:
        sub_id = _parse_category_id(suggestion.subcategory.target_value)
        sub_conf = suggestion.subcategory.confidence
        sub_tier = suggestion.subcategory.tier
        prefill_sub = tier_allows_prefill(sub_tier)
        evidence.append(
            f"subcategory:{sub_id} confidence={sub_conf:.1f}% tier={sub_tier} "
            f"approvals={suggestion.subcategory.approval_count}"
        )

    pay_method: str | None = None
    pay_conf: float | None = None
    pay_tier: learn.ConfidenceTier | None = None
    if suggestion.payment_method is not None:
        pay_method = suggestion.payment_method.target_value
        pay_conf = suggestion.payment_method.confidence
        pay_tier = suggestion.payment_method.tier
        evidence.append(
            f"payment:{pay_method} confidence={pay_conf:.1f}% tier={pay_tier} "
            f"approvals={suggestion.payment_method.approval_count} advisory"
        )

    explanation_parts: list[str] = []
    if prefill_cat and cat_id is not None:
        explanation_parts.append(
            f"Learned category #{cat_id} ({cat_conf:.0f}%, {cat_tier})"
        )
    elif cat_id is not None and cat_tier == learn.TIER_MANUAL:
        explanation_parts.append(
            f"Low-confidence category hint #{cat_id} ({cat_conf:.0f}%) — not prefilled"
        )
    if prefill_sub and sub_id is not None:
        explanation_parts.append(
            f"Learned subcategory #{sub_id} ({sub_conf:.0f}%, {sub_tier})"
        )
    if pay_method:
        explanation_parts.append(
            f"Advisory payment hint: {pay_method} ({pay_conf:.0f}%, {pay_tier})"
        )

    return LearnedReceiptSuggestion(
        vendor_signature=suggestion.vendor_signature,
        suggested_category_id=cat_id if prefill_cat else None,
        suggested_subcategory_id=sub_id if prefill_sub else None,
        category_confidence=cat_conf,
        category_tier=cat_tier,
        prefill_category=prefill_cat,
        prefill_subcategory=prefill_sub,
        suggested_payment_method=pay_method,
        payment_confidence=pay_conf,
        payment_tier=pay_tier,
        payment_advisory_only=True,
        explanation="; ".join(explanation_parts),
        evidence=tuple(evidence),
    )


def get_learned_receipt_suggestion(
    session: Session,
    company_id: int,
    vendor_signature: str | None,
    *,
    item_texts: tuple[str, ...] = (),
    source_signature: str | None = None,
    store: learn.LearningStore | None = None,
) -> LearnedReceiptSuggestion | None:
    """Return learned prefill hints for Receipt Capture (company-scoped).

    ``item_texts`` and ``source_signature`` are reserved for future item/format
    hints; vendor category/subcategory/payment drive prefill in this slice.
    """
    del item_texts, source_signature  # reserved — no item/format prefill yet
    if not vendor_signature or not str(vendor_signature).strip():
        return None

    learning_store = store or persistent_learning_store(session)
    vendor_suggestion = learn.suggest_for_vendor(
        learning_store, company_id, vendor_signature
    )
    if vendor_suggestion is None:
        return None
    return _build_from_vendor_suggestion(vendor_suggestion)


def apply_learned_category_prefill(
    learned: LearnedReceiptSuggestion | None,
    *,
    tx_category_id: int | None,
    tx_subcategory_id: int | None,
) -> tuple[int | None, int | None]:
    """Apply learned category/subcategory only when caller did not supply values."""
    if learned is None:
        return tx_category_id, tx_subcategory_id
    cat = tx_category_id
    sub = tx_subcategory_id
    if cat is None and learned.prefill_category:
        cat = learned.suggested_category_id
    if sub is None and learned.prefill_subcategory:
        sub = learned.suggested_subcategory_id
    return cat, sub
