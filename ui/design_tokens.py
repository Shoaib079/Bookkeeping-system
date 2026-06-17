"""UI-SYSTEM-02-S2 — ERP design token registry (single source of truth).

Lives under ``ui/`` (not ``registry/``) so ``ui/theme.py`` can import without
triggering ``registry/__init__.py`` service imports on early UI package load.

Colour tokens consumed by ``ui/theme.py`` injection (THEME-AUTHORITY-01).
Layout/spacing/radius/shadow/typography scales are mirrored in ``ui/theme.css``
:root and validated by contract tests — no visual change in S2.
"""

from __future__ import annotations

import re
from typing import Final

# ── Injectable colour tokens (light / dark) ───────────────────────────────────

LIGHT_COLOR_TOKENS: Final[dict[str, str]] = {
    "--hdr-bg": "#EEF2F7",
    "--theme-bg": "#F8FAFC",
    "--theme-card": "#FFFFFF",
    "--theme-border": "#E6E9EE",
    "--theme-text": "#0F172A",
    "--theme-muted": "#475569",
    "--theme-caption": "#475569",
    "--theme-success": "#16A34A",
    "--theme-danger": "#DC2626",
    "--theme-warning": "#D97706",
    "--theme-info": "#2563EB",
    "--erp-primary-fill": "#2563EB",
    "--erp-primary-fill-hover": "#1D4ED8",
    "--theme-success-text": "#15803D",
    "--theme-warning-text": "#B45309",
    "--theme-danger-text": "#B91C1C",
    "--theme-purple": "#6D28D9",
    "--theme-teal": "#0EA5A4",
    "--theme-input-border": "#CBD5E1",
    "--theme-focus": "#2563EB",
    "--theme-banner-primary-start": "#1e3a8a",
    "--theme-banner-primary-end": "#2563eb",
    "--theme-shadow": "rgba(0,0,0,0.08)",
}

DARK_COLOR_TOKENS: Final[dict[str, str]] = {
    "--hdr-bg": "#1A2332",
    "--theme-bg": "#0B1220",
    "--theme-card": "#141C2B",
    "--theme-border": "#2D3A4D",
    "--theme-text": "#E8EDF4",
    "--theme-muted": "#9CA8B8",
    "--theme-caption": "#B8C4D0",
    "--theme-success": "#4ADE80",
    "--theme-danger": "#F87171",
    "--theme-warning": "#FBBF24",
    "--theme-info": "#3B82F6",
    "--erp-primary-fill": "#2563EB",
    "--erp-primary-fill-hover": "#1D4ED8",
    "--theme-success-text": "#4ADE80",
    "--theme-warning-text": "#FBBF24",
    "--theme-danger-text": "#F87171",
    "--theme-purple": "#8B5CF6",
    "--theme-teal": "#14B8A6",
    "--theme-input-border": "#334155",
    "--theme-focus": "#60A5FA",
    "--theme-banner-primary-start": "#1e3a8a",
    "--theme-banner-primary-end": "#3b82f6",
    "--theme-shadow": "rgba(0,0,0,0.35)",
}

# System-mode OS dark (@media prefers-color-scheme) — mirrors theme.css block.
# --theme-focus intentionally matches --theme-info in CSS (#3b82f6); injectable
# dark uses #60A5FA (THEME-AUTHORITY-01 explicit preference path).
SYSTEM_DARK_MEDIA_COLOR_TOKENS: Final[dict[str, str]] = {
    **{k: v for k, v in DARK_COLOR_TOKENS.items() if k not in ("--theme-focus", "--theme-shadow")},
    "--theme-focus": "#3b82f6",
    "--theme-shadow": "rgba(0, 0, 0, 0.35)",
}

# ── Shell layout (desktop base in theme.css :root) ────────────────────────────

LAYOUT_TOKENS: Final[dict[str, str]] = {
    "--hdr-h": "60px",
    "--side-nav-w": "244px",
    "--erp-sidebar-w": "244px",
    "--mob-top-nav-h": "0px",
    "--bottom-nav-h": "62px",
    "--erp-on-primary": "#ffffff",
    "--erp-field-radius": "8px",
}

# Mobile header overrides — owned by mobile_header.css (not theme.css mobile @media).
MOBILE_HEADER_LAYOUT_TOKENS: Final[dict[str, str]] = {
    "--hdr-h": "56px",
    "--hdr-h-search": "86px",
    "--hdr-toolbar-cluster-w": "72px",
    "--hdr-toolbar-edge": "12px",
    "--hdr-toolbar-gap": "8px",
}

# ── Scales (S2 — documented registry; mirrored in theme.css :root) ───────────

SPACING_TOKENS: Final[dict[str, str]] = {
    "--erp-space-1": "4px",
    "--erp-space-2": "8px",
    "--erp-space-3": "12px",
    "--erp-space-4": "16px",
    "--erp-space-5": "24px",
    "--erp-space-6": "32px",
}

RADIUS_TOKENS: Final[dict[str, str]] = {
    "--erp-radius-sm": "6px",
    "--erp-radius-md": "8px",
    "--erp-radius-lg": "12px",
    "--erp-radius-pill": "999px",
}

