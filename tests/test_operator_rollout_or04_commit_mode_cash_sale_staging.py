"""OPERATOR-ROLLOUT-OR04 — COMMIT_MODE cash sale boundary staging gate tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "OPERATOR_ROLLOUT_OR04_COMMIT_MODE_CASH_SALE_STAGING.md"


def _load_rollout_contract():
    path = ROOT / "registry" / "operator_rollout_contract.py"
    spec = importlib.util.spec_from_file_location(
        "operator_rollout_contract_or04", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["operator_rollout_contract_or04"] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_commit_rollout_contract():
    path = ROOT / "registry/commit_mode_rollout_contract.py"
    spec = importlib.util.spec_from_file_location(
        "commit_mode_rollout_contract_or04", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["commit_mode_rollout_contract_or04"] = mod
    spec.loader.exec_module(mod)
    return mod


rollout = _load_rollout_contract()
commit_rollout = _load_commit_rollout_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Staging enablement",
    "Gate verification",
    "What must NOT change",
    "Test plan",
)

OTHER_COMMIT_MODE_PREFIXES = tuple(
    commit_rollout.commit_mode_env_var(spec.family)
    for spec in commit_rollout.ROLLOUT_FAMILIES
    if spec.family != "post_cash_sale"
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"OR-04 audit missing: {AUDIT_PATH}"
    return AUDIT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def api_env_text() -> str:
    return (ROOT / rollout.STAGING_API_ENV).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _reset_commit_modes():
    from services import commit_modes

    commit_modes.reset_commit_modes_for_tests()
    yield
    commit_modes.reset_commit_modes_for_tests()


def test_audit_doc_exists_and_sections(audit_text):
    for section in REQUIRED_AUDIT_SECTIONS:
        assert section.lower() in audit_text.lower(), f"Missing section: {section!r}"


@pytest.mark.parametrize("item", rollout.OR04_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text


def test_or04_stage_in_rollout_contract():
    stage = rollout.ROLLOUT_STAGES[3]
    assert stage.stage_id == "OPERATOR-ROLLOUT-OR04"
    assert stage.tag == "operator-rollout-or04-commit-mode-cash-sale-staging"


@pytest.mark.parametrize("flag_line", rollout.OR04_COMMIT_MODE_ENABLED)
def test_staging_api_enables_cash_sale_boundary(api_env_text, flag_line):
    assert flag_line in api_env_text


def test_staging_api_keeps_other_commit_modes_off(api_env_text):
    for line in api_env_text.splitlines():
        stripped = line.strip()
        for prefix in OTHER_COMMIT_MODE_PREFIXES:
            if stripped.startswith(f"{prefix}="):
                assert stripped.startswith("#"), stripped


def test_or03_write_flags_preserved_in_staging_api(api_env_text):
    for flag in rollout.OR03_WRITE_FLAGS_ENABLED:
        if flag.startswith("ERP_"):
            assert flag in api_env_text


def test_p0_gate_test_exists():
    assert (ROOT / rollout.OR04_P0_GATE_TEST).is_file()


def test_env_boundary_enables_post_cash_sale(monkeypatch):
    from services import commit_modes
    from services.commit_modes import CommitMode, POST_CASH_SALE_FAMILY

    monkeypatch.setenv("COMMIT_MODE_POST_CASH_SALE", "boundary")
    assert commit_modes.get_commit_mode(POST_CASH_SALE_FAMILY) is CommitMode.BOUNDARY


def test_other_families_still_internal_without_env(monkeypatch):
    from services import commit_modes
    from services.commit_modes import CommitMode

    monkeypatch.setenv("COMMIT_MODE_POST_CASH_SALE", "boundary")
    assert commit_modes.get_commit_mode("post_expense") is CommitMode.INTERNAL
    assert commit_modes.get_commit_mode("void_cascade") is CommitMode.INTERNAL
