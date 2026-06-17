"""UI-SYSTEM-02-S2 — design token registry contract tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ui.design_tokens import (
    CHIP_TOKEN_KEYS,
    DARK_COLOR_TOKENS,
    DEPRECATED_ROLE_TOKEN_VALUES,
    INJECTABLE_COLOR_KEYS,
    LAYOUT_TOKENS,
    LIGHT_COLOR_TOKENS,
    MOBILE_HEADER_LAYOUT_TOKENS,
    RADIUS_TOKENS,
    SCALE_TOKEN_KEYS,
    SHADOW_TOKENS,
    SYSTEM_DARK_MEDIA_COLOR_TOKENS,
    SPACING_TOKENS,
    TYPOGRAPHY_TOKENS,
    build_dark_root_vars,
    build_light_root_vars,
    color_values_match,
    normalize_hex,
    parse_css_root_vars,
    parse_system_dark_media_vars,
)
from ui.theme import DARK_ROOT_VARS, LIGHT_ROOT_VARS

ROOT = Path(__file__).resolve().parents[1]
THEME_CSS = ROOT / "ui" / "theme.css"
MOBILE_HEADER_CSS = ROOT / "ui" / "mobile_header.css"


@pytest.fixture(scope="module")
def theme_css_text() -> str:
    return THEME_CSS.read_text(encoding="utf-8")


def test_registry_module_exists():
    assert (ROOT / "ui" / "design_tokens.py").exists()


def test_theme_py_derives_from_registry():
    assert LIGHT_ROOT_VARS == build_light_root_vars()
    assert DARK_ROOT_VARS == build_dark_root_vars()


def test_light_and_dark_share_injectable_keys():
    assert set(LIGHT_ROOT_VARS) == set(DARK_ROOT_VARS)
    assert set(LIGHT_ROOT_VARS) == INJECTABLE_COLOR_KEYS


@pytest.mark.parametrize("key", sorted(LIGHT_COLOR_TOKENS))
def test_theme_css_light_colors_match_registry(theme_css_text, key):
    root = parse_css_root_vars(theme_css_text)
    assert key in root, f"{key} missing from theme.css :root"
    assert color_values_match(root[key], LIGHT_COLOR_TOKENS[key]), (
        f"{key}: css={root[key]!r} registry={LIGHT_COLOR_TOKENS[key]!r}"
    )


@pytest.mark.parametrize("key", sorted(SYSTEM_DARK_MEDIA_COLOR_TOKENS))
def test_theme_css_system_dark_media_matches_registry(theme_css_text, key):
    media = parse_system_dark_media_vars(theme_css_text)
    assert key in media, f"{key} missing from @media (prefers-color-scheme: dark)"
    assert color_values_match(media[key], SYSTEM_DARK_MEDIA_COLOR_TOKENS[key]), (
        f"{key}: css={media[key]!r} registry={SYSTEM_DARK_MEDIA_COLOR_TOKENS[key]!r}"
    )


@pytest.mark.parametrize("key", sorted(LAYOUT_TOKENS))
def test_theme_css_layout_tokens_match_registry(theme_css_text, key):
    root = parse_css_root_vars(theme_css_text)
    assert root.get(key) == LAYOUT_TOKENS[key]


@pytest.mark.parametrize("key", sorted(SCALE_TOKEN_KEYS))
def test_theme_css_scale_tokens_present(theme_css_text, key):
    root = parse_css_root_vars(theme_css_text)
    expected = (
        SPACING_TOKENS.get(key)
        or RADIUS_TOKENS.get(key)
        or SHADOW_TOKENS.get(key)
        or TYPOGRAPHY_TOKENS.get(key)
    )
    assert root.get(key) == expected


def test_chip_token_keys_documented_in_css(theme_css_text):
    for key in CHIP_TOKEN_KEYS:
        assert f"{key}:" in theme_css_text


def test_deprecated_role_tokens_still_in_css_for_compat(theme_css_text):
    root = parse_css_root_vars(theme_css_text)
    for key, val in DEPRECATED_ROLE_TOKEN_VALUES.items():
        assert key in root
        assert normalize_hex(root[key]) == normalize_hex(val)


def test_hdr_h_mobile_conflict_resolved(theme_css_text):
    """UI-02-C1 — theme.css must not assign mobile --hdr-h: 120px."""
    mobile_chunk = theme_css_text.split("@media (max-width: 968px)", 1)[-1][:5000]
    for line in mobile_chunk.splitlines():
        stripped = line.strip()
        if stripped.startswith("/*") or stripped.startswith("*"):
            continue
        assert "--hdr-h: 120px" not in stripped and "--hdr-h:120px" not in stripped.replace(" ", "")
    assert "--hdr-h: 60px" in theme_css_text


def test_mobile_header_tokens_match_registry():
    header = MOBILE_HEADER_CSS.read_text(encoding="utf-8")
    for key, val in MOBILE_HEADER_LAYOUT_TOKENS.items():
        if key == "--hdr-h":
            assert f"{key}: {val}" in header or f"{key}:{val}" in header.replace(" ", "")
        else:
            assert key in header
            assert val in header


def test_theme_css_no_mobile_block_container_padding_top(theme_css_text):
    """block-container padding-top on mobile is owned by mobile_header.css (M2)."""
    mobile_chunk = theme_css_text.split("@media (max-width: 968px)", 1)[-1][:4000]
    assert not re.search(
        r"\.block-container\s*\{[^}]*padding-top\s*:",
        mobile_chunk,
        flags=re.IGNORECASE | re.DOTALL,
    )


def test_registry_exports_documented_keys():
    assert "--erp-space-3" in SPACING_TOKENS
    assert "--erp-radius-md" in RADIUS_TOKENS
    assert "--erp-shadow-md" in SHADOW_TOKENS
    assert "--erp-font-body" in TYPOGRAPHY_TOKENS
