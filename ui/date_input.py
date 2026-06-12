"""Preferred date text inputs — Streamlit wrapper around registry.date_utils."""

from __future__ import annotations

import datetime
from typing import Callable

import streamlit as st

from registry.date_utils import (
    DATE_FORMAT_DEFAULT,
    date_input_placeholder,
    format_date_for_preference,
    format_date_input_for_preference,
    normalize_user_date_format,
    parse_date_text,
)

_SESSION_PREF_KEY = "_user_date_format"


def set_active_date_format(preference: str) -> None:
    st.session_state[_SESSION_PREF_KEY] = normalize_user_date_format(preference)


def get_active_date_format() -> str:
    return normalize_user_date_format(
        st.session_state.get(_SESSION_PREF_KEY, DATE_FORMAT_DEFAULT)
    )


def get_user_date_format() -> str:
    """Active user's date-format preference (cached in session by the host app)."""
    return get_active_date_format()


def format_display_date(d: datetime.date, preference: str | None = None) -> str:
    return format_date_for_preference(
        d, preference or get_active_date_format()
    )


def sync_date_text_mask(key: str, preference: str | None = None) -> None:
    pref = preference or get_active_date_format()
    raw = st.session_state.get(key)
    if raw is None:
        return
    formatted = format_date_input_for_preference(str(raw), pref)
    if formatted != raw:
        st.session_state[key] = formatted


def _make_on_change(key: str, preference: str | None) -> Callable[[], None]:
    def _cb() -> None:
        sync_date_text_mask(key, preference)

    return _cb


def seed_date_text_key(
    key: str,
    value: datetime.date,
    preference: str | None = None,
) -> None:
    existing = st.session_state.get(key)
    if existing is None:
        st.session_state[key] = format_display_date(value, preference)
    elif isinstance(existing, datetime.date):
        st.session_state[key] = format_display_date(existing, preference)


def date_text_error(
    key: str,
    preference: str | None = None,
    *,
    invalid_message: str | None = None,
) -> str | None:
    raw = st.session_state.get(key)
    if raw is None or not str(raw).strip():
        return None
    if parse_date_text(str(raw), preference or get_active_date_format()) is None:
        return invalid_message
    return None


def parse_bound_date(key: str, preference: str | None = None) -> datetime.date | None:
    raw = st.session_state.get(key)
    if raw is None or not str(raw).strip():
        return None
    return parse_date_text(str(raw), preference or get_active_date_format())


def normalize_date_text_key(key: str, preference: str | None = None) -> None:
    """Apply preference mask to a session-state text key (submit/resolve path)."""
    sync_date_text_mask(key, preference)


def render_preferred_date_input(
    label: str,
    key: str,
    *,
    default: datetime.date | None = None,
    in_form: bool = False,
    live_mask: bool = True,
    show_error: bool = True,
    help: str | None = None,
    placeholder: str | None = None,
    label_visibility: str = "visible",
    invalid_message: str | None = None,
    preference: str | None = None,
    disabled: bool = False,
) -> datetime.date | None:
    """Single masked text date field. Returns parsed date or None.

    When *in_form* is True, omits ``on_change`` (Streamlit forms forbid it).
    Masking then happens via :func:`normalize_date_text_key` on submit/resolve.
    """
    pref = preference or get_active_date_format()
    if default is not None:
        seed_date_text_key(key, default, pref)

    use_live_mask = live_mask and not in_form
    if use_live_mask:
        sync_date_text_mask(key, pref)

    ph = placeholder or date_input_placeholder(pref)
    text_kw: dict = {
        "label": label,
        "key": key,
        "placeholder": ph,
        "help": help,
        "label_visibility": label_visibility,
        "disabled": disabled,
    }
    if use_live_mask:
        text_kw["on_change"] = _make_on_change(key, pref)
    st.text_input(**text_kw)
    if show_error:
        err = date_text_error(key, pref, invalid_message=invalid_message)
        if err:
            st.caption(f"⚠️ {err}")
    return parse_bound_date(key, pref)


def render_preferred_date_range(
    container,
    from_key: str,
    to_key: str,
    *,
    default_from: datetime.date,
    default_to: datetime.date,
    from_label: str,
    to_label: str,
    preference: str | None = None,
    invalid_message: str | None = None,
) -> tuple[datetime.date, datetime.date]:
    """Two masked date fields; returns normalized (from, to) date objects."""
    pref = preference or get_active_date_format()
    seed_date_text_key(from_key, default_from, pref)
    seed_date_text_key(to_key, default_to, pref)

    col1, col2 = container.columns(2)
    with col1:
        render_preferred_date_input(
            from_label,
            from_key,
            show_error=True,
            label_visibility="collapsed",
            preference=pref,
            invalid_message=invalid_message,
        )
    with col2:
        render_preferred_date_input(
            to_label,
            to_key,
            show_error=True,
            label_visibility="collapsed",
            preference=pref,
            invalid_message=invalid_message,
        )

    d_from = parse_bound_date(from_key, pref) or default_from
    d_to = parse_bound_date(to_key, pref) or default_to
    if d_from > d_to:
        d_from, d_to = d_to, d_from
    return d_from, d_to
