"""THEME-CONTRAST-01 — WCAG contrast contracts for theme tokens (P0 + P1)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ui.theme import DARK_ROOT_VARS, LIGHT_ROOT_VARS

ROOT = Path(__file__).resolve().parents[1]
THEME_CSS = ROOT / "ui" / "theme.css"
WIDGETS_CSS = ROOT / "ui" / "widgets.css"

WCAG_AA_NORMAL = 4.5


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def channel(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def wcag_contrast(fg: str, bg: str) -> float:
    """Return WCAG 2.x contrast ratio for two #RRGGBB colours."""
    l1 = _relative_luminance(_hex_to_rgb(fg))
    l2 = _relative_luminance(_hex_to_rgb(bg))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _parse_theme_css_root_tokens() -> dict[str, str]:
    """Parse :root { ... } custom properties from theme.css (light defaults)."""
    text = THEME_CSS.read_text(encoding="utf-8")
    root_match = re.search(r":root\s*\{([^}]+)\}", text, flags=re.DOTALL)
    assert root_match, ":root block missing from theme.css"
    tokens: dict[str, str] = {}
    for line in root_match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("/*"):
            continue
        m = re.match(r"(--[\w-]+)\s*:\s*([^;]+);", stripped)
        if m:
            tokens[m.group(1)] = m.group(2).strip()
    return tokens


def _resolve_hex(palette: dict[str, str], token: str) -> str:
    value = palette[token]
    assert value.startswith("#"), f"{token} must be a hex colour for contrast tests, got {value!r}"
    return value.upper()


@pytest.fixture(scope="module")
def css_root_tokens() -> dict[str, str]:
    return _parse_theme_css_root_tokens()


def test_theme_css_declares_contrast_tokens(css_root_tokens: dict[str, str]):
    for name in (
        "--erp-primary-fill",
        "--erp-primary-fill-hover",
        "--theme-success-text",
        "--theme-warning-text",
    ):
        assert name in css_root_tokens, f"{name} missing from theme.css :root"


def test_light_injection_maps_include_contrast_tokens():
    for name in (
        "--erp-primary-fill",
        "--erp-primary-fill-hover",
        "--theme-success-text",
        "--theme-warning-text",
    ):
        assert name in LIGHT_ROOT_VARS
        assert name in DARK_ROOT_VARS


def test_white_on_primary_fill_light_mode():
    ratio = wcag_contrast("#FFFFFF", _resolve_hex(LIGHT_ROOT_VARS, "--erp-primary-fill"))
    assert ratio >= WCAG_AA_NORMAL, f"light: white on --erp-primary-fill = {ratio:.2f}:1"


def test_white_on_primary_fill_dark_mode():
    ratio = wcag_contrast("#FFFFFF", _resolve_hex(DARK_ROOT_VARS, "--erp-primary-fill"))
    assert ratio >= WCAG_AA_NORMAL, f"dark: white on --erp-primary-fill = {ratio:.2f}:1"


def test_theme_text_on_light_card():
    ratio = wcag_contrast(
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-text"),
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-card"),
    )
    assert ratio >= WCAG_AA_NORMAL, f"light: --theme-text on --theme-card = {ratio:.2f}:1"


def test_theme_muted_on_light_card():
    ratio = wcag_contrast(
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-muted"),
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-card"),
    )
    assert ratio >= WCAG_AA_NORMAL, f"light: --theme-muted on --theme-card = {ratio:.2f}:1"


def test_theme_text_on_light_bg():
    ratio = wcag_contrast(
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-text"),
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-bg"),
    )
    assert ratio >= WCAG_AA_NORMAL, f"light: --theme-text on --theme-bg = {ratio:.2f}:1"


def test_theme_muted_on_light_bg():
    ratio = wcag_contrast(
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-muted"),
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-bg"),
    )
    assert ratio >= WCAG_AA_NORMAL, f"light: --theme-muted on --theme-bg = {ratio:.2f}:1"


def test_success_text_on_light_card():
    ratio = wcag_contrast(
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-success-text"),
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-card"),
    )
    assert ratio >= WCAG_AA_NORMAL, f"light: --theme-success-text on --theme-card = {ratio:.2f}:1"


def test_warning_text_on_light_card():
    ratio = wcag_contrast(
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-warning-text"),
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-card"),
    )
    assert ratio >= WCAG_AA_NORMAL, f"light: --theme-warning-text on --theme-card = {ratio:.2f}:1"


