"""RECEIPT-AI-01-IMPL-1 — pure, FastAPI-ready receipt-AI service skeleton.

Phase 1 is **approval-first**: this module only *suggests* an expense draft from a
receipt extraction. It NEVER writes to the DB, never creates an ExpenseRecord or
JournalEntry, never approves/posts, never creates a bank transaction, and makes no
network/OCR/AI call. The OCR/AI step is an **injected callable** (the extractor seam),
exactly like the staff-capture ``post_fn`` posting seam.

No Streamlit, no ``app`` import, no schema change. All DTOs are frozen and
serializable via ``to_dict()``.

The produced :class:`DraftSuggestion` maps onto ``services.staff_capture.ExpenseDraftInput``
(date / amount / currency / payment_method / tx_category_id / tx_subcategory_id /
description) — but constructing/persisting the actual draft is a *later* slice.
"""

from __future__ import annotations

import datetime
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Literal

# ── Payment method ────────────────────────────────────────────────────────────

PaymentMethod = Literal["Cash", "Card", "Unknown"]

PAYMENT_CASH: PaymentMethod = "Cash"
PAYMENT_CARD: PaymentMethod = "Card"
PAYMENT_UNKNOWN: PaymentMethod = "Unknown"

# Keyword evidence — matched against a Turkish-folded, uppercased copy of the text.
# Stored already folded so the example "KREDİ KARTI" matches "KREDI KARTI".
_CASH_KEYWORDS: tuple[str, ...] = (
    "NAKIT",          # nakit / NAKİT (İ→I folded)
    "CASH",
    "CASH PAYMENT",
    "PAID CASH",
)
_CARD_KEYWORDS: tuple[str, ...] = (
    "CARD",
    "KREDI KARTI",    # kredi kartı
    "BANKA KARTI",    # banka kartı
    "VISA",
    "MASTERCARD",
    "POS",
    "SLIP",
    "TERMINAL",
    "TEMASSIZ",       # temassız
    "CONTACTLESS",
)

# Above this, the draft may be prefilled; at/below, the user must choose.
PAYMENT_PREFILL_THRESHOLD = 0.6


@dataclass(frozen=True)
class PaymentDetection:
    """Advisory payment-method detection — Phase 1 suggestion only."""

    payment_method: PaymentMethod
    payment_confidence: float
    payment_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "payment_method": self.payment_method,
            "payment_confidence": self.payment_confidence,
            "payment_evidence": list(self.payment_evidence),
        }


# ── Extraction DTOs ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ReceiptLineItem:
    description: str
    quantity: float | None = None
    unit_price: float | None = None
    amount: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "amount": self.amount,
        }


@dataclass(frozen=True)
class ReceiptExtraction:
    """What the (injected) extractor returns. Pure data — no DB identity."""

    vendor_text: str | None = None
    receipt_date: datetime.date | None = None
    total_amount: float | None = None
    tax_amount: float | None = None
    currency: str | None = None
    line_items: list[ReceiptLineItem] = field(default_factory=list)
    confidence: float = 0.0
    raw_text: str | None = None
    # Payment detection (advisory)
    payment_method: PaymentMethod = PAYMENT_UNKNOWN
    payment_confidence: float = 0.0
    payment_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vendor_text": self.vendor_text,
            "receipt_date": self.receipt_date.isoformat() if self.receipt_date else None,
            "total_amount": self.total_amount,
            "tax_amount": self.tax_amount,
            "currency": self.currency,
            "line_items": [li.to_dict() for li in self.line_items],
            "confidence": self.confidence,
            "raw_text": self.raw_text,
            "payment_method": self.payment_method,
            "payment_confidence": self.payment_confidence,
            "payment_evidence": list(self.payment_evidence),
        }


@dataclass(frozen=True)
class CreateSuggestion:
    """A 'this entity does not exist — create it?' hint. Never auto-created."""

    kind: Literal["vendor", "category", "subcategory", "item"]
    label: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "label": self.label}


