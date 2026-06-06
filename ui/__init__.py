"""UI layer — theme and shared presentation helpers (Phase 16)."""

from ui.section import section_header_html
from ui.theme import (
    bootstrap_theme,
    inject_theme_css,
    render_global_style,
    role_accent_css_var,
)

__all__ = [
    "bootstrap_theme",
    "inject_theme_css",
    "render_global_style",
    "role_accent_css_var",
    "section_header_html",
]
