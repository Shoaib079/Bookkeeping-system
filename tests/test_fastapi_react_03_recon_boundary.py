"""FASTAPI-REACT-03 — reconciliation boundary contract tests (TD-POSTING-06)."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_03_RECON_BOUNDARY_AUDIT.md"


def _load_contract_module():
    path = ROOT / "registry" / "recon_boundary_contract.py"
    spec = importlib.util.spec_from_file_location("recon_boundary_contract", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["recon_boundary_contract"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract_module()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Characterization",
    "TD-PS-01",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-03 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("gap_id", contract.DEFERRED_GAP_IDS)
def test_audit_documents_deferred_gaps(audit_text, gap_id):
    assert gap_id in audit_text, f"Deferred gap not documented: {gap_id}"


@pytest.mark.parametrize("module_path", contract.RECON_MODULES)
def test_recon_modules_exist(module_path):
    assert (ROOT / module_path).is_file()


@pytest.mark.parametrize("module_path", contract.RECON_MODULES)
@pytest.mark.parametrize("pattern", contract.FORBIDDEN_PATTERNS)
def test_recon_modules_forbid_lazy_app(module_path, pattern):
    src = (ROOT / module_path).read_text(encoding="utf-8")
    assert re.search(pattern, src, re.M) is None, (
        f"forbidden in {module_path}: {pattern}"
    )


def test_match_post_uses_posting_worker_advance_balance():
    src = (ROOT / "reconciliation" / "match_post.py").read_text(encoding="utf-8")
    assert "get_worker_advance_balance" in src
    assert "company_id=company_id" in src.split("post_worker_statement_match", 1)[1]


def test_company_card_health_uses_read_balances():
    src = (ROOT / "reconciliation" / "company_card.py").read_text(encoding="utf-8")
    block = src.split("def compute_cc_payable_recon_health", 1)[1].split("\ndef ", 1)[0]
    assert "posting_svc.get_account_by_name" in block or "posting as posting_svc" in block
    assert "calculate_account_balance" in block
    assert "company_id=company_id" in block


def test_posting_exports_get_worker_advance_balance():
    src = (ROOT / "services" / "posting.py").read_text(encoding="utf-8")
    assert "def get_worker_advance_balance(" in src


def test_roadmap_lists_fastapi_react_03_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-03" in roadmap
    assert "fastapi-react-03-recon-boundary-commit" in roadmap


def test_referenced_verification_artifacts_exist():
    assert (ROOT / "tests" / "test_cc_recon_health.py").is_file()
    assert (ROOT / "tests" / "test_fastapi_p2_reconciliation_write.py").is_file()
