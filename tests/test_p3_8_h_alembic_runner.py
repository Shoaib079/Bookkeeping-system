"""P3.8-H — contract tests for safe Alembic command wrapper."""

from __future__ import annotations

import inspect
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text

from paths import DATABASE_URL, PROJECT_ROOT
from services.alembic_runner import (
    AlembicCommandResult,
    build_stamp_command,
    build_upgrade_head_command,
    get_alembic_heads,
    get_current_revision,
    is_allowed_database_url,
    run_stamp,
    run_upgrade_head,
)
from services.schema_version import ALEMBIC_VERSION_TABLE, discover_local_revisions

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_8_H_SAFE_ALEMBIC_RUNNER.md"
APP_PATH = ROOT / "app.py"
MODULE_PATH = ROOT / "services" / "alembic_runner.py"

TEST_DB_URL = "sqlite:///:memory:"


def test_doc_exists():
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


def test_doc_covers_required_topics():
    text_doc = DOC_PATH.read_text(encoding="utf-8").lower()
    for topic in (
        "wrapper only",
        "not wired",
        "dry-run",
        "allow_execute",
        "no production",
        "p3.8-j",
        "migrate_schema",
    ):
        assert topic in text_doc, f"Doc missing topic: {topic!r}"


def test_get_alembic_heads_returns_0002():
    heads = get_alembic_heads()
    assert heads == ("0002",)
    assert "0001" in discover_local_revisions()


def test_build_upgrade_head_command_shape():
    argv = build_upgrade_head_command(database_url=TEST_DB_URL)
    assert argv[-2:] == ("upgrade", "head")
    assert "alembic" in argv
    assert f"sqlalchemy.url={TEST_DB_URL}" in argv
    assert "shell" not in argv


def test_build_stamp_command_shape():
    argv = build_stamp_command(database_url=TEST_DB_URL, revision="0001")
    assert argv[-2:] == ("stamp", "0001")


def test_default_run_upgrade_head_is_dry_run():
    result = run_upgrade_head(database_url=TEST_DB_URL)
    assert result.dry_run is True
    assert result.executed is False
    assert result.success is True
    assert result.command == "upgrade"
    assert result.target == "head"
    assert "dry-run" in result.message.lower()


def test_default_run_stamp_is_dry_run():
    result = run_stamp(database_url=TEST_DB_URL, revision="0001")
    assert result.dry_run is True
    assert result.executed is False
    assert result.success is True
    assert result.command == "stamp"
    assert result.target == "0001"


def test_allow_execute_required_for_execution(monkeypatch):
    mock_run = MagicMock(
        return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
    )
    monkeypatch.setattr("services.alembic_runner.subprocess.run", mock_run)

    result = run_upgrade_head(database_url=TEST_DB_URL, allow_execute=True)
    assert result.executed is True
    assert result.dry_run is False
    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs.get("shell") is False


def test_production_database_url_rejected():
    assert is_allowed_database_url(DATABASE_URL) is False
    with pytest.raises(ValueError, match="disallowed"):
        build_upgrade_head_command(database_url=DATABASE_URL)
    with pytest.raises(ValueError, match="disallowed"):
        run_upgrade_head(database_url=DATABASE_URL)


def test_missing_database_url_rejected():
    assert is_allowed_database_url(None) is False
    assert is_allowed_database_url("") is False
    with pytest.raises(ValueError):
        build_stamp_command(database_url="", revision="0001")


def test_no_downgrade_support():
    source = MODULE_PATH.read_text(encoding="utf-8").lower()
    assert "def run_downgrade" not in source
    assert "def build_downgrade" not in source
    from services.alembic_runner import _reject_blocked_subcommand

    with pytest.raises(ValueError, match="downgrade"):
        _reject_blocked_subcommand(["alembic", "downgrade", "base"])


def test_get_current_revision_read_only(tmp_path):
    db_file = tmp_path / "test_alembic_runner.db"
    url = f"sqlite:///{db_file.as_posix()}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    with engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE TABLE {ALEMBIC_VERSION_TABLE} "
                "(version_num VARCHAR(32) NOT NULL)"
            )
        )
        conn.execute(
            text(f"INSERT INTO {ALEMBIC_VERSION_TABLE} (version_num) VALUES ('0001')")
        )
    engine.dispose()

    assert get_current_revision(url) == "0001"


def test_get_current_revision_rejects_production_url():
    with pytest.raises(ValueError, match="disallowed"):
        get_current_revision(DATABASE_URL)


def test_wrapper_not_wired_into_app():
    app_text = APP_PATH.read_text(encoding="utf-8")
    for token in (
        "alembic_runner",
        "run_upgrade_head",
        "run_stamp",
        "build_upgrade_head_command",
    ):
        assert token not in app_text


def test_wrapper_does_not_reference_erp_data_db_in_tests():
    assert "erp_data.db" not in TEST_DB_URL
    result = run_stamp(database_url=TEST_DB_URL, revision="0001")
    assert isinstance(result, AlembicCommandResult)


def test_no_shell_true_in_module():
    source = inspect.getsource(
        __import__("services.alembic_runner", fromlist=["run_upgrade_head"])._execute_argv
    )
    assert "shell=True" not in source
    assert "shell=False" in source
