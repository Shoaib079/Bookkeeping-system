"""POSTGRES production cutover — gate wiring + doc contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from paths import SQLITE_DATABASE_URL, get_database_url
from services import postgres_runtime_cutover as gate

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "POSTGRES_PRODUCTION_CUTOVER.md"
SCRIPT = ROOT / "scripts" / "postgres_production_cutover.py"


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC.exists(), f"Missing cutover doc: {DOC}"
    return DOC.read_text(encoding="utf-8")


def test_cutover_doc_exists():
    assert DOC.stat().st_size > 400


def test_records_backup_and_rollback(doc_text: str):
    assert "erp_data_PRODUCTION_CUTOVER_20260616_212243.db" in doc_text
    low = doc_text.lower()
    assert "rollback" in low
    assert "unset" in low or "disable" in low


def test_records_runtime_env_vars(doc_text: str):
    assert gate.RUNTIME_CUTOVER_ENV_VAR in doc_text
    assert gate.RUNTIME_URL_ENV_VAR in doc_text
    assert gate.BACKUP_PATH_ENV_VAR in doc_text
    assert gate.RUNTIME_CUTOVER_APPROVAL_PHRASE in doc_text


def test_operator_script_exists():
    assert SCRIPT.exists()
    src = SCRIPT.read_text(encoding="utf-8")
    assert "compare_sqlite_postgres_parity" in src
    assert "copy_sqlite_rows_to_postgres" in src


def test_default_database_url_is_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv(gate.RUNTIME_CUTOVER_ENV_VAR, raising=False)
    monkeypatch.delenv(gate.RUNTIME_CUTOVER_APPROVAL_ENV_VAR, raising=False)
    monkeypatch.delenv(gate.RUNTIME_URL_ENV_VAR, raising=False)
    monkeypatch.delenv(gate.BACKUP_PATH_ENV_VAR, raising=False)
    assert get_database_url() == SQLITE_DATABASE_URL


def test_gate_resolves_postgres_url(monkeypatch, tmp_path):
    backup = tmp_path / "backup.db"
    backup.write_bytes(b"sqlite-backup")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv(gate.RUNTIME_CUTOVER_ENV_VAR, "1")
    monkeypatch.setenv(gate.RUNTIME_CUTOVER_APPROVAL_ENV_VAR, gate.RUNTIME_CUTOVER_APPROVAL_PHRASE)
    monkeypatch.setenv(gate.BACKUP_PATH_ENV_VAR, str(backup))
    monkeypatch.setenv(
        gate.RUNTIME_URL_ENV_VAR,
        "postgresql+psycopg://postgres@localhost/erp_pytest",
    )
    assert get_database_url().startswith("postgresql")


def test_explicit_database_url_overrides_gate(monkeypatch, tmp_path):
    backup = tmp_path / "backup.db"
    backup.write_bytes(b"sqlite-backup")
    monkeypatch.setenv(gate.RUNTIME_CUTOVER_ENV_VAR, "1")
    monkeypatch.setenv(gate.RUNTIME_CUTOVER_APPROVAL_ENV_VAR, gate.RUNTIME_CUTOVER_APPROVAL_PHRASE)
    monkeypatch.setenv(gate.BACKUP_PATH_ENV_VAR, str(backup))
    monkeypatch.setenv(gate.RUNTIME_URL_ENV_VAR, "postgresql+psycopg://localhost/erp_pytest")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost/erp_override")
    assert get_database_url() == "postgresql+psycopg://localhost/erp_override"


def test_blocked_without_backup(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv(gate.RUNTIME_CUTOVER_ENV_VAR, "1")
    monkeypatch.setenv(gate.RUNTIME_CUTOVER_APPROVAL_ENV_VAR, gate.RUNTIME_CUTOVER_APPROVAL_PHRASE)
    monkeypatch.delenv(gate.BACKUP_PATH_ENV_VAR, raising=False)
    monkeypatch.setenv(gate.RUNTIME_URL_ENV_VAR, "postgresql+psycopg://localhost/erp_pytest")
    evaluation = gate.evaluate_runtime_cutover()
    assert evaluation.blocked_reason is not None
    assert get_database_url() == SQLITE_DATABASE_URL


def test_cutover_script_stamps_alembic_after_copy():
    src = SCRIPT.read_text(encoding="utf-8")
    assert "ensure_pg_stamped_at_head" in src
    assert "alembic_after" in src


def test_schema_startup_wires_pg_cutover_stamp():
    wiring = (ROOT / "services" / "schema_startup_wiring.py").read_text(encoding="utf-8")
    assert "ensure_pg_stamped_at_head" in wiring
    assert "ACTION_REQUIRE_STAMP" in wiring
    assert "evaluate_runtime_cutover" in wiring