def test_success_text_on_light_bg():
    ratio = wcag_contrast(
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-success-text"),
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-bg"),
    )
    assert ratio >= WCAG_AA_NORMAL, f"light: --theme-success-text on --theme-bg = {ratio:.2f}:1"


def test_warning_text_on_light_bg():
    ratio = wcag_contrast(
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-warning-text"),
        _resolve_hex(LIGHT_ROOT_VARS, "--theme-bg"),
    )
    assert ratio >= WCAG_AA_NORMAL, f"light: --theme-warning-text on --theme-bg = {ratio:.2f}:1"


def test_filled_primary_buttons_use_primary_fill_token():
    widgets = WIDGETS_CSS.read_text(encoding="utf-8")
    block = widgets.split("/* Primary buttons", 1)[1].split("/* UI-1", 1)[0]
    assert "var(--erp-primary-fill)" in block
    assert "background-color: var(--theme-info)" not in block


def test_theme_info_unchanged_for_dark_accent_use():
    """--theme-info stays #3B82F6 in dark injection (links/tints); fill uses deeper blue."""
    assert DARK_ROOT_VARS["--theme-info"].upper() == "#3B82F6"
    assert DARK_ROOT_VARS["--erp-primary-fill"].upper() == "#2563EB"


def test_portal_surface_text_contrast_both_modes():
    """PORTAL-THEME-01 — popover/dialog content renders on --theme-card with
    --theme-text / --theme-caption; both modes must clear WCAG AA normal text."""
    for vars_map, mode in ((LIGHT_ROOT_VARS, "light"), (DARK_ROOT_VARS, "dark")):
        card = _resolve_hex(vars_map, "--theme-card")
        for token in ("--theme-text", "--theme-caption"):
            ratio = wcag_contrast(_resolve_hex(vars_map, token), card)
            assert ratio >= WCAG_AA_NORMAL, (
                f"{mode}: {token} on --theme-card (portal surface) = {ratio:.2f}:1"
            )


def test_portal_primary_button_contrast_both_modes(css_root_tokens: dict[str, str]):
    """PORTAL-THEME-01 — portal primary buttons use --erp-on-primary on --erp-primary-fill.

    --erp-on-primary lives only in theme.css :root (constant across modes, not
    swapped by the injection maps), so it is resolved from the parsed CSS tokens.
    """
    on_primary = _resolve_hex(css_root_tokens, "--erp-on-primary")
    for vars_map, mode in ((LIGHT_ROOT_VARS, "light"), (DARK_ROOT_VARS, "dark")):
        ratio = wcag_contrast(on_primary, _resolve_hex(vars_map, "--erp-primary-fill"))
        assert ratio >= WCAG_AA_NORMAL, (
            f"{mode}: --erp-on-primary on --erp-primary-fill (portal button) = {ratio:.2f}:1"
        )


def test_contrast_ratios_report(capsys):
    """Emit resolved ratios for audit trail (always passes)."""
    light_card = _resolve_hex(LIGHT_ROOT_VARS, "--theme-card")
    light_bg = _resolve_hex(LIGHT_ROOT_VARS, "--theme-bg")
    primary = _resolve_hex(LIGHT_ROOT_VARS, "--erp-primary-fill")
    dark_primary = _resolve_hex(DARK_ROOT_VARS, "--erp-primary-fill")
    pairs = [
        ("white on primary (light)", "#FFFFFF", primary),
        ("white on primary (dark)", "#FFFFFF", dark_primary),
        ("text on card", _resolve_hex(LIGHT_ROOT_VARS, "--theme-text"), light_card),
        ("muted on card", _resolve_hex(LIGHT_ROOT_VARS, "--theme-muted"), light_card),
        ("success-text on card", _resolve_hex(LIGHT_ROOT_VARS, "--theme-success-text"), light_card),
        ("warning-text on card", _resolve_hex(LIGHT_ROOT_VARS, "--theme-warning-text"), light_card),
        ("success-text on bg", _resolve_hex(LIGHT_ROOT_VARS, "--theme-success-text"), light_bg),
        ("warning-text on bg", _resolve_hex(LIGHT_ROOT_VARS, "--theme-warning-text"), light_bg),
    ]
    lines = [f"  {label}: {wcag_contrast(fg, bg):.2f}:1" for label, fg, bg in pairs]
    print("THEME-CONTRAST-01 ratios:\n" + "\n".join(lines))
