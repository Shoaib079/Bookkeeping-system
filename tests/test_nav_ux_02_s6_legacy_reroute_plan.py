"""NAV-UX-02-S6 — contract test for the legacy navigation reroute/alias plan.

Doc-only guard: verifies the plan exists, carries the required outputs (inventory,
behavior map, A–E classification, retirement recommendation, telemetry, contract
tests, slices, risk), enumerates every legacy mechanism, and pins the no-change
invariants. Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "NAV_UX_02_S6_LEGACY_REROUTE_PLAN.md"
)

REQUIRED_SECTIONS = (
    "Legacy alias inventory",
    "Reroute behavior map",
    "Risk classification",
    "Retirement recommendation",
    "Telemetry / logging recommendation",
    "Contract tests",
    "Implementation slices",
    "Risk assessment",
)

LEGACY_TARGETS = (
    "legacy_nav_aliases",
    "_legacy_rpt_exec_to_statement",
    "_legacy_rpt_exec_to_books",
    "_legacy_nav_to_reports_exec",
    "bank statement import",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"S6 plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"S6 plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "S6 plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


@pytest.mark.parametrize("target", LEGACY_TARGETS)
def test_all_legacy_mechanisms_inventoried(doc_text, target):
    assert target in doc_text.lower(), f"Inventory must include legacy mechanism: {target}"


def test_abcde_classification(doc_text):
    lowered = doc_text.lower()
    assert "keep until react migration" in lowered, "Must use class B (keep until React)"
    assert "telemetry-gated retirement" in lowered, "Must use class C (telemetry-gated)"
    assert "keep permanently" in lowered, "Must use class A (keep permanently) for the fallback"
    assert "safe to retire now" in lowered, "Must address class D"
    assert "compatibility shim" in lowered, "Must address class E"


def test_no_item_safe_now(doc_text):
    lowered = doc_text.lower()
    assert "no item is class d" in lowered or "none is provably unused" in lowered, (
        "Plan must state nothing is safe to retire now"
    )


def test_fallback_safety_net(doc_text):
    lowered = doc_text.lower()
    assert "normalize_nav_key" in lowered and "nav_home" in lowered, (
        "Plan must cite the normalize_nav_key -> NAV_HOME safety net"
    )


def test_telemetry_recommendation(doc_text):
    lowered = doc_text.lower()
    assert "nav.legacy" in lowered, "Telemetry must use a dedicated logger"
    assert "no behavior change" in lowered or "behavior-neutral" in lowered, (
        "Telemetry must be behavior-neutral"
    )
    assert "zero" in lowered and "hit" in lowered, "Retirement gated on zero hits"


def test_section_preserving_reroute(doc_text):
    lowered = doc_text.lower()
    assert "banking_section" in lowered and "import" in lowered, (
        "Plan must note the Bank Statement Import section-preserving reroute"
    )


def test_contract_tests_listed(doc_text):
    lowered = doc_text.lower()
    assert "all_nav_page_keys" in lowered, "Contract tests must assert alias targets are valid keys"
    assert "_page_dispatch" in lowered, "Contract tests must assert reroute targets are dispatchable"
    assert "idempoten" in lowered, "Contract tests must assert idempotency"


def test_risk_low(doc_text):
    lowered = doc_text.lower()
    assert "risk assessment" in lowered and "low" in lowered, "Plan must state LOW risk"


def test_no_change_statement(doc_text):
    lowered = doc_text.lower()
    assert "planning only" in lowered, "Plan must state planning only"
    assert "no route deleted" in lowered or "no route deletion" in lowered, (
        "Plan must state no route deleted"
    )
    assert "no alias deleted" in lowered or "no alias deletion" in lowered, (
        "Plan must state no alias deleted"
    )
    assert "no cleanup" in lowered, "Plan must state no cleanup"
