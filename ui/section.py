"""Reusable section headers — Phase 16A stub for 16C page sweep."""

from __future__ import annotations

import html

_ACCENT_CLASS = {
    "info": "",
    "success": "accent-success",
    "danger": "accent-danger",
    "warning": "accent-warning",
    "purple": "accent-purple",
    "teal": "accent-teal",
}


def section_header_html(title: str, *, accent: str = "info") -> str:
    """Token-based section title (replaces inline #3b82f6 / #6b7280 blocks)."""
    safe = html.escape(str(title))
    extra = _ACCENT_CLASS.get(accent, "")
    cls = f"erp-section-hdr {extra}".strip()
    return f'<div class="{cls}">{safe}</div>'


def tab_panel_intro(
    title: str | None = None,
    *,
    caption: str | None = None,
) -> str:
    """Heading strip inside a tab panel — separates tab bar from panel content."""
    parts: list[str] = []
    if title:
        parts.append(f'<div class="erp-tab-intro-title">{html.escape(title)}</div>')
    if caption:
        parts.append(f'<div class="erp-tab-intro-caption">{html.escape(caption)}</div>')
    if not parts:
        return '<div class="erp-tab-intro erp-tab-intro--gap-only" aria-hidden="true"></div>'
    return f'<div class="erp-tab-intro">{"".join(parts)}</div>'
