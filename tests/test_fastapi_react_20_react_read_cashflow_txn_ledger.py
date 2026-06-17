"""FASTAPI-REACT-20 — cash flow + transaction ledger contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_20_REACT_READ_CASHFLOW_TXN_LEDGER_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_pages_contract.py"
    spec = importlib.util.spec_from_file_location("react_pages_contract_fr20", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_pages_contract_fr20"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Page inventory",
    "Feature flag",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-20 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("path,component,_key", contract.FR20_REAL_PAGE_ROUTES)
def test_real_page_routes_documented_in_audit(audit_text, path, component, _key):
    assert path in audit_text
    assert component in audit_text


@pytest.mark.parametrize("path,component,_key", contract.FR20_REAL_PAGE_ROUTES)
def test_real_page_routes_have_page_files(path, component, _key):
    assert (ROOT / f"frontend/src/pages/{component}.tsx").is_file(), component


def test_app_router_wires_fr20_read_pages():
    router_src = (ROOT / "frontend/src/routes/AppRouter.tsx").read_text(
        encoding="utf-8"
    )
    for _path, component, _key in contract.FR20_REAL_PAGE_ROUTES:
        assert component in router_src


def test_cash_flow_page_calls_p1_read_api():
    src = (ROOT / "frontend/src/pages/CashFlowPage.tsx").read_text(encoding="utf-8")
    for path in contract.CASH_FLOW_READ_API_PATHS:
        assert path in src, path
    assert "companyScoped: true" in src


def test_transaction_ledger_page_calls_p1_read_api():
    src = (ROOT / "frontend/src/pages/TransactionLedgerPage.tsx").read_text(
        encoding="utf-8"
    )
    for path in contract.TRANSACTION_LEDGER_READ_API_PATHS:
        assert path in src, path
    assert "companyScoped: true" in src


@pytest.mark.parametrize(
    "api_path",
    contract.CASH_FLOW_READ_API_PATHS + contract.TRANSACTION_LEDGER_READ_API_PATHS,
)
def test_fr20_api_paths_are_frozen_read_contract(api_path):
    read_contract_path = ROOT / contract.READ_CONTRACT
    spec = importlib.util.spec_from_file_location(
        "api_read_contract_fr20", read_contract_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert api_path in mod.READ_API_PATHS, api_path


def test_read_transaction_history_service_exists():
    assert (ROOT / "services/read_transaction_history.py").is_file()


def test_app_txh_fetch_delegates_to_read_service():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "read_transaction_history" in src
    assert "fetch_filtered_rows_with_sources" in src


def test_roadmap_lists_fastapi_react_20_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-20" in roadmap
    assert "fastapi-react-20-react-read-cashflow-txn-ledger" in roadmap


@pytest.mark.parametrize("item", contract.DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
