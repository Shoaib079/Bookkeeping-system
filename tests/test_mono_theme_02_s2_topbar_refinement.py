"""MONO-THEME-02-S2 — desktop top bar refinement contract tests.

Scope: hdr_shell_row / erp-hdr-* / search / toolbar — desktop @media (min-width: 969px) only.
No sidebar, dashboard, mobile, or route changes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THEME_CSS = ROOT / "ui" / "theme.css"
MOBILE_HEADER_CSS = ROOT / "ui" / "mobile_header.css"
CONTRACT_DOC = ROOT / "docs" / "MONO_THEME_02_VISUAL_CONTRACT.md"


@pytest.fixture(scope="module")
def theme_css() -> str:
    return THEME_CSS.read_text(encoding="utf-8")


def _s2_block(css: str) -> str:
    start = css.index("MONO-THEME-02-S2 — desktop top bar refinement")
    end = css.index("/* Sidebar nav hierarchy", start)
    return css[start:end]


def test_s2_marker_present(theme_css):
    assert "MONO-THEME-02-S2" in theme_css


def test_s2_desktop_media_query_only(theme_css):
    block = _s2_block(theme_css)
    assert "@media (min-width: 969px)" in block
    assert "max-width: 968px" not in block


def test_s2_compact_desktop_header_height(theme_css):
    block = _s2_block(theme_css)
    assert "--hdr-h: 52px" in block


def test_s2_search_prominence_uses_card_tokens(theme_css):
    block = _s2_block(theme_css)
    assert "stTextInput" in block
    assert "var(--erp-card-bg)" in block
    assert "var(--erp-card-border)" in block
    assert "min(560px" in block or "560px" in block
    assert "var(--theme-focus)" in block


def test_s2_toolbar_softer_controls(theme_css):
    block = _s2_block(theme_css)
    assert "box-shadow: none !important" in block
    assert "var(--erp-nav-hover-bg)" in block
    assert "32px !important" in block


def test_s2_brand_identity_compact(theme_css):
    block = _s2_block(theme_css)
    assert ".erp-hdr-logo" in block
    assert "32px" in block
    assert ".erp-hdr-app-title" in block
    assert "font-weight: 700" in block


def test_s2_scope_no_sidebar_or_dashboard(theme_css):
    block = _s2_block(theme_css)
    assert "stSidebar" not in block
    assert "erp-dash-" not in block
    assert ".kpi-" not in block


def test_s2_does_not_modify_mobile_header_css():
    css = MOBILE_HEADER_CSS.read_text(encoding="utf-8")
    assert "MONO-THEME-02-S2" not in css


def test_no_route_changes(theme_css):
    block = _s2_block(theme_css)
    assert "react_route" not in block
    assert "registry/navigation" not in block


def test_contract_doc_lists_s2():
    text = CONTRACT_DOC.read_text(encoding="utf-8")
    assert "MONO-THEME-02-S2" in text
