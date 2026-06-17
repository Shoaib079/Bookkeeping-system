"""BANKING-UX-04 — contract test for the configurable banking workflow audit.

Doc-only guard: verifies the audit exists, carries the required outputs (architecture
assessment, setting location, slice plan, risk matrix, test plan, boundaries, wording,
recommendation), and pins the locked rules (UI-only, no posting/match_post/GL change,
company-scoped setting, manual always available, no schema change). Pure stdlib; no
app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "BANKING_UX_04_AUDIT.md"

REQUIRED_SECTIONS = (
    "Current architecture assessment",
    "Where the workflow-mode setting should live",
    "What must NOT change",
    "Minimal implementation slices",
    "Risk matrix",
    "Test plan",
    "UI wording",
    "Implementation boundaries",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"BANKING-UX-04 audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"BANKING-UX-04 audit doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "BANKING-UX-04 audit doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_recommendation_proceed(doc_text):
    low = doc_text.lower()
    assert "proceed" in low, "Must give a proceed/defer/revise recommendation"
    assert "ui-only" in low or "ui only" in low, "Recommendation rests on UI-only"


def test_architecture_anchored(doc_text):
    low = doc_text.lower()
    assert "render_banking" in low and "21080" in doc_text, "Must anchor render_banking"
    assert "_banking_section_select" in low, "Must cite the section picker"
    assert "_banking_reconciliation_on" in low and "_banking_pos_settlement_enabled" in low, (
        "Must cite the existing company-scoped setting precedent"
    )


def test_setting_location(doc_text):
    low = doc_text.lower()
    assert "banking.workflow_mode" in low, "Must name the setting"
    assert "registry/settings_catalog.py" in low, "Setting defined in settings_catalog"
    assert "company-scoped" in low, "Setting is company-scoped"
    assert "statement_first" in low and "hybrid" in low and "manual_first" in low, "Three modes"
    assert "default" in low and "statement_first" in low, "Default statement_first"
    assert "no schema change" in low, "No schema change needed"


def test_must_not_change(doc_text):
    low = doc_text.lower()
    assert "services/posting.py" in low, "Must protect posting service"
    assert "match_post" in low, "Must protect match_post"
    assert "gl line tuples" in low or "gl tuples" in low or "journal entries" in low, (
        "Must protect GL/journal entries"
    )
    assert "duplicate-post safeguard" in low, "Must protect the duplicate-post safeguard"


def test_manual_always_available(doc_text):
    low = doc_text.lower()
    assert "manual" in low and ("always" in low and "reachable" in low or "always available" in low), (
        "Manual entry must remain available in all modes"
    )
    assert "advanced" in low, "Manual hidden under Advanced in statement-first"


def test_slices(doc_text):
    low = doc_text.lower()
    for s in ("banking-ux-04-s1", "banking-ux-04-s2", "banking-ux-04-s3", "banking-ux-04-s4"):
        assert s in low, f"Slice plan must include {s}"


def test_risk_matrix(doc_text):
    low = doc_text.lower()
    assert "duplicate" in low and "posting" in low, "Risk: duplicate postings"
    assert "leakage" in low or "company isolation" in low, "Risk: multi-company leakage"
    assert "pos settlement vs" in low or "pos settlement" in low and "credit card" in low, (
        "Risk: POS settlement vs credit card"
    )
    assert "react" in low, "Risk: React migration impact"


def test_test_plan_posting_invariance(doc_text):
    low = doc_text.lower()
    assert "posting invariance" in low or "identical" in low and "journal" in low, (
        "Test plan must include posting invariance across modes"
    )
    assert "company a" in low and "company b" in low, "Test plan must include company isolation"


def test_wording_en_tr(doc_text):
    low = doc_text.lower()
    assert "how do you record bank activity" in low, "Plain-language chooser label"
    assert "banka" in low, "TR wording present"
    assert "jargon" in low, "Must avoid accounting jargon"


def test_no_change_statement(doc_text):
    low = doc_text.lower()
    assert "audit only" in low, "Must state audit-only"
    assert "no code changes" in low, "Must state no code changes"
    assert "no schema change" in low, "Must state no schema change"
