"""P3.8-N — contract tests for Alembic authority default flip.

Cross-ref: docs/P3_8_N_DEFAULT_FLIP.md
"""

from __future__ import annotations

from pathlib import Path

import pytest

from services.schema_startup import (
    ALEMBIC_AUTHORITATIVE_ENV_VAR,
    is_alembic_authoritative_enabled,
    parse_alembic_authoritative_flag,
)

DOC_PATH = Path(__file__).resolve().parents[1] / "docs" / "P3_8_N_DEFAULT_FLIP.md"


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Missing P3.8-N doc: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


def test_doc_covers_default_on_and_rollback(doc_text: str):
    low = doc_text.lower()
    for topic in (
        "default on",
        "unset",
        "explicit",
        "0",
        "migrate_schema",
        "retained",
        "rollback",
        "p3.9",
    ):
        assert topic in low, f"P3.8-N doc missing topic: {topic!r}"


def test_doc_states_unset_no_longer_rollback(doc_text: str):
    low = doc_text.lower()
    assert "unset" in low and "does not" in low or "not restore" in low


@pytest.mark.parametrize("value", [None, "", "   "])
def test_unset_and_empty_default_true(value):
    assert parse_alembic_authoritative_flag(value) is True


@pytest.mark.parametrize("value", ["bogus", "2", "maybe", "TRUE-ish"])
def test_invalid_values_fail_safe_false(value):
    assert parse_alembic_authoritative_flag(value) is False


@pytest.mark.parametrize("value", ["0", "false", "no", "off", " FALSE ", " No "])
def test_explicit_false_values(value):
    assert parse_alembic_authoritative_flag(value) is False


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", " TRUE ", " Yes ", " ON "])
def test_explicit_true_values(value):
    assert parse_alembic_authoritative_flag(value) is True


def test_is_alembic_authoritative_enabled_defaults_true():
    assert is_alembic_authoritative_enabled({}) is True


def test_is_alembic_authoritative_enabled_explicit_opt_out():
    assert is_alembic_authoritative_enabled({ALEMBIC_AUTHORITATIVE_ENV_VAR: "0"}) is False
    assert is_alembic_authoritative_enabled({ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"}) is True
