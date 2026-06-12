"""LOGIN-01 — auth UI modernization contract (visual only; behavior frozen)."""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import app as erp
from ui import theme

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ui"

_AUTH_MARKER = "/* LOGIN-01 — Login + company picker auth surfaces"
_ERP_AUTH_SELECTOR_RE = re.compile(r"\.erp-auth-[a-z0-9_-]+|\[class\*=\"st-key-(?:pick_co_|select_user_|login_|picker_)")

_FROZEN_WIDGET_KEYS = (
    'key=f"select_user_{u.id}"',
    'key="login_username"',
    'key="login_password"',
    'key="login_btn"',
    'key="login_back"',
    'key=f"pick_co_{_m.company_id}"',
    'key="picker_signout"',
    'key="picker_start_setup01"',
)


def _read_css(filename: str) -> str:
    return (UI / filename).read_text(encoding="utf-8")


def test_login01_auth_css_registered_in_loader():
    css = theme.load_theme_css()
    assert _AUTH_MARKER in css
    mobile_header_marker = "/* Mobile header compact pass"
    auth_marker = _AUTH_MARKER
    mobile_txn_marker = "/* Mobile New Transaction — bottom entry panel"
    assert css.index(mobile_header_marker) < css.index(auth_marker) < css.index(mobile_txn_marker)
    assert ".erp-auth-header-card" in css


def test_login01_auth_selectors_only_in_auth_css():
    auth = _read_css("auth.css")
    assert ".erp-auth-header-card" in auth
    assert ".erp-auth-role-chip" in auth

    mobile_header = _read_css("mobile_header.css")
    auth_hits = _ERP_AUTH_SELECTOR_RE.findall(mobile_header)
    assert not auth_hits, f"erp-auth-* selectors remain in mobile_header.css: {auth_hits[:5]}"


def test_login01_no_inline_styles_in_auth_renderers():
    login = inspect.getsource(erp.render_login)
    picker = inspect.getsource(erp.render_company_picker)
    for src in (login, picker):
        assert 'style="' not in src
        assert "style='" not in src


def test_login01_widget_keys_frozen():
    login = inspect.getsource(erp.render_login)
    picker = inspect.getsource(erp.render_company_picker)
    combined = login + picker
    for needle in _FROZEN_WIDGET_KEYS:
        assert needle in combined, f"Missing frozen widget key pattern: {needle}"


def test_login01_picker_create_still_uses_setup01_wizard():
    picker = inspect.getsource(erp.render_company_picker)
    assert '_start_create_company_wizard(return_to="picker")' in picker
    assert "picker_start_setup01" in picker


def test_login01_login_uses_flat_auth_header_not_gradient_banner():
    login = inspect.getsource(erp.render_login)
    picker = inspect.getsource(erp.render_company_picker)
    for src in (login, picker):
        assert "erp-auth-header-card" in src
        assert "erp-auth-top-spacer" in src
        assert "erp-auth-banner" not in src
        assert "banner banner-primary" not in src


def test_login01_user_tiles_use_avatar_cards():
    login = inspect.getsource(erp.render_login)
    assert "erp-auth-user-card" in login
    assert "render_user_avatar" in login
    assert "erp-auth-role-chip" in login
    assert 'key=f"select_user_{u.id}"' in login
    assert "_t(\"login.select\")" in login


def test_login01_dev_auth_and_restore_hooks_untouched():
    main_src = inspect.getsource(erp.main)
    assert "_try_restore_session_from_cookie" in main_src
    restore_pos = main_src.index("_try_restore_session_from_cookie")
    login_pos = main_src.index("render_login")
    assert restore_pos < login_pos

    assert hasattr(erp, "DEV_MODE")
    assert "ERP_DEV_MODE" in inspect.getsource(erp) or "DEV_MODE" in dir(erp)


def test_login01_login_form_and_error_path_preserved():
    login = inspect.getsource(erp.render_login)
    assert 'with st.form("login_form"):' in login
    assert "enter_to_submit=False" not in login
    assert "_login(session, username, password)" in login
    assert 'st.error(_t("validation.username_password"))' in login
    assert "st.error(err)" in login


def test_login01_company_picker_membership_validation_preserved():
    picker = inspect.getsource(erp.render_company_picker)
    assert "CompanyUser.is_active == True" in picker
    assert "_valid_co.is_active" in picker
    assert 'st.error(_t("picker.unavailable"))' in picker
