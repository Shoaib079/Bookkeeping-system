"""PRODUCTION-HARDENING-01-PH04 — COMMIT_MODE_* operator rollout tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "PRODUCTION_HARDENING_01_PH04_COMMIT_MODE_ROLLOUT_AUDIT.md"


def _load_rollout_contract():
    path = ROOT / "registry" / "commit_mode_rollout_contract.py"
    spec = importlib.util.spec_from_file_location(
        "commit_mode_rollout_contract_ph04", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["commit_mode_rollout_contract_ph04"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_boundary_contract():
    path = ROOT / "registry" / "commit_boundary_contract.py"
    spec = importlib.util.spec_from_file_location(
        "commit_boundary_contract_ph04", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["commit_boundary_contract_ph04"] = mod
    spec.loader.exec_module(mod)
    return mod


rollout_contract = _load_rollout_contract()
boundary_contract = _load_boundary_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "COMMIT_MODE_* operator contract",
    "Safest-first rollout order",
    "Operator preflight checklist",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"PH-04 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def roadmap_text() -> str:
    return (ROOT / "ROADMAP.md").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _reset_commit_modes():
    from services import commit_modes

    commit_modes.reset_commit_modes_for_tests()
    yield
    commit_modes.reset_commit_modes_for_tests()


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("item", rollout_contract.PH04_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text


@pytest.mark.parametrize("spec", rollout_contract.ROLLOUT_FAMILIES)
def test_audit_documents_rollout_family(audit_text, spec):
    assert spec.family in audit_text
    assert spec.characterization_test.split("/")[-1] in audit_text


@pytest.mark.parametrize("item", rollout_contract.OPERATOR_PREFLIGHT_CHECKLIST)
def test_audit_documents_preflight_checklist(audit_text, item):
    assert item in audit_text


@pytest.mark.parametrize("example", rollout_contract.OPERATOR_STAGING_EXAMPLE)
def test_audit_documents_staging_examples(audit_text, example):
    assert example in audit_text


def test_rollout_families_match_commit_boundary_contract():
    rollout = {spec.family for spec in rollout_contract.ROLLOUT_FAMILIES}
    boundary = set(boundary_contract.ALL_BOUNDARY_FAMILIES)
    assert rollout == boundary


@pytest.mark.parametrize("spec", rollout_contract.ROLLOUT_FAMILIES)
def test_rollout_characterization_tests_exist(spec):
    assert (ROOT / spec.characterization_test).is_file()


@pytest.mark.parametrize("spec", rollout_contract.ROLLOUT_FAMILIES)
def test_rollout_write_modules_exist_when_documented(spec):
    if spec.write_module is None:
        return
    assert (ROOT / spec.write_module).is_file()


def test_commit_modes_module_reads_env_prefix():
    src = (ROOT / rollout_contract.COMMIT_MODES_MODULE).read_text(encoding="utf-8")
    assert rollout_contract.ENV_PREFIX in src
    assert 'f"COMMIT_MODE_{family.upper()}"' in src


@pytest.mark.parametrize("spec", rollout_contract.ROLLOUT_FAMILIES)
def test_env_boundary_value_enables_family(monkeypatch, spec):
    from services import commit_modes
    from services.commit_modes import CommitMode

    monkeypatch.setenv(
        rollout_contract.commit_mode_env_var(spec.family),
        rollout_contract.VALID_BOUNDARY_VALUE,
    )
    assert commit_modes.get_commit_mode(spec.family) is CommitMode.BOUNDARY
    assert commit_modes.is_boundary_mode(spec.family)


@pytest.mark.parametrize("spec", rollout_contract.ROLLOUT_FAMILIES)
def test_env_internal_value_pins_family(monkeypatch, spec):
    from services import commit_modes
    from services.commit_modes import CommitMode

    monkeypatch.setenv(
        rollout_contract.commit_mode_env_var(spec.family),
        rollout_contract.VALID_INTERNAL_VALUE,
    )
    assert commit_modes.get_commit_mode(spec.family) is CommitMode.INTERNAL


@pytest.mark.parametrize("spec", rollout_contract.ROLLOUT_FAMILIES)
def test_invalid_env_value_ignored(monkeypatch, spec):
    from services import commit_modes
    from services.commit_modes import CommitMode

    monkeypatch.setenv(
        rollout_contract.commit_mode_env_var(spec.family),
        "maybe",
    )
    assert commit_modes.get_commit_mode(spec.family) is CommitMode.INTERNAL


def test_test_override_takes_precedence_over_env(monkeypatch):
    from services import commit_modes
    from services.commit_modes import CommitMode, POST_CASH_SALE_FAMILY

    monkeypatch.setenv(
        rollout_contract.commit_mode_env_var(POST_CASH_SALE_FAMILY),
        rollout_contract.VALID_BOUNDARY_VALUE,
    )
    commit_modes.set_commit_mode_for_tests(POST_CASH_SALE_FAMILY, CommitMode.INTERNAL)
    assert commit_modes.get_commit_mode(POST_CASH_SALE_FAMILY) is CommitMode.INTERNAL


def test_write_sales_wires_post_cash_sale_boundary_mode():
    src = (ROOT / "services/write_sales.py").read_text(encoding="utf-8")
    assert "is_boundary_mode" in src
    assert "POST_CASH_SALE_FAMILY" in src
    assert "boundary_commit_scope" in src


def test_roadmap_lists_ph04_complete(roadmap_text):
    assert rollout_contract.PH04_SLICE_ID in roadmap_text
    assert rollout_contract.PH04_TAG in roadmap_text
