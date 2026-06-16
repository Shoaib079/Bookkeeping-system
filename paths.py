"""Canonical project paths — independent of the shell's current working directory."""

from __future__ import annotations

import os
from pathlib import Path

# Directory that contains app.py, db.py, and erp_data.db
PROJECT_ROOT = Path(__file__).resolve().parent

DB_PATH = PROJECT_ROOT / "erp_data.db"
SQLITE_DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"
DATABASE_URL = SQLITE_DATABASE_URL

UPLOADS_DIR = PROJECT_ROOT / "uploads"
BACKUPS_DIR = PROJECT_ROOT / "backups"


def get_database_url() -> str:
    """Effective runtime database URL.

    Priority:
    1. Explicit ``DATABASE_URL`` environment variable
    2. Flag-gated PostgreSQL runtime URL when cutover gates pass
    3. Canonical SQLite ``erp_data.db`` fallback
    """
    explicit = os.environ.get("DATABASE_URL", "").strip()
    if explicit:
        return explicit
    from services.postgres_runtime_cutover import resolve_runtime_database_url

    pg_url = resolve_runtime_database_url()
    if pg_url:
        return pg_url
    return SQLITE_DATABASE_URL


def resolve_data_path(path: str | Path) -> Path:
    """Resolve a stored relative path (e.g. uploads/…) or pass through absolute paths."""
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p
