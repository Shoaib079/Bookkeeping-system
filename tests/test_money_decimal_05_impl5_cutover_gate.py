"""MD-05-IMPL-5 — flag-gated money NUMERIC cutover (0001 → 0002)."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from services.alembic_runner import AlembicCommandResult
from services.money_numeric_cutover import (
    MONEY_NUMERIC_CUTOVER_ENV_VAR,
    MONEY_NUMERIC_FROM_REVISION,
    MONEY_NUMERIC_PRODUCTION_APPROVAL_ENV_VAR,
    MONEY_NUMERIC_PRODUCTION_APPROVAL_PHRASE,
    MONEY_NUMERIC_TO_REVISION,
    evaluate_money_numeric_cutover_gate,
    is_money_numeric_cutover_eligible,
    is_money_numeric_production_approval_given,
    parse_money_numeric_cutover_flag,
    resolve_money_numeric_allow_production,
)
from services.schema_migration_gate import REQUIRED_CONFIRMATION_PHRASE
from services.schema_startup import (
    ACTION_ALEMBIC_UPGRADE_HEAD,
    ALEMBIC_AUTHORITATIVE_ENV_VAR,
    STATUS_BEHIND_HEAD,
)
from services.schema_startup_wiring import (
    SchemaStartupError,
    SchemaStartupSessionPlan,
    SchemaStartupSessionPlan,
    prepare_schema_startup_authoritative,
    reset_schema_startup_plan,
    run_schema_startup_in_session,
)
from services.schema_version import ALEMBIC_VERSION_TABLE

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "MONEY_DECIMAL_05_IMPL_5.md"
CUTOVER_MODULE = ROOT / "services" / "money_numeric_cutover.py"
WIRING_MODULE = ROOT / "services" / "schema_startup_wiring.py"

FLAG_ON = {ALEMBIC_AUTHORITATIVE_ENV_VAR: "1"}
CUTOVER_ON = {MONEY_NUMERIC_CUTOVER_ENV_VAR: "1"}


@pytest.fixture(autouse=True)
def _clear_startup_plan():
    reset_schema_startup_plan()
    yield
    reset_schema_startup_plan()


def _create_alembic_version_table(engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE TABLE {ALEMBIC_VERSION_TABLE} "
                "(version_num VARCHAR(32) NOT NULL)"
            )
        )


def _stamp(engine, revision: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(f"INSERT INTO {ALEMBIC_VERSION_TABLE} (version_num) VALUES (:rev)"),
            {"rev": revision},
        )


class TestImpl5DocContract:
    def test_impl5_doc_exists(self):
        assert DOC_PATH.exists()
        assert DOC_PATH.stat().st_size > 0

    def test_impl5_doc_covers_scope(self):
        text_doc = DOC_PATH.read_text(encoding="utf-8").lower()
        for topic in (
            "erp_money_numeric_cutover",
            "0001",
            "0002",
            "backup",
            "confirmation",
            "production",
            "erp_data.db",
        ):
            assert topic in text_doc, f"missing topic: {topic!r}"

    def test_cutover_module_wired_in_startup(self):
        src = WIRING_MODULE.read_text(encoding="utf-8")
        assert "money_numeric_cutover" in src
        assert "money_numeric_cutover_executed" in src
        assert "run_money_numeric_post_cutover" in src


class TestMoneyNumericCutoverFlag:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, False),
            ("", False),
            ("1", True),
            ("true", True),
            ("0", False),
            ("maybe", False),
        ],
    )
    def test_parse_cutover_flag(self, value, expected):
        assert parse_money_numeric_cutover_flag(value) is expected

    def test_production_approval_phrase_exact(self):
        assert is_money_numeric_production_approval_given(
            {MONEY_NUMERIC_PRODUCTION_APPROVAL_ENV_VAR: MONEY_NUMERIC_PRODUCTION_APPROVAL_PHRASE}
        )
        assert not is_money_numeric_production_approval_given(
            {MONEY_NUMERIC_PRODUCTION_APPROVAL_ENV_VAR: "wrong phrase"}
        )


class TestMoneyNumericCutoverEligibility:
    def test_eligible_only_for_0001_behind_0002(self):
        assert is_money_numeric_cutover_eligible(
            schema_status=STATUS_BEHIND_HEAD,
            db_revision=MONEY_NUMERIC_FROM_REVISION,
            head_revision=MONEY_NUMERIC_TO_REVISION,
        )
        assert not is_money_numeric_cutover_eligible(
            schema_status=STATUS_BEHIND_HEAD,
            db_revision="0000",
            head_revision=MONEY_NUMERIC_TO_REVISION,
        )
        assert not is_money_numeric_cutover_eligible(
            schema_status="at_head",
            db_revision=MONEY_NUMERIC_TO_REVISION,
            head_revision=MONEY_NUMERIC_TO_REVISION,
        )


class TestStartupWiringCutover:
    def test_behind_head_without_cutover_flag_still_blocks(self, tmp_path):
        import models  # noqa: F401
        from db import Base

        db_path = tmp_path / "populated.db"
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        _create_alembic_version_table(engine)
        _stamp(engine, MONEY_NUMERIC_FROM_REVISION)
        backup_path = tmp_path / "populated.bak"
        shutil.copy(db_path, backup_path)
        env = {
            **FLAG_ON,
            "ERP_SCHEMA_BACKUP_PATH": str(backup_path),
            "ERP_SCHEMA_MIGRATION_CONFIRMATION": REQUIRED_CONFIRMATION_PHRASE,
        }
        with pytest.raises(SchemaStartupError) as exc:
            prepare_schema_startup_authoritative(
                database_url=database_url,
                environ=env,
                run_upgrade_head_fn=MagicMock(),
            )
        assert exc.value.action == ACTION_ALEMBIC_UPGRADE_HEAD

    def test_cutover_flag_without_backup_blocks(self, tmp_path):
        import models  # noqa: F401
        from db import Base

        db_path = tmp_path / "populated.db"
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        _create_alembic_version_table(engine)
        _stamp(engine, MONEY_NUMERIC_FROM_REVISION)
        env = {**FLAG_ON, **CUTOVER_ON}
        with pytest.raises(SchemaStartupError):
            prepare_schema_startup_authoritative(
                database_url=database_url,
                environ=env,
                run_upgrade_head_fn=MagicMock(),
            )

    def test_cutover_flag_with_gate_runs_upgrade(self, tmp_path):
        import models  # noqa: F401
        from db import Base

        db_path = tmp_path / "populated.db"
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        _create_alembic_version_table(engine)
        _stamp(engine, MONEY_NUMERIC_FROM_REVISION)
        backup_path = tmp_path / "populated.bak"
        shutil.copy(db_path, backup_path)
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
        env = {
            **FLAG_ON,
            **CUTOVER_ON,
            "ERP_SCHEMA_BACKUP_PATH": str(backup_path),
            "ERP_SCHEMA_MIGRATION_CONFIRMATION": REQUIRED_CONFIRMATION_PHRASE,
        }
        plan = prepare_schema_startup_authoritative(
            database_url=database_url,
            environ=env,
            run_upgrade_head_fn=runner,
        )
        assert plan.money_numeric_cutover_executed is True
        assert plan.skip_migrate_schema is True
        runner.assert_called_once()

    def test_production_db_blocked_even_with_cutover_flag(self, tmp_path):
        import models  # noqa: F401
        from db import Base

        db_path = tmp_path / "erp_data.db"
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        _create_alembic_version_table(engine)
        _stamp(engine, MONEY_NUMERIC_FROM_REVISION)
        backup_path = tmp_path / "erp_data.bak"
        shutil.copy(db_path, backup_path)
        runner = MagicMock()
        env = {
            **FLAG_ON,
            **CUTOVER_ON,
            "ERP_SCHEMA_BACKUP_PATH": str(backup_path),
            "ERP_SCHEMA_MIGRATION_CONFIRMATION": REQUIRED_CONFIRMATION_PHRASE,
        }
        with pytest.raises(SchemaStartupError):
            prepare_schema_startup_authoritative(
                database_url=database_url,
                environ=env,
                run_upgrade_head_fn=runner,
            )
        runner.assert_not_called()
        assert not resolve_money_numeric_allow_production(database_url)

    def test_post_cutover_hook_runs_in_session(self, tmp_path, monkeypatch):
        import models  # noqa: F401
        from db import Base
        from services import schema_startup_wiring as wiring

        db_path = tmp_path / "populated.db"
        database_url = f"sqlite:///{db_path}"
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        _create_alembic_version_table(engine)
        _stamp(engine, MONEY_NUMERIC_TO_REVISION)
        wiring._session_plan = SchemaStartupSessionPlan(
            flag_authoritative=True,
            skip_migrate_schema=True,
            schema_step_succeeded=True,
            money_numeric_cutover_executed=True,
        )

        post_called: list[str] = []
        monkeypatch.setattr(
            "services.schema_startup_wiring.run_money_numeric_post_cutover",
            lambda _s: post_called.append("post"),
        )
        SessionLocal = sessionmaker(bind=engine)
        with SessionLocal() as session:
            run_schema_startup_in_session(
                session,
                migrate_schema_fn=lambda _s: None,
                log_diagnostics_fn=lambda _s: None,
                environ=FLAG_ON,
            )
        assert post_called == ["post"]


class TestMoneyNumericCutoverIntegration:
    """Real Alembic 0001→0002 on seeded throwaway DB (never production)."""

    @pytest.fixture
    def seeded_at_0001(self, tmp_path):
        if "streamlit" not in sys.modules:
            _st_mock = MagicMock()
            _st_mock.session_state = {}
            sys.modules["streamlit"] = _st_mock

        import app  # noqa: F401

        from tests.md05_migration_smoke_utils import (
            capture_money_snapshot,
            run_alembic_upgrade,
            seed_smoke_tenant,
            session_for_url,
        )

        db_path = tmp_path / "cutover_smoke.db"
        database_url = f"sqlite:///{db_path.as_posix()}"
        run_alembic_upgrade(database_url, "0001")
        session = session_for_url(database_url)
        try:
            seed_smoke_tenant(session)
            before = capture_money_snapshot(session)
        finally:
            session.close()
        backup_path = tmp_path / "cutover_smoke.bak"
        shutil.copy(db_path, backup_path)
        return database_url, backup_path, before

    def test_startup_cutover_preserves_money(self, seeded_at_0001):
        from services.alembic_runner import get_current_revision
        from tests.md05_migration_smoke_utils import (
            assert_sqlite_numeric_affinity,
            capture_money_snapshot,
            make_sqlite_file_engine,
            session_for_url,
        )

        database_url, backup_path, before = seeded_at_0001
        env = {
            **FLAG_ON,
            **CUTOVER_ON,
            "ERP_SCHEMA_BACKUP_PATH": str(backup_path),
            "ERP_SCHEMA_MIGRATION_CONFIRMATION": REQUIRED_CONFIRMATION_PHRASE,
        }
        plan = prepare_schema_startup_authoritative(
            database_url=database_url,
            environ=env,
        )
        assert plan.money_numeric_cutover_executed is True
        assert get_current_revision(database_url) == MONEY_NUMERIC_TO_REVISION

        engine = make_sqlite_file_engine(
            Path(database_url.removeprefix("sqlite:///"))
        )
        try:
            assert_sqlite_numeric_affinity(engine)
        finally:
            engine.dispose()

        session = session_for_url(database_url)
        try:
            after = capture_money_snapshot(session)
        finally:
            session.close()

        assert after.total_debit == before.total_debit
        assert after.total_credit == before.total_credit
        assert after.cash_balance == before.cash_balance
        assert after.pl_net == before.pl_net

    def test_cutover_gate_requires_confirmation(self, seeded_at_0001):
        database_url, backup_path, _before = seeded_at_0001
        gate = evaluate_money_numeric_cutover_gate(
            db_path_or_url=database_url,
            backup_path=str(backup_path),
            confirmation_value=None,
        )
        assert gate.allowed is False
        assert gate.requires_confirmation is True
