"""Phase 16A/16B — theme foundation tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
    sys.modules["streamlit"].session_state = {}

import pandas as pd

from ui.section import (
    financial_section_header_html,
    financial_statement_table_html,
    infer_column_kind,
    readable_dataframe_table_html,
    section_header_html,
    tab_panel_intro,
    theme_table_html,
)
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
    for token in (
        "--theme-input-border",
        "--theme-banner-primary-start",
        "--theme-shadow",
        "--theme-caption",
        "--erp-primary-fill",
        "--erp-primary-fill-hover",
        "--theme-success-text",
        "--theme-warning-text",
        "--theme-danger-text",
    ):
        assert token in LIGHT_ROOT_VARS
        assert token in DARK_ROOT_VARS


def test_vars_to_css_block_format():
    block = _vars_to_css_block({"--theme-bg": "#fff"})
    assert block == ":root{--theme-bg:#fff;}"


def test_role_accent_css_var():
    assert "var(--theme-info)" in role_accent_css_var("owner")
    assert role_accent_css_var("owner") == role_accent_css_var("unknown")


def test_financial_statement_table_has_code_name_amount():
    html_out = financial_statement_table_html(
        [
            ("Code", "Code", "code"),
            ("Account", "Account", "name"),
            ("Amount", "Amount", "amount"),
        ],
        [{"Code": "2110", "Account": "Credit Card Payable", "Amount": 1500.0}],
    )
    assert "erp-fin-table" in html_out
    assert "erp-fin-code" in html_out
    assert "erp-fin-name" in html_out
    assert "erp-fin-amount" in html_out
    assert "2110" in html_out
    assert "Credit Card Payable" in html_out
    assert "1,500.00" in html_out


def test_financial_statement_table_marks_total_row():
    rows = [
        {"Code": "1010", "Account": "Bank", "Amount": 100.0},
        {"Code": "TOTAL", "Account": "TOTAL", "Amount": 100.0},
    ]
    html_out = financial_statement_table_html(
        [
            ("Code", "Code", "code"),
            ("Account", "Account", "name"),
            ("Amount", "Amount", "amount"),
        ],
        rows,
        total_row_indexes={1},
    )
    assert "erp-fin-row-total" in html_out


def test_financial_section_header_html_uses_token_classes():
    html_out = financial_section_header_html("Liabilities", "TRY 1,500.00", accent="warning")
    assert "erp-fin-section-hdr" in html_out
    assert "erp-fin-section-title" in html_out
    assert "Liabilities" in html_out
    assert "TRY 1,500.00" in html_out


def test_infer_column_kind_maps_operational_columns():
    assert infer_column_kind("Customer") == "name"
    assert infer_column_kind("Total") == "amount"
    assert infer_column_kind("Code") == "code"
    assert infer_column_kind("Date") == "text"


def test_readable_dataframe_table_html_status_rows():
    df = pd.DataFrame([
        {"Account": "Rent", "Budgeted": 1000.0, "Actual": 1200.0, "Status": "Over"},
        {"Account": "Utilities", "Budgeted": 200.0, "Actual": 150.0, "Status": "On track"},
    ])
    html_out = readable_dataframe_table_html(df, status_col="Status")
    assert "erp-fin-row-over" in html_out
    assert "erp-fin-row-ok" in html_out
    assert "Rent" in html_out


def test_app_has_render_readable_df_helper():
    import app as erp_app

    assert hasattr(erp_app, "_render_readable_df")


def test_app_display_tables_avoid_st_dataframe():
    """Sweep 2: read-only tables use _render_readable_df, not Glide clip."""
    src = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
    assert "st.dataframe(" not in src
    assert "_render_readable_df(" in src


def test_theme_css_includes_financial_readability_rules():
    css = _theme_css_text()
    for cls in (
        ".erp-fin-table",
        ".erp-fin-code",
        ".erp-fin-name",
        ".erp-fin-amount",
        ".erp-fin-row-total",
        "--theme-caption",
    ):
        assert cls in css


def test_theme_table_html_escapes_and_marks_numeric_cols():
    html_out = theme_table_html(
        ["Card", "Balance"],
        [["Visa", "TRY 5,000.00"]],
        numeric_cols={1},
    )
    assert "erp-data-table" in html_out
    assert 'class="num"' in html_out
    assert "TRY 5,000.00" in html_out


def test_kpi_values_allow_wrap_not_ellipsis():
    css = _theme_css_text()
    block = css.split(".kpi-value {", 1)[1].split("}", 1)[0]
    assert "text-overflow: ellipsis" not in block
    assert "white-space: normal" in block


def test_dark_mode_metric_and_alert_rules_in_widgets():
    widgets = Path(__file__).resolve().parents[1] / "ui" / "widgets.css"
    text = widgets.read_text(encoding="utf-8")
    assert "stMetricValue" in text
    assert "stAlert" in text
    assert "text-overflow: unset" in text
    assert "stDataFrame" not in text
    assert "data-baseweb=\"tag\"" in text


def test_glide_dataframe_css_removed():
    widgets = Path(__file__).resolve().parents[1] / "ui" / "widgets.css"
    theme = Path(__file__).resolve().parents[1] / "ui" / "theme.css"
    assert "stDataFrame" not in widgets.read_text(encoding="utf-8")
    assert "stDataFrame" not in theme.read_text(encoding="utf-8")
    import ui.theme as theme_mod

    assert not hasattr(theme_mod, "_DARK_DATAFRAME_CSS")


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
    assert ".erp-kpi-section" in css
    assert "min-height: 76px" in css


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
    for cls in (".erp-hdr-brand-block", ".erp-hdr-app-title", ".erp-hdr-co-subtitle",
                ".erp-hdr-mobile-title", ".erp-hdr-mobile-co"):
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
