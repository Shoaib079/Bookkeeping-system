"""P2-HARDEN-01-H03 — contract test for the systemic-stamp-hook audit.

Doc-only guard: verifies the audit exists, carries the required outputs (recommendation,
evidence, risk analysis, conditional contract tests, roadmap recommendation), and pins
the decision (defer + reject auto-stamp; keep explicit stamping; hook would hide bugs;
fail-loud only, at FastAPI cutover). Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P2_HARDEN_01_H03_AUDIT.md"

REQUIRED_SECTIONS = (
    "Recommendation",
    "Evidence",
    "Risk analysis",
    "Answers to the questions",
    "Contract tests",
    "Roadmap update recommendation",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"H03 audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"H03 audit doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "H03 audit doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_recommendation_defer_reject_autostamp(doc_text):
    low = doc_text.lower()
    assert "defer" in low, "Recommendation must be DEFER"
    assert "reject" in low and "auto-stamp" in low, "Must reject the silent auto-stamp form"
    assert "explicit" in low and "standard" in low, "Explicit stamping stays the standard"


def test_evidence_no_contextvar_no_listener(doc_text):
    low = doc_text.lower()
    assert "requestcontext" in low and "no contextvar" in low or (
        "no contextvar" in low
    ), "Evidence must state RequestContext has no contextvar"
    assert "get_db" in low, "Evidence must cite get_db"
    assert "no before_flush" in low or "no listener" in low or "clean session" in low, (
        "Evidence must state the API session has no before_flush"
    )
    assert "explicit" in low and "company_id" in low, "Evidence: services stamp explicitly"
    assert "_stamp_company_on_movement" in low, "Evidence must cite the H01a tactical stamp"


def test_hook_would_hide_bugs(doc_text):
    low = doc_text.lower()
    assert "hide" in low and "bug" in low, "Risk: hook hides missing-stamp bugs"
    assert "ambient" in low, "Risk: reintroduces ambient state"
    assert "leak" in low or "leakage" in low, "Risk: cross-request contextvar leakage"


def test_fail_loud_not_silent(doc_text):
    low = doc_text.lower()
    assert "fail-loud" in low, "Any net must be fail-loud"
    assert "raise" in low, "Guard must raise, not auto-fill"
    assert "not" in low and "silent" in low, "Must contrast fail-loud vs silent auto-fill"


def test_conditional_contract_tests(doc_text):
    low = doc_text.lower()
    assert "no clobber" in low or "never override" in low, "Must include no-clobber test"
    assert "isolation" in low and "reset per request" in low, "ContextVar isolation/reset test"
    assert "parity" in low, "Parity with H01 matrix + fastapi_p2 suites"


def test_defer_to_fastapi_cutover(doc_text):
    low = doc_text.lower()
    assert "fastapi runtime cutover" in low or "runtime cutover" in low, (
        "Must defer any net to the FastAPI runtime cutover"
    )


def test_roadmap_recommendation(doc_text):
    low = doc_text.lower()
    assert "p2-harden-01-h03" in low and "deferred" in low, "Roadmap: H03 deferred"
    assert "explicit service-layer" in low and "standard" in low, "Roadmap states the standard"


def test_no_change_statement(doc_text):
    low = doc_text.lower()
    assert "audit only" in low, "Must state audit-only"
    assert "no production code" in low, "Must state no production code"
    assert "no hook" in low, "Must state no hook implementation"
    assert "no schema change" in low, "Must state no schema change"