SHADOW_TOKENS: Final[dict[str, str]] = {
    "--erp-shadow-sm": "0 1px 2px var(--theme-shadow)",
    "--erp-shadow-md": "0 2px 8px var(--theme-shadow)",
    "--erp-shadow-lg": "0 4px 16px var(--theme-shadow)",
}

TYPOGRAPHY_TOKENS: Final[dict[str, str]] = {
    "--erp-font-caption": "11px",
    "--erp-font-body": "13px",
    "--erp-font-subtitle": "15px",
    "--erp-font-title": "18px",
    "--erp-line-tight": "1.2",
    "--erp-line-body": "1.45",
}

# Chip grammar uses color-mix — CSS-only (UI-1); keys listed for contract docs.
CHIP_TOKEN_KEYS: Final[tuple[str, ...]] = (
    "--erp-chip-active-bg",
    "--erp-chip-active-fg",
    "--erp-chip-active-border",
    "--erp-chip-idle-bg",
    "--erp-chip-idle-fg",
    "--erp-chip-idle-border",
)

# MONO-THEME-01-S2 — shared component grammar (by reference; no new hex colours).
NAV_GRAMMAR_TOKEN_KEYS: Final[tuple[str, ...]] = (
    "--erp-nav-active-bg",
    "--erp-nav-active-fg",
    "--erp-nav-active-bar",
    "--erp-nav-hover-bg",
    "--erp-nav-section-fg",
)

CARD_GRAMMAR_TOKEN_KEYS: Final[tuple[str, ...]] = (
    "--erp-card-bg",
    "--erp-card-border",
    "--erp-card-radius",
    "--erp-card-shadow",
    "--erp-card-muted-bg",
)

CHIP_GRAMMAR_EXTENSION_KEYS: Final[tuple[str, ...]] = (
    "--erp-chip-radius",
    "--erp-chip-border",
    "--erp-chip-padding-x",
    "--erp-chip-padding-y",
)

TABLE_GRAMMAR_TOKEN_KEYS: Final[tuple[str, ...]] = (
    "--erp-table-border",
    "--erp-table-header-bg",
    "--erp-table-row-hover-bg",
    "--erp-table-total-bg",
)

COMPONENT_GRAMMAR_TOKENS: Final[dict[str, str]] = {
    # Nav — desktop sidebar + mobile bottom nav share active grammar
    "--erp-nav-active-bg": "color-mix(in srgb, var(--theme-info) 12%, var(--theme-card) 88%)",
    "--erp-nav-active-fg": "var(--theme-info)",
    "--erp-nav-active-bar": "var(--erp-primary-fill)",
    "--erp-nav-hover-bg": "color-mix(in srgb, var(--theme-bg) 6%, var(--theme-card) 94%)",
    "--erp-nav-section-fg": "var(--theme-muted)",
    # Card — dashboard/KPI/form panels
    "--erp-card-bg": "var(--theme-card)",
    "--erp-card-border": "var(--theme-border)",
    "--erp-card-radius": "var(--erp-radius-lg)",
    "--erp-card-shadow": "var(--erp-shadow-sm)",
    "--erp-card-muted-bg": "color-mix(in srgb, var(--theme-bg) 50%, var(--theme-card) 50%)",
    # Chip extensions — semantic chip colours remain CHIP_TOKEN_KEYS
    "--erp-chip-radius": "var(--erp-radius-pill)",
    "--erp-chip-border": "var(--erp-chip-idle-border)",
    "--erp-chip-padding-x": "var(--erp-space-3)",
    "--erp-chip-padding-y": "var(--erp-space-1)",
    # Table — dense accounting readability
    "--erp-table-border": "var(--theme-border)",
    "--erp-table-header-bg": "color-mix(in srgb, var(--theme-bg) 45%, var(--theme-card) 55%)",
    "--erp-table-row-hover-bg": "color-mix(in srgb, var(--theme-bg) 35%, var(--theme-card) 65%)",
    "--erp-table-total-bg": "color-mix(in srgb, var(--theme-bg) 30%, var(--theme-card) 70%)",
}

COMPONENT_GRAMMAR_TOKEN_KEYS: Final[frozenset[str]] = frozenset(COMPONENT_GRAMMAR_TOKENS)

_HEX_IN_VALUE_RE = re.compile(r"#[0-9a-fA-F]{3,8}")


def grammar_values_reference_only() -> bool:
    """True when every grammar token value avoids raw hex (references existing tokens only)."""
    return all(not _HEX_IN_VALUE_RE.search(v) for v in COMPONENT_GRAMMAR_TOKENS.values())

# Deprecated — mono avatar policy (role_accent_css_var); do not use for new UI.
DEPRECATED_ROLE_TOKEN_KEYS: Final[frozenset[str]] = frozenset(
    {
        "--role-owner",
        "--role-manager",
        "--role-cashier",
        "--role-partner",
        "--role-viewer",
        "--role-default",
    }
)

