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
