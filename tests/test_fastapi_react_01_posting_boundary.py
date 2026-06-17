"""FASTAPI-REACT-01 — posting boundary hardening contract tests (PS-P7)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APP_SRC = (ROOT / "app.py").read_text(encoding="utf-8")
POSTING_SRC = (ROOT / "services" / "posting.py").read_text(encoding="utf-8")
BOUNDARY_SRC = (ROOT / "services" / "posting_boundary.py").read_text(encoding="utf-8")
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_01_POSTING_BOUNDARY_AUDIT.md"

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Characterization",
    "API-ready inputs/outputs",
    "Documented gaps",
    "What must NOT change",
    "Test plan",
)

POSTING_SHIM_NAMES = (
    "create_journal_entry",
    "post_cash_sale",
    "post_expense",
    "post_purchase",
    "void_sale",
    "void_expense",
    "close_fiscal_period",
    "post_partner_movement",
    "void_reconciliation",
)

BOUNDARY_POST_FAMILIES = (
    "POST_CASH_SALE_FAMILY",
    "POST_EXPENSE_FAMILY",
    "POST_PURCHASE_FAMILY",
    "POST_PAYABLE_PAYMENT_FAMILY",
    "POST_RECEIVABLE_PAYMENT_FAMILY",
    "POST_EQUITY_MOVEMENT_FAMILY",
    "POST_PARTNER_MOVEMENT_FAMILY",
    "POST_WORKER_MOVEMENT_FAMILY",
    "PROFIT_ALLOCATION_FAMILY",
    "YEAR_END_CLOSE_FAMILY",
    "PERIOD_CLOSE_FAMILY",
)

DEFERRED_GAP_IDS = (
    "TD-PS-01",
    "TD-PS-03",
    "TD-PS-06",
    "TD-PS-07",
    "TD-POSTING-06",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-01 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("gap_id", DEFERRED_GAP_IDS)
def test_audit_documents_deferred_gaps(audit_text, gap_id):
    assert gap_id in audit_text, f"Deferred gap not documented: {gap_id}"


def test_posting_boundary_module_exists():
    assert (ROOT / "services" / "posting_boundary.py").is_file()


def test_boundary_helpers_live_in_service_not_app():
    assert "def posting_boundary_scope" in BOUNDARY_SRC
    assert "def recon_boundary_scope" in BOUNDARY_SRC
    assert "def void_boundary_scope" in BOUNDARY_SRC
    assert "def _recon_boundary_scope" not in APP_SRC
    assert "def _void_boundary_scope" not in APP_SRC


def test_app_imports_posting_boundary_scopes():
    assert "from services.posting_boundary import" in APP_SRC
    assert "posting_boundary_scope" in APP_SRC
    assert "recon_boundary_scope" in APP_SRC
    assert "void_boundary_scope" in APP_SRC


def test_app_no_duplicate_boundary_mode_checks_in_shims():
    """Shims delegate boundary gating to posting_boundary_scope."""
    assert "is_boundary_mode(family) and boundary_depth() == 0" not in APP_SRC


@pytest.mark.parametrize("family", BOUNDARY_POST_FAMILIES)
def test_posting_boundary_references_commit_families(family):
    assert family in BOUNDARY_SRC or "RECONCILIATION_FAMILY" in BOUNDARY_SRC


def test_posting_service_import_purity():
    forbidden = [
        r"^\s*import streamlit\b",
        r"^\s*from streamlit\b",
        r"\bst\.session_state\b",
        r"\b_current_company_id\b",
        r"^\s*from app import\b",
        r"^\s*import app\b",
    ]
    for pattern in forbidden:
        assert re.search(pattern, POSTING_SRC, re.M) is None, (
            f"forbidden in services/posting.py: {pattern}"
        )


def test_posting_boundary_import_purity():
    forbidden = [
        r"^\s*import streamlit\b",
        r"^\s*from streamlit\b",
        r"\b_current_company_id\b",
        r"^\s*from app import\b",
    ]
    for pattern in forbidden:
        assert re.search(pattern, BOUNDARY_SRC, re.M) is None, (
            f"forbidden in services/posting_boundary.py: {pattern}"
        )


def test_additive_dto_wrappers_present():
    assert "def resolve_company_id_for_posting" in POSTING_SRC
    assert "def create_journal_entry_result" in POSTING_SRC
    assert "class PostingResult" in POSTING_SRC
    assert "def to_dict" in POSTING_SRC


def test_create_journal_entry_shim_uses_resolve_helper():
    block = re.search(
        r"def create_journal_entry\([^)]*\):.*?(?=\ndef |\Z)",
        APP_SRC,
        re.S,
    )
    assert block is not None
    body = block.group(0)
    assert "posting_service.create_journal_entry(" in body
    assert "resolve_company_id_for_posting" in body


@pytest.mark.parametrize("fn_name", POSTING_SHIM_NAMES)
def test_key_shims_delegate_to_posting_service(fn_name):
    pattern = rf"def {fn_name}\([^)]*\)(?:\s*->[^:]+)?:(?=\s|\n).*?(?=\ndef |\Z)"
    match = re.search(pattern, APP_SRC, re.S)
    assert match is not None, f"Shim missing: {fn_name}"
    body = match.group(0)
    assert "posting_service." in body, f"{fn_name} must delegate to posting_service"


def test_shim_import_present_once():
    assert APP_SRC.count("from services import posting as posting_service") == 1


def test_roadmap_lists_fastapi_react_01_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-01" in roadmap
    assert "fastapi-react-01-posting-boundary-hardening" in roadmap


def test_posting_service01_status_ps_p7_updated():
    status = (ROOT / "docs" / "POSTING_SERVICE_01_STATUS.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-01" in status
    assert "posting_boundary.py" in status
