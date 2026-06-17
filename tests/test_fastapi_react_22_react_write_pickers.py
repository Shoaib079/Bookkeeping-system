"""FASTAPI-REACT-22 — bank/worker/partner write picker contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_22_REACT_WRITE_PICKERS_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_write_contract.py"
    spec = importlib.util.spec_from_file_location("react_write_contract_fr22", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_write_contract_fr22"] = mod
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
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-22 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("rel_path", contract.WRITE_PICKER_FRONTEND_FILES)
def test_picker_frontend_files_exist(rel_path):
    assert (ROOT / rel_path).is_file(), rel_path


def test_new_transaction_page_uses_write_pickers():
    page_src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert "BankAccountPicker" in page_src
    assert "WorkerPicker" in page_src
    assert "PartnerPicker" in page_src
    assert 'type="number"' in page_src
    bank_picker_src = (
        ROOT / "frontend/src/components/BankAccountPicker.tsx"
    ).read_text(encoding="utf-8")
    worker_picker_src = (ROOT / "frontend/src/components/WorkerPicker.tsx").read_text(
        encoding="utf-8"
    )
    partner_picker_src = (
        ROOT / "frontend/src/components/PartnerPicker.tsx"
    ).read_text(encoding="utf-8")
    for path in contract.BANK_ACCOUNTS_LIST_READ_API_PATHS:
        assert path in bank_picker_src, path
    for path in contract.WORKERS_LIST_READ_API_PATHS:
        assert path in worker_picker_src, path
    for path in contract.PARTNERS_LIST_READ_API_PATHS:
        assert path in partner_picker_src, path
    assert "No bank account selected." in page_src
    assert "Select a partner." in page_src
    assert "Select a worker." in page_src


@pytest.mark.parametrize("api_path", contract.WRITE_PICKER_READ_API_PATHS)
def test_fr22_api_paths_are_frozen_read_contract(api_path):
    read_contract_path = ROOT / "registry" / "api_read_contract.py"
    spec = importlib.util.spec_from_file_location(
        "api_read_contract_fr22", read_contract_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert api_path in mod.READ_API_PATHS, api_path


def test_write_client_still_post_only():
    src = (ROOT / contract.WRITE_CLIENT_MODULE).read_text(encoding="utf-8")
    assert "apiPost" in src
    for forbidden in contract.FORBIDDEN_FRONTEND_PATTERNS:
        assert forbidden not in src, forbidden


def test_roadmap_lists_fastapi_react_22_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-22" in roadmap
    assert "fastapi-react-22-react-write-pickers" in roadmap


@pytest.mark.parametrize("item", contract.DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
