"""BANKING-UX-04-S4 — frozen React banking workflow contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

import app as erp  # noqa: F401 — production import order

from registry.banking_config import BANKING_WORKFLOW_MODE_DEFAULT, BANKING_WORKFLOW_MODE_IDS
from registry.banking_workflow_contract import (
    ADD_TRANSACTION_REACT_PATH,
    AT_BANK_TXN_TYPE_IDX,
    BANKING_SECTION_REACT_ROUTES,
    CONTRACT_DOC,
    SETTING_KEY,
    SETTING_SCOPE,
    WORKFLOW_MODE_SPECS,
    banking_section_react_route,
    validate_banking_workflow_contract,
    workflow_contract_rows,
    workflow_mode_spec,
)
from registry.loader import get_setting_def
from registry.navigation import react_routes

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / CONTRACT_DOC

REQUIRED_SECTIONS = (
    "Purpose",
    "Contract rules",
    "Setting contract",
    "Frozen mode map",
    "Banking section",
    "Add Transaction contract",
    "No-change statement",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"React workflow contract doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_contract_module_exists():
    assert (ROOT / "registry" / "banking_workflow_contract.py").exists()


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing section: {section!r}"


def test_validate_banking_workflow_contract_passes():
    validate_banking_workflow_contract()


def test_doc_lists_all_modes(doc_text):
    for mode_id, label_key, react_default in workflow_contract_rows():
        assert mode_id in doc_text
        assert label_key in doc_text
        assert react_default in doc_text


def test_setting_catalog_matches_contract():
    defn = get_setting_def(SETTING_KEY)
    assert defn.scope == SETTING_SCOPE
    assert defn.default == BANKING_WORKFLOW_MODE_DEFAULT
    assert set(defn.options) == set(BANKING_WORKFLOW_MODE_IDS)
    assert len(WORKFLOW_MODE_SPECS) == len(BANKING_WORKFLOW_MODE_IDS)


def test_banking_section_routes_unique_and_absolute():
    for section, path in BANKING_SECTION_REACT_ROUTES.items():
        assert path.startswith("/banking/")
        assert banking_section_react_route(section) == path
    assert len(BANKING_SECTION_REACT_ROUTES) == len(set(BANKING_SECTION_REACT_ROUTES.values()))


def test_add_transaction_path_aligns_with_nav_registry():
    assert react_routes()["New Transaction"] == ADD_TRANSACTION_REACT_PATH


@pytest.mark.parametrize("mode_id", sorted(BANKING_WORKFLOW_MODE_IDS))
def test_mode_spec_manual_always_reachable(mode_id):
    spec = workflow_mode_spec(mode_id)
    assert "accounts" in spec.banking_section_order or "accounts" in spec.banking_advanced_sections
    assert spec.add_txn_bank_type_in_primary or spec.add_txn_manual_bank_advanced


def test_statement_first_spec_matches_streamlit_intent():
    spec = workflow_mode_spec("statement_first")
    assert "accounts" not in spec.banking_section_order
    assert "accounts" in spec.banking_advanced_sections
    assert spec.add_txn_manual_bank_advanced is True
    assert spec.add_txn_statement_callout == "prominent"


def test_manual_first_defaults_to_accounts_route():
    spec = workflow_mode_spec("manual_first")
    assert spec.banking_default_section == "accounts"
    assert spec.react_default_subroute == "/banking/accounts"


def test_at_bank_type_idx_frozen():
    assert AT_BANK_TXN_TYPE_IDX == 5
