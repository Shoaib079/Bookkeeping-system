"""Shared CRUD UI helpers — DRY widgets for void confirmation and attachment selectors.

Extracted from repeated patterns in app.py (Phase 16 refactor).
Each function encapsulates a Streamlit interaction pattern that was
copy-pasted across purchases, expenses, inventory, bank transactions,
sales, and payables.
"""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st


# ---------------------------------------------------------------------------
# Void confirmation widget
# ---------------------------------------------------------------------------

def void_confirmation_widget(
    *,
    record_id: int,
    prefix: str,
    void_fn: Callable[..., Any],
    void_fn_args: tuple = (),
    reason_label: str,
    confirm_label: str,
    cancel_label: str,
    error_empty_label: str,
    success_label: str,
    void_btn_label: str,
    permission_check: bool = True,
    btn_container: Any = None,
    pre_void_checks: Callable[[Any], str | None] | None = None,
) -> None:
    """Render a void-button → reason-input → confirm/cancel flow.

    Parameters
    ----------
    record_id:
        Primary key of the record being voided.
    prefix:
        Short string to namespace session-state keys (e.g. ``"purchase"``,
        ``"expense"``).
    void_fn:
        Callable that performs the void. Called as
        ``void_fn(session, record_id, reason, *void_fn_args)`` when session
        is the first positional, or as ``void_fn(record_id, reason)``
        depending on arity — but callers should pass a lambda or partial
        that already has the session bound.  Simpler: ``void_fn(reason)``
        with record pre-bound.
    void_fn_args:
        Extra positional args forwarded after ``reason``.
    reason_label:
        Label for the text input asking for a void reason.
    confirm_label:
        Label for the confirm button.
    cancel_label:
        Label for the cancel button.
    error_empty_label:
        Error message when the void reason is empty.
    success_label:
        Success message after voiding.
    void_btn_label:
        Label for the initial void toggle button.
    permission_check:
        Whether the current user may void.  Pass ``_can("void_transaction")``.
    btn_container:
        Streamlit container (e.g. a column) in which to place the trigger
        button.  When ``None``, renders in the current scope.
    pre_void_checks:
        Optional callable receiving the stripped reason; returns an error
        string to display (and abort void) or ``None`` to proceed.
    """
    confirm_key = f"confirm_void_{prefix}_{record_id}"
    container = btn_container or st

    if container.button(
        void_btn_label,
        key=f"erp_void_{prefix}_{record_id}",
        disabled=not permission_check,
    ):
        st.session_state[confirm_key] = True

    if st.session_state.get(confirm_key, False):
        void_reason = st.text_input(
            reason_label, key=f"void_reason_{prefix}_{record_id}"
        )
        c1, c2 = st.columns(2)
        if c1.button(
            confirm_label,
            key=f"erp_danger_confirm_void_{prefix}_{record_id}",
            disabled=not permission_check,
        ):
            if not void_reason.strip():
                st.error(error_empty_label)
            elif pre_void_checks:
                err = pre_void_checks(void_reason.strip())
                if err:
                    st.error(err)
                    st.session_state[confirm_key] = False
                else:
                    void_fn(void_reason.strip(), *void_fn_args)
                    st.session_state[confirm_key] = False
                    st.success(success_label)
                    st.rerun()
            else:
                void_fn(void_reason.strip(), *void_fn_args)
                st.session_state[confirm_key] = False
                st.success(success_label)
                st.rerun()
        if c2.button(cancel_label, key=f"cancel_void_{prefix}_{record_id}"):
            st.session_state[confirm_key] = False
            st.rerun()


# ---------------------------------------------------------------------------
# Attachment section selector
# ---------------------------------------------------------------------------

def attachment_section_selector(
    *,
    session: Any,
    records: list[Any],
    entity_type: str,
    header_label: str,
    select_label: str,
    label_fn: Callable[[Any], str],
    key_prefix: str,
    render_attachment_fn: Callable[..., Any],
) -> None:
    """Render a record-picker + attachment panel for a list of active records.

    Parameters
    ----------
    session:
        SQLAlchemy session.
    records:
        Active (non-void) record objects.
    entity_type:
        Entity type string passed to ``render_attachment_fn``
        (e.g. ``"Purchase"``, ``"ExpenseRecord"``).
    header_label:
        Markdown label rendered above the selector.
    select_label:
        Label for the selectbox widget.
    label_fn:
        Callable receiving a record and returning a display string for the
        selectbox option.
    key_prefix:
        Unique key prefix for the Streamlit selectbox widget.
    render_attachment_fn:
        The ``render_attachment_section`` function from ``app.py``.
    """
    if not records:
        return
    from ui.section import section_header_html

    st.markdown("---")
    st.markdown(section_header_html(header_label), unsafe_allow_html=True)
    options = {label_fn(r): r.id for r in records}
    sel_label = st.selectbox(
        select_label, list(options.keys()), key=f"att_{key_prefix}_selector"
    )
    sel_id = options[sel_label]
    render_attachment_fn(session, entity_type, sel_id, f"{key_prefix}{sel_id}")
