"""MONO-THEME-02-S1 — sidebar polish contract tests.

Quiet nav row: subtle tint + 3px accent bar + blue text/icon — no filled button box.
Section headers: muted uppercase + tighter spacing. Routes unchanged (CSS only).
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THEME_CSS = ROOT / "ui" / "theme.css"
ICONS_CSS = ROOT / "ui" / "icons.css"
CONTRACT_DOC = ROOT / "docs" / "MONO_THEME_02_VISUAL_CONTRACT.md"

ACTIVE_NAV_KEYS = (
    "--erp-nav-active-bg",
    "--erp-nav-active-fg",
    "--erp-nav-active-bar",
)


@pytest.fixture(scope="module")
def theme_css() -> str:
    return THEME_CSS.read_text(encoding="utf-8")


def _sidebar_nav_buttons_block(css: str) -> str:
    start = css.index("MONO-THEME-02-S1 quiet row grammar")
    end = css.index("/* Sidebar form fields", start)
    return css[start:end]


def _sidebar_hierarchy_block(css: str) -> str:
    start = css.index("MONO-THEME-02-S1 spacing polish")
    return css[start:]


def test_s1_marker_present(theme_css):
    assert "MONO-THEME-02-S1" in theme_css


def test_top_level_active_no_filled_button_border(theme_css):
    block = _sidebar_nav_buttons_block(theme_css)
    assert "var(--erp-nav-active-bg)" in block
    assert "border-left: 3px solid var(--erp-nav-active-bar)" in block
    assert "border: 1px solid color-mix" not in block
    assert "box-shadow: none !important" in block
    assert "font-weight: 600 !important" in block


def test_idle_secondary_nav_transparent_border(theme_css):
    block = _sidebar_nav_buttons_block(theme_css)
    assert "button[kind=\"secondary\"]" in block
    assert "border: none !important" in block
    assert "var(--erp-nav-hover-bg)" in block


def test_active_child_quiet_row_grammar(theme_css):
    block = _sidebar_hierarchy_block(theme_css)
    child = block.split("MONO-THEME-02-S1 — active child")[1][:700]
    assert "nav-item-active-mark" in block
    for key in ACTIVE_NAV_KEYS:
        assert f"var({key})" in child
    assert "border: none !important" in child
    assert "border-left: 3px solid var(--erp-nav-active-bar)" in child
    assert "box-shadow: none !important" in child


def test_active_folder_header_no_button_box(theme_css):
    block = _sidebar_hierarchy_block(theme_css)
    folder = block.split("Active folder header")[1][:800]
    assert "nav-grp-active" in folder
    assert "border: 1px solid color-mix" not in folder
    assert "border-left: 3px solid var(--erp-nav-active-bar)" in folder


def test_section_headers_muted_uppercase_spacing(theme_css):
    block = _sidebar_hierarchy_block(theme_css)
    hdr = block.split(".erp-nav-section-hdr")[1][:400]
    assert "text-transform: uppercase" in hdr
    assert "var(--erp-nav-section-fg)" in hdr
    assert "font-weight: 600 !important" in hdr
    assert "letter-spacing: 0.08em !important" in hdr
    assert "var(--erp-space-5)" in hdr
    assert "var(--erp-space-2)" in hdr


def test_open_folder_header_no_shadow(theme_css):
    block = _sidebar_hierarchy_block(theme_css)
    open_hdr = block.split("MONO-THEME-02-S1 — open folder header")[1][:200]
    assert "box-shadow: none !important" in open_hdr


def test_active_nav_icon_uses_blue_fg():
    icons = ICONS_CSS.read_text(encoding="utf-8")
    assert "nav-item-active-mark" in icons
    assert "var(--erp-nav-active-fg)" in icons


def test_no_route_changes_in_css(theme_css):
    assert "react_route" not in theme_css
    assert "registry/navigation" not in theme_css


def test_theme_css_s1_diff_scope_sidebar_only(theme_css):
    """S1 must not touch non-sidebar surfaces — guard against scope creep."""
    start = theme_css.index("MONO-THEME-02-S1 quiet row grammar")
    end = theme_css.index("/* Sidebar form fields", start)
    s1_block = theme_css[start:end]
    assert "[data-testid=\"stSidebar\"]" in s1_block
    assert ".kpi-grid" not in s1_block
    assert ".erp-dash-" not in s1_block
    assert "st-key-hdr_" not in s1_block

    hier_start = theme_css.index("MONO-THEME-02-S1 spacing polish")
    hier_block = theme_css[hier_start:]
    assert "[data-testid=\"stSidebar\"]" in hier_block[:3500]
    assert "erp-mobile" not in hier_block[:3500]


def test_contract_doc_marks_s1_complete():
    text = CONTRACT_DOC.read_text(encoding="utf-8")
    assert "MONO-THEME-02-S1" in text
    assert "desktop sidebar only" in text.lower()
