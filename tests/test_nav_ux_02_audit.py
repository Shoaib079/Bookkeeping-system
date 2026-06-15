"""NAV-UX-02 — contract test for the sidebar & navigation audit.

Doc-only guard for the audit deliverable: verifies the audit exists, carries all six
required outputs (plan, inventory, duplicate report, ownership map, test
recommendations, implementation slices), records the key findings, and pins the
audit-only no-change invariants. Pure stdlib; no app imports; no DB / runtime.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "NAV_UX_02_AUDIT.md"

REQUIRED_SECTIONS = (
    "Audit plan",
    "Navigation inventory",
    "Duplicate workflow report",
    "Proposed ownership map",
    "Contract-test recommendations",
    "Implementation slices",
)

INVENTORY_FIELDS = (
    "route_key",
    "render_fn",
    "surface",
    "role_gate",
    "owner_area",
    "control_type",
    "parent_surface",
    "opens_dialog",
    "navigates_to",
    "duplicate_workflow",
    "daily_use_impact",
    "react_route",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Navigation audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists(), f"Navigation audit doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0, "Navigation audit doc is empty"


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


@pytest.mark.parametrize("field", INVENTORY_FIELDS)
def test_inventory_fields_present(doc_text, field):
    assert field in doc_text.lower(), f"Inventory must capture {field}"


def test_covers_navigation_surfaces(doc_text):
    lowered = doc_text.lower()
    for surface in (
        "desktop sidebar",
        "mobile bottom nav",
        "mobile hub",
        "accordion",
        "header",
        "dialog",
        "tabs",
        "picker",
        "hidden",
    ):
        assert surface in lowered, f"Audit must cover surface: {surface!r}"


def test_dispatch_source_referenced(doc_text):
    lowered = doc_text.lower()
    assert "_page_dispatch" in lowered, "Audit must cite _PAGE_DISPATCH"
    assert "_nav_accordion" in lowered, "Audit must cite _NAV_ACCORDION"
    assert "_mobile_bottom_nav" in lowered, "Audit must cite _MOBILE_BOTTOM_NAV"
    assert "_nav_role_pages" in lowered, "Audit must cite _NAV_ROLE_PAGES"


def test_records_key_findings(doc_text):
    lowered = doc_text.lower()
    assert "today's summary" in lowered and "orphan" in lowered, (
        "Audit must record the Today's Summary orphan route"
    )
    assert "staff expenses" in lowered, "Audit must record Staff Expenses"
    assert "permission" in lowered or "submit_expense_drafts" in lowered, (
        "Audit must record Staff Expenses permission-derived nav (S5)"
    )
    assert "statements" in lowered and "canonical" in lowered, (
        "Audit must classify statements as canonical routes"
    )
    assert "shortcut" in lowered, "Audit must document statement shortcut doors"


def test_duplicate_workflow_clusters(doc_text):
    lowered = doc_text.lower()
    assert "duplicate_workflow" in lowered, "Audit must use the duplicate_workflow field"
    for wf in ("banking", "txn_ledger", "new_txn"):
        assert wf in lowered, f"Duplicate report must include the {wf} cluster"


def test_statements_not_classified_as_duplicate_render(doc_text):
    lowered = doc_text.lower()
    assert "does not render statements" in lowered or "does not render" in lowered, (
        "Audit must state Reports page does not render statements"
    )
    assert "shortcut" in lowered and "canonical" in lowered, (
        "Audit must classify statements as canonical + shortcut doors"
    )


def test_implementation_slices_not_implemented(doc_text):
    lowered = doc_text.lower()
    assert "do not implement" in lowered, "Slices must be marked do-not-implement"
    for slice_id in ("nav-ux-02-s1", "nav-ux-02-s3", "nav-ux-02-s4", "nav-ux-02-s5", "nav-ux-02-s7"):
        assert slice_id in lowered, f"Implementation slices must include {slice_id}"


def test_no_change_statement(doc_text):
    lowered = doc_text.lower()
    assert "audit only" in lowered, "Audit must state audit-only"
    assert "no route renamed" in lowered or "no route renaming" in lowered, (
        "Audit must state no route renamed"
    )
    assert "no page deleted" in lowered or "no deletion" in lowered, (
        "Audit must state no page deleted"
    )
    assert "no role gate changed" in lowered or "no role gates changed" in lowered, (
        "Audit must state no role gate changed"
    )
    assert "no cleanup" in lowered, "Audit must state no cleanup performed"
