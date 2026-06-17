"""FASTAPI-REACT-04 — read API + commit boundary characterization contract tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from services import commit_modes as cm
from services.commit_modes import CommitMode

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "FASTAPI_REACT_04_READ_API_BOUNDARY_AUDIT.md"
MAIN_SRC = (ROOT / "api" / "main.py").read_text(encoding="utf-8")
ERRORS_SRC = (ROOT / "api" / "errors.py").read_text(encoding="utf-8")
DEPS_SRC = (ROOT / "api" / "dependencies.py").read_text(encoding="utf-8")


def _load_module(name: str, rel_path: str):
    path = ROOT / rel_path
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


read_contract = _load_module("api_read_contract", "registry/api_read_contract.py")
boundary_contract = _load_module(
    "commit_boundary_contract", "registry/commit_boundary_contract.py"
)

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Read API inventory",
    "Error contract",
    "TD-PS-01",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"FASTAPI-REACT-04 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("gap_id", read_contract.DEFERRED_GAP_IDS)
def test_audit_documents_deferred_gaps(audit_text, gap_id):
    assert gap_id in audit_text, f"Deferred gap not documented: {gap_id}"


@pytest.mark.parametrize("path", read_contract.READ_API_PATHS)
def test_read_contract_paths_documented_in_p1_test(path):
    p1_src = (ROOT / read_contract.P1_CONTRACT_TEST).read_text(encoding="utf-8")
    assert path in p1_src, f"P1 contract must pin read path: {path}"


@pytest.mark.parametrize("module_path", read_contract.READ_SERVICE_MODULES)
def test_read_service_modules_exist(module_path):
    assert (ROOT / module_path).is_file()


def test_serialization_module_exists():
    assert (ROOT / read_contract.SERIALIZATION_MODULE).is_file()


def test_error_contract_documented_in_main_and_errors():
    for marker in read_contract.ERROR_CONTRACT_MARKERS:
        assert marker in MAIN_SRC.lower(), marker
    for marker in read_contract.HTTP_ERROR_MARKERS:
        assert marker in ERRORS_SRC, marker


def test_get_db_has_no_commit():
    assert "commit()" not in DEPS_SRC
    assert "before_flush" not in DEPS_SRC


@pytest.mark.parametrize("family", boundary_contract.ALL_BOUNDARY_FAMILIES)
def test_all_boundary_families_default_internal(family):
    assert cm.get_commit_mode(family) is CommitMode.INTERNAL


@pytest.mark.parametrize("spec", boundary_contract.COMMIT_FAMILY_CHARACTERIZATION)
def test_commit_family_has_characterization_test(spec):
    assert (ROOT / spec.characterization_test).is_file(), spec.characterization_test


@pytest.mark.parametrize("module_path", boundary_contract.BOUNDARY_READY_WRITE_MODULES)
def test_write_modules_have_boundary_mode_hook(module_path):
    src = (ROOT / module_path).read_text(encoding="utf-8")
    assert "is_boundary_mode" in src, module_path
    assert "boundary_commit_scope" in src, module_path


def test_p1_verification_artifacts_exist():
    assert (ROOT / read_contract.P1_CONTRACT_TEST).is_file()
    assert (ROOT / read_contract.P1_READ_TEST).is_file()
    assert (ROOT / boundary_contract.SCAFFOLD_TEST).is_file()


def test_roadmap_lists_fastapi_react_04_complete():
    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert "FASTAPI-REACT-04" in roadmap
    assert "fastapi-react-04-read-api-boundary-commit" in roadmap
