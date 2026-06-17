"""NAV-ARCH-S1 — navigation audit doc + live parity guardrails.

Audit-only slice: no runtime navigation behavior change. Extends NAV-UX-02-S1
contract tests with NAV-ARCH guardrails and verifies docs/NAV_ARCH_AUDIT.md.
"""

from __future__ import annotations

import inspect
from collections import Counter
from pathlib import Path

import pytest

import app as erp
from registry.nav_keys import ALL_NAV_PAGE_KEYS, LEGACY_NAV_ALIASES
from tests.nav_ux_02_contract import (
    KNOWN_HIDDEN,
    accordion_page_keys,
    handler_has_meaningful_body,
    mobile_bottom_hub_targets,
    mobile_hub_page_keys_flat,
    page_dispatch_from_main,
    page_surface_map,
    resolve_dispatch_handler,
)

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "NAV_ARCH_AUDIT.md"
APP_PATH = Path(__file__).resolve().parents[1] / "app.py"

REQUIRED_SECTIONS = (
    "Navigation inventory",
    "Duplicate labels",
    "Duplicate destinations / routes",
    "Dead / orphan pages",
    "Risk areas",
    "Recommended single source of truth",
    "Safe cleanup plan",
)


def _app_line(marker: str) -> int:
    for i, line in enumerate(APP_PATH.read_text(encoding="utf-8").splitlines(), 1):
        if marker in line:
            return i
    raise AssertionError(f"Marker not found in app.py: {marker!r}")


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"NAV-ARCH audit doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


# ── Doc contract (NAV-ARCH audit artifact) ────────────────────────────────────


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_inventory_mechanisms_with_line_numbers(doc_text):
    low = doc_text.lower()
    assert "_page_dispatch" in low
    assert "_render_navigation_tree" in low
    assert "_nav_accordion" in low
    assert "_mobile_bottom_nav" in low
    assert "registry/nav_keys.py" in low
    # Live line anchors must match current app.py (S1 refresh).
    assert str(_app_line("_PAGE_DISPATCH = build_page_dispatch(")) in doc_text
    assert str(_app_line("def _render_navigation_tree(")) in doc_text
    assert str(_app_line("_NAV_ACCORDION = build_nav_accordion()")) in doc_text
    assert str(_app_line("_MOBILE_BOTTOM_NAV = (")) in doc_text


def test_no_option_menu(doc_text):
    low = doc_text.lower()
    assert "option_menu" in low and "not used" in low
    assert "st.sidebar" in low


def test_orphan_resolved(doc_text):
    low = doc_text.lower()
    assert "today's summary" in low and "retired" in low
    assert "no remaining dispatch orphan" in low
    assert "no dead" in low and "render_" in low


def test_settings_inside_settings_checked(doc_text):
    low = doc_text.lower()
    assert "settings inside settings" in low
    assert "not a nested-settings recursion" in low or "distinct admin pages" in low


def test_risk_seven_structures(doc_text):
    low = doc_text.lower()
    assert "seven" in low and "sync" in low
    assert "drift" in low
    assert "no" in low and "business logic" in low and "navigation" in low


def test_single_source_recommendation(doc_text):
    low = doc_text.lower()
    assert "registry/navigation.py" in low
    assert "derive" in low and "_page_dispatch" in low
    assert "react_route" in low


def test_s2_registry_exists():
    """NAV-ARCH-S2: registry/navigation.py is the dispatch SSOT."""
    root = Path(__file__).resolve().parents[1]
    assert (root / "registry" / "navigation.py").exists()


def test_avoid_duplicate_fixes_link(doc_text):
    low = doc_text.lower()
    assert "nav-ux-02" in low
    assert "duplicate" in low


def test_cleanup_plan_slices(doc_text):
    low = doc_text.lower()
    for s in (
        "nav-arch-s1",
        "nav-arch-s2",
        "nav-arch-s3a",
        "nav-arch-s3b",
        "nav-arch-s3c",
        "nav-arch-s4",
    ):
        assert s in low, f"Cleanup plan must include {s}"
    assert "parity test" in low


def test_roadmap_separate(doc_text):
    assert "roadmap suggestions" in doc_text.lower()


def test_s1_completion_recorded(doc_text):
    low = doc_text.lower()
    assert "nav-arch-s1" in low
    assert "complete" in low or "guardrails" in low


def test_dispatch_keys_unique():
    dispatch = page_dispatch_from_main()
    assert len(dispatch) == len(set(dispatch))


