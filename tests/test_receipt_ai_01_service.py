"""RECEIPT-AI-01-IMPL-1 — tests for the pure receipt-AI service skeleton.

Verifies: injected fake extractor, no network/AI/DB/posting, BİM/BIM/Bim vendor
normalization, payment detection (NAKİT→Cash, POS/VISA/KREDİ KARTI→Card, ambiguous→
Unknown), payment is suggestion-only, create-if-missing returns suggestions only,
and DTO serializability. Pure stdlib + the service module; no app/Streamlit import.
"""

from __future__ import annotations

import datetime
import json

import pytest

from services import receipt_ai as rcpt


# ── Fake extractor (the injected seam) — makes NO network/AI call ─────────────

class _FakeExtractor:
    def __init__(self, extraction: rcpt.ReceiptExtraction):
        self._extraction = extraction
        self.calls = 0

    def __call__(self, *args, **kwargs) -> rcpt.ReceiptExtraction:
        self.calls += 1
        return self._extraction


def _extraction(**kw) -> rcpt.ReceiptExtraction:
    base = dict(
        vendor_text="BİM",
        receipt_date=datetime.date(2026, 6, 14),
        total_amount=123.45,
        currency="TRY",
        line_items=[rcpt.ReceiptLineItem(description="Süt", amount=20.0)],
        confidence=0.8,
    )
    base.update(kw)
    return rcpt.ReceiptExtraction(**base)


# ── Extractor seam ────────────────────────────────────────────────────────────

def test_fake_extractor_returns_fields():
    fake = _FakeExtractor(_extraction())
    out = rcpt.extract_receipt_with(fake)
    assert fake.calls == 1
    assert out.vendor_text == "BİM"
    assert out.receipt_date == datetime.date(2026, 6, 14)
    assert out.total_amount == 123.45
    assert out.line_items[0].description == "Süt"


def _imported_module_roots() -> set[str]:
    """Top-level module names imported by services/receipt_ai.py (via AST)."""
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(rcpt))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_service_makes_no_network_or_ai_call():
    """The service imports no network/AI/OCR library — extraction is the injected seam."""
    roots = _imported_module_roots()
    for forbidden in ("requests", "urllib", "urllib3", "httpx", "http", "openai",
                      "anthropic", "socket", "pytesseract", "cv2", "PIL", "easyocr"):
        assert forbidden not in roots, f"service must not import {forbidden!r}"
    # No extractor passed in => nothing happens; the module never self-extracts.
    fake = _FakeExtractor(_extraction())
    rcpt.extract_receipt_with(fake)
    assert fake.calls == 1


# ── Vendor normalization ──────────────────────────────────────────────────────

@pytest.mark.parametrize("raw", ["BİM", "BIM", "Bim", "  bim ", "B.İ.M"])
def test_vendor_signature_collapses_bim_variants(raw):
    assert rcpt.normalize_vendor_signature(raw) == "BIM"


def test_vendor_signature_blank_is_none():
    assert rcpt.normalize_vendor_signature("") is None
    assert rcpt.normalize_vendor_signature(None) is None


# ── Payment detection ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", ["NAKİT", "ÖDEME: NAKİT", "CASH", "CASH PAYMENT", "PAID CASH"])
def test_cash_detection(text):
    d = rcpt.detect_payment_method(text)
    assert d.payment_method == "Cash"
    assert d.payment_confidence > 0.6
    assert d.payment_evidence


@pytest.mark.parametrize("text", ["POS", "VISA", "MASTERCARD", "KREDİ KARTI",
                                  "BANKA KARTI", "TEMASSIZ", "CONTACTLESS", "SLIP"])
def test_card_detection(text):
    d = rcpt.detect_payment_method(text)
    assert d.payment_method == "Card"
    assert d.payment_confidence > 0.6
    assert d.payment_evidence


@pytest.mark.parametrize("text", ["", "TEŞEKKÜRLER", "FİŞ NO 12345", None])
def test_unknown_detection(text):
    d = rcpt.detect_payment_method(text)
    assert d.payment_method == "Unknown"