@dataclass(frozen=True)
class DraftSuggestion:
    """Suggested expense draft + advisory payment + create-if-missing hints.

    Maps onto ``ExpenseDraftInput``; a later slice persists it. ``payment_method`` is
    prefilled only when payment detection is confident; otherwise ``None`` =
    'user must choose'. Nothing here posts or writes.
    """

    date: datetime.date | None
    amount: float | None
    currency: str | None
    description: str
    tx_category_id: int | None
    tx_subcategory_id: int | None
    vendor_signature: str | None
    # Advisory payment (suggestion only)
    payment_method: PaymentMethod
    payment_confidence: float
    payment_evidence: list[str]
    payment_prefilled: bool
    user_must_choose_payment: bool
    # Create-if-missing hints (never auto-created)
    create_suggestions: list[CreateSuggestion] = field(default_factory=list)
    extraction_confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat() if self.date else None,
            "amount": self.amount,
            "currency": self.currency,
            "description": self.description,
            "tx_category_id": self.tx_category_id,
            "tx_subcategory_id": self.tx_subcategory_id,
            "vendor_signature": self.vendor_signature,
            "payment_method": self.payment_method,
            "payment_confidence": self.payment_confidence,
            "payment_evidence": list(self.payment_evidence),
            "payment_prefilled": self.payment_prefilled,
            "user_must_choose_payment": self.user_must_choose_payment,
            "create_suggestions": [c.to_dict() for c in self.create_suggestions],
            "extraction_confidence": self.extraction_confidence,
        }


# The injected OCR/AI seam. Phase 1 ships no implementation; tests pass a fake.
ExtractorFn = Callable[..., ReceiptExtraction]


# ── Pure helpers ──────────────────────────────────────────────────────────────

# Turkish-specific letter folding so İ/I/ı and ş/ç/ğ/ü/ö collapse to ASCII.
_TR_FOLD = str.maketrans(
    {
        "İ": "I", "ı": "I", "i": "I",
        "Ş": "S", "ş": "S",
        "Ğ": "G", "ğ": "G",
        "Ç": "C", "ç": "C",
        "Ü": "U", "ü": "U",
        "Ö": "O", "ö": "O",
    }
)


def _fold_text(text: str) -> str:
    """Uppercase + Turkish-fold + strip combining marks. Pure, locale-independent."""
    folded = text.translate(_TR_FOLD)
    folded = unicodedata.normalize("NFKD", folded)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return folded.upper()


def normalize_vendor_signature(vendor_text: str | None) -> str | None:
    """Stable vendor key — 'BİM' / 'BIM' / 'Bim' → 'BIM'. None/blank → None."""
    if not vendor_text or not vendor_text.strip():
        return None
    folded = _fold_text(vendor_text)
    # Keep only alphanumerics so punctuation/spacing never splits a vendor.
    signature = re.sub(r"[^A-Z0-9]", "", folded)
    return signature or None


def detect_payment_method(text: str | None) -> PaymentDetection:
    """Advisory Cash/Card/Unknown detection from receipt text. Pure; no network."""
    if not text or not text.strip():
        return PaymentDetection(PAYMENT_UNKNOWN, 0.0, [])
    folded = _fold_text(text)
    cash_hits = [kw for kw in _CASH_KEYWORDS if kw in folded]
    card_hits = [kw for kw in _CARD_KEYWORDS if kw in folded]

    if cash_hits and not card_hits:
        confidence = min(0.95, 0.75 + 0.1 * (len(cash_hits) - 1))
        return PaymentDetection(PAYMENT_CASH, confidence, cash_hits)
    if card_hits and not cash_hits:
        confidence = min(0.95, 0.75 + 0.1 * (len(card_hits) - 1))
        return PaymentDetection(PAYMENT_CARD, confidence, card_hits)
    if cash_hits and card_hits:
        # Conflicting evidence — do not guess.
        return PaymentDetection(PAYMENT_UNKNOWN, 0.3, sorted(cash_hits + card_hits))
    return PaymentDetection(PAYMENT_UNKNOWN, 0.0, [])


