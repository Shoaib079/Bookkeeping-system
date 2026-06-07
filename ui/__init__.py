"""UI layer — theme and shared presentation helpers (Phase 16)."""

from ui.section import (
    aging_buckets_html,
    financial_section_header_html,
    financial_statement_table_html,
    infer_column_kind,
    mono_role_pill_html,
    page_report_banner_html,
    readable_dataframe_table_html,
    section_header_html,
    tab_panel_intro,
    theme_table_html,
)
from ui.theme import (
    bootstrap_theme,
    chart_reference_color,
    chart_series_color,
    inject_theme_css,
    render_global_style,
    role_accent_css_var,
)

__all__ = [
    "aging_buckets_html",
    "bootstrap_theme",
    "chart_reference_color",
    "chart_series_color",
    "financial_section_header_html",
    "financial_statement_table_html",
    "infer_column_kind",
    "mono_role_pill_html",
    "page_report_banner_html",
    "readable_dataframe_table_html",
    "inject_theme_css",
    "render_global_style",
    "role_accent_css_var",
    "section_header_html",
    "tab_panel_intro",
    "theme_table_html",
]
