"""FASTAPI-REACT-09 — expense write tab contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_09_REACT_WRITE_EXPENSE_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_write_contract.py"
    spec = importlib.util.spec_from_file_location("react_write_contract_fr09", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_write_contract_fr09"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Page inventory",
    "Feature flags",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-09 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


def test_expense_feature_flags_documented(audit_text):
    assert contract.WRITE_EXPENSES_FLAG_ENV in audit_text
    assert contract.API_WRITE_EXPENSES_ENV in audit_text
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert "reactWriteExpensesEnabled" in flags_src
    assert "reactWriteEnabled" in flags_src
    assert contract.WRITE_EXPENSES_FLAG_ENV in flags_src


def test_app_router_mounts_write_page_with_either_write_flag():
    router_src = (ROOT / "frontend/src/routes/AppRouter.tsx").read_text(
        encoding="utf-8"
    )
    assert "reactWriteEnabled" in router_src
    assert "NewTransactionPage" in router_src


def test_new_transaction_page_posts_expense_api():
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    for path in contract.EXPENSE_WRITE_API_PATHS:
        assert path in src, path
    assert "category_name" in src
    assert "Save cash expense" in src
    assert "erp-write-tabs" in src


def test_new_transaction_page_still_posts_sales_api():
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    for path in contract.WRITE_API_PATHS:
        assert path in src, path
    assert "Save cash sale" in src


@pytest.mark.parametrize("api_path", contract.EXPENSE_WRITE_API_PATHS)
def test_expense_api_path_in_route_and_p2_tests(api_path):
    expense_route = (ROOT / "api/routes/expenses.py").read_text(encoding="utf-8")
    assert "post_expense" in expense_route
    p2_src = (ROOT / contract.P2_EXPENSE_WRITE_TEST).read_text(encoding="utf-8")
    assert api_path in p2_src


def test_p2_expense_write_tests_exist():
    assert (ROOT / contract.P2_EXPENSE_WRITE_TEST).is_file()


def test_roadmap_lists_fastapi_react_09_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-09" in roadmap
    assert "fastapi-react-09-react-write-expense" in roadmap


@pytest.mark.parametrize("item", contract.DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
