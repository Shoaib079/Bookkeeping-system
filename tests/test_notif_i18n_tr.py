"""P0-1 — notification bell lines and View CTA resolve in EN/TR."""

from __future__ import annotations

import inspect

import app as erp
from registry.i18n import t

_NOTIF_KEYS = (
    "notif.line.overdue_ar",
    "notif.line.overdue_ap",
    "notif.line.low_stock",
    "notif.view",
)


def test_notif_line_keys_resolve_en_and_tr():
    for key in _NOTIF_KEYS:
        for loc in ("en", "tr"):
            text = t(key, loc, count=3)
            assert text != key, f"unresolved {loc} key: {key}"


def test_notif_line_tr_not_english_leaks():
    assert "overdue receivable" not in t("notif.line.overdue_ar", "tr", count=2).lower()
    assert "View" not in t("notif.view", "tr")
    assert "→" in t("notif.view", "tr")


def test_hdr_toolbar_notifications_use_i18n():
    src = inspect.getsource(erp._render_hdr_toolbar)
    assert 'notif.line.overdue_ar' in src
    assert 'notif.line.overdue_ap' in src
    assert 'notif.line.low_stock' in src
    assert '_t("notif.view")' in src
    assert "overdue receivable" not in src
    assert '"View →"' not in src
