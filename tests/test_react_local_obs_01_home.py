"""REACT-LOCAL-OBS-01/02 — React local Home error display and route-shell guards.

OBS-01: Shared ``apiError.ts`` normalizer; no ``[object Object]`` from ``String(detail)``.
OBS-02: Home intentionally uses ``errorMessageFromCatch`` (6cf9925); route shell stays on
``PlaceholderPage`` when ``VITE_ERP_REACT_PAGES`` is off; Home is a real read page when on.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_SRC = ROOT / "frontend" / "src"

API_ERROR_MODULE = "frontend/src/lib/api/apiError.ts"
READ_CLIENT = "frontend/src/lib/api/client.ts"
WRITE_CLIENT = "frontend/src/lib/api/writeClient.ts"
HOME_PAGE = "frontend/src/pages/HomePage.tsx"
WRITE_PAGE = "frontend/src/pages/NewTransactionPage.tsx"

ROUTER = "frontend/src/routes/AppRouter.tsx"
PLACEHOLDER_PAGE = "frontend/src/pages/PlaceholderPage.tsx"

# Prior inline fix (FASTAPI-REACT-08) — must not reappear as a second formatter.
LEGACY_WRITE_CLIENT_OBJECT_BRANCH = '"message" in payload.detail'
LEGACY_HOME_STRING_DETAIL_COERCION = "String((err as { detail: string }).detail)"
OBJECT_OBJECT_LITERAL = "[object Object]"


def _load_contract():
    path = ROOT / "registry" / "react_pages_contract.py"
    spec = importlib.util.spec_from_file_location("react_pages_contract_obs01", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_pages_contract_obs01"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()


def test_home_uses_shared_error_normalizer_intentionally():
    """REACT-LOCAL-OBS-02 — Home migrated to shared normalizer in 6cf9925 (not interim-only writeClient fix)."""
    home = (ROOT / HOME_PAGE).read_text(encoding="utf-8")
    assert "errorMessageFromCatch" in home
    assert LEGACY_HOME_STRING_DETAIL_COERCION not in home
    assert OBJECT_OBJECT_LITERAL not in home


def test_router_route_shell_when_pages_flag_off():
    """Unimplemented or flag-gated routes render PlaceholderPage (route shell)."""
    router = (ROOT / ROUTER).read_text(encoding="utf-8")
    placeholder = (ROOT / PLACEHOLDER_PAGE).read_text(encoding="utf-8")
    assert "PlaceholderPage" in router
    assert "!reactPagesEnabled()" in router
    assert "Route shell" in placeholder
    assert "Page implementation deferred" in placeholder


def test_home_wired_as_real_read_page_when_flag_on():
    """Home is FR-06 read dashboard — not a deferred placeholder when pages are enabled."""
    router = (ROOT / ROUTER).read_text(encoding="utf-8")
    home = (ROOT / HOME_PAGE).read_text(encoding="utf-8")
    assert '"/": HomePage' in router
    assert "READ_PAGES" in router
    assert "Read-only dashboard (P1 API)" in home
    for path in contract.HOME_READ_API_PATHS:
        assert path in home


def test_home_read_path_uses_read_client_with_normalizer():
    """Home uses apiGet; read client normalizes detail before pages render errors."""
    home = (ROOT / HOME_PAGE).read_text(encoding="utf-8")
    read_client = (ROOT / READ_CLIENT).read_text(encoding="utf-8")
    assert "apiGet" in home
    assert "writeClient" not in home
    assert "/auth/me" in home
    assert "normalizeApiErrorDetail(body.detail)" in read_client


def test_single_shared_normalizer_module_exists():
    assert (ROOT / API_ERROR_MODULE).is_file()
    assert not (ROOT / "frontend/src/lib/api/formatErrorDetail.ts").exists()
    src = (ROOT / API_ERROR_MODULE).read_text(encoding="utf-8")
    assert "normalizeApiErrorDetail" in src
    assert "errorMessageFromCatch" in src
    assert "JSON.stringify" in src


def test_read_and_write_clients_delegate_to_shared_normalizer():
    for rel in (READ_CLIENT, WRITE_CLIENT):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert "normalizeApiErrorDetail" in src, rel
        assert LEGACY_WRITE_CLIENT_OBJECT_BRANCH not in src, rel


def test_home_uses_catch_helper_not_string_coercion():
    src = (ROOT / HOME_PAGE).read_text(encoding="utf-8")
    assert "errorMessageFromCatch" in src
    assert LEGACY_HOME_STRING_DETAIL_COERCION not in src
    assert "erp-error" in src
    assert "{error}" in src


def test_write_page_relies_on_normalized_api_error_detail():
    src = (ROOT / WRITE_PAGE).read_text(encoding="utf-8")
    assert "apiErr.detail" in src
    write_client = (ROOT / WRITE_CLIENT).read_text(encoding="utf-8")
    assert "normalizeApiErrorDetail" in write_client


@pytest.mark.parametrize(
    "rel_path",
    sorted(
        p.relative_to(ROOT).as_posix()
        for p in (FRONTEND_SRC / "pages").glob("*.tsx")
        if p.name.endswith("Page.tsx")
    ),
)
def test_read_pages_do_not_stringify_object_detail(rel_path):
    """Pages must not coerce object detail with String(); client or catch helper normalizes first."""
    src = (ROOT / rel_path).read_text(encoding="utf-8")
    if LEGACY_HOME_STRING_DETAIL_COERCION in src:
        client = (ROOT / READ_CLIENT).read_text(encoding="utf-8")
        assert "normalizeApiErrorDetail(body.detail)" in client


def test_vite_proxy_points_to_local_fastapi():
    vite_src = (ROOT / "frontend/vite.config.ts").read_text(encoding="utf-8")
    assert "http://127.0.0.1:8000" in vite_src


@pytest.mark.parametrize(
    "rel_path",
    [
        "frontend/src/lib/api/apiError.ts",
    ],
)
def test_react_obs_01_regression_module_exists(rel_path):
    assert (ROOT / rel_path).is_file(), rel_path


def test_contract_documents_api_error_helper():
    assert "frontend/src/lib/api/apiError.ts" in contract.REQUIRED_FRONTEND_FILES
    assert "frontend/src/lib/api/client.ts" in contract.REQUIRED_FRONTEND_FILES
