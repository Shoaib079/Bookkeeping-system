"""FASTAPI-REACT-11 — void write tab contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_11_REACT_WRITE_VOID_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_write_contract.py"
    spec = importlib.util.spec_from_file_location("react_write_contract_fr11", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_write_contract_fr11"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Form inventory",
    "Feature flags",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-11 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


def test_void_feature_flags_documented(audit_text):
    assert contract.WRITE_VOIDS_FLAG_ENV in audit_text
    assert contract.API_WRITE_VOIDS_ENV in audit_text
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert "reactWriteVoidsEnabled" in flags_src
    assert "reactWriteVoidsEnabled()" in flags_src or "reactWriteVoidsEnabled" in flags_src
    assert contract.WRITE_VOIDS_FLAG_ENV in flags_src


def test_react_write_enabled_includes_voids():
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert "reactWriteVoidsEnabled()" in flags_src


def test_new_transaction_page_posts_void_api():
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    for path in contract.VOID_WRITE_API_PATHS:
        assert path in src, path
    assert "Void record" in src or "Voiding" in src
    assert "target_type" in src
    assert "Void reason is required." in src


@pytest.mark.parametrize("target_type", contract.VOID_TARGET_TYPES)
def test_void_target_types_in_page_and_audit(audit_text, target_type):
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert target_type in audit_text
    assert f'value="{target_type}"' in src or f"value='{target_type}'" in src


@pytest.mark.parametrize("api_path", contract.VOID_WRITE_API_PATHS)
def test_void_api_path_in_route_and_p2_tests(api_path):
    void_route = (ROOT / "api/routes/voids.py").read_text(encoding="utf-8")
    assert "post_void" in void_route
    p2_src = (ROOT / contract.P2_VOID_WRITE_TEST).read_text(encoding="utf-8")
    assert api_path in p2_src


def test_p2_void_write_tests_exist():
    assert (ROOT / contract.P2_VOID_WRITE_TEST).is_file()


def test_roadmap_lists_fastapi_react_11_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-11" in roadmap
    assert "fastapi-react-11-react-write-void" in roadmap


@pytest.mark.parametrize("item", contract.DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
