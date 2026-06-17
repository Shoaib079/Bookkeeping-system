"""UI-SYSTEM-02-S5 — frozen React design contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ui import section as section_module
from ui.design_tokens import DEPRECATED_ROLE_TOKEN_KEYS
from ui.react_design_contract import (
    CONTRACT_DOC,
    KPI_GRID_MODIFIERS,
    REACT_COMPONENTS,
    STREAMLIT_ONLY_SELECTORS,
    react_component_rows,
    react_token_bundle,
    validate_react_design_contract,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / CONTRACT_DOC


REQUIRED_SECTIONS = (
    "Purpose",
    "Contract rules",
    "Token governance",
    "Frozen component map",
    "Streamlit-only selectors",
    "No-change statement",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"React design contract doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_contract_module_exists():
    assert (ROOT / "ui" / "react_design_contract.py").exists()


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing section: {section!r}"


def test_validate_react_design_contract_passes():
    validate_react_design_contract()


def test_doc_lists_all_react_components(doc_text):
    for name, _source, _css in react_component_rows():
        assert name in doc_text, f"Missing React component {name!r} in doc"


def test_portable_helpers_in_section_all():
    portable = [s for s in REACT_COMPONENTS if not s.streamlit_only and s.streamlit_source in section_module.__all__]
    assert len(portable) >= 15
    for spec in portable:
        assert spec.streamlit_source in section_module.__all__
        assert callable(getattr(section_module, spec.streamlit_source))


def test_react_component_names_unique():
    names = [spec.name for spec in REACT_COMPONENTS]
    assert len(names) == len(set(names))


def test_streamlit_only_selectors_documented(doc_text):
    for entry in STREAMLIT_ONLY_SELECTORS:
        assert entry.selector_id in doc_text


def test_streamlit_only_selector_ids_unique():
    ids = [e.selector_id for e in STREAMLIT_ONLY_SELECTORS]
    assert len(ids) == len(set(ids))


def test_react_token_bundle_serializable():
    bundle = react_token_bundle()
    raw = json.dumps(bundle)
    parsed = json.loads(raw)
    assert parsed["version"] == "UI-SYSTEM-02-S5"
    assert "light" in parsed and "dark" in parsed
    assert "spacing" in parsed and "deprecated" in parsed
    assert parsed["grammarVersion"] == "MONO-THEME-01-S7"
    assert "componentGrammar" in parsed
    assert "--erp-nav-active-bg" in parsed["componentGrammar"]


def test_react_token_bundle_grammar_key_families():
    bundle = react_token_bundle()
    for key in (
        "navGrammarKeys",
        "cardGrammarKeys",
        "chipGrammarExtensionKeys",
        "tableGrammarKeys",
    ):
        assert key in bundle
        assert len(bundle[key]) > 0


def test_deprecated_role_tokens_in_bundle():
    bundle = react_token_bundle()
    deprecated = set(bundle["deprecated"])
    assert DEPRECATED_ROLE_TOKEN_KEYS <= deprecated


def test_kpi_grid_modifiers_frozen():
    assert "reports-cf" in KPI_GRID_MODIFIERS
    components = (ROOT / "ui" / "mobile_components.css").read_text(encoding="utf-8")
    assert ".erp-mob-kpi-grid--reports-cf" in components


def test_doc_mentions_registry_and_nav_contract(doc_text):
    low = doc_text.lower()
    assert "ui/react_design_contract.py" in low
    assert "NAV_ARCH_REACT_ROUTE_CONTRACT" in doc_text
    assert "frozen" in low


def test_doc_mentions_design_tokens_ssot(doc_text):
    assert "ui/design_tokens.py" in doc_text
