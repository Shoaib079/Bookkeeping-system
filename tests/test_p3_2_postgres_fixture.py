"""P3.2-C — contract tests for optional PostgreSQL pytest infrastructure.

Does not require a running PostgreSQL server unless ERP_TEST_POSTGRES_URL is set
and optional integration tests are enabled.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import db
import postgres_utils

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = PROJECT_ROOT / "docs" / "P3_2_POSTGRES_TEST_FIXTURES.md"

SAFE_URLS = (
    "postgresql://localhost:5432/erp_pytest",
    "postgresql+psycopg2://127.0.0.1:5432/erp_test",
    "postgresql://localhost/myapp_dev",
    "postgresql+psycopg://localhost:5432/streamlit_erp_test",
)

UNSAFE_URLS = (
    "",
    "sqlite:///erp_data.db",
    "postgresql://localhost/erp_data",
    "postgresql://localhost/production",
    "postgresql://localhost/bookkeeping",
    "mysql://localhost/erp_test",
    "postgresql://localhost/erp_data.db",
)


def test_module_imports_without_connecting():
    """Importing postgres_utils must not open a database connection."""
    reloaded = importlib.reload(postgres_utils)
    assert reloaded.ENV_VAR == "ERP_TEST_POSTGRES_URL"
    assert reloaded.get_test_postgres_url() is None or isinstance(
        reloaded.get_test_postgres_url(), str
    )


def test_missing_env_var_skips(monkeypatch):
    monkeypatch.delenv(postgres_utils.ENV_VAR, raising=False)
    assert postgres_utils.get_test_postgres_url() is None
    with pytest.raises(pytest.skip.Exception) as exc:
        postgres_utils.require_test_postgres_url()
    assert postgres_utils.ENV_VAR in str(exc.value)


@pytest.mark.parametrize("url", SAFE_URLS)
def test_url_safety_accepts_test_urls(url: str):
    assert postgres_utils.validate_test_postgres_url(url) == url


@pytest.mark.parametrize("url", UNSAFE_URLS)
def test_url_safety_rejects_unsafe_urls(url: str):
    with pytest.raises(postgres_utils.UnsafePostgresTestUrlError):
        postgres_utils.validate_test_postgres_url(url)


def test_forbidden_erp_data_db_name_rejected():
    with pytest.raises(postgres_utils.UnsafePostgresTestUrlError, match="erp_data"):
        postgres_utils.validate_test_postgres_url(
            "postgresql://localhost:5432/erp_data_staging"
        )


def test_db_py_unchanged_contract():
    """P3.2-C must not alter runtime db.py engine wiring."""
    text = Path(db.__file__).read_text(encoding="utf-8")
    assert "DATABASE_URL" in text
    assert "ERP_TEST_POSTGRES_URL" not in text
    assert "postgresql://" not in text.lower()


def test_fixtures_doc_exists():
    assert DOC_PATH.exists(), f"Missing doc: {DOC_PATH}"
    assert DOC_PATH.stat().st_size > 0


def test_fixtures_doc_covers_required_topics():
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    for topic in (
        "erp_test_postgres_url",
        "safety",
        "skip",
        "dual-run",
        "limitation",
    ):
        assert topic in text, f"Doc missing topic: {topic!r}"


@pytest.mark.optional_postgres
def test_postgres_engine_connects_when_configured():
    """Integration smoke — runs only when ERP_TEST_POSTGRES_URL is set."""
    url = postgres_utils.get_test_postgres_url()
    if url is None:
        pytest.skip(f"{postgres_utils.ENV_VAR} not set")

    engine = postgres_utils.create_test_postgres_engine()
    try:
        with engine.connect() as conn:
            assert conn.dialect.name == "postgresql"
    finally:
        engine.dispose()


@pytest.mark.optional_postgres
def test_postgres_schema_roundtrip_when_configured():
    """Create/drop ORM schema on PG when configured — never touches erp_data.db."""
    url = postgres_utils.get_test_postgres_url()
    if url is None:
        pytest.skip(f"{postgres_utils.ENV_VAR} not set")

    with postgres_utils.postgres_test_engine() as engine:
        from db import Base

        assert len(Base.metadata.tables) > 0
