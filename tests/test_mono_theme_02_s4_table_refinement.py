"""MONO-THEME-02-S4 — desktop table density & money alignment contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THEME_CSS = ROOT / "ui" / "theme.css"
WIDGETS_CSS = ROOT / "ui" / "widgets.css"
CONTRACT_DOC = ROOT / "docs" / "MONO_THEME_02_VISUAL_CONTRACT.md"


@pytest.fixture(scope="module")
def theme_css() -> str:
    return THEME_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def widgets_css() -> str:
    return WIDGETS_CSS.read_text(encoding="utf-8")


def _s4_theme_block(css: str) -> str:
    start = css.index("MONO-THEME-02-S4 — desktop table density")
    end = css.index("/* Header profile popover card */", start)
    return css[start:end]


def _s4_widgets_block(css: str) -> str:
    marker = "MONO-THEME-02-S3 — desktop dashboard bordered panels"
    media_start = css.index("@media (min-width: 969px)", css.index(marker))
    depth = 0
    media_end = media_start
    for i, ch in enumerate(css[media_start:], media_start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                media_end = i
                break
    block = css[media_start:media_end]
    assert "MONO-THEME-02-S4" in block
    return block[block.index("MONO-THEME-02-S4") :]


def test_s4_marker_present(theme_css, widgets_css):
    assert "MONO-THEME-02-S4" in theme_css
    assert "MONO-THEME-02-S4" in widgets_css


def test_s4_desktop_media_only(theme_css, widgets_css):
    tblock = _s4_theme_block(theme_css)
    wblock = _s4_widgets_block(widgets_css)
    assert "@media (min-width: 969px)" in tblock
    assert "MONO-THEME-02-S4" in wblock
    assert "max-width: 968px" not in tblock


def test_s4_fin_table_denser_rows(theme_css):
    block = _s4_theme_block(theme_css)
    assert ".erp-fin-table td" in block
    assert "padding: 8px 10px" in block
    assert ".erp-fin-table thead th" in block
    assert "padding: 7px 10px" in block


def test_s4_fin_table_sticky_header(theme_css):
    block = _s4_theme_block(theme_css)
    thead = block.split(".erp-fin-table thead th")[1][:400]
    assert "position: sticky" in thead
    assert "var(--hdr-h" in thead


def test_s4_data_table_money_alignment(theme_css):
    block = _s4_theme_block(theme_css)
    assert ".erp-data-table td.num" in block
    assert "font-weight: 600" in block
    assert ".erp-fin-amount" in block
    assert "min-width: 7.5rem" in block


def test_s4_widgets_uses_table_hover_token(widgets_css):
    block = _s4_widgets_block(widgets_css)
    assert "var(--erp-table-row-hover-bg)" in block


def test_s4_widgets_sttable_hover_and_tabular(widgets_css):
    block = _s4_widgets_block(widgets_css)
    assert "stTable" in block
    assert "tbody tr:hover td" in block
    assert "font-variant-numeric: tabular-nums" in block
    assert "padding: 8px 10px" in block


def test_s4_scope_no_sidebar_dashboard_or_mobile(theme_css):
    block = _s4_theme_block(theme_css)
    assert "stSidebar" not in block
    assert "erp-dash-" not in block
    assert "erp-mob-" not in block


def test_s4_no_route_or_logic_changes(theme_css, widgets_css):
    assert "react_route" not in _s4_theme_block(theme_css)
    assert "registry/navigation" not in _s4_theme_block(theme_css)
    assert "react_route" not in _s4_widgets_block(widgets_css)


def test_contract_doc_lists_s4():
    text = CONTRACT_DOC.read_text(encoding="utf-8")
    assert "MONO-THEME-02-S4" in text
