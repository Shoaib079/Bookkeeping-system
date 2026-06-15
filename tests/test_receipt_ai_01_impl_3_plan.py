"""RECEIPT-AI-01-IMPL-3 — contract test for the review-UI / manual-extractor plan.

Doc-only guard: verifies the plan exists, recommends UI location A (Staff Expenses),
pins the exact workflow, the reused permission gates, the Cash-only payment handling
(Card/Unknown resolved at approval, never auto-posted/auto-settled), the feature flag,
tests, slices, and the no-change invariants. Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "RECEIPT_AI_01_IMPL_3_PLAN.md"
)

REQUIRED_SECTIONS = (
    "Recommended UI location",
    "Exact user workflow",
    "Permission model",
    "Payment method handling",
    "Feature flag",
    "Tests needed",
    "Implementation slices",
    "Risks",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"IMPL-3 plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"IMPL-3 plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "IMPL-3 plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_recommends_staff_expenses_page(doc_text):
    low = doc_text.lower()
    assert "staff expenses page" in low, "Must recommend the Staff Expenses page"
    assert "reject b" in low and "add transaction" in low, "Must reject Add Transaction (B)"
    assert "reject c" in low or "new receipt-ai page" in low, "Must reject a new page (C)"


def test_workflow_draft_first(doc_text):
    low = doc_text.lower()
    assert "create_expense_draft" in low, "Workflow must use create_expense_draft"
    assert 'status="draft"' in low or "status=draft" in low, "Draft created with status=draft"
    assert "add_draft_attachment" in low, "Workflow must attach via add_draft_attachment"
    assert "approve_expense_draft" in low, "Posting stays on the existing approve path"
    assert "no posting" in low or "no posting." in low, "Workflow must not post"


def test_permission_gates_reused(doc_text):
    low = doc_text.lower()
    for perm in ("upload_receipts", "submit_expense_drafts", "approve_expense_drafts"):
        assert perm in low, f"Permission model must reuse {perm}"
    assert "no new permission" in low, "No new permission introduced"


def test_payment_cash_only_handling(doc_text):
    low = doc_text.lower()
    assert "draft_payment_methods" in low, "Must note drafts accept Cash/Card/Unknown"
    assert "v1_payment_methods" in low, "Must note Cash-only posting default"
    assert "resolved" in low and "approval" in low, (
        "Card/Unknown must be resolved at approval"
    )
    assert "never" in low and "banktransaction" in low, (
        "Payment detection must never auto-create a bank transaction"
    )
    assert "never auto-post" in low or "never" in low and "auto-post" in low, (
        "Payment detection must never auto-post"
    )


def test_feature_flag_default_off(doc_text):
    low = doc_text.lower()
    assert "feature flag" in low or "module setting" in low, "Must hide behind a flag"
    assert "default" in low and "off" in low, "Flag default off"
    assert "get_setting" in low or "get_effective_config" in low, "Reuse the registry settings"


def test_tests_listed(doc_text):
    low = doc_text.lower()
    assert "no" in low and ("expenserecord" in low and "journalentry" in low), (
        "Tests must assert no ExpenseRecord/JournalEntry"
    )
    assert "create-if-missing" in low, "Tests must cover create-if-missing suggestion"
    assert "thin" in low, "Tests must assert thin UI / logic in services"


def test_slices_not_implemented(doc_text):
    low = doc_text.lower()
    assert "do not implement" in low, "Slices must be marked do-not-implement"
    for s in ("impl-3a", "impl-3b", "impl-3c"):
        assert s in low, f"Implementation slices must include {s}"


def test_no_change_statement(doc_text):
    low = doc_text.lower()
    assert "planning only" in low, "Plan must state planning only"
    assert "no ocr" in low, "Plan must state no OCR"
    assert "no auto-post" in low, "Plan must state no auto-post"
    assert "no new schema" in low, "Plan must state no new schema"
    assert "no direct" in low and "expenserecord" in low, "Plan must state no direct ExpenseRecord"
