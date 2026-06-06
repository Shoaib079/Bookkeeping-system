"""Phase 16A/16B — theme foundation tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
    sys.modules["streamlit"].session_state = {}

from ui.section import section_header_html, tab_panel_intro
from ui.theme import (
    DARK_ROOT_VARS,
    LIGHT_ROOT_VARS,
    load_theme_css,
    role_accent_css_var,
    _vars_to_css_block,
)


def test_theme_css_file_exists_and_non_empty():
    css_path = Path(__file__).resolve().parents[1] / "ui" / "theme.css"
    text = css_path.read_text(encoding="utf-8")
    assert "--theme-bg" in text
    assert ".kpi-card" in text
    assert len(text) > 2000


def test_load_theme_css_includes_widgets():
    css = load_theme_css()
    root = Path(__file__).resolve().parents[1] / "ui"
    assert root.joinpath("theme.css").read_text(encoding="utf-8") in css
    assert "Phase 16B" in css
    assert "[data-testid=\"stVerticalBlockBorderWrapper\"]" in css


def test_widgets_css_file_exists():
    path = Path(__file__).resolve().parents[1] / "ui" / "widgets.css"
    text = path.read_text(encoding="utf-8")
    assert "stExpander" in text
    assert "stTabs" in text


def test_light_and_dark_vars_include_new_tokens():
    for token in ("--theme-input-border", "--theme-banner-primary-start", "--theme-shadow"):
        assert token in LIGHT_ROOT_VARS
        assert token in DARK_ROOT_VARS


def test_vars_to_css_block_format():
    block = _vars_to_css_block({"--theme-bg": "#fff"})
    assert block == ":root{--theme-bg:#fff;}"


def test_role_accent_css_var():
    assert "var(--role-owner)" == role_accent_css_var("owner")
    assert "var(--role-default)" == role_accent_css_var("unknown")


def test_section_header_escapes_html():
    html = section_header_html("<script>")
    assert "&lt;script&gt;" in html
    assert "erp-section-hdr" in html


def test_section_header_accent_class():
    html = section_header_html("Title", accent="success")
    assert "accent-success" in html


def test_tab_panel_intro_title_and_caption():
    html = tab_panel_intro("Today", caption="Count the drawer.")
    assert "erp-tab-intro-title" in html
    assert "erp-tab-intro-caption" in html
    assert "Count the drawer." in html


def test_app_imports_bootstrap_theme():
    import app as erp_app

    assert hasattr(erp_app, "bootstrap_theme")


# ── Phase 16D — responsive layout + header identity ──────────────────────────

def _theme_css_text():
    path = Path(__file__).resolve().parents[1] / "ui" / "theme.css"
    return path.read_text(encoding="utf-8")


def test_kpi_grid_collapses_on_mobile():
    css = _theme_css_text()
    assert "@media (max-width: 640px)" in css
    assert "grid-template-columns: 1fr" in css


def test_sidebar_has_desktop_and_mobile_rules():
    css = _theme_css_text()
    assert "@media (min-width: 969px)" in css
    assert "@media (max-width: 968px)" in css
    assert '[class*="st-key-hdr_shell_row"]' in css
    assert "position: fixed" in css


def test_sidebar_surface_is_theme_aware():
    css = _theme_css_text()
    # sidebar background must use a theme token, not Streamlit's fixed secondaryBackground
    assert "Sidebar surface" in css
    sidebar_block = css.split("Sidebar surface", 1)[1]
    assert "background: var(--theme-card)" in sidebar_block


def test_header_identity_classes_present():
    css = _theme_css_text()
    for cls in (".erp-hdr-brand", ".erp-hdr-co", ".erp-hdr-user-name",
                ".erp-hdr-hide-sm", ".erp-hdr-hide-md"):
        assert cls in css


def test_section_header_teal_accent():
    html = section_header_html("Banking", accent="teal")
    assert "accent-teal" in html


# ── Phase 16E — pastel banners migrated to theme tokens ──────────────────────

def test_no_hardcoded_statement_pastels_in_app():
    src = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    for dead in ("background:#f0fdf4", "background:#fef2f2", "background:#eff6ff",
                 "background-color:#fee2e2", "background-color:#f0fdf4",
                 "background:#d1fae5", "color:#15803d", "color:#b91c1c"):
        assert dead not in src, f"hardcoded pastel still present: {dead}"
    # token-based tints are used instead
    assert "color-mix(in srgb,var(--theme-success)" in src
    assert "color-mix(in srgb,var(--theme-danger)" in src
