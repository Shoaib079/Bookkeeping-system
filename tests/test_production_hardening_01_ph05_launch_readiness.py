"""PRODUCTION-HARDENING-01-PH05 — launch-readiness verification gate tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from services import commit_modes
from services.commit_modes import CommitMode

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "PRODUCTION_HARDENING_01_PH05_LAUNCH_READINESS_AUDIT.md"


def _load_gate_contract():
    path = ROOT / "registry/launch_readiness_gate_contract.py"
    spec = importlib.util.spec_from_file_location(
        "launch_readiness_gate_contract_ph05", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["launch_readiness_gate_contract_ph05"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_epic_contract():
    path = ROOT / "registry" / "production_hardening_contract.py"
    spec = importlib.util.spec_from_file_location(
        "production_hardening_contract_ph05", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["production_hardening_contract_ph05"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_boundary_contract():
    path = ROOT / "registry" / "commit_boundary_contract.py"
    spec = importlib.util.spec_from_file_location(
        "commit_boundary_contract_ph05", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["commit_boundary_contract_ph05"] = mod
    spec.loader.exec_module(mod)
    return mod


gate = _load_gate_contract()
epic = _load_epic_contract()
boundary = _load_boundary_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Epic slice inventory",
    "Launch-readiness verdict",
    "Verification gate",
    "Epic closure",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"PH-05 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def roadmap_text() -> str:
    return (ROOT / "ROADMAP.md").read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("item", gate.PH05_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text


@pytest.mark.parametrize("slice_id,audit_doc,tag", gate.EPIC_SLICE_AUDITS)
def test_epic_audit_docs_exist(slice_id, audit_doc, tag):
    assert (ROOT / audit_doc).is_file(), audit_doc


@pytest.mark.parametrize("slice_id,audit_doc,tag", gate.EPIC_SLICE_AUDITS)
def test_roadmap_documents_epic_slice(roadmap_text, slice_id, audit_doc, tag):
    assert slice_id in roadmap_text
    assert tag in roadmap_text


@pytest.mark.parametrize("rel_path", gate.EPIC_SLICE_TESTS)
def test_epic_slice_tests_exist(rel_path):
    assert (ROOT / rel_path).is_file(), rel_path


@pytest.mark.parametrize("rel_path", gate.SUPPORTING_CONTRACTS)
def test_supporting_contracts_exist(rel_path):
    assert (ROOT / rel_path).is_file(), rel_path


@pytest.mark.parametrize("command", gate.VERIFICATION_GATE_COMMANDS)
def test_audit_documents_verification_gate_commands(audit_text, command):
    token = command.replace("pytest ", "").split()[0]
    assert token in audit_text


def test_audit_documents_streamlit_launch_verdict(audit_text):
    assert gate.STREAMLIT_LAUNCH_VERDICT in audit_text


def test_audit_documents_api_write_launch_verdict(audit_text):
    assert gate.API_WRITE_LAUNCH_VERDICT in audit_text


@pytest.mark.parametrize("item", gate.POST_EPIC_OPERATOR_DEFERRALS)
def test_audit_documents_operator_deferrals(audit_text, item):
    assert item.replace("`", "") in audit_text.replace("`", "")


@pytest.mark.parametrize("item", gate.POST_EPIC_INTENTIONAL_DEFERRALS)
def test_audit_documents_intentional_deferrals(audit_text, item):
    assert item in audit_text


def test_epic_status_complete_in_contract():
    assert epic.EPIC_STATUS == "complete"
    assert all(status == "complete" for _sid, _scope, status in epic.EPIC_SLICES)


def test_default_commit_mode_internal_for_all_families():
    for family in boundary.ALL_BOUNDARY_FAMILIES:
        assert commit_modes.get_commit_mode(family) is CommitMode.INTERNAL


def test_roadmap_epic_complete(roadmap_text):
    assert gate.EPIC_ID in roadmap_text
    assert gate.PH05_SLICE_ID in roadmap_text
    assert gate.PH05_TAG in roadmap_text
