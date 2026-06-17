"""FASTAPI-REACT-08 — first React write page contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_08_REACT_WRITE_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_write_contract.py"
    spec = importlib.util.spec_from_file_location("react_write_contract", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_write_contract"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Page inventory",
    "Feature flags",
    "API client",
    "Boundary",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-08 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("rel_path", contract.REQUIRED_FRONTEND_FILES)
def test_required_frontend_files_exist(rel_path):
    assert (ROOT / rel_path).is_file(), rel_path


@pytest.mark.parametrize("path,component,_key", contract.WRITE_PAGE_ROUTES)
def test_write_routes_documented_in_audit(audit_text, path, component, _key):
    assert path in audit_text
    assert component in audit_text


def test_feature_flags_documented(audit_text):
    assert contract.READ_PAGES_FLAG_ENV in audit_text
    assert contract.WRITE_SALES_FLAG_ENV in audit_text
    assert contract.API_WRITE_SALES_ENV in audit_text
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert "reactWriteSalesEnabled" in flags_src
    assert contract.WRITE_SALES_FLAG_ENV in flags_src


def test_app_router_wires_write_page_behind_dual_flags():
    router_src = (ROOT / "frontend/src/routes/AppRouter.tsx").read_text(
        encoding="utf-8"
    )
    assert "NewTransactionPage" in router_src
    assert "reactWriteSalesEnabled" in router_src
    assert "reactPagesEnabled" in router_src


def test_new_transaction_page_posts_sales_api():
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    for path in contract.WRITE_API_PATHS:
        assert path in src, path
    assert 'payment_method: "Cash"' in src or "payment_method: 'Cash'" in src
    assert contract.WRITE_METHOD_NAME in src


def test_write_client_is_post_only():
    src = (ROOT / contract.WRITE_CLIENT_MODULE).read_text(encoding="utf-8")
    assert 'method: "POST"' in src
    assert "Authorization" in src
    assert "X-Company-Id" in src
    assert "apiPut" not in src
    assert "apiDelete" not in src


def test_api_post_defined_only_in_write_client_module():
    src_root = ROOT / "frontend/src"
    for path in src_root.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        text = path.read_text(encoding="utf-8")
        if "export async function apiPost" in text:
            assert rel == contract.WRITE_CLIENT_MODULE, rel


@pytest.mark.parametrize("api_path", contract.WRITE_API_PATHS)
def test_write_api_path_in_sales_route_and_p2_tests(api_path):
    sales_route = (ROOT / "api/routes/sales.py").read_text(encoding="utf-8")
    assert "post_sale" in sales_route
    p2_src = (ROOT / contract.P2_SALES_WRITE_TEST).read_text(encoding="utf-8")
    assert api_path in p2_src


def test_p2_sales_write_tests_exist():
    assert (ROOT / contract.P2_SALES_WRITE_TEST).is_file()


def test_frontend_has_no_forbidden_patterns():
    src_root = ROOT / "frontend/src"
    combined = "\n".join(
        p.read_text(encoding="utf-8")
        for p in src_root.rglob("*")
        if p.suffix in {".ts", ".tsx", ".css"}
    ).lower()
    for pattern in contract.FORBIDDEN_FRONTEND_PATTERNS:
        assert pattern.lower() not in combined, pattern


def test_roadmap_lists_fastapi_react_08_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-08" in roadmap
    assert "fastapi-react-08-react-write" in roadmap


@pytest.mark.parametrize("item", contract.DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
