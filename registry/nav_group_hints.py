"""Sidebar accordion hint i18n keys (UI-SYSTEM-02-S3).

Lightweight module — no navigation registry import side effects.
Re-exported from ``registry.navigation`` for app.py consumers.
"""

from __future__ import annotations

from typing import Final

NAV_GROUP_HINTS: Final[dict[str, str]] = {
    "close_day": "nav.group.close_day_hint",
    "accounting": "nav.group.accounting_hint",
}
