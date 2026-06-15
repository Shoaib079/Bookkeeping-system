"""NAV-UX-02-A — contract test for the sidebar/navigation audit plan.

Doc-only guard: verifies the audit plan exists, carries the required sections, and
pins the scope + rules (desktop sidebar, mobile nav, duplicate routes, settings
placement, role gates, page ownership, React route mapping, no runtime changes).
Pure stdlib; no app imports; no DB / runtime behavior involved.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "NAV_UX_02_A_NAVIGATION_AUDIT_PLAN.md"
)

REQUIRED_SECTIONS = (
    "Audit method",
    "Inventory table format",
    "Scope to audit",
    "Duplicate detection rules",
    "Role-gate review rules",
    "Mobile / desktop consistency rules",
    "Settings cleanup rules",
    "Future React route mapping rules",
    "No-change decision",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Navigation audit plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Navigation audit plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Navigation audit plan doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_desktop_sidebar(doc_text):
    assert "desktop sidebar" in doc_text.lower(), "Plan must cover the desktop sidebar"


def test_mobile_nav(doc_text):
    lowered = doc_text.lower()
    assert "mobile bottom nav" in lowered or "mobile nav" in lowered, (
        "Plan must cover the mobile bottom nav/hubs"
    )


def test_duplicate_routes(doc_text):
    lowered = doc_text.lower()
    assert "duplicate" in lowered and ("route" in lowered), (
        "Plan must cover duplicate page names/routes"
    )
    assert "duplicate functionality" in lowered, (
        "Plan must cover duplicate functionality across pages"
    )


def test_settings_placement(doc_text):
    lowered = doc_text.lower()
    assert "settings placement" in lowered, "Plan must cover settings placement"
    assert "settings cleanup" in lowered, "Plan must include settings cleanup rules"


def test_role_gates(doc_text):
    lowered = doc_text.lower()
    assert "role gate" in lowered, "Plan must cover role gates"
    assert "permission" in lowered, "Plan must cover permissions"


def test_page_ownership(doc_text):
    assert "page ownership" in doc_text.lower(), "Plan must cover page ownership"


def test_react_route_mapping(doc_text):
    lowered = doc_text.lower()
    assert "react route" in lowered, "Plan must cover future React route mapping"
    assert "route_key" in lowered and "react_route" in lowered, (
        "Plan must define a route_key -> react_route mapping"
    )


def test_inventory_columns(doc_text):
    lowered = doc_text.lower()
    for col in ("route_key", "render_fn", "surface", "role_gate", "owner_area", "classification"):
        assert col in lowered, f"Inventory format must include the {col} column"


def test_added_inventory_fields(doc_text):
    lowered = doc_text.lower()
    for col in (
        "control_type",
        "parent_surface",
        "opens_dialog",
        "navigates_to",
        "duplicate_workflow",
        "daily_use_impact",
    ):
        assert col in lowered, f"Inventory format must include the {col} field"


def test_all_navigation_surfaces_in_scope(doc_text):
    lowered = doc_text.lower()
    for surface in (
        "sidebar items",
        "sidebar section headers",
        "sidebar expanders",
        "dropdown / selectbox page pickers",
        "radio / tab navigation",
        "buttons that navigate or open dialogs",
        "quick-entry shortcuts",
        "inline `+` and `⚙` controls",
        "settings shortcuts inside transaction forms",
        "mobile bottom nav",
        "mobile hubs / cards",
        "hidden / admin / dev pages",
        "duplicate entry point to the same workflow",
    ):
        assert surface in lowered, f"Scope must include navigation surface: {surface!r}"


def test_control_type_assertions(doc_text):
    """Every required control kind must be covered by the audit scope."""
    lowered = doc_text.lower()
    assert "radio" in lowered, "Scope must cover toggles/radio navigation"
    assert "selectbox" in lowered or "dropdown" in lowered, "Scope must cover dropdown/selectbox pickers"
    assert "tab" in lowered, "Scope must cover tab navigation"
    assert "button" in lowered, "Scope must cover navigation buttons"
    assert "dialog" in lowered, "Scope must cover dialog-opening controls"
    assert "inline" in lowered and "⚙" in doc_text, "Scope must cover inline + and ⚙ controls"
    assert "quick-entry" in lowered, "Scope must cover quick-entry shortcuts"


def test_opens_dialog_field_documented(doc_text):
    lowered = doc_text.lower()
    assert "opens_dialog" in lowered and "dialog" in lowered, (
        "Plan must record whether a control opens a dialog vs navigates"
    )


def test_no_runtime_changes(doc_text):
    lowered = doc_text.lower()
    assert "no ui/runtime change" in lowered or "no runtime change" in lowered, (
        "Plan must state no UI/runtime change"
    )
    assert "no pages removed" in lowered, "Plan must state no pages removed"
    assert "no routes renamed" in lowered, "Plan must state no routes renamed"
    assert "no role gates changed" in lowered, "Plan must state no role gates changed"
    assert "untouched" in lowered, "Plan must state app.py navigation is untouched"
