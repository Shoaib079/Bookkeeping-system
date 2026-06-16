"""P3.2-A — contract tests for Alembic introduction scaffold.

Verifies files, documentation sections, and absence of real migration revisions.
Does not run ``alembic upgrade`` or mutate any database.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"
ALEMBIC_ENV = PROJECT_ROOT / "alembic" / "env.py"
ALEMBIC_VERSIONS = PROJECT_ROOT / "alembic" / "versions"
DOC_PATH = PROJECT_ROOT / "docs" / "P3_2_ALEMBIC_INTRODUCTION_PLAN.md"

REQUIRED_SECTIONS = (
    "Purpose",
    "Non-goals",
    "Current SQLite migration helpers remain active",
    "Alembic is introduced but not authoritative yet",
    "Future cutover plan",
    "Rules for creating migrations",
    "Rollback strategy",
    "How this affects local Streamlit use",
    "How this affects FastAPI tests",
    "Why Float → Decimal is deferred",
)

# Alembic op / DDL calls that would indicate a real migration body.
DDL_OPERATION_PATTERNS = (
    r"\bop\.add_column\b",
    r"\bop\.drop_column\b",
    r"\bop\.create_table\b",
    r"\bop\.drop_table\b",
    r"\bop\.create_index\b",
    r"\bop\.drop_index\b",
    r"\bop\.execute\b",
    r"\bop\.batch_alter_table\b",
    r"\bop\.alter_column\b",
)


@pytest.fixture(scope="module")
def doc_text() -> str:
    assert DOC_PATH.exists(), f"Plan doc missing: {DOC_PATH}"
    return DOC_PATH.read_text(encoding="utf-8")


def test_alembic_ini_exists():
    assert ALEMBIC_INI.exists(), f"Missing {ALEMBIC_INI}"
    assert ALEMBIC_INI.stat().st_size > 0


def test_alembic_env_py_exists():
    assert ALEMBIC_ENV.exists(), f"Missing {ALEMBIC_ENV}"
    assert ALEMBIC_ENV.stat().st_size > 0


def test_alembic_versions_directory_exists():
    assert ALEMBIC_VERSIONS.is_dir(), f"Missing directory: {ALEMBIC_VERSIONS}"


def test_plan_doc_exists():
    assert DOC_PATH.exists(), f"Plan doc missing: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0


@pytest.mark.parametrize("section", REQUIRED_SECTIONS)
def test_required_sections_present(doc_text, section):
    assert section.lower() in doc_text.lower(), f"Missing required section: {section!r}"


def test_env_py_wires_base_metadata():
    text = ALEMBIC_ENV.read_text(encoding="utf-8")
    assert "from db import Base" in text
    assert "import models" in text
    assert "target_metadata = Base.metadata" in text


def test_baseline_revision_exists_with_expected_metadata():
    py_files = sorted(ALEMBIC_VERSIONS.glob("*.py"))
    assert [p.name for p in py_files] == [
        "0001_baseline.py",
        "0002_money_numeric.py",
    ], f"Unexpected revision files: {[p.name for p in py_files]}"
    baseline = (ALEMBIC_VERSIONS / "0001_baseline.py").read_text(encoding="utf-8")
    assert 'revision = "0001"' in baseline
    assert "down_revision = None" in baseline
    money_numeric = (ALEMBIC_VERSIONS / "0002_money_numeric.py").read_text(encoding="utf-8")
    assert 'revision = "0002"' in money_numeric
    assert 'down_revision = "0001"' in money_numeric


def test_alembic_ini_points_at_script_location():
    text = ALEMBIC_INI.read_text(encoding="utf-8")
    assert "script_location = alembic" in text


def test_requirements_lists_alembic():
    req = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "alembic" in req, "requirements.txt must list alembic dependency"


def test_alembic_config_import_smoke():
    """Load alembic.ini via the installed package Config API — no DB upgrade.

    The local ``alembic/`` migration tree is on ``sys.path`` during pytest and
    shadows ``import alembic``; load ``config.py`` from site-packages explicitly.
    """
    import importlib.util
    import site

    config_py = None
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        candidate = Path(sp) / "alembic" / "config.py"
        if candidate.is_file():
            config_py = candidate
            break
    if config_py is None:
        pytest.skip("alembic package not installed")

    spec = importlib.util.spec_from_file_location(
        "alembic_config_installed", config_py
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    cfg = mod.Config(str(ALEMBIC_INI))
    assert cfg.get_main_option("script_location") == "alembic"


def test_doc_states_migrate_schema_still_authoritative(doc_text):
    lowered = doc_text.lower()
    assert "migrate_schema" in lowered
    assert "remain" in lowered or "remains" in lowered or "authoritative" in lowered


def test_doc_states_no_upgrade_in_p32a(doc_text):
    lowered = doc_text.lower()
    assert "do not" in lowered and "upgrade" in lowered


def _upgrade_body_is_noop(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "upgrade":
            body = node.body
            if not body:
                return True
            if len(body) == 1 and isinstance(body[0], ast.Pass):
                return True
            if (
                len(body) == 1
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                return True
    return False


def test_any_placeholder_revision_is_documented_noop():
    """P3.2-A placeholder revisions must be pass-only; 0001/0002 are real revisions."""
    real_revisions = {"0001_baseline.py", "0002_money_numeric.py"}
    for path in ALEMBIC_VERSIONS.glob("*.py"):
        if path.name in real_revisions:
            continue
        source = path.read_text(encoding="utf-8")
        for pattern in DDL_OPERATION_PATTERNS:
            assert not re.search(pattern, source), (
                f"{path.name} contains DDL operation {pattern!r}; "
                "P3.2-A forbids real migration operations"
            )
        assert _upgrade_body_is_noop(source), (
            f"{path.name} upgrade() must be empty/pass placeholder only"
        )
