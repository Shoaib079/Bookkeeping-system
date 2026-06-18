"""OPERATOR-ROLLOUT-OR01 — React read pages staging enable gate tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "OPERATOR_ROLLOUT_OR01_REACT_READ_STAGING.md"


def _load_rollout_contract():
    path = ROOT / "registry" / "operator_rollout_contract.py"
    spec = importlib.util.spec_from_file_location(
        "operator_rollout_contract_or01", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["operator_rollout_contract_or01"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_pages_contract():
    path = ROOT / "registry" / "react_pages_contract.py"
    spec = importlib.util.spec_from_file_location("react_pages_contract_or01", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_pages_contract_or01"] = mod
    spec.loader.exec_module(mod)
    return mod


rollout = _load_rollout_contract()
pages = _load_pages_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Staging enablement",
    "Gate verification",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"OR-01 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def frontend_env_text() -> str:
    path = ROOT / rollout.STAGING_FRONTEND_ENV
    assert path.is_file(), rollout.STAGING_FRONTEND_ENV
    return path.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("item", rollout.OR01_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text


def test_staging_frontend_env_enables_read_pages(frontend_env_text):
    assert "VITE_ERP_REACT_PAGES=1" in frontend_env_text
    for line in frontend_env_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("VITE_ERP_REACT_WRITE"):
            assert stripped.startswith("#"), f"Write flag must stay commented in OR-01: {stripped!r}"


def test_staging_readme_documents_or01():
    readme = (ROOT / rollout.STAGING_README).read_text(encoding="utf-8")
    assert "OR-01" in readme
    assert rollout.STAGING_FRONTEND_ENV in readme


def test_or01_stage_in_rollout_contract():
    stage = rollout.ROLLOUT_STAGES[0]
    assert stage.stage_id == "OPERATOR-ROLLOUT-OR01"
    assert stage.tag == "operator-rollout-or01-react-read-staging"
    assert "VITE_ERP_REACT_PAGES=1" in stage.staging_env_keys


def test_feature_flags_match_pages_contract(frontend_env_text):
    assert pages.VITE_FEATURE_FLAG_ENV in frontend_env_text
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert pages.VITE_FEATURE_FLAG_ENV in flags_src
    assert "reactPagesEnabled" in flags_src


@pytest.mark.parametrize("path,component,_key", pages.REAL_PAGE_ROUTES)
def test_all_real_page_routes_wired_in_app_router(path, component, _key):
    router_src = (ROOT / "frontend/src/routes/AppRouter.tsx").read_text(
        encoding="utf-8"
    )
    assert component in router_src, component
    assert "reactPagesEnabled" in router_src


def test_default_commit_mode_unchanged():
    from services import commit_modes
    from services.commit_modes import CommitMode

    commit_modes.reset_commit_modes_for_tests()
    for family in (
        "post_cash_sale",
        "void_cascade",
    ):
        assert commit_modes.get_commit_mode(family) is CommitMode.INTERNAL
