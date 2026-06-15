"""NAV-UX-02-S2-IMPL — Today's Summary dispatch route retirement contract tests."""

from __future__ import annotations

import inspect

import app as erp
from registry.nav_keys import (
    ALL_NAV_PAGE_KEYS,
    LEGACY_NAV_ALIASES,
    NAV_REPORTS,
    NAV_TODAY_SUMMARY,
    normalize_nav_key,
)
from tests.nav_ux_02_contract import KNOWN_HIDDEN, page_dispatch_from_main

IMPL_DOC = (
    __import__("pathlib").Path(__file__).resolve().parents[1]
    / "docs"
    / "NAV_UX_02_S2_IMPLEMENTATION.md"
)


def test_today_summary_not_in_page_dispatch():
    dispatch = page_dispatch_from_main()
    assert NAV_TODAY_SUMMARY not in dispatch


def test_today_summary_not_in_all_nav_page_keys():
    assert NAV_TODAY_SUMMARY not in ALL_NAV_PAGE_KEYS


def test_render_today_summary_still_exists():
    assert hasattr(erp, "render_today_summary")
    assert callable(erp.render_today_summary)


def test_reports_exec_today_summary_option_unchanged():
    src = inspect.getsource(erp.render_reports)
    assert '("today_summary", "reports.exec.today_summary")' in src
    assert 'exec_sel == "today_summary"' in src
    assert "render_today_summary(session)" in src


def test_legacy_aliases_repoint_to_reports():
    assert LEGACY_NAV_ALIASES["📅 Today's Summary"] == NAV_REPORTS
    assert LEGACY_NAV_ALIASES["Today's Summary"] == NAV_REPORTS


def test_normalize_legacy_today_summary_to_reports():
    assert normalize_nav_key("📅 Today's Summary") == NAV_REPORTS
    assert normalize_nav_key("Today's Summary") == NAV_REPORTS


def test_main_legacy_reroute_presets_reports_exec():
    main_src = inspect.getsource(erp.main)
    assert "_LEGACY_NAV_TO_REPORTS_EXEC" in main_src
    assert 'st.session_state["rpt_exec_sel"]' in main_src
    assert NAV_TODAY_SUMMARY in erp._LEGACY_NAV_TO_REPORTS_EXEC


def test_known_hidden_empty_after_retirement():
    assert KNOWN_HIDDEN == frozenset()


def test_no_orphan_dispatch_routes():
    dispatch = set(page_dispatch_from_main())
    from tests.nav_ux_02_contract import page_surface_map

    surfaces = page_surface_map()
    orphans = dispatch - set(surfaces.keys())
    assert orphans == set()


def test_implementation_doc_exists():
    assert IMPL_DOC.exists()
    text = IMPL_DOC.read_text(encoding="utf-8").lower()
    assert "implemented" in text
    assert "render_today_summary" in text
