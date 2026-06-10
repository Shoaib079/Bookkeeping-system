"""SETUP-01 wizard UI shell."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

from registry.setup01_wizard import (
    BUSINESS_OTHER,
    BUSINESS_RESTAURANT,
    BUSINESS_RETAIL,
    BUSINESS_SERVICES,
    CONTROL_BALANCED,
    CONTROL_RELAXED,
    CONTROL_STRICT,
    POS_IMMEDIATE,
    POS_LATER,
    POS_NO_CARDS,
    SETUP01_PROGRESS_STEP,
    SETUP01_STEP_ORDER,
    SETUP01_SESSION_CANCEL_CONFIRM,
    SETUP01_SESSION_CREATE_ERROR,
    SETUP01_SESSION_CREATING,
    SETUP01_SESSION_JUMP,
    SETUP01_SESSION_STEP,
    apply_skip_side_effects,
    discard_setup01_wizard,
    get_setup01_answers,
    get_setup01_step,
    is_setup01_creating,
    next_setup01_step,
    prev_setup01_step,
    set_setup01_answers,
    summary_display_rows,
    validate_setup01_step,
)


def _tw(t: Callable[..., str], key: str, fallback: str, **kwargs: Any) -> str:
    """Translate; never surface raw i18n keys to users."""
    text = t(key, **kwargs)
    return text if text and text != key else fallback


def _has_partial_setup01_data(answers: dict[str, Any], step: str) -> bool:
    if step != "details":
        return True
    return bool((answers.get("company_name") or "").strip())


def _sync_details_from_widgets(answers: dict[str, Any]) -> dict[str, Any]:
    return {
        **answers,
        "company_name": st.session_state.get("setup01_company_name", answers.get("company_name", "")),
        "company_legal": st.session_state.get("setup01_company_legal", answers.get("company_legal", "")),
        "company_email": st.session_state.get("setup01_company_email", answers.get("company_email", "")),
        "company_phone": st.session_state.get("setup01_company_phone", answers.get("company_phone", "")),
    }


def _render_edu_box(t: Callable[..., str], about_key: str, fallback: str) -> None:
    st.markdown(
        f'<div class="setup01-edu-box">{_tw(t, about_key, fallback)}</div>',
        unsafe_allow_html=True,
    )


def _render_progress(step: str, t: Callable[..., str]) -> None:
    if step == "details":
        st.markdown(
            f'<div class="setup01-progress-label">{_tw(t, "setup01.progress.intro", "First, tell us about your company")}</div>',
            unsafe_allow_html=True,
        )
        return
    current = SETUP01_PROGRESS_STEP.get(step, 8)
    dots = []
    for i in range(1, 9):
        cls = "setup01-progress-dot"
        if i < current:
            cls += " is-done"
        elif i == current:
            cls += " is-active"
        dots.append(f'<span class="{cls}"></span>')
    st.markdown(
        f'<div class="setup01-progress-wrap">'
        f'<div class="setup01-progress-label">{_tw(t, "setup01.progress.step", f"Step {current} of 8", n=current)}</div>'
        f'<div class="setup01-progress">{"".join(dots)}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_radio_step(
    *,
    step_key: str,
    title_key: str,
    lead_key: str,
    about_key: str,
    hint_key: str,
    options: list[tuple[str, str, str]],
    answers: dict[str, Any],
    answer_field: str,
    t: Callable[..., str],
) -> None:
    st.markdown(
        f'<div class="setup01-step-title">{_tw(t, title_key, title_key.split(".")[-1].replace("_", " ").title())}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="setup01-step-lead">{_tw(t, lead_key, "")}</div>',
        unsafe_allow_html=True,
    )
    _render_edu_box(t, about_key, "")

    labels = {oid: _tw(t, label_key, oid) for oid, label_key, _ in options}
    descs = {oid: _tw(t, desc_key, "") for oid, _, desc_key in options}
    opt_ids = [oid for oid, _, _ in options]
    current = answers.get(answer_field, opt_ids[0])
    choice = st.radio(
        _tw(t, "setup01.choose_option", "Choose one"),
        options=opt_ids,
        format_func=lambda k: labels[k],
        key=f"setup01_radio_{step_key}",
        index=opt_ids.index(current) if current in opt_ids else 0,
        label_visibility="collapsed",
    )
    if descs.get(choice):
        st.markdown(f'<div class="setup01-option-desc">{descs[choice]}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="setup01-option-hint">{_tw(t, hint_key, "", option=labels[choice])}</div>',
        unsafe_allow_html=True,
    )
    set_setup01_answers(**{answer_field: choice})


def _render_summary(t: Callable[..., str], answers: dict[str, Any]) -> None:
    st.markdown(
        f'<div class="setup01-step-title">{_tw(t, "setup01.summary.title", "Review your setup")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="setup01-step-lead">{_tw(t, "setup01.summary.lead", "")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="setup01-summary-card">', unsafe_allow_html=True)

    def _summary_line(row_key: str, label: str, value: str) -> None:
        text_col, btn_col = st.columns([5, 1])
        with text_col:
            st.markdown(
                f'<div class="setup01-summary-row">'
                f'<div class="setup01-summary-label">{label}</div>'
                f'<div class="setup01-summary-value">{value}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
        with btn_col:
            if st.button(
                _tw(t, "setup01.summary.edit", "Edit"),
                key=f"setup01_edit_{row_key}",
                type="secondary",
                use_container_width=True,
            ):
                st.session_state[SETUP01_SESSION_JUMP] = row_key
                st.rerun()

    company_name = (answers.get("company_name") or "").strip() or "—"
    _summary_line(
        "details",
        _tw(t, "setup01.summary.row.company", "Company name"),
        company_name,
    )
    for row_key, label_key, value_key in summary_display_rows(answers):
        _summary_line(row_key, _tw(t, label_key, label_key), _tw(t, value_key, value_key))

    st.markdown("</div>", unsafe_allow_html=True)


def render_setup01_wizard(
    session,
    *,
    t: Callable[..., str],
    on_sign_out: Callable[[], None],
    on_create_company: Callable[[Any, int], tuple[bool, str | None]],
    current_user_id: int | None,
) -> None:
    """Full-page SETUP-01 flow."""
    step = get_setup01_step()
    answers = get_setup01_answers()

    jump = st.session_state.pop(SETUP01_SESSION_JUMP, None)
    if jump and jump in SETUP01_STEP_ORDER:
        st.session_state[SETUP01_SESSION_STEP] = jump

    st.markdown('<div class="setup01-shell">', unsafe_allow_html=True)

    st.markdown(
        f'<div class="banner banner-primary setup01-banner setup01-banner-compact">'
        f'<div class="setup01-banner-icon">🏢</div>'
        f'<div class="setup01-banner-title">{_tw(t, "setup01.title", "Set up your company")}</div>'
        f'<div class="setup01-banner-sub">{_tw(t, "setup01.subtitle", "")}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )

    _render_progress(step, t)

    if st.session_state.get(SETUP01_SESSION_CANCEL_CONFIRM):
        st.warning(_tw(t, "setup01.cancel_confirm", "Discard this setup?"))
        c1, c2 = st.columns(2)
        if c1.button(_tw(t, "setup01.discard", "Discard"), key="setup01_discard_yes", type="primary", use_container_width=True):
            discard_setup01_wizard()
            st.rerun()
        if c2.button(_tw(t, "common.cancel", "Cancel"), key="setup01_discard_no", use_container_width=True):
            st.session_state.pop(SETUP01_SESSION_CANCEL_CONFIRM, None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if st.button(_tw(t, "setup01.cancel", "Cancel setup"), key="setup01_cancel_btn"):
        answers = _sync_details_from_widgets(answers)
        set_setup01_answers(**answers)
        if _has_partial_setup01_data(get_setup01_answers(), step):
            st.session_state[SETUP01_SESSION_CANCEL_CONFIRM] = True
            st.rerun()
        discard_setup01_wizard()
        st.rerun()

    if step == "details":
        st.markdown(
            f'<div class="setup01-step-title">{_tw(t, "setup01.details.title", "Company details")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="setup01-step-lead">{_tw(t, "setup01.details.lead", "")}</div>',
            unsafe_allow_html=True,
        )
        _render_edu_box(t, "setup01.details.about", "")
        st.caption(_tw(t, "picker.create_owner_note", "You will be the owner of the new company."))
        c1, c2 = st.columns(2)
        c1.text_input(_tw(t, "picker.company_name", "Company name"), key="setup01_company_name", placeholder="e.g. Spice Corner Ltd")
        c2.text_input(_tw(t, "picker.legal_name", "Legal name"), key="setup01_company_legal")
        c3, c4 = st.columns(2)
        c3.text_input(_tw(t, "picker.email", "Email"), key="setup01_company_email")
        c4.text_input(_tw(t, "picker.phone", "Phone"), key="setup01_company_phone")
        answers = _sync_details_from_widgets(answers)
        set_setup01_answers(**answers)

    elif step == "business":
        _render_radio_step(
            step_key="business",
            title_key="setup01.business.title",
            lead_key="setup01.business.lead",
            about_key="setup01.business.about",
            hint_key="setup01.business.hint",
            options=[
                (BUSINESS_RESTAURANT, "setup01.business.restaurant", "setup01.business.restaurant.desc"),
                (BUSINESS_RETAIL, "setup01.business.retail", "setup01.business.retail.desc"),
                (BUSINESS_SERVICES, "setup01.business.services", "setup01.business.services.desc"),
                (BUSINESS_OTHER, "setup01.business.other", "setup01.business.other.desc"),
            ],
            answers=answers,
            answer_field="business",
            t=t,
        )

    elif step == "pos":
        _render_radio_step(
            step_key="pos",
            title_key="setup01.pos.title",
            lead_key="setup01.pos.lead",
            about_key="setup01.pos.about",
            hint_key="setup01.pos.hint",
            options=[
                (POS_IMMEDIATE, "setup01.pos.immediate", "setup01.pos.immediate.desc"),
                (POS_LATER, "setup01.pos.later", "setup01.pos.later.desc"),
                (POS_NO_CARDS, "setup01.pos.no_cards", "setup01.pos.no_cards.desc"),
            ],
            answers=answers,
            answer_field="pos",
            t=t,
        )

    elif step == "statements":
        _render_radio_step(
            step_key="statements",
            title_key="setup01.statements.title",
            lead_key="setup01.statements.lead",
            about_key="setup01.statements.about",
            hint_key="setup01.statements.hint",
            options=[
                ("yes", "setup01.common.yes", "setup01.statements.yes.desc"),
                ("no", "setup01.common.no", "setup01.statements.no.desc"),
            ],
            answers=answers,
            answer_field="statements",
            t=t,
        )

    elif step == "company_cc":
        _render_radio_step(
            step_key="company_cc",
            title_key="setup01.company_cc.title",
            lead_key="setup01.company_cc.lead",
            about_key="setup01.company_cc.about",
            hint_key="setup01.company_cc.hint",
            options=[
                ("yes", "setup01.common.yes", "setup01.company_cc.yes.desc"),
                ("no", "setup01.common.no", "setup01.company_cc.no.desc"),
            ],
            answers=answers,
            answer_field="company_cc",
            t=t,
        )

    elif step == "inventory":
        _render_radio_step(
            step_key="inventory",
            title_key="setup01.inventory.title",
            lead_key="setup01.inventory.lead",
            about_key="setup01.inventory.about",
            hint_key="setup01.inventory.hint",
            options=[
                ("yes", "setup01.common.yes", "setup01.inventory.yes.desc"),
                ("no", "setup01.common.no", "setup01.inventory.no.desc"),
            ],
            answers=answers,
            answer_field="inventory",
            t=t,
        )

    elif step == "currency":
        _render_radio_step(
            step_key="currency",
            title_key="setup01.currency.title",
            lead_key="setup01.currency.lead",
            about_key="setup01.currency.about",
            hint_key="setup01.currency.hint",
            options=[
                ("yes", "setup01.common.yes", "setup01.currency.yes.desc"),
                ("no", "setup01.common.no", "setup01.currency.no.desc"),
            ],
            answers=answers,
            answer_field="currency",
            t=t,
        )

    elif step == "controls":
        _render_radio_step(
            step_key="controls",
            title_key="setup01.controls.title",
            lead_key="setup01.controls.lead",
            about_key="setup01.controls.about",
            hint_key="setup01.controls.hint",
            options=[
                (CONTROL_RELAXED, "setup01.controls.relaxed", "setup01.controls.relaxed.desc"),
                (CONTROL_BALANCED, "setup01.controls.balanced", "setup01.controls.balanced.desc"),
                (CONTROL_STRICT, "setup01.controls.strict", "setup01.controls.strict.desc"),
            ],
            answers=answers,
            answer_field="controls",
            t=t,
        )

    elif step == "summary":
        _render_summary(t, get_setup01_answers())
        err_key = st.session_state.pop(SETUP01_SESSION_CREATE_ERROR, None)
        if err_key:
            st.error(_tw(t, str(err_key), str(err_key)))

    st.markdown('<div class="setup01-footer is-sticky"><div class="setup01-footer-inner">', unsafe_allow_html=True)
    back_col, fwd_col = st.columns(2)
    answers = get_setup01_answers()
    with back_col:
        if step != "details":
            if st.button("← " + _tw(t, "common.back", "Back"), key="setup01_back", use_container_width=True):
                st.session_state[SETUP01_SESSION_STEP] = prev_setup01_step(step, answers)
                st.rerun()
    with fwd_col:
        if step == "summary":
            _creating = is_setup01_creating()
            if _creating:
                st.caption(_tw(t, "setup01.create.working", "Creating…"))
            if st.button(
                _tw(t, "picker.create_btn", "Create company"),
                key="setup01_create_btn",
                type="primary",
                use_container_width=True,
                disabled=_creating or current_user_id is None,
            ):
                answers = _sync_details_from_widgets(get_setup01_answers())
                set_setup01_answers(**answers)
                err = validate_setup01_step("summary", get_setup01_answers())
                if err:
                    st.session_state[SETUP01_SESSION_CREATE_ERROR] = (
                        "picker.name_required" if err == "company_name_required" else err
                    )
                    st.rerun()
                elif current_user_id is not None:
                    with st.spinner(_tw(t, "setup01.create.working", "Creating…")):
                        ok, result = on_create_company(session, current_user_id)
                    if ok:
                        st.success(_tw(t, "picker.created_open", "Created.", name=result or ""))
                        st.rerun()
                    if result:
                        st.session_state[SETUP01_SESSION_CREATE_ERROR] = result
                    st.rerun()
        else:
            if st.button(_tw(t, "common.next", "Next") + " →", key="setup01_next", type="primary", use_container_width=True):
                if step == "details":
                    answers = _sync_details_from_widgets(answers)
                    set_setup01_answers(**answers)
                err = validate_setup01_step(step, get_setup01_answers())
                if err:
                    st.error(_tw(t, "picker.name_required", "Company name is required."))
                else:
                    answers = get_setup01_answers()
                    if step == "pos":
                        answers = apply_skip_side_effects(answers)
                        set_setup01_answers(**answers)
                    st.session_state[SETUP01_SESSION_STEP] = next_setup01_step(step, answers)
                    st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

    if st.button("⏻ " + _tw(t, "picker.sign_out", "Sign out"), key="setup01_signout", use_container_width=True):
        discard_setup01_wizard()
        on_sign_out()
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
