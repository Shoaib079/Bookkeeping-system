"""P3.9-B-CHAR — migrate_schema() caller inventory & deprecation contract.

Pins all call sites and the P3.9-B DeprecationWarning contract before implementation.
Tests-only; no production code change.

Cross-ref: docs/P3_9_B_CHAR_MIGRATE_SCHEMA_CALLERS.md
"""

from __future__ import annotations

import ast
import warnings
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from db import Base

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "docs" / "P3_9_B_CHAR_MIGRATE_SCHEMA_CALLERS.md"
APP_PATH = ROOT / "app.py"
WIRING_PATH = ROOT / "services" / "schema_startup_wiring.py"

# Pinned direct app.migrate_schema call sites (production + test harness).
DIRECT_APP_MIGRATE_SCHEMA_CALLS: dict[str, int] = {
    "tests/p3_schema_equivalence_utils.py": 1,
    "tests/test_phase14da_model.py": 3,
}

MOCK_INJECTION_MODULES = (
    "tests/test_p3_8_k2_startup_wiring.py",
    "tests/test_p3_8_l_exec_bakein_execution.py",
    "tests/test_p3_8_l_tests_bakein_characterization.py",
)

DEPRECATION_MESSAGE_SNIPPET = (
    "migrate_schema() is deprecated; use Alembic (ERP_ALEMBIC_AUTHORITATIVE=1)"
)

REQUIRED_DOC_SECTIONS = (
    "Executive summary",
    "Production runtime path",
    "Test harness — direct callers",
    "Test harness — mock injections",
    "P3.9-B deprecation warning contract",
    "PostgreSQL",
    "No-change statement",
)


def _repo_py_files() -> list[Path]:
    skip = {"__pycache__", ".git", ".venv", "venv", "node_modules"}
    paths: list[Path] = []
    for path in ROOT.rglob("*.py"):
        if any(part in skip for part in path.parts):
            continue
        paths.append(path)
    return sorted(paths)


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _count_app_migrate_schema_calls(path: Path) -> int:
    """Count real AST call sites — ignores string literals and docstrings."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return 0
    count = 0
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
            count += 1
    return count


def _scan_direct_app_migrate_schema_calls() -> dict[str, int]:
    skip_prefixes = (
        "tests/test_p3_9_b_char_migrate_schema_callers.py",
    )
    found: dict[str, int] = {}
    for path in _repo_py_files():
        rel = _rel(path)
        if rel == "app.py" or rel in skip_prefixes:
            continue
        count = _count_app_migrate_schema_calls(path)
        if count:
            found[rel] = count
    return found


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
    assert DOC_PATH.exists(), f"P3.9-B-CHAR doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_migrate_schema_source() -> str:
    import app

    import inspect

    return inspect.getsource(app.migrate_schema)


# ── Doc contract ──────────────────────────────────────────────────────────────


class TestP39BCharDocContract:
    def test_doc_exists(self):
        assert DOC_PATH.exists()
        assert DOC_PATH.stat().st_size > 0

    @pytest.mark.parametrize("section", REQUIRED_DOC_SECTIONS)
    def test_required_sections(self, doc_text: str, section: str):
        assert section.lower() in doc_text.lower(), f"Missing section: {section!r}"

    def test_doc_states_no_warning_yet(self, doc_text: str):
        low = doc_text.lower()
        assert "no" in low and "deprecationwarning" in low
        assert "not implemented" in low or "not yet" in low or "p3.9-b" in low

    def test_doc_pins_deprecation_message(self, doc_text: str):
        assert DEPRECATION_MESSAGE_SNIPPET in doc_text

    def test_doc_pins_stacklevel_two(self, doc_text: str):
        assert "stacklevel=2" in doc_text or "stacklevel=2," in doc_text


# ── Direct caller inventory ───────────────────────────────────────────────────


class TestDirectCallerInventory:
    def test_pinned_direct_call_site_counts(self):
        for rel_path, expected in DIRECT_APP_MIGRATE_SCHEMA_CALLS.items():
            count = _count_app_migrate_schema_calls(ROOT / rel_path)
            assert count == expected, (
                f"{rel_path}: expected {expected} app.migrate_schema( calls, found {count}"
            )

    def test_no_unpinned_app_migrate_schema_calls_in_repo(self):
        found = _scan_direct_app_migrate_schema_calls()
        assert found == DIRECT_APP_MIGRATE_SCHEMA_CALLS, (
            "Unexpected app.migrate_schema call sites — update P3.9-B-CHAR inventory: "
            f"{found!r}"
        )

    def test_equivalence_harness_calls_migrate_schema(self):
        text = (ROOT / "tests/p3_schema_equivalence_utils.py").read_text(encoding="utf-8")
        assert "build_migrate_evolved_schema_summary" in text
        assert "app.migrate_schema(session)" in text


# ── Runtime wiring guards (extends P3.8-L-TESTS) ─────────────────────────────


class TestRuntimeWiringInventory:
    def test_single_migrate_schema_fn_injection_in_app(self):
        text = APP_PATH.read_text(encoding="utf-8")
        assert text.count("migrate_schema_fn=migrate_schema") == 1

    def test_wiring_dispatches_migrate_schema_fn(self):
        text = WIRING_PATH.read_text(encoding="utf-8")
        assert text.count("migrate_schema_fn(session)") == 2

    def test_services_never_import_app_migrate_schema(self):
        for path in sorted((ROOT / "services").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            assert "from app import migrate_schema" not in text, path.name
            assert "app.migrate_schema(" not in text, path.name

    def test_mock_injection_modules_exist(self):
        for rel in MOCK_INJECTION_MODULES:
            assert (ROOT / rel).exists(), f"Missing mock-injection module: {rel}"


# ── Pre-B: no DeprecationWarning today ───────────────────────────────────────


class TestPreBNoDeprecationWarning:
    def test_migrate_schema_source_has_no_warnings_warn(self, app_migrate_schema_source: str):
        assert "warnings.warn" not in app_migrate_schema_source
        assert "DeprecationWarning" not in app_migrate_schema_source

    def test_migrate_schema_emits_no_deprecation_warning(self):
        import app  # noqa: F401

        engine = _make_memory_engine()
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            with Session() as session:
                app.migrate_schema(session)
        dep_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert dep_warnings == [], (
            "P3.9-B-CHAR pins zero DeprecationWarning pre-B; "
            f"found: {[str(w.message) for w in dep_warnings]}"
        )


# ── P3.9-B contract (future implementation pins) ─────────────────────────────


class TestP39BDeprecationContractPins:
    def test_contract_message_in_doc(self, doc_text: str):
        assert DEPRECATION_MESSAGE_SNIPPET in doc_text
        assert "P3.9-C" in doc_text

    def test_contract_category_deprecation_warning(self, doc_text: str):
        assert "DeprecationWarning" in doc_text

    def test_contract_warns_every_entry(self, doc_text: str):
        low = doc_text.lower()
        assert "every" in low and "entry" in low

    def test_receipt_ai_inspects_source_not_call(self):
        text = (
            ROOT / "tests/test_receipt_ai_02_impl_3_learning_map.py"
        ).read_text(encoding="utf-8")
        assert "inspect.getsource" in text
        assert _count_app_migrate_schema_calls(
            ROOT / "tests/test_receipt_ai_02_impl_3_learning_map.py"
        ) == 0

    def test_app_defines_migrate_schema_once(self):
        tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
        defs = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "migrate_schema"
        ]
        assert defs == ["migrate_schema"]