def test_every_dispatch_key_in_all_nav_page_keys():
    dispatch = page_dispatch_from_main()
    missing = set(dispatch) - ALL_NAV_PAGE_KEYS
    assert not missing, f"_PAGE_DISPATCH keys missing from ALL_NAV_PAGE_KEYS: {missing}"


def test_every_dispatch_handler_callable_and_non_stub():
    dispatch = page_dispatch_from_main()
    failures: list[str] = []
    for page_key, handler_name in dispatch.items():
        fn = resolve_dispatch_handler(handler_name)
        if not callable(fn):
            failures.append(f"{page_key}: {handler_name} not callable")
        elif not handler_has_meaningful_body(fn):
            failures.append(f"{page_key}: {handler_name} empty stub")
    assert not failures, failures


def test_non_hidden_dispatch_reachable_or_known_hidden():
    dispatch = set(page_dispatch_from_main())
    surfaces = page_surface_map()
    unreachable = [
        k for k in dispatch if k not in KNOWN_HIDDEN and k not in surfaces
    ]
    assert not unreachable, f"Unreachable routes (not KNOWN_HIDDEN): {unreachable}"


def test_orphans_match_known_hidden_only():
    dispatch = set(page_dispatch_from_main())
    surfaces = set(page_surface_map())
    orphans = dispatch - surfaces
    assert orphans == KNOWN_HIDDEN


def test_direct_pages_valid_in_dispatch():
    dispatch = set(page_dispatch_from_main())
    missing = [k for k in erp._NAV_DIRECT_PAGES if k not in dispatch]
    assert not missing, f"_NAV_DIRECT_PAGES missing from dispatch: {missing}"


def test_role_pages_valid_in_dispatch():
    dispatch = set(page_dispatch_from_main())
    missing: list[str] = []
    for role, pages in erp._NAV_ROLE_PAGES.items():
        for page_key in pages:
            if page_key not in dispatch:
                missing.append(f"{role}:{page_key}")
    assert not missing, f"_NAV_ROLE_PAGES keys missing from dispatch: {missing}"


def test_accordion_keys_valid_in_dispatch():
    dispatch = set(page_dispatch_from_main())
    missing = [
        f"{group}:{page_key}"
        for group, page_key in accordion_page_keys()
        if page_key not in dispatch
    ]
    assert not missing, f"Accordion keys missing from dispatch: {missing}"


def test_mobile_hub_page_keys_valid_in_dispatch():
    dispatch = set(page_dispatch_from_main())
    missing = [k for k in mobile_hub_page_keys_flat() if k not in dispatch]
    assert not missing, f"Mobile hub page keys missing from dispatch: {missing}"


def test_mobile_bottom_nav_exactly_five_slots():
    assert len(erp._MOBILE_BOTTOM_NAV) == 5


def test_mobile_bottom_hub_targets_in_hub_config():
    config_keys = set(erp._MOBILE_HUB_CONFIG)
    missing = [h for h in mobile_bottom_hub_targets() if h not in config_keys]
    assert not missing, f"Bottom hub targets missing from _MOBILE_HUB_CONFIG: {missing}"


def test_legacy_aliases_explicit_and_valid():
    assert LEGACY_NAV_ALIASES, "LEGACY_NAV_ALIASES must be explicit"
    dispatch = set(page_dispatch_from_main())
    bad_targets = {
        alias: target
        for alias, target in LEGACY_NAV_ALIASES.items()
        if target not in ALL_NAV_PAGE_KEYS
    }
    assert not bad_targets, f"Invalid alias targets: {bad_targets}"
    missing_dispatch = {
        alias: target
        for alias, target in LEGACY_NAV_ALIASES.items()
        if target not in dispatch
    }
    assert not missing_dispatch, f"Alias targets missing from dispatch: {missing_dispatch}"


def test_no_duplicate_nav_display_labels_within_dispatch():
    """Sidebar labels for distinct routes must not collide within dispatch set."""
    dispatch = page_dispatch_from_main()
    labels = Counter(erp._nav_display(k) for k in dispatch)
    dupes = {lbl: cnt for lbl, cnt in labels.items() if cnt > 1}
    assert not dupes, f"Duplicate nav display labels in dispatch: {dupes}"


def test_no_show_calendar_or_hybrid_nav_registry():
    """NAV-ARCH: no calendar hybrid in nav render tree."""
    root = Path(__file__).resolve().parents[1]
    assert (root / "registry" / "navigation.py").exists()
    nav_src = inspect.getsource(erp._render_navigation_tree)
    for banned in ("show_calendar", "reconcile_text_and_calendar"):
        assert banned not in nav_src


# ── NAV-ARCH-S1 live parity guardrails ────────────────────────────────────────
