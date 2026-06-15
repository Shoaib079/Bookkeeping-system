"""NAV-UX-02-S5 — contract test for the Staff Expenses role-gate review plan.

Doc-only guard: verifies the plan exists, carries the required outputs (exposure map,
workflow analysis, role recommendation, future permission model, React/API contract,
contract tests, slices, risk), and pins the findings (nav owner-only vs page
permission-gated, approval is the posting boundary, not payroll, classification B+D).
Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "NAV_UX_02_S5_STAFF_EXPENSES_ROLE_PLAN.md"
)

REQUIRED_SECTIONS = (
    "Exposure map",
    "Workflow analysis",
    "Role recommendation",
    "Future FastAPI permission model",
    "React / API contract",
    "Contract tests",
    "Implementation slices",
    "Risk assessment",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"S5 plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"S5 plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "S5 plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_gate_mismatch_finding(doc_text):
    lowered = doc_text.lower()
    assert "owner-only" in lowered, "Plan must record the owner-only nav gate"
    assert "submit_expense_drafts" in lowered and "approve_expense_drafts" in lowered, (
        "Plan must cite the page's granular permissions"
    )
    assert "mismatch" in lowered, "Plan must identify the gate mismatch"


def test_workflow_draft_submit_approve(doc_text):
    lowered = doc_text.lower()
    assert "draft" in lowered and "submit" in lowered and "approve" in lowered, (
        "Plan must describe the draft → submit → approve workflow"
    )
    assert "only on approval" in lowered or "approval is the only" in lowered or "posting boundary" in lowered, (
        "Plan must state only approval posts to the GL"
    )
    assert "post_fn" in lowered or "_staff_capture_post_expense_draft" in lowered, (
        "Plan must cite the approval post_fn"
    )


def test_not_payroll(doc_text):
    lowered = doc_text.lower()
    assert "not" in lowered and "payroll" in lowered, "Plan must clarify this is not payroll"
    assert "workers" in lowered, "Plan must point salaries/advances to Workers"


def test_classification_b_d(doc_text):
    lowered = doc_text.lower()
    assert "b + d" in lowered or "b — needs wider" in lowered, (
        "Plan must classify as B (wider access)"
    )
    assert "permission-derived" in lowered or "derive from permission" in lowered or "derive from permissions" in lowered, (
        "Plan must recommend permission-derived nav visibility (D)"
    )


def test_permission_model(doc_text):
    lowered = doc_text.lower()
    assert "upload_receipts" in lowered, "Permission model must include upload_receipts"
    assert "has(submit_expense_drafts) or has(approve_expense_drafts)" in lowered or (
        "submit_expense_drafts" in lowered and "approve_expense_drafts" in lowered
    ), "Nav visibility must be permission-derived"


def test_react_api_contract(doc_text):
    lowered = doc_text.lower()
    assert "/expenses/staff-capture" in lowered, "Route must be /expenses/staff-capture"
    assert "expense-drafts" in lowered, "API contract must include the expense-drafts endpoints"
    assert "approve" in lowered and "posting endpoint" in lowered or "posts to gl" in lowered, (
        "Approve must be the posting endpoint"
    )


def test_default_mapping_verification(doc_text):
    lowered = doc_text.lower()
    assert "default role→permission" in lowered or "default role" in lowered and "mapping" in lowered, (
        "Plan must require verifying the default role->permission mapping"
    )


def test_risk_low_moderate(doc_text):
    lowered = doc_text.lower()
    assert "risk assessment" in lowered, "Plan must have a risk assessment"
    assert "low" in lowered and "moderate" in lowered, "Risk must be LOW-MODERATE"
    assert "grants no" in lowered or "no new capability" in lowered, (
        "Plan must note nav widening grants no new capability"
    )


def test_no_change_statement(doc_text):
    lowered = doc_text.lower()
    assert "planning only" in lowered, "Plan must state planning only"
    assert "no role change" in lowered or "no role changed" in lowered, (
        "Plan must state no role change"
    )
    assert "no route deleted" in lowered or "no route deletion" in lowered, (
        "Plan must state no route deleted"
    )
    assert "no cleanup" in lowered, "Plan must state no cleanup"
