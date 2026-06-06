"""Phase A — shell stabilization contract tests (header, breakpoints, hubs, reports)."""
from __future__ import annotations

import re
from pathlib import Path

import app as erp
from ui.shell import SHELL_DESKTOP_MIN_PX, SHELL_MOBILE_MAX_PX

ROOT = Path(__file__).resolve().parents[1]


def _css_blob() -> str:
    parts = (
        ROOT / "ui" / "theme.css",
        ROOT / "ui" / "widgets.css",
        ROOT / "ui" / "mobile_shell.css",
    )
    return "\n".join(p.read_text(encoding="utf-8") for p in parts)


def test_shell_breakpoint_constants():
    assert SHELL_MOBILE_MAX_PX == 968
    assert SHELL_DESKTOP_MIN_PX == 969


def test_header_fixed_on_shell_row_not_orphan_marker():
    css = _css_blob()
    assert '[class*="st-key-hdr_shell_row"]' in css
    assert "position: fixed" in css
    shell_fixed = re.search(
        r'\[class\*="st-key-hdr_shell_row"\]\s*\{[^}]*position:\s*fixed',
        css,
        re.S,
    )
    assert shell_fixed, "hdr_shell_row must be position:fixed"
    orphan = re.search(
        r'div\[data-testid="stHorizontalBlock"\]:has\(\.erp-hdr-appname\)\s*\{[^}]*position:\s*fixed',
        css,
    )
    assert not orphan, "legacy orphan-marker fixed rule must be removed"


def test_no_tablet_nav_dead_zone_in_widgets_css():
    css = (ROOT / "ui" / "widgets.css").read_text(encoding="utf-8")
    assert "@media (min-width: 969px)" in css
    assert 'min-width: 769px' not in css
    hide_block = css.split("@media (min-width: 969px)", 1)[1].split("}", 1)[0]
    assert "erp-mobile-chrome-active" in hide_block


def test_sidebar_desktop_breakpoint_matches_shell():
    css = (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")
    assert "@media (min-width: 969px)" in css
    assert 'Sidebar — desktop (>=969px)' in css or "min-width: 969px" in css
    assert 'min-width: 769px' not in css


def test_single_toolbar_in_right_column():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'slot="desktop_right"' in src
    assert 'slot="primary"' not in src
    assert "hdr_mob_toolbar_slot" not in src
    css = (ROOT / "ui" / "mobile_shell.css").read_text(encoding="utf-8")
    mobile = css.split("@media (max-width: 968px)", 1)[1].split("@media", 1)[0]
    assert "st-key-hdr_toolbar_row" in mobile
    assert "st-key-hdr_desktop_brand" in mobile
    assert "nth-child(1)" in mobile or "first-child" in mobile


def test_desktop_uses_pre_mobile_sidebar_flow():
    css = (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")
    desktop = css.split("@media (min-width: 969px)", 1)[1].split("@media", 1)[0]
    assert "margin-left: var(--erp-sidebar-w)" not in desktop
    sidebar = desktop.split('[data-testid="stSidebar"]', 1)[1].split("}", 1)[0]
    assert "top: var(--hdr-h)" in sidebar
    assert "position: fixed" not in sidebar


def test_desktop_header_matches_pre_mobile_contract():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "st.columns([2.8, 5.4, 2.8]" in src
    assert "_tb_key = \"hdr_toolbar_row\"" in src
    assert 'key="hdr_dark_toggle"' in src
    theme = (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")
    assert "z-index: 9999" in theme


def test_search_open_expands_header_height():
    css = (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")
    assert ":has(.erp-hdr-shell-search-open)" in css
    assert "--hdr-h: 104px" in css
    assert '[class*="st-key-hdr_shell_row"]:has(.erp-hdr-shell-search-open)' in css


def test_people_hub_wired_not_duplicated_in_more():
    more = erp._MOBILE_HUB_CONFIG["more"]
    kinds = [k for k, *_ in more]
    assert "open_hub" in kinds
    assert kinds.count("open_hub") == 1
    assert ("open_hub", "people", None, "nav.mobile.hub.people") in more
    assert not any(k == "page" and p == "👥 Customers" for k, p, *_ in more)
    assert "people" in erp._MOBILE_HUB_KEYS


def test_reports_tab_scope_helpers_exist():
    assert hasattr(erp, "_reports_tab_scope")
    assert hasattr(erp, "_render_mobile_reports_tab_bar")
    assert ("sales", "reports.tab.sales") in erp._REPORTS_MOB_TAB_IDS


def test_render_top_header_marker_inside_shell_row():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    idx = src.index('def render_top_header(')
    chunk = src[idx : idx + 2500]
    assert 'with st.container(key="hdr_shell_row"):' in chunk
    assert chunk.index('hdr_shell_row') < chunk.index("erp-hdr-appname")


def test_mobile_hub_open_hub_visibility():
    allowed = {"🏠 Home", "👥 Customers", "🏢 Vendors", "👤 Members"}
    assert erp._mobile_hub_entry_visible(
        "more", "open_hub", "people", allowed, erp._NAV_ACCORDION_BY_KEY
    )
