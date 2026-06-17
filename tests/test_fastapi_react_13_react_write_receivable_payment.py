"""FASTAPI-REACT-13 — receivable payment write tab contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_13_REACT_WRITE_RECEIVABLE_PAYMENT_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_write_contract.py"
    spec = importlib.util.spec_from_file_location("react_write_contract_fr13", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_write_contract_fr13"] = mod
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
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-13 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


def test_receivable_feature_flags_documented(audit_text):
    assert contract.WRITE_RECEIVABLE_PAYMENTS_FLAG_ENV in audit_text
    assert contract.API_WRITE_RECEIVABLE_PAYMENTS_ENV in audit_text
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert "reactWriteReceivablePaymentsEnabled" in flags_src
    assert contract.WRITE_RECEIVABLE_PAYMENTS_FLAG_ENV in flags_src


def test_react_write_enabled_includes_receivable_payments():
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert "reactWriteReceivablePaymentsEnabled()" in flags_src


def test_new_transaction_page_posts_receivable_api():
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    for path in contract.RECEIVABLE_PAYMENT_WRITE_API_PATHS:
        assert path in src, path
    assert "Payment recorded" in src
    assert "sale_id" in src
    assert "No bank account selected." in src


@pytest.mark.parametrize("method", contract.ALLOWED_RECEIVABLE_PAYMENT_METHODS)
def test_receivable_payment_methods_in_page_and_audit(audit_text, method):
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert method in audit_text
    assert f'value="{method}"' in src or f"value='{method}'" in src


@pytest.mark.parametrize("api_path", contract.RECEIVABLE_PAYMENT_WRITE_API_PATHS)
def test_receivable_api_path_in_route_and_p2_tests(api_path):
    route = (ROOT / "api/routes/receivable_payments.py").read_text(encoding="utf-8")
    assert "post_receivable_payment" in route
    p2_src = (ROOT / contract.P2_RECEIVABLE_PAYMENT_WRITE_TEST).read_text(
        encoding="utf-8"
    )
    assert api_path in p2_src


def test_p2_receivable_payment_write_tests_exist():
    assert (ROOT / contract.P2_RECEIVABLE_PAYMENT_WRITE_TEST).is_file()


def test_roadmap_lists_fastapi_react_13_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-13" in roadmap
    assert "fastapi-react-13-react-write-receivable-payment" in roadmap


@pytest.mark.parametrize("item", contract.FR13_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
