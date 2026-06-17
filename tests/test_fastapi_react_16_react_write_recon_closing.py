"""FASTAPI-REACT-16 — reconciliation/closing write tab contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_16_REACT_WRITE_RECON_CLOSING_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_write_contract.py"
    spec = importlib.util.spec_from_file_location("react_write_contract_fr16", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_write_contract_fr16"] = mod
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
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-16 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


def test_recon_closing_feature_flags_documented(audit_text):
    assert contract.WRITE_RECONCILIATION_FLAG_ENV in audit_text
    assert contract.WRITE_CLOSING_FLAG_ENV in audit_text
    assert contract.API_WRITE_RECONCILIATION_ENV in audit_text
    assert contract.API_WRITE_CLOSING_ENV in audit_text
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert "reactWriteReconciliationEnabled" in flags_src
    assert "reactWriteClosingEnabled" in flags_src


def test_react_write_enabled_includes_recon_and_closing():
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert "reactWriteReconciliationEnabled()" in flags_src
    assert "reactWriteClosingEnabled()" in flags_src


def test_new_transaction_page_posts_recon_and_closing_apis():
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    for path in contract.RECONCILIATION_WRITE_API_PATHS:
        assert path in src, path
    assert "/api/v1/periods/" in src
    assert "/close" in src
    assert "/api/v1/profit-allocations" in src
    assert "Statement row matched" in src
    assert "Period closed" in src
    assert "Void reason is required." in src


@pytest.mark.parametrize("match_type", contract.ALLOWED_RECONCILIATION_MATCH_TYPES)
def test_reconciliation_match_types_in_page_and_audit(audit_text, match_type):
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert match_type in audit_text
    assert f'value="{match_type}"' in src or f"value='{match_type}'" in src


@pytest.mark.parametrize("api_path", contract.RECONCILIATION_WRITE_API_PATHS)
def test_reconciliation_api_path_in_route_and_p2_tests(api_path):
    route = (ROOT / "api/routes/reconciliation.py").read_text(encoding="utf-8")
    assert "post_reconciliation" in route
    p2_src = (ROOT / contract.P2_RECONCILIATION_WRITE_TEST).read_text(encoding="utf-8")
    assert api_path in p2_src


@pytest.mark.parametrize("api_path", contract.CLOSING_WRITE_API_PATHS)
def test_closing_api_path_in_route_and_p2_tests(api_path):
    route = (ROOT / "api/routes/closing.py").read_text(encoding="utf-8")
    assert "post_" in route
    p2_src = (ROOT / contract.P2_CLOSING_WRITE_TEST).read_text(encoding="utf-8")
    assert api_path in p2_src


def test_p2_reconciliation_and_closing_write_tests_exist():
    assert (ROOT / contract.P2_RECONCILIATION_WRITE_TEST).is_file()
    assert (ROOT / contract.P2_CLOSING_WRITE_TEST).is_file()


def test_roadmap_lists_fastapi_react_16_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-16" in roadmap
    assert "fastapi-react-16-react-write-recon-closing" in roadmap


@pytest.mark.parametrize("item", contract.FR16_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
