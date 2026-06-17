"""FASTAPI-REACT-15 — partner/worker write tab contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_15_REACT_WRITE_PARTNER_WORKER_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "react_write_contract.py"
    spec = importlib.util.spec_from_file_location("react_write_contract_fr15", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["react_write_contract_fr15"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Form inventory",
    "Feature flags",
    "Client validation",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-15 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


def test_partner_worker_feature_flags_documented(audit_text):
    assert contract.WRITE_PARTNER_WORKER_FLAG_ENV in audit_text
    assert contract.API_WRITE_PARTNER_WORKER_ENV in audit_text
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert "reactWritePartnerWorkerEnabled" in flags_src
    assert contract.WRITE_PARTNER_WORKER_FLAG_ENV in flags_src


def test_react_write_enabled_includes_partner_worker():
    flags_src = (ROOT / "frontend/src/config/featureFlags.ts").read_text(
        encoding="utf-8"
    )
    assert "reactWritePartnerWorkerEnabled()" in flags_src


def test_new_transaction_page_posts_partner_and_worker_apis():
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    for path in contract.PARTNER_MOVEMENT_WRITE_API_PATHS:
        assert path in src, path
    for path in contract.WORKER_PAYMENT_WRITE_API_PATHS:
        assert path in src, path
    assert "Partner movement saved" in src
    assert "Worker payment saved" in src
    assert "Amount must be greater than zero." in src
    assert "partner_id" in src
    assert "worker_id" in src


@pytest.mark.parametrize("movement_type", contract.ALLOWED_PARTNER_MOVEMENT_TYPES)
def test_partner_movement_types_in_page_and_audit(audit_text, movement_type):
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert movement_type in audit_text
    assert f'value="{movement_type}"' in src or f"value='{movement_type}'" in src


@pytest.mark.parametrize("movement_type", contract.ALLOWED_WORKER_MOVEMENT_TYPES)
def test_worker_movement_types_in_page_and_audit(audit_text, movement_type):
    src = (ROOT / "frontend/src/pages/NewTransactionPage.tsx").read_text(
        encoding="utf-8"
    )
    assert movement_type in audit_text
    assert f'value="{movement_type}"' in src or f"value='{movement_type}'" in src


@pytest.mark.parametrize("api_path", contract.PARTNER_MOVEMENT_WRITE_API_PATHS)
def test_partner_api_path_in_route_and_p2_tests(api_path):
    route = (ROOT / "api/routes/partner_movements.py").read_text(encoding="utf-8")
    assert "post_partner_movement" in route
    p2_src = (ROOT / contract.P2_PARTNER_WORKER_WRITE_TEST).read_text(encoding="utf-8")
    assert api_path in p2_src


@pytest.mark.parametrize("api_path", contract.WORKER_PAYMENT_WRITE_API_PATHS)
def test_worker_api_path_in_route_and_p2_tests(api_path):
    route = (ROOT / "api/routes/worker_payments.py").read_text(encoding="utf-8")
    assert "post_worker_payment" in route
    p2_src = (ROOT / contract.P2_PARTNER_WORKER_WRITE_TEST).read_text(encoding="utf-8")
    assert api_path in p2_src


def test_p2_partner_worker_write_tests_exist():
    assert (ROOT / contract.P2_PARTNER_WORKER_WRITE_TEST).is_file()


def test_roadmap_lists_fastapi_react_15_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-15" in roadmap
    assert "fastapi-react-15-react-write-partner-worker" in roadmap


@pytest.mark.parametrize("item", contract.FR15_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text
