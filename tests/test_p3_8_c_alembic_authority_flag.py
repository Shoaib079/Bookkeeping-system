"""P3.8-C — contract tests for ERP_ALEMBIC_AUTHORITATIVE flag parser."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from services.schema_startup import (
    ALEMBIC_AUTHORITATIVE_ENV_VAR,
    is_alembic_authoritative_enabled,
    parse_alembic_authoritative_flag,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_8_C_ALEMBIC_AUTHORITY_FLAG.md"
APP_PATH = ROOT / "app.py"
MODULE_PATH = ROOT / "services" / "schema_startup.py"


@pytest.mark.parametrize(
    "value",
    ["bogus", "2", "maybe", "TRUE-ish"],
)
def test_invalid_values_are_false(value):
    assert parse_alembic_authoritative_flag(value) is False


@pytest.mark.parametrize("value", [None, "", "   "])
def test_unset_and_empty_default_true_after_p3_8_n(value):
    assert parse_alembic_authoritative_flag(value) is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", " FALSE ", " No "])
def test_explicit_false_values(value):
    assert parse_alembic_authoritative_flag(value) is False


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", " TRUE ", " Yes ", " ON "])
def test_explicit_true_values(value):
    assert parse_alembic_authoritative_flag(value) is True


def test_is_alembic_authoritative_enabled_defaults_true_after_p3_8_n():
    assert is_alembic_authoritative_enabled({}) is True


def test_is_alembic_authoritative_enabled_reads_env_mapping():
    assert is_alembic_authoritative_enabled({ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"}) is True
    assert is_alembic_authoritative_enabled({ALEMBIC_AUTHORITATIVE_ENV_VAR: "0"}) is False
    assert is_alembic_authoritative_enabled({ALEMBIC_AUTHORITATIVE_ENV_VAR: "bogus"}) is False


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


def test_doc_covers_required_topics():
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    for topic in (
        "parser only",
        "not wired",
        "p3.8-d",
        "p3.8-n",
        "erp_alembic_authoritative",
    ):
        assert topic in text, f"Doc missing topic: {topic!r}"


def test_flag_helpers_have_no_db_or_alembic_command_path():
    for name in ("parse_alembic_authoritative_flag", "is_alembic_authoritative_enabled"):
        source = inspect.getsource(
            __import__("services.schema_startup", fromlist=[name]).__dict__[name]
        ).lower()
        assert "alembic upgrade" not in source
        assert "alembic stamp" not in source
        assert "op.upgrade" not in source
        assert "migrate_schema" not in source
        assert "sqlalchemy" not in source
        assert "detect_schema_version" not in source


def test_flag_not_wired_into_app_startup():
    app_text = APP_PATH.read_text(encoding="utf-8")
    assert "ERP_ALEMBIC_AUTHORITATIVE" not in app_text
    assert "is_alembic_authoritative_enabled" not in app_text
    assert "parse_alembic_authoritative_flag" not in app_text
