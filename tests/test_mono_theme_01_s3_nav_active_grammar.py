"""MONO-THEME-01-S3 — nav active grammar migration contract tests.

Desktop sidebar + mobile bottom-nav/hub active states must reference the shared
``--erp-nav-*`` grammar tokens from MONO-THEME-01-S2 (no new colors).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ui.design_tokens import NAV_GRAMMAR_TOKEN_KEYS

ROOT = Path(__file__).resolve().parents[1]
THEME_CSS = ROOT / "ui" / "theme.css"
MOBILE_SHELL_CSS = ROOT / "ui" / "mobile_shell.css"
ICONS_CSS = ROOT / "ui" / "icons.css"

ACTIVE_NAV_KEYS = (
    "--erp-nav-active-bg",
    "--erp-nav-active-fg",
    "--erp-nav-active-bar",
)


@pytest.fixture(scope="module")
def theme_css() -> str:
    return THEME_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def mobile_shell_css() -> str:
    return MOBILE_SHELL_CSS.read_text(encoding="utf-8")


def _sidebar_nav_block(css: str) -> str:
    start = css.index("/* Sidebar nav buttons")
    end = css.index("/* Sidebar form fields", start)
    nav_hierarchy = css.index("/* Sidebar nav hierarchy", end)
    return css[start:nav_hierarchy + 2500]


def _mobile_nav_block(css: str) -> str:
    idx = css.index("st-key-mob_bar_")
    return css[idx : idx + 4500]


def test_desktop_sidebar_section_header_uses_nav_section_token(theme_css):
    block = theme_css.split(".erp-nav-section-hdr")[1][:500]
    assert "var(--erp-nav-section-fg)" in block


@pytest.mark.parametrize("token", ACTIVE_NAV_KEYS)
def test_desktop_sidebar_primary_buttons_use_nav_grammar(theme_css, token):
    block = _sidebar_nav_block(theme_css).split("Sidebar nav buttons")[1].split("Sidebar form")[0]
    assert f"var({token})" in block, f"desktop sidebar primary missing {token}"


def test_desktop_nav_item_active_uses_nav_grammar(theme_css):
    anchor = "background-color: var(--erp-nav-active-bg) !important;\n  border-left: 3px solid var(--erp-nav-active-bar)"
    assert anchor in theme_css
    idx = theme_css.index(anchor)
    block = theme_css[max(0, idx - 400) : idx + 200]
    assert "nav-item-active-mark" in block
    for token in ACTIVE_NAV_KEYS:
        assert f"var({token})" in block, f"nav-item-active missing {token}"
    assert "color-mix(in srgb, var(--theme-info)" not in block


def test_desktop_nav_grp_active_uses_nav_grammar(theme_css):
    block = theme_css.split("/* Active folder header")[1][:1200]
    for token in ACTIVE_NAV_KEYS:
        assert f"var({token})" in block, f"nav-grp-active missing {token}"


def test_desktop_idle_nav_hover_uses_nav_hover_token(theme_css):
    assert "div:has(.nav-item-mark) + div [data-testid=\"stButton\"] > button:hover" in theme_css
    block = theme_css.split("div:has(.nav-item-mark) + div [data-testid=\"stButton\"] > button:hover")[1][:200]
    assert "var(--erp-nav-hover-bg)" in block


@pytest.mark.parametrize("token", ACTIVE_NAV_KEYS)
def test_mobile_bottom_nav_active_uses_nav_grammar(mobile_shell_css, token):
    block = _mobile_nav_block(mobile_shell_css)
    assert f"var({token})" in block, f"mobile bottom nav missing {token}"


def test_mobile_hub_active_uses_nav_grammar_not_solid_fill(mobile_shell_css):
    idx = mobile_shell_css.index('[class*="st-key-mob_hub_"] button[kind="primary"]')
    block = mobile_shell_css[idx : idx + 600]
    assert "var(--erp-nav-active-bg)" in block
    assert "var(--erp-nav-active-fg)" in block
    assert "var(--erp-primary-fill) !important" not in block


def test_mobile_active_icon_uses_nav_active_fg(mobile_shell_css):
    match = re.search(
        r':has\(button\[kind="primary"\].*?\)\s*\.erp-mob-bar-ico\s*\{([^}]*)\}',
        mobile_shell_css,
        flags=re.S,
    )
    assert match, "active bottom-nav icon rule missing"
    assert "var(--erp-nav-active-fg)" in match.group(1)


def test_sidebar_active_icon_uses_nav_active_fg():
    icons = ICONS_CSS.read_text(encoding="utf-8")
    assert "div:has(.nav-item-active-mark)" in icons
    assert "var(--erp-nav-active-fg)" in icons


def test_desktop_mobile_nav_token_parity(theme_css, mobile_shell_css):
    """Both surfaces reference the same active grammar token names."""
    desktop = (
        _sidebar_nav_block(theme_css)
        + theme_css.split("/* Active folder header")[1][:1200]
    )
    mobile = _mobile_nav_block(mobile_shell_css) + mobile_shell_css.split(
        '[class*="st-key-mob_hub_"] button[kind="primary"]'
    )[1][:600]
    for key in ACTIVE_NAV_KEYS:
        assert f"var({key})" in desktop, f"desktop missing {key}"
        assert f"var({key})" in mobile, f"mobile missing {key}"


def test_all_nav_grammar_keys_documented():
    assert len(NAV_GRAMMAR_TOKEN_KEYS) == 5
