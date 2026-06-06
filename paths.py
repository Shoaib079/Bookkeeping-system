"""Canonical project paths — independent of the shell's current working directory."""

from __future__ import annotations

from pathlib import Path

# Directory that contains app.py, db.py, and erp_data.db
PROJECT_ROOT = Path(__file__).resolve().parent

DB_PATH = PROJECT_ROOT / "erp_data.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

UPLOADS_DIR = PROJECT_ROOT / "uploads"
BACKUPS_DIR = PROJECT_ROOT / "backups"


def resolve_data_path(path: str | Path) -> Path:
    """Resolve a stored relative path (e.g. uploads/…) or pass through absolute paths."""
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p
