"""OPERATOR-ROLLOUT-OR05 — COMMIT_MODE expense boundary staging gate tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "docs" / "OPERATOR_ROLLOUT_OR05_COMMIT_MODE_EXPENSE_STAGING.md"


def _load_rollout_contract():
    path = ROOT / "registry" / "operator_rollout_contract.py"
    spec = importlib.util.spec_from_file_location(
        "operator_rollout_contract_or05", path
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["operator_rollout_contract_or05"] = mod
    spec.loader.exec_module(mod)
    return mod


rollout = _load_rollout_contract()

REQUIRED_AUDIT_SECTIONS = (
    "Executive summary",
    "Staging enablement",
    "Gate verification",
    "What must NOT change",
    "Test plan",
)


@pytest.fixture(scope="module")
def audit_text() -> str:
    assert AUDIT_PATH.exists(), f"OR-05 audit missing: {AUDIT_PATH}"
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


@pytest.mark.parametrize("item", rollout.OR05_DEFERRED_ITEMS)
def test_audit_documents_deferred_items(audit_text, item):
    assert item in audit_text


def test_or05_stage_in_rollout_contract():
    stage = rollout.ROLLOUT_STAGES[4]
    assert stage.stage_id == "OPERATOR-ROLLOUT-OR05"
    assert stage.tag == "operator-rollout-or05-commit-mode-expense-staging"


@pytest.mark.parametrize("flag_line", rollout.OR05_CUMULATIVE_COMMIT_MODES_ENABLED)
def test_staging_api_enables_cumulative_commit_modes(api_env_text, flag_line):
    assert flag_line in api_env_text


def test_staging_api_keeps_later_commit_modes_off(api_env_text):
    for prefix in rollout.OR05_STILL_COMMENTED_COMMIT_MODES:
        for line in api_env_text.splitlines():
            stripped = line.strip()
            if stripped.startswith(f"{prefix}="):
                assert stripped.startswith("#"), stripped


def test_or03_write_flags_preserved_in_staging_api(api_env_text):
    for flag in rollout.OR03_WRITE_FLAGS_ENABLED:
        if flag.startswith("ERP_"):
            assert flag in api_env_text


def test_p0_gate_test_exists():
    assert (ROOT / rollout.OR05_P0_GATE_TEST).is_file()


def test_env_boundary_enables_post_expense(monkeypatch):
    from services import commit_modes
    from services.commit_modes import CommitMode, POST_EXPENSE_FAMILY

    monkeypatch.setenv("COMMIT_MODE_POST_EXPENSE", "boundary")
    assert commit_modes.get_commit_mode(POST_EXPENSE_FAMILY) is CommitMode.BOUNDARY


def test_purchase_still_internal_when_only_expense_env_set(monkeypatch):
    from services import commit_modes
    from services.commit_modes import CommitMode

    monkeypatch.setenv("COMMIT_MODE_POST_EXPENSE", "boundary")
    assert commit_modes.get_commit_mode("post_purchase") is CommitMode.INTERNAL
