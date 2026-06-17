"""FASTAPI-REACT-23 — reconcile/closing pickers + match-type forms contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_23_REACT_WRITE_RECON_FORMS_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_write_contract.py"
    spec = importlib.util.spec_from_file_location("react_write_contract_fr23", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_write_contract_fr23"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Picker inventory",
    "Match-type payload forms",
    "Feature flags",
    "Client validation",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-23 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("rel_path", contract.WRITE_PICKER_FRONTEND_FILES)
def test_picker_frontend_files_exist(rel_path):
    assert (ROOT / rel_path).is_file(), rel_path


def test_new_transaction_page_uses_recon_closing_pickers_and_forms():
    page_src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert "StatementRowPicker" in page_src
    assert "FiscalPeriodPicker" in page_src
    assert "VendorPicker" in page_src
    assert "CoaAccountPicker" in page_src
    assert "Select a statement row." in page_src
    assert "Select a fiscal period." in page_src
    assert "owner_capital" in page_src
    assert "confirm_inferred_fee" in page_src or "Confirm inferred fee" in page_src
    for match_type in contract.ALLOWED_RECONCILIATION_MATCH_TYPES:
        assert match_type in page_src, match_type
    for path in contract.BANK_STATEMENT_ROWS_LIST_READ_API_PATHS:
        picker_src = (ROOT / "frontend/src/components/StatementRowPicker.tsx").read_text(
            encoding="utf-8"
        )
        assert path in picker_src, path
    for path in contract.FISCAL_PERIODS_LIST_READ_API_PATHS:
        picker_src = (ROOT / "frontend/src/components/FiscalPeriodPicker.tsx").read_text(
            encoding="utf-8"
        )
        assert path in picker_src, path
    for path in contract.VENDORS_LIST_READ_API_PATHS:
        picker_src = (ROOT / "frontend/src/components/VendorPicker.tsx").read_text(
            encoding="utf-8"
        )
        assert path in picker_src, path


@pytest.mark.parametrize(
    "api_path",
    contract.BANK_STATEMENT_ROWS_LIST_READ_API_PATHS
    + contract.FISCAL_PERIODS_LIST_READ_API_PATHS
    + contract.VENDORS_LIST_READ_API_PATHS,
)
def test_fr23_api_paths_are_frozen_read_contract(api_path):
    read_contract_path = ROOT / "registry" / "api_read_contract.py"
    spec = importlib.util.spec_from_file_location(
        "api_read_contract_fr23", read_contract_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert api_path in mod.READ_API_PATHS, api_path


def test_roadmap_lists_fastapi_react_23_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-23" in roadmap
    assert "fastapi-react-23-react-write-recon-forms" in roadmap


@pytest.mark.parametrize("item", contract.FR23_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
