"""OPERATOR-ROLLOUT-OR07 — COMMIT_MODE receivable + bank boundary (staging)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "OPERATOR_ROLLOUT_OR07_COMMIT_MODE_RECEIVABLE_BANK_STAGING.md"


def _rollout():
    path = ROOT / "registry/operator_rollout_contract.py"
    spec = importlib.util.spec_from_file_location("orc_or07", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orc_or07"] = mod
    spec.loader.exec_module(mod)
    return mod


r = _rollout()


@pytest.fixture(scope="module")
def audit_text():
    return AUDIT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def api_env_text():
    return (ROOT / r.STAGING_API_ENV).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _reset():
    from services import commit_modes

    commit_modes.reset_commit_modes_for_tests()
    yield
    commit_modes.reset_commit_modes_for_tests()


def test_audit_sections(audit_text):
    for s in ("Executive summary", "Gate verification", "Test plan"):
        assert s.lower() in audit_text.lower()


@pytest.mark.parametrize("item", r.OR07_DEFERRED_ITEMS)
def test_deferred(audit_text, item):
    assert item in audit_text


def test_stage():
    assert r.ROLLOUT_STAGES[6].stage_id == "OPERATOR-ROLLOUT-OR07"


@pytest.mark.parametrize("line", r.OR07_CUMULATIVE_COMMIT_MODES_ENABLED)
def test_cumulative(api_env_text, line):
    assert line in api_env_text


def test_frozen_still_commented():
    assert "COMMIT_MODE_POST_PARTNER_MOVEMENT" in r.OR07_STILL_COMMENTED_COMMIT_MODES


@pytest.mark.parametrize("rel", r.OR07_P0_GATE_TESTS)
def test_p0_exists(rel):
    assert (ROOT / rel).is_file()


def test_env_bank(monkeypatch):
    from services import commit_modes
    from services.commit_modes import CommitMode, POST_BANK_TRANSACTION_FAMILY

    monkeypatch.setenv("COMMIT_MODE_BANK_TRANSACTION", "boundary")
    assert commit_modes.get_commit_mode(POST_BANK_TRANSACTION_FAMILY) is CommitMode.BOUNDARY
