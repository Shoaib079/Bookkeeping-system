"""P3.2-C — optional PostgreSQL pytest helpers.

Activated only when ``ERP_TEST_POSTGRES_URL`` is set to a URL that passes the
safety validator. Importing this module does **not** connect to any database.

Runtime ``db.py`` / ``erp_data.db`` are never touched by these helpers.
"""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from typing import Generator, Iterator
from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

ENV_VAR = "ERP_TEST_POSTGRES_URL"

# Database-name fragments that are never allowed (even with other markers).
_FORBIDDEN_DB_FRAGMENTS = (
    "erp_data",
    "production",
    "prod_db",
    "bookkeeping_prod",
)

# At least one must appear in the database name (path segment).
_REQUIRED_DB_MARKERS = (
    "_test",
    "-test",
    "test_",
    "pytest",
    "_dev",
    "-dev",
    "dev_",
    "_local",
)

_POSTGRES_SCHEMES = frozenset(
    {
        "postgresql",
        "postgresql+psycopg2",
        "postgresql+psycopg",
        "postgres",
    }
)


class UnsafePostgresTestUrlError(ValueError):
    """Raised when ERP_TEST_POSTGRES_URL fails safety checks."""


def get_test_postgres_url() -> str | None:
    """Return the configured test URL, or None if unset/blank."""
    raw = os.environ.get(ENV_VAR)
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped or None


def validate_test_postgres_url(url: str) -> str:
    """Fail fast unless *url* is an obvious PostgreSQL test/dev database URL."""
    stripped = url.strip()
    if not stripped:
        raise UnsafePostgresTestUrlError("URL is empty")

    if stripped.startswith("sqlite:"):
        raise UnsafePostgresTestUrlError("SQLite URLs are not allowed for PostgreSQL tests")

    parsed = urlparse(stripped)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _POSTGRES_SCHEMES:
        raise UnsafePostgresTestUrlError(
            f"URL scheme must be PostgreSQL (got {scheme!r})"
        )

    db_name = (parsed.path or "").lstrip("/").split("?")[0]
    if not db_name:
        raise UnsafePostgresTestUrlError("PostgreSQL URL must include a database name")

    db_lower = db_name.lower()
    for forbidden in _FORBIDDEN_DB_FRAGMENTS:
        if forbidden in db_lower:
            raise UnsafePostgresTestUrlError(
                f"Database name {db_name!r} contains forbidden fragment {forbidden!r}"
            )

    if not any(marker in db_lower for marker in _REQUIRED_DB_MARKERS):
        raise UnsafePostgresTestUrlError(
            "Database name must include a test/dev marker "
            f"(one of: {', '.join(_REQUIRED_DB_MARKERS)})"
        )

    # Reject bare file-like paths that could point at the SQLite production DB.
    if re.search(r"erp_data\.db", stripped, re.IGNORECASE):
        raise UnsafePostgresTestUrlError("URL must not reference erp_data.db")

    return stripped


def require_test_postgres_url() -> str:
    """Return a validated test URL or pytest-skip when not configured."""
    raw = get_test_postgres_url()
    if raw is None:
        pytest.skip(f"{ENV_VAR} is not set — PostgreSQL tests are optional")
    return validate_test_postgres_url(raw)


def _ensure_postgres_driver() -> None:
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        try:
            import psycopg  # noqa: F401
        except ImportError:
            pytest.skip(
                "PostgreSQL driver not installed (pip install psycopg2-binary or psycopg)"
            )


def create_test_postgres_engine(url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine for the validated test URL only."""
    safe_url = validate_test_postgres_url(url or require_test_postgres_url())
    _ensure_postgres_driver()
    return create_engine(safe_url, pool_pre_ping=True, future=True)


def create_test_schema(engine: Engine) -> None:
    """Create all ORM tables on the test engine (no Alembic)."""
    from db import Base
    import models  # noqa: F401 — register metadata

    Base.metadata.create_all(bind=engine)


def drop_test_schema(engine: Engine) -> None:
    """Drop all ORM tables from the test engine."""
    from db import Base
    import models  # noqa: F401

    Base.metadata.drop_all(bind=engine)


@contextmanager
def postgres_test_engine(
    url: str | None = None,
) -> Iterator[Engine]:
    """Context manager: validated engine with create/drop schema for tests."""
    engine = create_test_postgres_engine(url)
    try:
        create_test_schema(engine)
        yield engine
    finally:
        drop_test_schema(engine)
        engine.dispose()


@pytest.fixture(scope="session")
def postgres_engine() -> Generator[Engine, None, None]:
    """Session-scoped PostgreSQL engine; skips when ERP_TEST_POSTGRES_URL unset."""
    with postgres_test_engine() as engine:
        yield engine


@pytest.fixture
def postgres_db(postgres_engine: Engine) -> Generator[Engine, None, None]:
    """Per-test fixture: fresh schema via drop/create around the test."""
    drop_test_schema(postgres_engine)
    create_test_schema(postgres_engine)
    yield postgres_engine
