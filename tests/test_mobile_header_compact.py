"""Mobile header compact pass — header + auth screens only."""

from __future__ import annotations

import inspect
from pathlib import Path

import app as erp
from ui import theme

ROOT = Path(__file__).resolve().parents[1]


def test_mobile_header_css_loaded():
    """MOBILE-14: mobile_header.css is inlined after mobile_shell.css in load_theme_css()."""
    css = theme.load_theme_css()
    mobile_shell_marker = "/* Mobile shell — html.erp-mobile"
    mobile_header_marker = "/* Mobile header compact pass"
    mobile_txn_marker = "/* Mobile New Transaction — bottom entry panel"
    assert mobile_header_marker in css
    assert css.index(mobile_shell_marker) < css.index(mobile_header_marker) < css.index(mobile_txn_marker)
    assert ".erp-auth-banner" in css
    assert "--hdr-h: 56px" in css
    assert "erp-hdr-co-pill" in css


def test_login_and_picker_use_compact_auth_banner():
    login = inspect.getsource(erp.render_login)
    picker = inspect.getsource(erp.render_company_picker)
    for src in (login, picker):
        assert "erp-auth-banner" in src
        assert "erp-auth-top-spacer" in src
        assert "height:40px" not in src
        assert "padding:24px 32px" not in src


def test_mobile_toolbar_uses_icon_profile_and_standalone_bell():
    src = inspect.getsource(erp._render_hdr_toolbar)
    assert '"👤"' in src
    assert 'key="hdr_mobile_profile_btn"' in src
    assert "_is_mobile_ui()" in src
    assert '_bell_lbl = (\n            "🔔"\n            if _is_mobile_ui()' in src


def test_single_company_mobile_title_uses_pill_class():
    src = inspect.getsource(erp.render_top_header)
    assert "erp-hdr-co-pill" in src


def test_shell_stabilization_hdr_height_contract_updated():
    header_css = (ROOT / "ui" / "mobile_header.css").read_text(encoding="utf-8")
    assert "--hdr-h: 56px" in header_css
    assert "--hdr-h-search: 86px" in header_css


def test_hdr01_layout_tokens_defined():
    header_css = (ROOT / "ui" / "mobile_header.css").read_text(encoding="utf-8")
    assert "--hdr-toolbar-cluster-w: 72px" in header_css
    assert "--hdr-toolbar-edge: 12px" in header_css
    assert "--hdr-toolbar-gap: 8px" in header_css
    assert "--hdr-title-side-reserve: calc(var(--hdr-toolbar-cluster-w) + var(--hdr-toolbar-edge))" in header_css


def test_hdr01_no_fixed_220px_company_pill_cap():
    header_css = (ROOT / "ui" / "mobile_header.css").read_text(encoding="utf-8")
    assert "220px" not in header_css
    assert "max-width: min(100%, 220px)" not in header_css


def test_hdr01_ellipsis_selectors_present():
    header_css = (ROOT / "ui" / "mobile_header.css").read_text(encoding="utf-8")
    assert '[class*="st-key-hdr_mobile_title"] [data-testid="stButton"] > button p' in header_css
    assert "text-overflow: ellipsis" in header_css
    assert ".erp-hdr-mobile-co" in header_css
    assert ".erp-hdr-co-pill .erp-hdr-mobile-co" in header_css


def test_hdr01_toolbar_cluster_uses_gap_token():
    header_css = (ROOT / "ui" / "mobile_header.css").read_text(encoding="utf-8")
    assert "gap: var(--hdr-toolbar-gap)" in header_css
    assert "--hdr-toolbar-cluster-w" in header_css


def test_hdr01_mobile_profile_switch_opens_co_switch_sheet():
    profile_sheet = inspect.getsource(erp._render_mobile_profile_sheet)
    panel = inspect.getsource(erp._render_hdr_profile_panel_content)
    assert "show_co_switch_link=True" in profile_sheet
    assert 'show_inline_company_switch' not in profile_sheet
    assert '_mobile_open_surface("co_switch")' in panel


def test_hdr01_header_company_switch_opens_co_switch_sheet():
    header = inspect.getsource(erp.render_top_header)
    mobile_title_block = header.split('key="hdr_mobile_title"')[1].split("if _header_search_active")[0]
    assert 'key="hdr_mobile_co_switch_btn"' in mobile_title_block
    assert '_mobile_open_surface("co_switch")' in mobile_title_block
    assert "_render_company_switch_menu" not in mobile_title_block


def test_hdr01_theme_mobile_header_gaps_reconciled():
    theme_css = (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")
    mobile_block = theme_css.split("/* Sidebar — mobile (<=968px)", 1)[1].split("/* Desktop", 1)[0]
    assert "var(--hdr-toolbar-gap, 8px)" in mobile_block
    assert "var(--hdr-title-side-reserve, 84px)" in mobile_block
