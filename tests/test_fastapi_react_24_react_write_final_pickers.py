"""FASTAPI-REACT-24 — receivable sale + allocation picker contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_24_REACT_WRITE_FINAL_PICKERS_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_write_contract.py"
    spec = importlib.util.spec_from_file_location("react_write_contract_fr24", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_write_contract_fr24"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Picker inventory",
    "Feature flags",
    "Client validation",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-24 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("rel_path", contract.WRITE_PICKER_FRONTEND_FILES)
def test_picker_frontend_files_exist(rel_path):
    assert (ROOT / rel_path).is_file(), rel_path


def test_new_transaction_page_uses_final_write_pickers():
    page_src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert "ReceivableSalePicker" in page_src
    assert "ProfitAllocationPicker" in page_src
    assert "Select a credit sale." in page_src
    assert "Select a profit allocation." in page_src
    receivable_picker_src = (
        ROOT / "frontend/src/components/ReceivableSalePicker.tsx"
    ).read_text(encoding="utf-8")
    allocation_picker_src = (
        ROOT / "frontend/src/components/ProfitAllocationPicker.tsx"
    ).read_text(encoding="utf-8")
    for path in contract.RECEIVABLE_SALES_LIST_READ_API_PATHS:
        assert path in receivable_picker_src, path
    for path in contract.PROFIT_ALLOCATIONS_LIST_READ_API_PATHS:
        assert path in allocation_picker_src, path


@pytest.mark.parametrize(
    "api_path",
    contract.RECEIVABLE_SALES_LIST_READ_API_PATHS
    + contract.PROFIT_ALLOCATIONS_LIST_READ_API_PATHS,
)
def test_fr24_api_paths_are_frozen_read_contract(api_path):
    read_contract_path = ROOT / "registry" / "api_read_contract.py"
    spec = importlib.util.spec_from_file_location(
        "api_read_contract_fr24", read_contract_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert api_path in mod.READ_API_PATHS, api_path


def test_roadmap_lists_fastapi_react_24_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-24" in roadmap
    assert "fastapi-react-24-react-write-final-pickers" in roadmap


@pytest.mark.parametrize("item", contract.DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
