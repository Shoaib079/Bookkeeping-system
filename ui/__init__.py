"""UI layer — theme and shared presentation helpers (Phase 16)."""

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
    bootstrap_theme,
    inject_theme_css,
    render_global_style,
    role_accent_css_var,
)

__all__ = [
    "bootstrap_theme",
    "financial_section_header_html",
    "financial_statement_table_html",
    "infer_column_kind",
    "readable_dataframe_table_html",
    "inject_theme_css",
    "render_global_style",
    "role_accent_css_var",
    "section_header_html",
    "tab_panel_intro",
    "theme_table_html",
]
