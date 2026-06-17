"""MONO-THEME-02-S3 — desktop dashboard & card hierarchy contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THEME_CSS = ROOT / "ui" / "theme.css"
WIDGETS_CSS = ROOT / "ui" / "widgets.css"


@pytest.fixture(scope="module")
def theme_css() -> str:
    return THEME_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def widgets_css() -> str:
    return WIDGETS_CSS.read_text(encoding="utf-8")


def _s3_theme_block(css: str) -> str:
    start = css.index("MONO-THEME-02-S3 — desktop dashboard density")
    end = css.index(".erp-hdr-profile-card", start)
    return css[start:end]


def _s3_widgets_block(css: str) -> str:
    start = css.index("MONO-THEME-02-S3 — desktop dashboard bordered panels")
    return css[start : start + 1200]


def test_s3_marker_present(theme_css, widgets_css):
    assert "MONO-THEME-02-S3" in theme_css
    assert "MONO-THEME-02-S3" in widgets_css


def test_s3_desktop_media_only(theme_css, widgets_css):
    tblock = _s3_theme_block(theme_css)
    wblock = _s3_widgets_block(widgets_css)
    assert "@media (min-width: 969px)" in tblock
    assert "@media (min-width: 969px)" in wblock
    assert "max-width: 968px" not in tblock


def test_s3_kpi_grid_denser(theme_css):
    block = _s3_theme_block(theme_css)
    assert ".kpi-grid" in block
    assert "gap: 10px" in block
    assert "minmax(168px" in block
    assert ".kpi-card" in block
    assert "min-height: 64px" in block


def test_s3_dashboard_surfaces_use_card_tokens(theme_css):
    block = _s3_theme_block(theme_css)
    assert "var(--erp-card-bg)" in block
    assert "var(--erp-card-border)" in block
    assert "var(--erp-card-radius)" in block
    assert "var(--erp-card-shadow)" in block
    assert "var(--erp-card-muted-bg)" in block


def test_s3_activity_focal_point(theme_css):
    block = _s3_theme_block(theme_css)
    assert ".erp-dash-activity-row:hover" in block
    assert "var(--erp-table-row-hover-bg)" in block
    assert ".erp-dash-activity-amt" in block


def test_s3_insight_rows_as_cards(theme_css):
    block = _s3_theme_block(theme_css)
    insight = block.split(".erp-dash-insight-row")[1][:500]
    assert "border: 1px solid var(--erp-card-border)" in insight
    assert "box-shadow: var(--erp-card-shadow)" in insight


def test_s3_widgets_bordered_panels_tighter(widgets_css):
    block = _s3_widgets_block(widgets_css)
    assert "stVerticalBlockBorderWrapper" in block
    assert "padding: 12px 14px !important" in block
    assert "margin-bottom: 12px !important" in block
    assert "stMetric" in block


def test_s3_scope_no_sidebar_or_mobile(theme_css):
    block = _s3_theme_block(theme_css)
    assert "stSidebar" not in block
    assert "erp-mob-" not in block
    assert "mob_bar" not in block


def test_s3_no_route_or_logic_changes(theme_css, widgets_css):
    assert "react_route" not in _s3_theme_block(theme_css)
    assert "render_dashboard" not in _s3_theme_block(theme_css)
    assert "react_route" not in _s3_widgets_block(widgets_css)
    assert "render_dashboard" not in _s3_widgets_block(widgets_css)
