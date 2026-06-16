"""P3.9-C — migrate_schema() implementation removal contract.

Cross-ref: docs/P3_9_C_REMOVAL.md
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, inspect as sa_inspect
from sqlalchemy.orm import sessionmaker

from db import Base
from p3_schema_equivalence_utils import (
    assert_alembic_0001_matches_migrate_schema,
    run_post_0001_baseline_equivalence,
)

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_9_C_REMOVAL.md"
APP_PATH = ROOT / "app.py"
LEGACY_PATH = ROOT / "tests" / "legacy_migrate_schema.py"

REQUIRED_SECTIONS = (
    "Verdict",
    "Implementation",
    "Flag-off path",
    "Test harness",
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


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"P3.9-C doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


class TestP39CDocContract:
    def test_doc_exists(self):
        assert DOC_PATH.exists()
        assert DOC_PATH.stat().st_size > 0

    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_required_sections(self, doc_text: str, section: str):
        assert section.lower() in doc_text.lower(), f"Missing section: {section!r}"

    def test_doc_states_phase_c_shipped(self, doc_text: str):
        low = doc_text.lower()
        assert "phase c" in low and "shipped" in low
        assert "no-op" in low or "no op" in low


class TestP39CProductionStub:
    def test_legacy_module_exists(self):
        assert LEGACY_PATH.exists()
        assert LEGACY_PATH.stat().st_size > 10_000

    def test_app_migrate_schema_has_no_ddl(self):
        import app

        src = inspect.getsource(app.migrate_schema)
        assert "ALTER TABLE" not in src
        assert "CREATE INDEX" not in src
        assert "MigrationFlag" not in src

    def test_legacy_has_ddl_body(self):
        text = LEGACY_PATH.read_text(encoding="utf-8")
        assert "ALTER TABLE" in text
        assert "CREATE INDEX IF NOT EXISTS" in text

    def test_app_migrate_schema_is_short_stub(self):
        import app

        src = inspect.getsource(app.migrate_schema)
        assert src.count("\n") < 15

    def test_no_direct_app_migrate_schema_outside_deprecation_tests(self):
        skip = {
            "tests/test_p3_9_b_deprecation.py",
            "tests/test_p3_9_c_removal.py",
            "tests/test_p3_9_b_char_migrate_schema_callers.py",
        }
        found: list[str] = []
        for path in sorted((ROOT / "tests").rglob("*.py")):
            rel = path.relative_to(ROOT).as_posix()
            if rel in skip or rel == "tests/legacy_migrate_schema.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "migrate_schema"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "app"
                ):
                    found.append(rel)
                    break
        assert found == [], f"unexpected app.migrate_schema callers: {found}"

    def test_no_op_does_not_add_columns(self):
        import app

        engine = _make_memory_engine()
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        with Session() as session:
            before = {c["name"] for c in sa_inspect(engine).get_columns("companies")}
            app.migrate_schema(session)
            after = {c["name"] for c in sa_inspect(engine).get_columns("companies")}
        assert before == after


class TestP39CSchemaEquivalenceGate:
    def test_alembic_0001_still_matches_legacy_evolved_schema(self):
        result = run_post_0001_baseline_equivalence()
        assert_alembic_0001_matches_migrate_schema(result["drift"])
