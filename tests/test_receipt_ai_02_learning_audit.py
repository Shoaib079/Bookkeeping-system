"""RECEIPT-AI-02 — contract test for the learning-engine audit.

Doc-only guard: verifies the audit exists, carries all eight required outputs, records
the captured-suggestion gap, the approval-driven + void-aware learning rules, the
confidence tiers, company isolation, the never-learn list, the future schema, and the
no-change invariants. Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "RECEIPT_AI_02_LEARNING_AUDIT.md"

REQUIRED_SECTIONS = (
    "Current reusable data map",
    "Proposed learning model",
    "Confidence model",
    "Safety rules",
    "Future schema proposal",
    "Contract tests",
    "Implementation slices",
    "Risk assessment",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Learning audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Learning audit doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Learning audit doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_reusable_assets(doc_text):
    low = doc_text.lower()
    for asset in ("expensedraft", "draftattachment", "normalize_vendor_signature",
                  "auditlog", "transactioncategory", "vendor", "product"):
        assert asset in low, f"Data map must cover {asset}"
    assert "expense_record_id" in low, "Must use expense_record_id as posted ground truth"


def test_captured_suggestion_gap(doc_text):
    low = doc_text.lower()
    assert "original ai suggestion" in low or "original suggestion" in low, (
        "Must identify the missing captured-suggestion artifact"
    )
    assert "not persisted" in low or "not stored" in low, "Must state the suggestion is not persisted"
    assert "correction" in low, "Must tie the gap to correction-learning"


def test_learn_on_approval_not_creation(doc_text):
    low = doc_text.lower()
    assert "on approval" in low, "Must learn on approval"
    assert "never on draft creation" in low or "draft creation" in low and "never" in low, (
        "Must not learn on draft creation/submission"
    )


def test_void_aware(doc_text):
    low = doc_text.lower()
    assert "void" in low and ("decrement" in low or "invalidate" in low or "reverse" in low), (
        "Learning must be void-aware (decrement/invalidate on reversal)"
    )


def test_what_is_learned(doc_text):
    low = doc_text.lower()
    assert "vendor_signature → category" in low or "vendor_signature → category" in doc_text, (
        "Must learn vendor → category"
    )
    assert "payment_method" in low, "Must learn vendor → payment_method (advisory)"
    assert "item_text → product" in low or "item-text → product" in low or (
        "item_text" in low and "product" in low
    ), "Must learn item text → product"


def test_confidence_tiers(doc_text):
    low = doc_text.lower()
    assert "consistency" in low, "Confidence must include consistency"
    assert "approval_count" in low, "Confidence must include approval_count"
    for tier in ("80", "95", "99"):
        assert tier in doc_text, f"Confidence tiers must reference {tier}"


def test_never_learn_list(doc_text):
    low = doc_text.lower()
    for forbidden in ("payroll", "tax", "bank transfer", "blank", "company isolation"):
        assert forbidden in low, f"Safety rules must forbid/handle: {forbidden}"
    assert "advisory only" in low, "Payment learning must be advisory only"


def test_future_schema(doc_text):
    low = doc_text.lower()
    assert "receipt_learning_map" in low, "Future schema must propose receipt_learning_map"
    assert "additive" in low, "Future schema must be additive / migration-safe"


def test_slices_not_implemented(doc_text):
    low = doc_text.lower()
    assert "do not implement" in low, "Slices must be marked do-not-implement"
    for s in ("receipt-ai-02-impl-1", "receipt-ai-02-impl-3"):
        assert s in low, f"Implementation slices must include {s}"


def test_no_change_statement(doc_text):
    low = doc_text.lower()
    assert "audit only" in low, "Must state audit-only"
    assert "no schema change" in low, "Must state no schema change"
    assert "no learning table" in low, "Must state no learning table"
    assert "no auto-post" in low, "Must state no auto-post"