def test_conflicting_evidence_is_unknown():
    d = rcpt.detect_payment_method("NAKİT ... VISA POS")
    assert d.payment_method == "Unknown"
    assert d.payment_confidence < 0.6


def test_bim_receipt_with_nakit_via_raw_text_backfill():
    fake = _FakeExtractor(_extraction(raw_text="BİM A.Ş.\nTOPLAM 123,45\nNAKİT"))
    out = rcpt.extract_receipt_with(fake)
    assert out.payment_method == "Cash"
    assert "NAKIT" in out.payment_evidence


# ── Mapping to a draft suggestion (no posting) ────────────────────────────────

def test_high_confidence_payment_prefilled():
    ext = _extraction(payment_method="Card", payment_confidence=0.9, payment_evidence=["VISA"])
    s = rcpt.map_extraction_to_draft_suggestion(ext, existing_tx_category_id=5, vendor_exists=True)
    assert s.payment_method == "Card"
    assert s.payment_prefilled is True
    assert s.user_must_choose_payment is False


def test_low_confidence_payment_requires_user_choice():
    ext = _extraction(payment_method="Unknown", payment_confidence=0.0)
    s = rcpt.map_extraction_to_draft_suggestion(ext, existing_tx_category_id=5, vendor_exists=True)
    assert s.payment_method == "Unknown"
    assert s.payment_prefilled is False
    assert s.user_must_choose_payment is True


def test_missing_vendor_and_category_return_create_suggestions_only():
    ext = _extraction()
    s = rcpt.map_extraction_to_draft_suggestion(
        ext, existing_tx_category_id=None, vendor_exists=False
    )
    kinds = {c.kind for c in s.create_suggestions}
    assert "vendor" in kinds, "missing vendor must be a create-suggestion"
    assert "category" in kinds, "missing category must be a create-suggestion"
    # Suggestions only — the suggestion carries no created ids.
    assert s.tx_category_id is None
    assert s.vendor_signature == "BIM"


def test_known_item_not_resuggested():
    ext = _extraction(line_items=[rcpt.ReceiptLineItem(description="Süt", amount=20.0)])
    s = rcpt.map_extraction_to_draft_suggestion(
        ext, existing_tx_category_id=5, vendor_exists=True, known_item_descriptions=["süt"]
    )
    assert all(c.kind != "item" for c in s.create_suggestions)


# ── No posting / no journal entry / no approval ───────────────────────────────

def test_service_does_not_post_or_touch_db():
    """Static guarantee: the module imports no DB/ORM/app/posting modules and calls
    no posting/approval functions. (Doc prose may mention these names; we analyse the
    AST so comments/docstrings don't count.)"""
    import ast
    import inspect

    roots = _imported_module_roots()
    for forbidden in ("sqlalchemy", "models", "app", "db"):
        assert forbidden not in roots, f"pure service must not import {forbidden!r}"

    tree = ast.parse(inspect.getsource(rcpt))
    called = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                called.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                called.add(fn.attr)
    for forbidden in ("create_journal_entry", "approve_expense_draft", "commit",
                      "add", "post_expense"):
        assert forbidden not in called, f"service must not call {forbidden!r}"


# ── Duplicate detection ───────────────────────────────────────────────────────

def test_duplicate_by_sha256():
    assert rcpt.detect_duplicate_by_sha256("abc", ["abc", "def"]) is True
    assert rcpt.detect_duplicate_by_sha256("zzz", ["abc", "def"]) is False
    assert rcpt.detect_duplicate_by_sha256(None, ["abc"]) is False


# ── Serializability ───────────────────────────────────────────────────────────

def test_dtos_are_serializable():
    ext = _extraction(payment_method="Cash", payment_confidence=0.9, payment_evidence=["NAKIT"])
    s = rcpt.map_extraction_to_draft_suggestion(ext, existing_tx_category_id=5, vendor_exists=True)
    # Round-trips through JSON without error.
    json.dumps(ext.to_dict())
    json.dumps(s.to_dict())
    json.dumps(rcpt.detect_payment_method("VISA").to_dict())
    json.dumps(ext.line_items[0].to_dict())