DEPRECATED_ROLE_TOKEN_VALUES: Final[dict[str, str]] = {
    "--role-owner": "#1e40af",
    "--role-manager": "#0891b2",
    "--role-cashier": "#065f46",
    "--role-partner": "#6d28d9",
    "--role-viewer": "#6b7280",
    "--role-default": "#374151",
}

INJECTABLE_COLOR_KEYS: Final[frozenset[str]] = frozenset(LIGHT_COLOR_TOKENS) | frozenset(
    DARK_COLOR_TOKENS
)

SCALE_TOKEN_KEYS: Final[frozenset[str]] = frozenset(
    {
        *SPACING_TOKENS,
        *RADIUS_TOKENS,
        *SHADOW_TOKENS,
        *TYPOGRAPHY_TOKENS,
    }
)

_ROOT_BLOCK_RE = re.compile(r":root\s*\{([^}]*)\}", re.DOTALL)
_DARK_MEDIA_ROOT_RE = re.compile(
    r"html\[data-erp-theme=\"system\"\]\s*:root\s*,\s*"
    r"html:not\(\[data-erp-theme\]\)\s*:root\s*\{([^}]*)\}",
    re.DOTALL | re.IGNORECASE,
)
_VAR_ASSIGN_RE = re.compile(
    r"(--[a-zA-Z0-9_-]+)\s*:\s*([^;]+);",
    re.MULTILINE,
)


def build_light_root_vars() -> dict[str, str]:
    """Tokens injected for explicit light preference."""
    return dict(LIGHT_COLOR_TOKENS)


def build_dark_root_vars() -> dict[str, str]:
    """Tokens injected for explicit dark preference."""
    return dict(DARK_COLOR_TOKENS)


def system_dark_media_color_keys() -> frozenset[str]:
    """Colour keys that must appear in theme.css @media (prefers-color-scheme: dark)."""
    return frozenset(DARK_COLOR_TOKENS)


def parse_css_root_vars(css_text: str, *, block_index: int = 0) -> dict[str, str]:
    """Parse :root { --k: v; } assignments from CSS (first block by default)."""
    blocks = _ROOT_BLOCK_RE.findall(css_text)
    if not blocks or block_index >= len(blocks):
        return {}
    return {
        m.group(1).strip(): m.group(2).strip()
        for m in _VAR_ASSIGN_RE.finditer(blocks[block_index])
    }


def parse_system_dark_media_vars(css_text: str) -> dict[str, str]:
    """Parse colour overrides inside @media (prefers-color-scheme: dark)."""
    for match in re.finditer(r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)", css_text):
        chunk = css_text[match.start() : match.start() + 3500]
        root_inner = _DARK_MEDIA_ROOT_RE.search(chunk)
        if root_inner:
            return {
                m.group(1).strip(): m.group(2).strip()
                for m in _VAR_ASSIGN_RE.finditer(root_inner.group(1))
            }
    return {}


def normalize_hex(value: str) -> str:
    """Lowercase hex colours for parity comparison."""
    v = value.strip()
    if v.startswith("#") and len(v) in (4, 7):
        if len(v) == 4:
            v = "#" + "".join(ch * 2 for ch in v[1:])
        return v.lower()
    return v


def color_values_match(css_value: str, registry_value: str) -> bool:
    """Compare CSS and registry colour tokens (hex case-insensitive; rgba spacing)."""
    css_n = css_value.strip().replace(" ", "")
    reg_n = registry_value.strip().replace(" ", "")
    if css_n.startswith("#") or reg_n.startswith("#"):
        return normalize_hex(css_value) == normalize_hex(registry_value)
    return css_n.lower() == reg_n.lower()


__all__ = (
    "CARD_GRAMMAR_TOKEN_KEYS",
    "CHIP_GRAMMAR_EXTENSION_KEYS",
    "CHIP_TOKEN_KEYS",
    "COMPONENT_GRAMMAR_TOKEN_KEYS",
    "COMPONENT_GRAMMAR_TOKENS",
    "DARK_COLOR_TOKENS",
    "DEPRECATED_ROLE_TOKEN_KEYS",
    "DEPRECATED_ROLE_TOKEN_VALUES",
    "INJECTABLE_COLOR_KEYS",
    "LAYOUT_TOKENS",
    "LIGHT_COLOR_TOKENS",
    "MOBILE_HEADER_LAYOUT_TOKENS",
    "NAV_GRAMMAR_TOKEN_KEYS",
    "RADIUS_TOKENS",
    "SCALE_TOKEN_KEYS",
    "SPACING_TOKENS",
    "SHADOW_TOKENS",
    "SYSTEM_DARK_MEDIA_COLOR_TOKENS",
    "TABLE_GRAMMAR_TOKEN_KEYS",
    "TYPOGRAPHY_TOKENS",
    "build_dark_root_vars",
    "build_light_root_vars",
    "color_values_match",
    "grammar_values_reference_only",
    "normalize_hex",
    "parse_css_root_vars",
    "parse_system_dark_media_vars",
    "system_dark_media_color_keys",
)
