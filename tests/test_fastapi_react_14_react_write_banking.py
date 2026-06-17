"""FASTAPI-REACT-14 — bank transaction write tab contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_14_REACT_WRITE_BANKING_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_write_contract.py"
    spec = importlib.util.spec_from_file_location("react_write_contract_fr14", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_write_contract_fr14"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Form inventory",
    "Feature flags",
    "Client validation",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-14 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


def test_banking_feature_flags_documented(audit_text):
    assert contract.WRITE_BANKING_FLAG_ENV in audit_text
    assert contract.API_WRITE_BANKING_ENV in audit_text
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert "reactWriteBankingEnabled" in flags_src
    assert contract.WRITE_BANKING_FLAG_ENV in flags_src


def test_react_write_enabled_includes_banking():
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert "reactWriteBankingEnabled()" in flags_src


def test_new_transaction_page_posts_banking_api():
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    for path in contract.BANK_TRANSACTION_WRITE_API_PATHS:
        assert path in src, path
    assert "Bank transaction saved" in src
    assert "transaction_type" in src
    assert "Choose a different destination account for transfer." in src


@pytest.mark.parametrize("txn_type", contract.ALLOWED_BANK_TRANSACTION_TYPES)
def test_bank_transaction_types_in_page_and_audit(audit_text, txn_type):
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert txn_type in audit_text
    assert f'value="{txn_type}"' in src or f"value='{txn_type}'" in src


@pytest.mark.parametrize("api_path", contract.BANK_TRANSACTION_WRITE_API_PATHS)
def test_banking_api_path_in_route_and_p2_tests(api_path):
    route = (ROOT / "api/routes/bank_transactions.py").read_text(encoding="utf-8")
    assert "post_bank_transaction" in route
    p2_src = (ROOT / contract.P2_BANKING_WRITE_TEST).read_text(encoding="utf-8")
    assert api_path in p2_src


def test_p2_banking_write_tests_exist():
    assert (ROOT / contract.P2_BANKING_WRITE_TEST).is_file()


def test_roadmap_lists_fastapi_react_14_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-14" in roadmap
    assert "fastapi-react-14-react-write-banking" in roadmap


@pytest.mark.parametrize("item", contract.DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
