"""OBS-004 — centralized Add Transaction date ownership (SSOT).

Single path for DATE-01 rollover, follow-today flag, submit pinning, and posting
resolution. Desktop and mobile both write ``at_date``; submit reads via
``capture_submit_resolved_date`` / ``resolve_submit_date`` without mutating the
widget key after instantiation (OBS-001).
"""

from __future__ import annotations

import datetime
from typing import Any, Mapping, MutableMapping

AT_DATE_KEY = "at_date"
AT_DATE_FOLLOWS_TODAY_KEY = "at_date_follows_today"
AT_SUBMIT_RESOLVED_DATE_KEY = "at_submit_resolved_date"
MOB_AT_DATE_CUSTOM_PICK_KEY = "mob_at_date_custom_pick"


def apply_follow_today_rollover(
    state: MutableMapping[str, Any],
    *,
    today: datetime.date | None = None,
) -> None:
    """DATE-01 — roll ``at_date`` forward only when pinned to Today.

    Deliberate backdates are preserved (follow flag cleared, date unchanged).
    """
    if state.get(AT_DATE_FOLLOWS_TODAY_KEY, True) is False:
        return
    today = today or datetime.date.today()
    d = state.get(AT_DATE_KEY)
    if not isinstance(d, datetime.date):
        state[AT_DATE_KEY] = today
        return
    if d >= today:
        state[AT_DATE_KEY] = today
        return
    if d == today - datetime.timedelta(days=1):
        state[AT_DATE_KEY] = today
        return
    state[AT_DATE_FOLLOWS_TODAY_KEY] = False


def sync_follow_today_flag(
    state: MutableMapping[str, Any],
    d: datetime.date,
    *,
    today: datetime.date | None = None,
) -> None:
    today = today or datetime.date.today()
    state[AT_DATE_FOLLOWS_TODAY_KEY] = d == today


def ensure_at_date_seed(
    state: MutableMapping[str, Any],
    *,
    today: datetime.date | None = None,
) -> None:
    """Seed ``at_date`` before first widget render (pre-instantiation only)."""
    today = today or datetime.date.today()
    if not isinstance(state.get(AT_DATE_KEY), datetime.date):
        state[AT_DATE_KEY] = today
        state[AT_DATE_FOLLOWS_TODAY_KEY] = True


def pre_render_date_sync(
    state: MutableMapping[str, Any],
    *,
    today: datetime.date | None = None,
) -> None:
    """Page-entry sync: rollover then seed (call before any date widget)."""
    apply_follow_today_rollover(state, today=today)
    ensure_at_date_seed(state, today=today)


def read_at_date(
    state: Mapping[str, Any],
    *,
    today: datetime.date | None = None,
) -> datetime.date:
    today = today or datetime.date.today()
    d = state.get(AT_DATE_KEY)
    if isinstance(d, datetime.date):
        return d
    return today


def capture_submit_resolved_date(
    state: MutableMapping[str, Any],
    *,
    today: datetime.date | None = None,
) -> datetime.date:
    """Submit-time SSOT: read widget date, sync follow flag, pin resolved date."""
    today = today or datetime.date.today()
    d = read_at_date(state, today=today)
    if d != today:
        state[AT_DATE_FOLLOWS_TODAY_KEY] = False
    else:
        sync_follow_today_flag(state, d, today=today)
    state[AT_SUBMIT_RESOLVED_DATE_KEY] = d
    return d


def resolve_submit_date(
    state: MutableMapping[str, Any],
    *,
    today: datetime.date | None = None,
) -> datetime.date:
    """Return submit-pinned date without mutating ``at_date`` (OBS-001)."""
    cached = state.pop(AT_SUBMIT_RESOLVED_DATE_KEY, None)
    if isinstance(cached, datetime.date):
        return cached
    return read_at_date(state, today=today)


def set_date_choice(
    state: MutableMapping[str, Any],
    chosen: datetime.date,
    *,
    follows_today: bool,
) -> None:
    """Mobile date sheet / explicit picks (outside desktop ``st.form``)."""
    state[AT_DATE_KEY] = chosen
    state[AT_DATE_FOLLOWS_TODAY_KEY] = follows_today
    state.pop("mob_at_date_custom", None)
    state[MOB_AT_DATE_CUSTOM_PICK_KEY] = chosen


def is_backdated(
    state: Mapping[str, Any],
    *,
    today: datetime.date | None = None,
) -> bool:
    today = today or datetime.date.today()
    d = state.get(AT_DATE_KEY, today)
    return isinstance(d, datetime.date) and d != today
