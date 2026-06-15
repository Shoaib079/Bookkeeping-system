"""NAV-UX-02-S3 — contract test for the financial-statements consolidation plan.

Doc-only guard: verifies the plan exists, carries the required outputs (exposure map,
canonical ownership, shortcut model, migration path, contract tests, slices, risk),
records the Reports-page correction, the canonical routes, all-roles preservation,
the React 1:1 contract, and the no-change invariants. Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "NAV_UX_02_S3_STATEMENTS_CONSOLIDATION_PLAN.md"
)

REQUIRED_SECTIONS = (
    "Current exposure map",
    "Proposed canonical ownership",
    "Shortcut model",
    "Migration path",
    "React route contract",
    "Mobile behavior",
    "Role implications",
    "Contract tests",
    "Implementation slices",
    "Risk assessment",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"S3 plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"S3 plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "S3 plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_reports_page_correction(doc_text):
    lowered = doc_text.lower()
    assert "reports page does not render" in lowered or "does not render the statements" in lowered, (
        "Plan must correct that the Reports page does not render statements"
    )
    assert "exec" in lowered and "sales" in lowered and "eod" in lowered, (
        "Plan must cite the actual Reports tabs"
    )


def test_canonical_routes(doc_text):
    lowered = doc_text.lower()
    for key in ("nav_profit_loss", "nav_balance_sheet", "nav_cash_flow"):
        assert key in lowered, f"Plan must reference canonical route {key}"
    assert "render_profit_loss_page" in lowered, "Plan must cite the page wrapper"
    assert "core renderer" in lowered or "render_profit_loss" in lowered, (
        "Plan must cite the single render path"
    )


def test_three_doors(doc_text):
    lowered = doc_text.lower()
    assert "accordion" in lowered and "financial statements" in lowered, "Door 1: desktop accordion"
    assert "mobile reports hub" in lowered, "Door 2: mobile reports hub"
    assert "_legacy_rpt_exec_to_statement" in lowered, "Door 3: legacy reroute"


def test_shortcut_model(doc_text):
    lowered = doc_text.lower()
    assert "shortcut" in lowered, "Plan must define a shortcut model"
    assert "never" in lowered and "render" in lowered, (
        "Shortcuts must never render a statement themselves"
    )


def test_react_contract_1to1(doc_text):
    lowered = doc_text.lower()
    assert "/reports/profit-loss" in lowered, "React contract must include /reports/profit-loss"
    assert "/reports/balance-sheet" in lowered, "React contract must include /reports/balance-sheet"
    assert "/reports/cash-flow" in lowered, "React contract must include /reports/cash-flow"
    assert "1:1" in lowered, "React contract must be 1:1"


def test_role_implications_none(doc_text):
    lowered = doc_text.lower()
    assert "role implications" in lowered, "Plan must address role implications"
    assert "all five roles" in lowered or "all-roles" in lowered, (
        "Plan must preserve all-roles visibility"
    )


def test_contract_tests_listed(doc_text):
    lowered = doc_text.lower()
    assert "_page_dispatch" in lowered, "Contract tests must cover dispatch presence"
    assert "_nav_role_pages" in lowered, "Contract tests must cover role visibility"
    assert "not a reports tab" in lowered or "not include p&l" in lowered or "regression guard" in lowered, (
        "Contract tests must guard against a duplicate Reports tab"
    )


def test_legacy_retirement_deferred(doc_text):
    lowered = doc_text.lower()
    assert "telemetry" in lowered, "Legacy reroute retirement must be telemetry-gated"
    assert "not now" in lowered or "deferred" in lowered or "later" in lowered, (
        "Legacy retirement must be deferred"
    )


def test_risk_low(doc_text):
    lowered = doc_text.lower()
    assert "risk assessment" in lowered and "low" in lowered, "Plan must state LOW risk"


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
