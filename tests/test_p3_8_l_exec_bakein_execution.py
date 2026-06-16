"""P3.8-L-EXEC — automated Alembic authority bake-in execution.

Runs the bake-in scenario matrix from docs/P3_8_L_BAKE_IN_REVIEW_PLAN.md against real
temporary SQLite DBs. Records pass/fail evidence for P3.8-L; no production DB mutation,
no flag default change, no schema/model change.

Cross-ref: docs/P3_8_L_BAKEIN_EXEC.md
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from db import Base
from services.alembic_runner import AlembicCommandResult
from services.schema_migration_gate import REQUIRED_CONFIRMATION_PHRASE
from services.schema_startup import (
    ACTION_ALEMBIC_UPGRADE_HEAD,
    ACTION_FAIL_CLOSED,
    ACTION_REQUIRE_STAMP,
    ALEMBIC_AUTHORITATIVE_ENV_VAR,
)
from services.schema_startup_wiring import (
    SchemaStartupError,
    prepare_schema_startup_authoritative,
    reset_schema_startup_plan,
    run_schema_startup_in_session,
)
from services.schema_version import ALEMBIC_VERSION_TABLE

ROOT = Path(__file__).resolve().parents[1]
EXEC_DOC = ROOT / "docs" / "P3_8_L_BAKEIN_EXEC.md"
REVIEW_PLAN = ROOT / "docs" / "P3_8_L_BAKE_IN_REVIEW_PLAN.md"
SMOKE_DOC = ROOT / "docs" / "P3_8_M_LOCAL_SMOKE_TEST.md"
FLAG_ON = {ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"}
FLAG_OFF = {ALEMBIC_AUTHORITATIVE_ENV_VAR: "0"}


def _make_memory_engine() -> Engine:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
        if engine.dialect.name != "sqlite":
            return
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


def _create_alembic_version_table(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE TABLE {ALEMBIC_VERSION_TABLE} "
                "(version_num VARCHAR(32) NOT NULL)"
            )
        )


def _stamp(engine: Engine, revision: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(f"INSERT INTO {ALEMBIC_VERSION_TABLE} (version_num) VALUES (:rev)"),
            {"rev": revision},
        )


@pytest.fixture(autouse=True)
def _clear_startup_plan():
    reset_schema_startup_plan()
    yield
    reset_schema_startup_plan()


@pytest.fixture
def populated_db(tmp_path):
    import models  # noqa: F401

    db_path = tmp_path / "populated.db"
    database_url = f"sqlite:///{db_path}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield database_url, engine
    engine.dispose()


# ── Execution record contract ───────────────────────────────────────────────────


class TestBakeInExecDocContract:
    @pytest.fixture(scope="class")
    def exec_text(self) -> str:
        assert EXEC_DOC.exists(), f"Missing execution record: {EXEC_DOC}"
        return EXEC_DOC.read_text(encoding="utf-8")

    def test_exec_doc_exists(self):
        assert EXEC_DOC.exists()
        assert EXEC_DOC.stat().st_size > 0

    def test_exec_records_all_scenarios(self, exec_text: str):
        low = exec_text.lower()
        for label in (
            "flag off",
            "flag on",
            "at_head",
            "unstamped legacy",
            "ahead",
            "strict-new empty",
            "rollback",
        ):
            assert label in low, f"Execution record missing scenario: {label!r}"

    def test_exec_references_automated_and_manual_evidence(self, exec_text: str):
        low = exec_text.lower()
        assert "test_p3_8_l_exec" in low or "automated" in low
        assert "p3.8-m" in low or "p3_8_m" in low

    def test_exec_states_l_tests_still_required(self, exec_text: str):
        low = exec_text.lower()
        assert "p3.8-l-tests" in low or "schema equivalence" in low
        assert "not ready to retire" in low or "no retirement" in low

    def test_review_plan_and_smoke_prerequisites_exist(self):
        assert REVIEW_PLAN.exists()
        assert SMOKE_DOC.exists()


# ── Bake-in scenario execution (throwaway DBs only) ───────────────────────────


class TestBakeInExecutionScenarios:
    def test_scenario_flag_off_migrate_schema_authoritative(self):
        migrate_calls: list[str] = []
        engine = _make_memory_engine()
        SessionLocal = sessionmaker(bind=engine)
        try:
            prepare_schema_startup_authoritative(
                database_url=str(engine.url),
                environ=FLAG_OFF,
            )
            with SessionLocal() as session:
                run_schema_startup_in_session(
                    session,
                    migrate_schema_fn=lambda _s: migrate_calls.append("migrate"),
                    log_diagnostics_fn=lambda _s: None,
                    environ=FLAG_OFF,
                )
        finally:
            engine.dispose()
        assert migrate_calls == ["migrate"]

    def test_scenario_flag_on_at_head_verify_only_skips_migrate(self, populated_db):
        database_url, engine = populated_db
        _create_alembic_version_table(engine)
        _stamp(engine, "0002")
        migrate_calls: list[str] = []

        prepare_schema_startup_authoritative(
            database_url=database_url,
            environ=FLAG_ON,
            run_upgrade_head_fn=MagicMock(),
        )
        SessionLocal = sessionmaker(bind=engine)
        with SessionLocal() as session:
            run_schema_startup_in_session(
                session,
                migrate_schema_fn=lambda _s: migrate_calls.append("migrate"),
                log_diagnostics_fn=lambda _s: None,
                environ=FLAG_ON,
            )
        assert migrate_calls == []

    def test_scenario_flag_on_unstamped_legacy_blocks(self, populated_db):
        database_url, _engine = populated_db
        with pytest.raises(SchemaStartupError) as exc:
            prepare_schema_startup_authoritative(
                database_url=database_url,
                environ=FLAG_ON,
                run_upgrade_head_fn=MagicMock(),
            )
        assert exc.value.action == ACTION_REQUIRE_STAMP

    def test_scenario_flag_on_ahead_fail_closed(self, populated_db):
        database_url, engine = populated_db
        _create_alembic_version_table(engine)
        _stamp(engine, "0003")
        with pytest.raises(SchemaStartupError) as exc:
            prepare_schema_startup_authoritative(
                database_url=database_url,
                environ=FLAG_ON,
                run_upgrade_head_fn=MagicMock(),
            )
        assert exc.value.action == ACTION_FAIL_CLOSED

    def test_scenario_flag_on_unknown_fail_closed(self, populated_db):
        database_url, engine = populated_db
        _create_alembic_version_table(engine)
        _stamp(engine, "not-a-real-revision")
        with pytest.raises(SchemaStartupError) as exc:
            prepare_schema_startup_authoritative(
                database_url=database_url,
                environ=FLAG_ON,
                run_upgrade_head_fn=MagicMock(),
            )
        assert exc.value.action == ACTION_FAIL_CLOSED

    def test_scenario_strict_new_empty_db_upgrade_via_runner(self, tmp_path):
        db_path = tmp_path / "throwaway_empty.db"
        database_url = f"sqlite:///{db_path}"
        runner = MagicMock(
            return_value=AlembicCommandResult(
                command="upgrade",
                target="head",
                success=True,
                message="ok",
                dry_run=False,
                executed=True,
                argv=("python", "-m", "alembic", "upgrade", "head"),
            )
        )
        plan = prepare_schema_startup_authoritative(
            database_url=database_url,
            environ=FLAG_ON,
            run_upgrade_head_fn=runner,
        )
        assert plan.skip_migrate_schema is True
        assert plan.schema_step_succeeded is True
        runner.assert_called_once()

    def test_scenario_populated_behind_head_blocks_even_with_gate(
        self, populated_db, tmp_path
    ):
        import shutil

        database_url, engine = populated_db
        _create_alembic_version_table(engine)
        _stamp(engine, "0001")
        db_path = database_url.removeprefix("sqlite:///")
        backup_path = tmp_path / "populated.bak"
        shutil.copy(db_path, backup_path)
        gate_env = {
            **FLAG_ON,
            "ERP_SCHEMA_BACKUP_PATH": str(backup_path),
            "ERP_SCHEMA_MIGRATION_CONFIRMATION": REQUIRED_CONFIRMATION_PHRASE,
        }
        two_head_revisions = {"0001": None, "0002": "0001"}
        with patch(
            "services.schema_version.discover_local_revisions",
            return_value=two_head_revisions,
        ):
            with pytest.raises(SchemaStartupError) as exc:
                prepare_schema_startup_authoritative(
                    database_url=database_url,
                    environ=gate_env,
                    run_upgrade_head_fn=MagicMock(),
                )
        assert exc.value.action == ACTION_ALEMBIC_UPGRADE_HEAD

    def test_scenario_rollback_flag_off_after_block(self, populated_db):
        database_url, engine = populated_db
        with pytest.raises(SchemaStartupError):
            prepare_schema_startup_authoritative(
                database_url=database_url,
                environ=FLAG_ON,
                run_upgrade_head_fn=MagicMock(),
            )
        reset_schema_startup_plan()
        migrate_calls: list[str] = []
        SessionLocal = sessionmaker(bind=engine)
        prepare_schema_startup_authoritative(
            database_url=database_url,
            environ=FLAG_OFF,
        )
        with SessionLocal() as session:
            run_schema_startup_in_session(
                session,
                migrate_schema_fn=lambda _s: migrate_calls.append("migrate"),
                log_diagnostics_fn=lambda _s: None,
                environ=FLAG_OFF,
            )
        assert migrate_calls == ["migrate"]
