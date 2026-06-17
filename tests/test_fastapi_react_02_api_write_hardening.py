"""FASTAPI-REACT-02 — API write hardening contract tests (explicit company_id)."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_contract_module():
    path = ROOT / "registry" / "api_write_contract.py"
    spec = importlib.util.spec_from_file_location("api_write_contract", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["api_write_contract"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract_module()
AUDIT_PATH = ROOT / contract.CONTRACT_DOC
DEPS_SRC = (ROOT / "api" / "dependencies.py").read_text(encoding="utf-8")

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Characterization",
    "Write endpoint inventory",
    "P2-HARDEN-01",
    "Documented gaps",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-02 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("gap_id", contract.DEFERRED_GAP_IDS)
def test_audit_documents_deferred_gaps(audit_text, gap_id):
    assert gap_id in audit_text, f"Deferred gap not documented: {gap_id}"


def test_p2_harden_closure_cited(audit_text):
    assert "P2_HARDEN_01_AUDIT_CLOSURE" in audit_text
    assert (ROOT / contract.P2_HARDEN_CLOSURE_DOC).is_file()


@pytest.mark.parametrize("invariant", contract.CORE_INVARIANTS)
def test_audit_states_core_invariants(audit_text, invariant):
    assert invariant in audit_text, f"Missing invariant: {invariant!r}"


def test_api_write_contract_module_matches_audit_inventory():
    assert len(contract.API_WRITE_ENDPOINTS) == 13
    handlers = {spec.handler for spec in contract.API_WRITE_ENDPOINTS}
    assert "post_sale" in handlers
    assert "post_reconciliation_unmatch" in handlers
    assert "post_void_allocation" in handlers


@pytest.mark.parametrize("route_file", contract.WRITE_ROUTE_FILES)
def test_write_route_files_exist(route_file):
    assert (ROOT / route_file).is_file(), f"Missing route file: {route_file}"


@pytest.mark.parametrize("service_module", contract.WRITE_SERVICE_MODULES)
def test_write_service_modules_exist(service_module):
    assert (ROOT / service_module).is_file(), f"Missing write service: {service_module}"


def _handler_body(src: str, handler: str) -> str:
    marker = f"def {handler}("
    start = src.index(marker)
    rest = src[start + len(marker) :]
    next_def = re.search(r"\n(?:async )?def ", rest)
    end = next_def.start() if next_def else len(rest)
    return src[start : start + len(marker) + end]


@pytest.mark.parametrize("spec", contract.API_WRITE_ENDPOINTS)
def test_write_handlers_use_guard_and_pass_company_id(spec):
    src = (ROOT / spec.route_file).read_text(encoding="utf-8")
    assert f"def {spec.handler}(" in src, f"Handler missing: {spec.handler}"
    body = _handler_body(src, spec.handler)
    assert "require_company_write_access" in body, spec.handler
    assert f'"{spec.permission}"' in body or f"'{spec.permission}'" in body, spec.handler
    assert "company_id=company_id" in body, spec.handler
    assert spec.service_call in body, spec.handler


@pytest.mark.parametrize("service_module", contract.WRITE_SERVICE_MODULES)
def test_write_services_no_ambient_company_import(service_module):
    src = (ROOT / service_module).read_text(encoding="utf-8")
    forbidden = [
        r"^\s*import streamlit\b",
        r"^\s*from streamlit\b",
        r"\b_current_company_id\b",
        r"current_company_required\b",
        r"^\s*from app import\b",
        r"^\s*import app\b",
        r"resolve_company_id_for_posting",
    ]
    for pattern in forbidden:
        assert re.search(pattern, src, re.M) is None, (
            f"forbidden in {service_module}: {pattern}"
        )


def test_get_db_has_no_before_flush_stamp_hook():
    assert "before_flush" not in DEPS_SRC
    assert "SessionLocal()" in DEPS_SRC


def test_roadmap_lists_fastapi_react_02_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-02" in roadmap
    assert "fastapi-react-02-api-write-hardening" in roadmap


def test_referenced_verification_artifacts_exist():
    assert (ROOT / "tests" / "test_p2_harden_01_company_stamp_matrix.py").is_file()
    p2_tests = list((ROOT / "tests").glob("test_fastapi_p2_*.py"))
    assert len(p2_tests) >= 9
