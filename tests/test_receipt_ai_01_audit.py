"""RECEIPT-AI-01 — contract test for the receipt-AI pre-design audit.

Doc-only guard: verifies the audit exists, carries all ten required outputs, and pins
the findings (reuse the ExpenseDraft + DraftAttachment + post_fn seam, draft-first,
no OCR deps yet, learning store, auto-post safety rules, FastAPI deferral, no-change).
Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "RECEIPT_AI_01_AUDIT.md"

REQUIRED_SECTIONS = (
    "Current capability map",
    "Reusable components",
    "Gaps",
    "Recommended architecture",
    "Learning model proposal",
    "Auto-post safety rules",
    "FastAPI / React migration design",
    "Contract tests",
    "Implementation slices",
    "Risk assessment",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Receipt-AI audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Receipt-AI audit doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Receipt-AI audit doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_reuses_draft_seam(doc_text):
    lowered = doc_text.lower()
    assert "expensedraft" in lowered, "Must cite the ExpenseDraft model"
    assert "draftattachment" in lowered, "Must cite the DraftAttachment model"
    assert "post_fn" in lowered, "Must cite the injected post_fn posting seam"
    assert "staff_capture" in lowered, "Must cite the staff_capture service"


def test_draft_first_recommendation(doc_text):
    lowered = doc_text.lower()
    assert "create an expense draft first" in lowered or "create a draft first" in lowered, (
        "Must recommend draft-first (Q4)"
    )
    assert "approval-first" in lowered, "Must be approval-first in Phase 1"
    assert "no posting change" in lowered or "no posting-schema change" in lowered or (
        "no schema change" in lowered
    ), "Phase 1 must require no posting/schema change"


def test_no_ocr_deps_yet(doc_text):
    lowered = doc_text.lower()
    assert "no ocr" in lowered or "greenfield" in lowered, "Must note OCR/AI is greenfield"
    assert "reportlab" in lowered, "Must note only reportlab exists (no vision deps)"


def test_extractor_is_a_seam(doc_text):
    lowered = doc_text.lower()
    assert "injected extractor" in lowered or "extractor seam" in lowered, (
        "Extractor must be an injected seam"
    )
    assert "no network" in lowered or "no ai call" in lowered or "does no network" in lowered, (
        "Service itself must do no network/AI"
    )


def test_learning_store(doc_text):
    lowered = doc_text.lower()
    assert "vendor" in lowered and "category" in lowered and "map" in lowered, (
        "Learning store must map vendor -> category"
    )
    assert "on each human approval" in lowered or "only on approval" in lowered, (
        "Learning writes only on approval"
    )
    assert "bİm" in lowered or "bim" in lowered, "Should reference the BİM example"


def test_auto_post_safety(doc_text):
    lowered = doc_text.lower()
    assert "owner-controlled" in lowered or "owner-only" in lowered, "Auto-post owner-controlled"
    assert "confidence" in lowered, "Auto-post confidence-gated"
    assert "auditlog" in lowered or "auditable" in lowered, "Auto-post auditable"
    assert "void" in lowered or "reversible" in lowered, "Auto-post reversible"
    assert "default" in lowered and "off" in lowered, "Auto-post default off"


def test_fastapi_deferral(doc_text):
    lowered = doc_text.lower()
    assert "fastapi" in lowered, "Must address FastAPI deferral"
    assert "defer" in lowered and ("ocr" in lowered or "ai" in lowered), (
        "OCR/AI network calls deferred to FastAPI"
    )


def test_create_if_missing(doc_text):
    lowered = doc_text.lower()
    assert "inline" in lowered and "quick-add" in lowered, (
        "Create-if-missing must reuse inline-category-add + vendor-quick-add"
    )
    assert "never" in lowered and ("silent" in lowered or "auto-create" in lowered), (
        "Must not silently auto-create in Phase 1"
    )


def test_risk_low(doc_text):
    lowered = doc_text.lower()
    assert "risk assessment" in lowered and "low" in lowered, "Audit must state LOW risk"


def test_no_change_statement(doc_text):
    lowered = doc_text.lower()
    assert "audit only" in lowered, "Must state audit-only"
    assert "no schema change" in lowered, "Must state no schema change"
    assert "no posting change" in lowered, "Must state no posting change"
    assert "no auto-post" in lowered, "Must state no auto-post"