def extract_receipt_with(extractor: ExtractorFn, *args: Any, **kwargs: Any) -> ReceiptExtraction:
    """Run the **injected** extractor and return its ReceiptExtraction.

    This module performs no OCR/AI/network itself — it only calls the seam. If the
    extractor leaves payment detection empty/Unknown but provided ``raw_text``, we
    backfill it with the pure :func:`detect_payment_method` (still no network).
    """
    extraction = extractor(*args, **kwargs)
    if not isinstance(extraction, ReceiptExtraction):
        raise TypeError("extractor must return a ReceiptExtraction")

    needs_payment_backfill = (
        extraction.payment_method == PAYMENT_UNKNOWN
        and not extraction.payment_evidence
        and bool(extraction.raw_text)
    )
    if needs_payment_backfill:
        detected = detect_payment_method(extraction.raw_text)
        if detected.payment_method != PAYMENT_UNKNOWN or detected.payment_evidence:
            return ReceiptExtraction(
                vendor_text=extraction.vendor_text,
                receipt_date=extraction.receipt_date,
                total_amount=extraction.total_amount,
                tax_amount=extraction.tax_amount,
                currency=extraction.currency,
                line_items=list(extraction.line_items),
                confidence=extraction.confidence,
                raw_text=extraction.raw_text,
                payment_method=detected.payment_method,
                payment_confidence=detected.payment_confidence,
                payment_evidence=list(detected.payment_evidence),
            )
    return extraction


def map_extraction_to_draft_suggestion(
    extraction: ReceiptExtraction,
    *,
    existing_tx_category_id: int | None = None,
    existing_tx_subcategory_id: int | None = None,
    vendor_exists: bool = False,
    known_item_descriptions: Iterable[str] | None = None,
    payment_prefill_threshold: float = PAYMENT_PREFILL_THRESHOLD,
) -> DraftSuggestion:
    """Map an extraction to a *suggested* draft. Pure: no DB, no posting, no create.

    - Payment is prefilled only when method is Cash/Card AND confidence is high;
      otherwise the user must choose (advisory only).
    - Missing vendor/category/items become :class:`CreateSuggestion` hints — never
      auto-created.
    """
    vendor_signature = normalize_vendor_signature(extraction.vendor_text)

    confident_payment = (
        extraction.payment_method in (PAYMENT_CASH, PAYMENT_CARD)
        and extraction.payment_confidence > payment_prefill_threshold
    )
    if confident_payment:
        suggested_payment: PaymentMethod = extraction.payment_method
        payment_prefilled = True
        user_must_choose = False
    else:
        suggested_payment = PAYMENT_UNKNOWN
        payment_prefilled = False
        user_must_choose = True

    create_suggestions: list[CreateSuggestion] = []
    if vendor_signature and not vendor_exists:
        create_suggestions.append(
            CreateSuggestion(kind="vendor", label=(extraction.vendor_text or "").strip())
        )
    if existing_tx_category_id is None and extraction.vendor_text:
        # No resolved category — suggest creating/choosing one (never silent).
        create_suggestions.append(
            CreateSuggestion(kind="category", label=(extraction.vendor_text or "").strip())
        )
    known = {d.strip().casefold() for d in (known_item_descriptions or [])}
    for li in extraction.line_items:
        desc = (li.description or "").strip()
        if desc and desc.casefold() not in known:
            create_suggestions.append(CreateSuggestion(kind="item", label=desc))

    description = (extraction.vendor_text or "").strip()

    return DraftSuggestion(
        date=extraction.receipt_date,
        amount=extraction.total_amount,
        currency=extraction.currency,
        description=description,
        tx_category_id=existing_tx_category_id,
        tx_subcategory_id=existing_tx_subcategory_id,
        vendor_signature=vendor_signature,
        payment_method=suggested_payment,
        payment_confidence=extraction.payment_confidence,
        payment_evidence=list(extraction.payment_evidence),
        payment_prefilled=payment_prefilled,
        user_must_choose_payment=user_must_choose,
        create_suggestions=create_suggestions,
        extraction_confidence=extraction.confidence,
    )


def detect_duplicate_by_sha256(
    sha256: str | None,
    known_hashes: Iterable[str],
) -> bool:
    """True if this receipt's sha256 already exists (advisory dedup). Pure."""
    if not sha256:
        return False
    return sha256 in set(known_hashes)
