"""PY313-CLEANUP-01 — utc_now_naive contract."""

from __future__ import annotations

import datetime

from utc_datetime import utc_now_naive


def test_utc_now_naive_is_naive_utc():
    ts = utc_now_naive()
    assert ts.tzinfo is None
    assert isinstance(ts, datetime.datetime)
    delta = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) - ts
    assert abs(delta.total_seconds()) < 2
