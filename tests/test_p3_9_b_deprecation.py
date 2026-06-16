"""P3.9-B — migrate_schema() DeprecationWarning implementation contract.

Cross-ref: docs/P3_9_B_DEPRECATION.md · docs/P3_9_B_CHAR_MIGRATE_SCHEMA_CALLERS.md
"""

from __future__ import annotations

import inspect
import warnings
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from db import Base
from services.schema_startup import ALEMBIC_AUTHORITATIVE_ENV_VAR
from services.schema_startup_wiring import (
    prepare_schema_startup_authoritative,
    reset_schema_startup_plan,
    run_schema_startup_in_session,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_9_B_DEPRECATION.md"
UTILS_PATH = ROOT / "tests" / "p3_schema_equivalence_utils.py"

FLAG_OFF = {ALEMBIC_AUTHORITATIVE_ENV_VAR: "0"}

REQUIRED_SECTIONS = (
    "Verdict",
    "Implementation",
    "Test harness updates",
    "Rollback",
    "Next slice",
    "No-change statement",
)


def _make_memory_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    return engine


@pytest.fixture(autouse=True)
def _clear_startup_plan():
    reset_schema_startup_plan()
    yield
    reset_schema_startup_plan()


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"P3.9-B doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


# ── Doc contract ──────────────────────────────────────────────────────────────


class TestP39BDocContract:
    def test_doc_exists(self):
        assert DOC_PATH.exists()
        assert DOC_PATH.stat().st_size > 0

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_required_sections(self, doc_text: str, section: str):
        assert section.lower() in doc_text.lower(), f"Missing section: {section!r}"

    def test_doc_states_phase_b_shipped(self, doc_text: str):
        low = doc_text.lower()
        assert "phase b" in low and "shipped" in low
        assert "not removed" in low or "p3.9-c" in low

    def test_doc_names_constant(self, doc_text: str):
        assert "MIGRATE_SCHEMA_DEPRECATION_MESSAGE" in doc_text


# ── Source contract ───────────────────────────────────────────────────────────


class TestP39BSourceContract:
    def test_constant_matches_message(self):
        import app

        assert app.MIGRATE_SCHEMA_DEPRECATION_MESSAGE.startswith(
            "migrate_schema() is deprecated"
        )
        assert "ERP_ALEMBIC_AUTHORITATIVE=1" in app.MIGRATE_SCHEMA_DEPRECATION_MESSAGE
        assert "P3.9-C" in app.MIGRATE_SCHEMA_DEPRECATION_MESSAGE

    def test_migrate_schema_warns_with_stacklevel_two(self):
        import app

        src = inspect.getsource(app.migrate_schema)
        assert "warnings.warn" in src
        assert "MIGRATE_SCHEMA_DEPRECATION_MESSAGE" in src
        assert "DeprecationWarning" in src
        assert "stacklevel=2" in src

    def test_equivalence_harness_filters_deprecation(self):
        text = UTILS_PATH.read_text(encoding="utf-8")
        assert "catch_warnings" in text
        assert "simplefilter" in text
        assert "DeprecationWarning" in text


# ── Runtime behavior ──────────────────────────────────────────────────────────


class TestP39BDeprecationWarningBehavior:
    def test_single_call_emits_deprecation_warning(self):
        import app

        engine = _make_memory_engine()
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        with pytest.warns(DeprecationWarning, match=r"migrate_schema\(\) is deprecated"):
            with Session() as session:
                app.migrate_schema(session)

    def test_double_call_emits_two_warnings(self):
        import app

        engine = _make_memory_engine()
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            with Session() as session:
                app.migrate_schema(session)
                app.migrate_schema(session)
        dep = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(dep) == 2
        assert all("migrate_schema() is deprecated" in str(w.message) for w in dep)

    def test_idempotent_schema_after_warning(self):
        import app

        engine = _make_memory_engine()
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with Session() as session:
                app.migrate_schema(session)
                app.migrate_schema(session)
        # no exception — idempotency preserved

    def test_flag_off_startup_invokes_real_migrate_schema_with_warning(self):
        import app

        engine = _make_memory_engine()
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine)
        try:
            prepare_schema_startup_authoritative(
                database_url=str(engine.url),
                environ=FLAG_OFF,
            )
            with pytest.warns(DeprecationWarning, match=r"migrate_schema\(\) is deprecated"):
                with SessionLocal() as session:
                    run_schema_startup_in_session(
                        session,
                        migrate_schema_fn=app.migrate_schema,
                        log_diagnostics_fn=lambda _s: None,
                        environ=FLAG_OFF,
                    )
        finally:
            engine.dispose()

    def test_mock_migrate_schema_fn_emits_no_warning(self):
        engine = _make_memory_engine()
        SessionLocal = sessionmaker(bind=engine)
        try:
            prepare_schema_startup_authoritative(
                database_url=str(engine.url),
                environ=FLAG_OFF,
            )
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", DeprecationWarning)
                with SessionLocal() as session:
                    run_schema_startup_in_session(
                        session,
                        migrate_schema_fn=lambda _s: None,
                        log_diagnostics_fn=lambda _s: None,
                        environ=FLAG_OFF,
                    )
        finally:
            engine.dispose()

        dep = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert dep == []
