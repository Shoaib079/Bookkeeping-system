"""NAV-UX-02-S4 — contract test for the Members & Audit Log consistency plan.

Doc-only guard: verifies the plan exists, carries the required outputs (exposure map,
purpose classification, ownership model, role-gate recommendation, mobile/desktop
consistency, React contract, contract tests, slices, risk), and pins the decisions
(Members → Settings/Admin, People = records only, Members owner-only, Audit Log stays
manager-visible, React 1:1, no-change). Pure stdlib; no app imports.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "NAV_UX_02_S4_MEMBERS_AUDIT_CONSISTENCY_PLAN.md"
)

REQUIRED_SECTIONS = (
    "Current exposure map",
    "Purpose classification",
    "Recommended ownership model",
    "Role-gate recommendation",
    "Mobile / Desktop consistency recommendation",
    "React route contract",
    "Contract tests",
    "Implementation slices",
    "Risk assessment",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"S4 plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"S4 plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "S4 plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_exposure_map_inconsistencies(doc_text):
    lowered = doc_text.lower()
    assert "nav_members" in lowered and "nav_audit_log" in lowered, "Plan must reference both routes"
    assert "people hub" in lowered, "Plan must record Members in the mobile People hub"
    assert "owner + manager" in lowered or "owner+manager" in lowered, (
        "Plan must record Audit Log owner+manager gate"
    )
    assert "owner-only" in lowered, "Plan must record Members owner-only gate"


def test_purpose_classification(doc_text):
    lowered = doc_text.lower()
    assert "access administration" in lowered, "Members purpose = access administration"
    assert "read-only" in lowered and "oversight" in lowered, "Audit Log = read-only oversight"
    assert "business" in lowered and "records" in lowered, (
        "Plan must distinguish business people records from system users"
    )


def test_ownership_members_to_settings(doc_text):
    lowered = doc_text.lower()
    assert "members → settings" in lowered or "members → settings / administration" in lowered, (
        "Members must be owned by Settings/Admin"
    )
    assert "people hub = operational" in lowered or "operational people" in lowered, (
        "People hub must be operational records only"
    )


def test_role_gate_recommendation(doc_text):
    lowered = doc_text.lower()
    assert "keep owner-only" in lowered, "Members must stay owner-only"
    assert "keep manager-visible" in lowered or "remain manager-visible" in lowered, (
        "Audit Log must stay manager-visible"
    )


def test_mobile_desktop_consistency(doc_text):
    lowered = doc_text.lower()
    assert "match desktop" in lowered, "Mobile placement must match desktop ownership"
    assert "more → admin" in lowered or "more/admin" in lowered or "more → admin" in lowered, (
        "Members must move to More/Admin on mobile"
    )


def test_react_contract(doc_text):
    lowered = doc_text.lower()
    assert "/settings/members" in lowered, "React contract must place Members under /settings"
    assert "/settings/audit-log" in lowered, "React contract must place Audit Log under /settings"
    assert "no" in lowered and "/people/members" in lowered, (
        "Plan must state there is no /people/members route"
    )
    assert "1:1" in lowered, "React contract must be 1:1"


def test_contract_tests_listed(doc_text):
    lowered = doc_text.lower()
    assert "_nav_role_pages" in lowered, "Contract tests must cover role lists"
    assert "_mobile_hub_config" in lowered, "Contract tests must cover mobile hub config"
    assert "excludes" in lowered and "nav_members" in lowered, (
        "Contract tests must assert People hub excludes Members"
    )


def test_risk_low(doc_text):
    lowered = doc_text.lower()
    assert "risk assessment" in lowered and "low" in lowered, "Plan must state LOW risk"
    assert "relocation" in lowered, "Plan must note the mobile relocation as the only effect"


def test_no_change_statement(doc_text):
    lowered = doc_text.lower()
    assert "planning only" in lowered, "Plan must state planning only"
    assert "no route deleted" in lowered or "no route deletion" in lowered, (
        "Plan must state no route deleted"
    )
    assert "no role changed" in lowered or "no role change" in lowered, (
        "Plan must state no role change"
    )
    assert "no cleanup" in lowered, "Plan must state no cleanup"
