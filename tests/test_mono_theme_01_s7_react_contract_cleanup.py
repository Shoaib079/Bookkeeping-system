"""MONO-THEME-01-S7 — React grammar contract export + role-hue cleanup."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ui.design_tokens import (
    CARD_GRAMMAR_TOKEN_KEYS,
    CHIP_GRAMMAR_EXTENSION_KEYS,
    COMPONENT_GRAMMAR_TOKENS,
    DEPRECATED_ROLE_TOKEN_KEYS,
    NAV_GRAMMAR_TOKEN_KEYS,
    TABLE_GRAMMAR_TOKEN_KEYS,
)
from ui.react_design_contract import (
    GRAMMAR_CONTRACT_VERSION,
    react_token_bundle,
    validate_react_design_contract,
)

ROOT = Path(__file__).resolve().parents[1]
AUTH_CSS = ROOT / "ui" / "auth.css"
CONTRACT_DOC = ROOT / "docs" / "UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md"
AUDIT_DOC = ROOT / "docs" / "MONO_THEME_01_AUDIT.md"


@pytest.fixture(scope="module")
def auth_css() -> str:
    return AUTH_CSS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def contract_doc() -> str:
    return CONTRACT_DOC.read_text(encoding="utf-8")


def test_auth_css_has_no_role_hue_references(auth_css):
    assert "var(--role-" not in auth_css
    assert "MONO-THEME-01-S7" in auth_css


def test_react_token_bundle_exports_grammar_families():
    bundle = react_token_bundle()
    assert bundle["grammarVersion"] == GRAMMAR_CONTRACT_VERSION
    assert set(bundle["componentGrammar"]) == set(COMPONENT_GRAMMAR_TOKENS)
    assert tuple(bundle["navGrammarKeys"]) == NAV_GRAMMAR_TOKEN_KEYS
    assert tuple(bundle["cardGrammarKeys"]) == CARD_GRAMMAR_TOKEN_KEYS
    assert tuple(bundle["chipGrammarExtensionKeys"]) == CHIP_GRAMMAR_EXTENSION_KEYS
    assert tuple(bundle["tableGrammarKeys"]) == TABLE_GRAMMAR_TOKEN_KEYS


def test_react_token_bundle_grammar_serializable():
    bundle = react_token_bundle()
    parsed = json.loads(json.dumps(bundle))
    assert parsed["grammarVersion"] == GRAMMAR_CONTRACT_VERSION
    assert "--erp-nav-active-bg" in parsed["componentGrammar"]
    assert "--erp-card-bg" in parsed["componentGrammar"]
    assert "--erp-table-border" in parsed["componentGrammar"]


def test_deprecated_role_tokens_still_in_bundle():
    bundle = react_token_bundle()
    deprecated = set(bundle["deprecated"])
    assert DEPRECATED_ROLE_TOKEN_KEYS <= deprecated


def test_validate_react_design_contract_passes():
    validate_react_design_contract()


def test_contract_doc_records_grammar_export(contract_doc):
    assert "componentGrammar" in contract_doc
    assert "grammarVersion" in contract_doc
    assert "MONO-THEME-01-S7" in contract_doc
    assert "navGrammarKeys" in contract_doc


def test_audit_doc_marks_s7_complete():
    text = AUDIT_DOC.read_text(encoding="utf-8")
    assert "MONO-THEME-01-S7" in text
    assert "✅ **Complete**" in text.split("MONO-THEME-01-S7")[1][:400]
