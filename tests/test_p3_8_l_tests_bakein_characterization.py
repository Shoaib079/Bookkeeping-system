"""P3.8-L-TESTS — Alembic authority bake-in characterization gate.

Pins §6 invariants from docs/P3_8_L_BAKEIN_AUDIT.md required before
migrate_schema() retirement. Tests-only; no production code change.

Cross-ref: docs/P3_8_L_TESTS.md
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from db import Base
from p3_schema_equivalence_utils import (
    assert_alembic_0001_matches_migrate_schema,
    run_post_0001_baseline_equivalence,
)
from services.schema_startup import (
    ACTION_RUN_MIGRATE_SCHEMA,
    ALEMBIC_AUTHORITATIVE_ENV_VAR,
    decide_schema_startup_action,
)
from services.schema_startup_wiring import (
    prepare_schema_startup_authoritative,
    reset_schema_startup_plan,
    run_schema_startup_in_session,
)
from services.schema_version import (
    ALEMBIC_VERSION_TABLE,
    STATUS_AHEAD_OF_CODE,
    STATUS_AT_HEAD,
    STATUS_BEHIND_HEAD,
    STATUS_UNKNOWN,
    STATUS_UNSTAMPED,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_8_L_TESTS.md"
APP_PATH = ROOT / "app.py"
EXEC_TEST = ROOT / "tests" / "test_p3_8_l_exec_bakein_execution.py"
K2_TEST = ROOT / "tests" / "test_p3_8_k2_startup_wiring.py"
P34D_TEST = ROOT / "tests" / "test_p3_4_d_alembic_baseline.py"


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


# ── Doc contract ──────────────────────────────────────────────────────────────


class TestBakeInCharacterizationDocContract:
    @pytest.fixture(scope="class")
    def doc_text(self) -> str:
        assert DOC_PATH.exists(), f"Missing gate doc: {DOC_PATH}"
        return DOC_PATH.read_text(encoding="utf-8")

    def test_doc_exists(self):
        assert DOC_PATH.exists()
        assert DOC_PATH.stat().st_size > 0

    def test_doc_covers_all_section_six_gates(self, doc_text: str):
        low = doc_text.lower()
        for label in (
            "schema equivalence",
            "single runtime caller",
            "never invokes",
            "postgresql",
            "lock-safety",
            "flag-off parity",
            "end-to-end",
        ):
            assert label in low, f"Gate doc missing invariant: {label!r}"

    def test_doc_states_not_ready_to_retire(self, doc_text: str):
        low = doc_text.lower()
        assert "not ready to retire" in low or "no retirement" in low

    def test_supporting_test_modules_exist(self):
        for path in (EXEC_TEST, K2_TEST, P34D_TEST):
            assert path.exists(), f"Missing supporting test module: {path}"


# ── Schema equivalence gate ───────────────────────────────────────────────────


class TestSchemaEquivalenceGate:
    def test_alembic_0001_matches_migrate_schema_evolved_continuously(self):
        result = run_post_0001_baseline_equivalence()
        assert_alembic_0001_matches_migrate_schema(result["drift"])

    def test_equivalence_harness_never_imports_production_database_url(self):
        utils = ROOT / "tests" / "p3_schema_equivalence_utils.py"
        text = utils.read_text(encoding="utf-8")
        assert "from paths import DATABASE_URL" not in text
        assert "from paths import" not in text


class TestSingleCallerGuard:
    def test_app_wires_migrate_schema_only_via_dispatcher(self):
        text = APP_PATH.read_text(encoding="utf-8")
        assert text.count("migrate_schema_fn=migrate_schema") == 1
        assert "def migrate_schema(session)" in text
        for lineno, line in enumerate(text.splitlines(), 1):
            if "def migrate_schema(session)" in line:
                continue
            if re.search(r"\bmigrate_schema\s*\(\s*session", line):
                pytest.fail(
                    f"app.py line {lineno} must not call migrate_schema(session) "
                    f"outside the dispatcher: {line.strip()!r}"
                )

    def test_services_never_import_or_call_app_migrate_schema(self):
        services_dir = ROOT / "services"
        for path in sorted(services_dir.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            assert "from app import migrate_schema" not in text, path.name
            assert "app.migrate_schema(" not in text, path.name
            if path.name != "schema_startup_wiring.py":
                assert "migrate_schema_fn" not in text, path.name

    def test_startup_wiring_is_only_runtime_dispatch_site(self):
        app_text = APP_PATH.read_text(encoding="utf-8")
        assert "_run_schema_startup(_boot_session)" in app_text
        assert "migrate_schema(_boot_session)" not in app_text.replace(
            "migrate_schema_fn=migrate_schema", ""
        )


# ── Never-on-PG (flag-on decision + wiring) ───────────────────────────────────


class TestPostgreSQLNeverMigrateSchemaWhenFlagOn:
    @pytest.mark.parametrize(
        "schema_status",
        [
            STATUS_UNSTAMPED,
            STATUS_AT_HEAD,
            STATUS_BEHIND_HEAD,
            STATUS_AHEAD_OF_CODE,
            STATUS_UNKNOWN,
        ],
    )
    def test_pure_decision_never_run_migrate_schema(self, schema_status: str):
        decision = decide_schema_startup_action(
            flag_authoritative=True,
            schema_status=schema_status,
            is_new_db=False,
            dialect="postgresql",
            db_revision="0001",
            head_revision="0001",
        )
        assert decision.action != ACTION_RUN_MIGRATE_SCHEMA

    def test_wiring_skips_migrate_fn_when_flag_on_at_head(self, tmp_path):
        import models  # noqa: F401

        db_path = tmp_path / "at_head.db"
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(engine)
        _create_alembic_version_table(engine)
        _stamp(engine, "0001")

        migrate_calls: list[str] = []
        prepare_schema_startup_authoritative(
            database_url=database_url,
            environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
            run_upgrade_head_fn=MagicMock(),
        )
        SessionLocal = sessionmaker(bind=engine)
        with SessionLocal() as session:
            run_schema_startup_in_session(
                session,
                migrate_schema_fn=lambda _s: migrate_calls.append("migrate"),
                log_diagnostics_fn=lambda _s: None,
                environ={ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"},
            )
        assert migrate_calls == []


# ── Lock-safety ───────────────────────────────────────────────────────────────


class TestLockSafety:
    def test_prepare_runs_before_boot_session_in_main(self):
        main_src = inspect.getsource(__import__("app", fromlist=["main"]).main)
        assert main_src.index("prepare_schema_startup_authoritative()") < main_src.index(
            "with get_session() as _boot_session:"
        )

    def test_runner_subprocess_not_in_wiring_module(self):
        wiring_src = inspect.getsource(prepare_schema_startup_authoritative).lower()
        assert "run_upgrade_head" in wiring_src
        assert "subprocess.run" not in wiring_src
        assert "import subprocess" not in wiring_src


# ── Flag-off parity ───────────────────────────────────────────────────────────


class TestFlagOffParity:
    def test_wiring_source_migrate_before_diagnostics(self):
        wiring_src = inspect.getsource(run_schema_startup_in_session)
        assert wiring_src.index("migrate_schema_fn(session)") < wiring_src.index(
            "log_fn(session)"
        )

    def test_flag_off_invokes_migrate_then_diagnostics_in_order(self):
        migrate_calls: list[str] = []
        diag_calls: list[str] = []
        engine = _make_memory_engine()
        SessionLocal = sessionmaker(bind=engine)
        try:
            prepare_schema_startup_authoritative(
                database_url=str(engine.url),
                environ={},
            )
            with SessionLocal() as session:
                run_schema_startup_in_session(
                    session,
                    migrate_schema_fn=lambda _s: migrate_calls.append("migrate"),
                    log_diagnostics_fn=lambda _s: diag_calls.append("diag"),
                    environ={},
                )
        finally:
            engine.dispose()
        assert migrate_calls == ["migrate"]
        assert diag_calls == ["diag"]
