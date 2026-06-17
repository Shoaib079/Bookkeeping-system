"""FASTAPI-REACT-10 — payment method expansion contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_10_REACT_WRITE_PAYMENT_METHODS_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_write_contract.py"
    spec = importlib.util.spec_from_file_location("react_write_contract_fr10", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_write_contract_fr10"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Form inventory",
    "Client validation",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-10 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("method", contract.ALLOWED_SALE_PAYMENT_METHODS)
def test_sale_payment_methods_in_page_and_audit(audit_text, method):
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert method in audit_text
    assert f'value="{method}"' in src or f"value='{method}'" in src


@pytest.mark.parametrize("method", contract.ALLOWED_EXPENSE_PAYMENT_METHODS)
def test_expense_payment_methods_in_page_and_audit(audit_text, method):
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert method in audit_text
    assert f'value="{method}"' in src or f"value='{method}'" in src


@pytest.mark.parametrize("field", contract.SALE_PAYMENT_OPTIONAL_FIELDS)
def test_sale_optional_fields_in_page(audit_text, field):
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert field in audit_text
    assert field in src


@pytest.mark.parametrize("field", contract.EXPENSE_PAYMENT_OPTIONAL_FIELDS)
def test_expense_optional_fields_in_page(audit_text, field):
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert field in audit_text
    assert field in src


def test_credit_customer_validation_pinned():
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert "Walk-in Customer" in src
    assert "on-account (credit) sales" in src


def test_p2_sales_supports_card_and_credit():
    p2_src = (ROOT / contract.P2_SALES_WRITE_TEST).read_text(encoding="utf-8")
    assert 'payment_method="Card"' in p2_src or '"Card"' in p2_src
    assert 'payment_method="Credit"' in p2_src or '"Credit"' in p2_src
    assert "card_bank_account_id" in p2_src


def test_p2_expense_supports_bank():
    p2_src = (ROOT / contract.P2_EXPENSE_WRITE_TEST).read_text(encoding="utf-8")
    assert 'payment_method="Bank"' in p2_src or '"Bank"' in p2_src
    assert "bank_account_id" in p2_src


def test_roadmap_lists_fastapi_react_10_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-10" in roadmap
    assert "fastapi-react-10-react-write-payment-methods" in roadmap


@pytest.mark.parametrize("item", contract.FR10_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
