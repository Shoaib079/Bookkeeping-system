"""MOBILE-UX-02-A — shared mobile component grammar contract tests."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(*parts: str) -> str:
    return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")


def test_mobile_components_css_exists_with_tokens():
    css = _read("ui", "mobile_components.css")
    for token in (
        "--mob-space-2",
        "--mob-space-4",
        "--mob-radius-md",
        "--mob-surface-bg",
    ):
        assert token in css
    for cls in (
        ".erp-mob-kpi-grid",
        ".erp-mob-kpi-chip",
        ".erp-mob-list-row",
        ".erp-mob-empty",
        ".erp-mob-section-label",
        ".erp-mob-screen-title",
        ".erp-mob-status-pill",
    ):
        assert cls in css


def test_mobile_components_loaded_in_theme_bundle():
    theme_py = _read("ui", "theme.py")
    assert "mobile_components.css" in theme_py
    assert "_MOBILE_COMPONENTS_CSS_PATH" in theme_py
    assert "mobile_components" in theme_py


def test_section_mobile_helpers_exported():
    section = _read("ui", "section.py")
    for name in (
        "mobile_kpi_chip_html",
        "mobile_kpi_grid_html",
        "mobile_list_row_html",
        "mobile_empty_state_html",
        "mobile_section_label_html",
        "mobile_screen_title_html",
        "mobile_status_pill_html",
        "mobile_highlight_banner_html",
    ):
        assert f"def {name}" in section
        assert name in section.split("__all__")[1]


def test_highlight_banner_and_filters_use_shared_helpers():
    app = _read("app.py")
    assert "mobile_highlight_banner_html" in app
    assert "mobile_section_label_html" in app
    assert 'erp-txh-filters-label' not in app
    components = _read("ui", "mobile_components.css")
    assert ".erp-mob-highlight-banner" in components


def test_app_uses_mobile_helpers_for_at_and_cf_kpi():
    app = _read("app.py")
    assert "mobile_kpi_grid_html" in app
    assert "mobile_kpi_chip_html" in app
    assert "mobile_list_row_html" in app
    assert "mobile_empty_state_html" in app
    assert "mobile_screen_title_html" in app
    assert "mobile_section_label_html" in app
    cf_block = app.split('key="mob_rpt_cf_kpi"')[1][:800]
    assert "mobile_kpi_grid_html" in cf_block
    assert 'class="card"' not in cf_block


def test_status_pills_use_shared_variant_map():
    app = _read("app.py")
    assert "_TXH_STATUS_VARIANT" in app
    assert "mobile_status_pill_html" in app
    assert "_TXH_STATUS_PILL" not in app


def test_pill_styles_not_duplicated_in_txh_css():
    txh = _read("ui", "mobile_txn_history.css")
    assert ".erp-txh-pill--success" not in txh
    components = _read("ui", "mobile_components.css")
    assert ".erp-mob-status-pill--success" in components
    assert ".erp-txh-pill--success" in components


def test_cf_kpi_uses_shared_chip_not_card():
    reports = _read("ui", "mobile_reports.css")
    assert "erp-mob-kpi-grid" in reports
    assert ".card" not in reports.split("mob_rpt_cf_kpi")[1].split("Global mobile date")[0]
