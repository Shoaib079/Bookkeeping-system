"""MONO-THEME-01-S2 — shared component grammar token contract tests.

Token definitions only: registry + theme.css :root parity. No component migration.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ui.design_tokens import (
    CARD_GRAMMAR_TOKEN_KEYS,
    CHIP_GRAMMAR_EXTENSION_KEYS,
    CHIP_TOKEN_KEYS,
    COMPONENT_GRAMMAR_TOKENS,
    COMPONENT_GRAMMAR_TOKEN_KEYS,
    NAV_GRAMMAR_TOKEN_KEYS,
    TABLE_GRAMMAR_TOKEN_KEYS,
    grammar_values_reference_only,
    parse_css_root_vars,
)

ROOT = Path(__file__).resolve().parents[1]
THEME_CSS = ROOT / "ui" / "theme.css"
AUDIT_DOC = ROOT / "docs" / "MONO_THEME_01_AUDIT.md"

_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}")


@pytest.fixture(scope="module")
def theme_css_text() -> str:
    return THEME_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def root_vars(theme_css_text) -> dict[str, str]:
    return parse_css_root_vars(theme_css_text)


def test_registry_defines_all_grammar_families():
    assert len(NAV_GRAMMAR_TOKEN_KEYS) == 5
    assert len(CARD_GRAMMAR_TOKEN_KEYS) == 5
    assert len(CHIP_GRAMMAR_EXTENSION_KEYS) == 4
    assert len(TABLE_GRAMMAR_TOKEN_KEYS) == 4
    assert COMPONENT_GRAMMAR_TOKEN_KEYS == frozenset(COMPONENT_GRAMMAR_TOKENS)


def test_grammar_values_reference_only_no_raw_hex():
    assert grammar_values_reference_only()
    for key, value in COMPONENT_GRAMMAR_TOKENS.items():
        assert not _HEX_RE.search(value), f"{key} must not introduce raw hex: {value!r}"


def test_chip_semantic_tokens_preserved():
    for key in CHIP_TOKEN_KEYS:
        assert key not in CHIP_GRAMMAR_EXTENSION_KEYS, f"semantic chip key duplicated: {key}"


@pytest.mark.parametrize("key", sorted(COMPONENT_GRAMMAR_TOKENS))
def test_theme_css_grammar_tokens_match_registry(theme_css_text, root_vars, key):
    assert f"{key}:" in theme_css_text, f"{key} missing from theme.css"
    assert key in root_vars, f"{key} missing from :root parse"
    assert root_vars[key] == COMPONENT_GRAMMAR_TOKENS[key], (
        f"{key}: css={root_vars[key]!r} registry={COMPONENT_GRAMMAR_TOKENS[key]!r}"
    )


def test_theme_css_documents_mono_theme_s2_block(theme_css_text):
    assert "MONO-THEME-01-S2" in theme_css_text
    assert "--erp-nav-active-bg:" in theme_css_text
    assert "--erp-table-total-bg:" in theme_css_text


def test_audit_doc_marks_s2_complete():
    text = AUDIT_DOC.read_text(encoding="utf-8")
    assert "MONO-THEME-01-S2" in text
    assert "complete" in text.lower().split("mono-theme-01-s2")[1][:200]
