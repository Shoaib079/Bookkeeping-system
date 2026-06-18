"""PRODUCTION-HARDENING-01-PH02 — commit characterization contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "PRODUCTION_HARDENING_01_PH02_COMMIT_CHARACTERIZATION_AUDIT.md"


def _load_contract():
    path = ROOT / "registry" / "production_hardening_contract.py"
    spec = importlib.util.spec_from_file_location(
        "production_hardening_contract_ph02", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["production_hardening_contract_ph02"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_boundary_contract():
    path = ROOT / "registry" / "commit_boundary_contract.py"
    spec = importlib.util.spec_from_file_location(
        "commit_boundary_contract_ph02", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["commit_boundary_contract_ph02"] = mod
    spec.loader.exec_module(mod)
    return mod


contract = _load_contract()
boundary_contract = _load_boundary_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Families extended",
    "Contract updates",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"PH-02 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def roadmap_text() -> str:
    return (ROOT / "ROADMAP.md").read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("item", contract.PH02_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text


@pytest.mark.parametrize("rel_path", contract.PH02_CHARACTERIZATION_TESTS)
def test_characterization_test_files_exist(rel_path):
    assert (ROOT / rel_path).is_file(), rel_path


@pytest.mark.parametrize("family", contract.PH02_BOUNDARY_FAMILIES)
def test_commit_boundary_contract_points_at_dedicated_test(family):
    mapping = {
        spec.family: spec.characterization_test
        for spec in boundary_contract.COMMIT_FAMILY_CHARACTERIZATION
    }
    assert family in mapping
    assert mapping[family] != boundary_contract.SCAFFOLD_TEST
    assert (ROOT / mapping[family]).is_file()


def test_banking_test_covers_dual_run_parity():
    src = (
        ROOT / "tests/test_fastapi_p0_commit_ownership_banking.py"
    ).read_text(encoding="utf-8")
    assert "TestManualBankTransactionDualRunParity" in src
    assert "POST_BANK_TRANSACTION_FAMILY" in src
    assert "create_manual_bank_transaction" in src


def test_movements_test_covers_equity_dual_run_parity():
    src = (
        ROOT / "tests/test_fastapi_p0_commit_ownership_movements.py"
    ).read_text(encoding="utf-8")
    assert "equity_contribution" in src
    assert "POST_EQUITY_MOVEMENT_FAMILY" in src


def test_roadmap_lists_ph02_complete(roadmap_text):
    assert contract.PH02_SLICE_ID in roadmap_text
    assert contract.PH02_TAG in roadmap_text
    assert "✅" in roadmap_text.split(contract.PH02_SLICE_ID, 1)[1].split("\n", 1)[0]
