"""FASTAPI-REACT-06 — first React pages contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_06_REACT_PAGES_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_pages_contract.py"
    spec = importlib.util.spec_from_file_location("react_pages_contract", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_pages_contract"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Page inventory",
    "Feature flag",
    "API client",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-06 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("rel_path", contract.REQUIRED_FRONTEND_FILES)
def test_required_frontend_files_exist(rel_path):
    assert (ROOT / rel_path).is_file(), rel_path


@pytest.mark.parametrize("path,component,_key", contract.FR06_REAL_PAGE_ROUTES)
def test_real_page_routes_documented_in_audit(audit_text, path, component, _key):
    assert path in audit_text
    assert component in audit_text


def test_feature_flag_documented_in_audit_and_code(audit_text):
    assert contract.FEATURE_FLAG_ENV in audit_text
    assert contract.VITE_FEATURE_FLAG_ENV in audit_text
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert contract.VITE_FEATURE_FLAG_ENV in flags_src
    assert "reactPagesEnabled" in flags_src


def test_app_router_wires_real_pages_behind_flag():
    router_src = (ROOT / "frontend/src/routes/AppRouter.tsx").read_text(
        encoding="utf-8"
    )
    assert "reactPagesEnabled" in router_src
    assert "HomePage" in router_src
    assert "LedgerPage" in router_src
    assert "PlaceholderPage" in router_src
    for _path, component, _key in contract.REAL_PAGE_ROUTES:
        assert component in router_src


def test_home_page_calls_p1_read_apis():
    src = (ROOT / "frontend/src/pages/HomePage.tsx").read_text(encoding="utf-8")
    for path in contract.HOME_READ_API_PATHS:
        assert path in src, path
    assert "X-Company-Id" not in src or "companyScoped: true" in src


def test_ledger_page_calls_p1_read_api():
    src = (ROOT / "frontend/src/pages/LedgerPage.tsx").read_text(encoding="utf-8")
    for path in contract.LEDGER_READ_API_PATHS:
        assert path in src, path
    assert "companyScoped: true" in src


def test_api_client_is_get_only():
    src = (ROOT / "frontend/src/lib/api/client.ts").read_text(encoding="utf-8")
    assert 'method: "GET"' in src
    assert "Authorization" in src
    assert "X-Company-Id" in src


def test_desktop_shell_ledger_link_matches_contract():
    src = (ROOT / "frontend/src/layouts/DesktopShell.tsx").read_text(encoding="utf-8")
    assert "/books/general-ledger" in src


@pytest.mark.parametrize("api_path", contract.HOME_READ_API_PATHS + contract.LEDGER_READ_API_PATHS)
def test_page_api_paths_are_frozen_read_contract(api_path):
    read_contract_path = ROOT / contract.READ_CONTRACT
    spec = importlib.util.spec_from_file_location(
        "api_read_contract_fr06", read_contract_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    normalized = api_path.split("?")[0]
    assert normalized in mod.READ_API_PATHS, normalized


def test_frontend_has_no_forbidden_patterns():
    src_root = ROOT / "frontend/src"
    combined = "\n".join(
        p.read_text(encoding="utf-8")
        for p in src_root.rglob("*")
        if p.suffix in {".ts", ".tsx", ".css"}
    ).lower()
    for pattern in contract.FORBIDDEN_FRONTEND_PATTERNS:
        assert pattern.lower() not in combined, pattern


def test_roadmap_lists_fastapi_react_06_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-06" in roadmap
    assert "fastapi-react-06-react-pages" in roadmap


@pytest.mark.parametrize("item", contract.FR06_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
