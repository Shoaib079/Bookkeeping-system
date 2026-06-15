"""PY313-CLEANUP-01 — UTC datetime helpers (replaces deprecated datetime.utcnow)."""

from __future__ import annotations

import datetime


def utc_now_naive() -> datetime.datetime:
    """Current UTC time as naive datetime for DateTime(timezone=False) / SQLite columns."""
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
