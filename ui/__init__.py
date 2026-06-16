"""UI layer — theme and shared presentation helpers (Phase 16)."""

from ui.crud_helpers import (
    attachment_section_selector,
    void_confirmation_widget,
)
from ui.report_helpers import (
    growth_comparison_kpi,
)
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
    apply_altair_theme,
    bootstrap_theme,
    chart_accent_color,
    chart_palette,
    chart_reference_color,
    chart_series_color,
    chart_theme_tokens,
    inject_theme_css,
    render_global_style,
    render_themed_bar,
    render_themed_grouped_bar,
    render_themed_line,
    role_accent_css_var,
    sync_derived_dark_mode,
)

__all__ = [
    "attachment_section_selector",
    "void_confirmation_widget",
    "growth_comparison_kpi",
    "aging_buckets_html",
    "apply_altair_theme",
    "bootstrap_theme",
    "chart_accent_color",
    "chart_palette",
    "chart_reference_color",
    "chart_series_color",
    "chart_theme_tokens",
    "financial_section_header_html",
    "financial_statement_table_html",
    "infer_column_kind",
    "mono_role_pill_html",
    "page_report_banner_html",
    "readable_dataframe_table_html",
    "inject_theme_css",
    "render_global_style",
    "render_themed_bar",
    "render_themed_grouped_bar",
    "render_themed_line",
    "role_accent_css_var",
    "sync_derived_dark_mode",
    "section_header_html",
    "tab_panel_intro",
    "theme_table_html",
]
