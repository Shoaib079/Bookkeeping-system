"""NAV-UX-02-S2 — contract test for the Today's Summary orphan-route decision plan.

Doc-only guard: verifies the plan exists, carries the required sections, records the
key correction (function still reachable via Reports exec), pins the recommendation
(D + optional B), the legacy-alias reroute, the risk level, the implementation slice,
the contract tests, and the suite-unchanged-except-nav statement. Pure stdlib; no app
imports; no DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "NAV_UX_02_S2_TODAY_SUMMARY_PLAN.md"
)

REQUIRED_SECTIONS = (
    "what it does",
    "How it differs from",
    "daily-use value",
    "Duplication assessment",
    "Options A",
    "Recommendation",
    "Legacy alias impact",
    "Risk level",
    "Proposed implementation slice",
    "Contract tests",
    "Suite impact",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"S2 plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"S2 plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "S2 plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_correction_function_still_reachable(doc_text):
    lowered = doc_text.lower()
    assert "render_today_summary" in lowered, "Plan must reference render_today_summary"
    assert "reports" in lowered and "reachable" in lowered, (
        "Plan must correct that the function is still reachable via Reports"
    )
    assert "22646" in doc_text or "rpt_exec_sel" in lowered, (
        "Plan must cite the Reports exec caller evidence"
    )


def test_compares_to_dashboard(doc_text):
    lowered = doc_text.lower()
    assert "render_dashboard" in lowered, "Plan must compare to render_dashboard"
    assert "trend" in lowered and "alert" in lowered, (
        "Plan must note dashboard trend/alert differences"
    )
    assert "export" in lowered, "Plan must note the unique exportable table"


def test_recommendation_d_plus_b(doc_text):
    lowered = doc_text.lower()
    assert "recommendation" in lowered, "Plan must give a recommendation"
    assert "d (primary)" in lowered or "d (retire" in lowered or "retire the" in lowered, (
        "Recommendation must be retire the dead route (D)"
    )
    assert "optional" in lowered and "b" in lowered, "Recommendation must include optional B link"


def test_legacy_alias_reroute(doc_text):
    lowered = doc_text.lower()
    assert "legacy_nav_aliases" in lowered or "legacy alias" in lowered, (
        "Plan must address the legacy alias"
    )
    assert "nav_reports" in lowered, "Alias must repoint to NAV_REPORTS"
    assert "fall back" in lowered or "fallback" in lowered or "falls back" in lowered, (
        "Plan must address the Home fallback behavior"
    )


def test_risk_low(doc_text):
    lowered = doc_text.lower()
    assert "risk level" in lowered and "low" in lowered, "Plan must state LOW risk"


def test_contract_tests_listed(doc_text):
    lowered = doc_text.lower()
    assert "normalize_nav_key" in lowered, "Contract tests must cover alias normalization"
    assert "_page_dispatch" in lowered, "Contract tests must cover dispatch retirement"
    assert "today_summary" in lowered, "Contract tests must keep the Reports exec option"


def test_suite_unchanged_except_nav(doc_text):
    lowered = doc_text.lower()
    assert "unchanged except" in lowered and "nav" in lowered, (
        "Plan must state suite unchanged except navigation tests"
    )


def test_no_change_statement(doc_text):
    lowered = doc_text.lower()
    assert "planning only" in lowered, "Plan must state planning only"
    assert "no route deleted" in lowered or "no route deletion" in lowered, (
        "Plan must state no route deleted"
    )
    assert "no role change" in lowered or "no role changed" in lowered, (
        "Plan must state no role change"
    )
    assert "no cleanup" in lowered, "Plan must state no cleanup"
