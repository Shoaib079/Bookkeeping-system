"""SC-P1b — Staff expense capture presentation (no business logic).

Calls services.staff_capture only for reads and mutations.
Approval posting uses injected post_fn from app.py (TD-SC-01).
"""

from __future__ import annotations

import datetime
import mimetypes

import pandas as pd
import streamlit as st

from models import TransactionCategory, TransactionSubcategory
from paths import UPLOADS_DIR, resolve_data_path
from services import staff_capture as sc_svc
from ui import date_input as date_ui
from ui.section import section_header_html


def _erp():
    import app as app_module

    return app_module


def _actor(session) -> tuple[int, str | None]:
    erp = _erp()
    user = erp._current_user() or {}
    return int(user.get("id") or 0), user.get("username")


def _handle_mutation(erp, result: sc_svc.MutationResult) -> bool:
    if result.error:
        st.error(result.error)
        return False
    for code in result.warnings:
        if code == "attachment_recommended":
            st.warning(erp._t("sc.warn.no_receipt"))
    if result.ok:
        st.success(erp._t("sc.msg.saved"))
    return result.ok


def _expense_categories(session, erp) -> list[TransactionCategory]:
    return (
        erp.cq(session, TransactionCategory)
        .filter_by(transaction_type="Expense", is_active=True)
        .order_by(TransactionCategory.name)
        .all()
    )


def _expense_subcategories(session, erp, category_id: int | None) -> list[TransactionSubcategory]:
    if not category_id:
        return []
    return (
        erp.cq(session, TransactionSubcategory)
        .filter_by(category_id=category_id, is_active=True)
        .order_by(TransactionSubcategory.name)
        .all()
    )


def _category_label(session, erp, cat_id: int | None, sub_id: int | None) -> str:
    if sub_id:
        sub = session.get(TransactionSubcategory, sub_id)
        if sub:
            return sub.name
    if cat_id:
        cat = session.get(TransactionCategory, cat_id)
        if cat:
            return cat.name
    return "—"


def _draft_payload_from_form(
    erp,
    *,
    draft_date: datetime.date,
    amount: float,
    currency: str,
    cat_id: int | None,
    sub_id: int | None,
    description: str,
) -> sc_svc.ExpenseDraftInput:
    return sc_svc.ExpenseDraftInput(
        date=draft_date,
        amount=amount,
        currency=currency,
        payment_method="Cash",
        tx_category_id=cat_id,
        tx_subcategory_id=sub_id,
        description=description,
    )


def _load_draft_into_session(draft: sc_svc.ExpenseDraftView) -> None:
    st.session_state["sc_edit_draft_id"] = draft.id
    st.session_state["sc_form_desc"] = draft.description or ""


def _render_submit_form(session, company_id: int, actor_id: int, performed_by: str | None) -> None:
    erp = _erp()
    settings = erp.load_settings()
    currency = settings.get("currency", "TRY")
    today = datetime.date.today()
    edit_id = st.session_state.get("sc_edit_draft_id")

    draft = sc_svc.get_expense_draft(session, company_id, edit_id) if edit_id else None
    if edit_id and draft is None:
        st.session_state.pop("sc_edit_draft_id", None)
        draft = None
    if draft and draft.status not in sc_svc.EDITABLE_STATUSES:
        st.session_state.pop("sc_edit_draft_id", None)
        draft = None
        edit_id = None

    default_date = draft.date if draft else today
    st.caption(erp._t("sc.submit.caption"))
    if draft and draft.status == "returned" and draft.review_note:
        st.info(f"{erp._t('sc.field.review_note')}: {draft.review_note}")

    date_ui.render_preferred_date_input(
        erp._t("sc.field.date"),
        "sc_form_date",
        default=default_date,
        invalid_message=erp._t("txn.date_invalid"),
    )
    draft_date = date_ui.parse_bound_date("sc_form_date") or default_date

    amount = erp.amount_input(
        erp._t("sc.field.amount"),
        key="sc_form_amount",
        default=draft.amount if draft else None,
    )

    cats = _expense_categories(session, erp)
    cat_names = [c.name for c in cats]
    cat_ids = [c.id for c in cats]
    default_cat_idx = 0
    if draft and draft.tx_category_id in cat_ids:
        default_cat_idx = cat_ids.index(draft.tx_category_id)
    cat_label = st.selectbox(
        erp._t("sc.field.category"),
        cat_names if cat_names else [erp._t("sc.no_categories")],
        index=default_cat_idx if cat_names else 0,
        disabled=not cat_names,
        key="sc_form_cat_name",
    )
    cat_id = cat_ids[cat_names.index(cat_label)] if cat_names and cat_label in cat_names else None

    subcats = _expense_subcategories(session, erp, cat_id)
    sub_names = [s.name for s in subcats]
    sub_ids = [s.id for s in subcats]
    sub_id = None
    if sub_names:
        default_sub_idx = 0
        if draft and draft.tx_subcategory_id in sub_ids:
            default_sub_idx = sub_ids.index(draft.tx_subcategory_id)
        sub_label = st.selectbox(
            erp._t("sc.field.subcategory"),
            sub_names,
            index=default_sub_idx,
            key="sc_form_sub_name",
        )
        sub_id = sub_ids[sub_names.index(sub_label)]

    description = st.text_area(
        erp._t("sc.field.description"),
        value=st.session_state.get("sc_form_desc", draft.description if draft else ""),
        key="sc_form_desc",
    )

    st.text_input(erp._t("sc.field.payment"), value="Cash", disabled=True)
    st.text_input(erp._t("sc.field.currency"), value=currency, disabled=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        save = st.button(erp._t("sc.action.save_draft"), key="sc_save_draft")
    with c2:
        submit = st.button(erp._t("sc.action.submit"), key="sc_submit_draft")
    with c3:
        if edit_id:
            if st.button(erp._t("sc.action.new_draft"), key="sc_new_draft"):
                st.session_state.pop("sc_edit_draft_id", None)
                st.rerun()

    payload = _draft_payload_from_form(
        erp,
        draft_date=draft_date,
        amount=amount,
        currency=currency,
        cat_id=cat_id,
        sub_id=sub_id,
        description=description,
    )

    if save:
        if edit_id:
            result = sc_svc.update_expense_draft(
                session, company_id, edit_id, actor_id, payload, performed_by=performed_by
            )
        else:
            result = sc_svc.create_expense_draft(
                session, company_id, actor_id, payload, performed_by=performed_by
            )
            if result.ok:
                st.session_state["sc_edit_draft_id"] = result.record_id
        _handle_mutation(erp, result)

    if submit:
        target_id = edit_id
        if not target_id:
            created = sc_svc.create_expense_draft(
                session, company_id, actor_id, payload, performed_by=performed_by
            )
            if not created.ok:
                _handle_mutation(erp, created)
                return
            target_id = created.record_id
            st.session_state["sc_edit_draft_id"] = target_id
        else:
            updated = sc_svc.update_expense_draft(
                session, company_id, target_id, actor_id, payload, performed_by=performed_by
            )
            if not updated.ok:
                _handle_mutation(erp, updated)
                return
        result = sc_svc.submit_expense_draft(
            session, company_id, target_id, actor_id, performed_by=performed_by
        )
        if _handle_mutation(erp, result):
            st.session_state.pop("sc_edit_draft_id", None)

    if edit_id and erp._can("upload_receipts"):
        _render_attachments(session, company_id, actor_id, edit_id, performed_by)


def _render_attachments(
    session,
    company_id: int,
    actor_id: int,
    draft_id: int,
    performed_by: str | None,
) -> None:
    erp = _erp()
    st.markdown(f"**{erp._t('sc.section.receipts')}**")
    attachments = sc_svc.list_draft_attachments(
        session, company_id, sc_svc.EXPENSE_DRAFT_TYPE, draft_id
    )
    if attachments:
        for att in attachments:
            st.caption(f"{att.original_name} ({att.mime}, {att.size_bytes // 1024} KB)")
            path = resolve_data_path(att.file_path)
            if path.is_file():
                st.download_button(
                    erp._t("sc.action.download"),
                    data=path.read_bytes(),
                    file_name=att.original_name,
                    mime=att.mime,
                    key=f"sc_dl_{att.id}",
                )

    uploaded = st.file_uploader(
        erp._t("sc.field.receipt"),
        type=["jpg", "jpeg", "png", "webp", "pdf"],
        key=f"sc_upload_{draft_id}",
    )
    if uploaded and st.button(erp._t("sc.action.attach"), key=f"sc_attach_{draft_id}"):
        mime = uploaded.type or mimetypes.guess_type(uploaded.name)[0] or "application/octet-stream"
        result = sc_svc.add_draft_attachment(
            session,
            company_id,
            sc_svc.EXPENSE_DRAFT_TYPE,
            draft_id,
            actor_id,
            file_bytes=uploaded.getvalue(),
            original_name=uploaded.name,
            mime_type=mime,
            uploads_root=UPLOADS_DIR,
            performed_by=performed_by,
        )
        _handle_mutation(erp, result)


def _render_my_submissions(session, company_id: int, actor_id: int) -> None:
    erp = _erp()
    drafts = sc_svc.list_expense_drafts(session, company_id, actor_id)
    if not drafts:
        st.info(erp._t("sc.empty.my_submissions"))
        return

    rows = []
    for d in drafts:
        rows.append(
            {
                erp._t("sc.col.id"): d.id,
                erp._t("sc.col.date"): d.date.isoformat(),
                erp._t("sc.col.amount"): f"{d.currency} {d.amount:,.2f}",
                erp._t("sc.col.status"): d.status,
                erp._t("sc.col.category"): _category_label(
                    session, erp, d.tx_category_id, d.tx_subcategory_id
                ),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    editable = [d for d in drafts if d.status in sc_svc.EDITABLE_STATUSES]
    if editable:
        options = {f"#{d.id} — {d.status} — {d.date}": d.id for d in editable}
        choice = st.selectbox(erp._t("sc.field.edit_draft"), list(options.keys()))
        if st.button(erp._t("sc.action.open_draft"), key="sc_open_draft"):
            draft = sc_svc.get_expense_draft(session, company_id, options[choice])
            if draft:
                _load_draft_into_session(draft)
                st.rerun()


def _member_name(session, company_id: int, user_id: int) -> str:
    from services import user_access as ua_svc

    for m in ua_svc.list_active_members(session, company_id):
        if m.user_id == user_id:
            return f"{m.display_name} ({m.username})"
    return str(user_id)


def _render_inbox(session, company_id: int, reviewer_id: int, performed_by: str | None) -> None:
    erp = _erp()
    drafts = sc_svc.list_submitted_expense_drafts(session, company_id, reviewer_id)
    if not drafts:
        st.info(erp._t("sc.empty.inbox"))
        return

    options = {
        f"#{d.id} — {_member_name(session, company_id, d.created_by_id)} — {d.currency} {d.amount:,.2f}": d.id
        for d in drafts
    }
    choice = st.selectbox(erp._t("sc.field.inbox_draft"), list(options.keys()))
    draft_id = options[choice]
    draft = sc_svc.get_expense_draft(session, company_id, draft_id)
    if draft is None:
        return

    att_count = len(
        sc_svc.list_draft_attachments(
            session, company_id, sc_svc.EXPENSE_DRAFT_TYPE, draft_id
        )
    )
    if att_count == 0:
        st.warning(erp._t("sc.warn.no_receipt"))

    c1, c2, c3 = st.columns(3)
    c1.metric(erp._t("sc.field.amount"), f"{draft.currency} {draft.amount:,.2f}")
    c2.metric(erp._t("sc.field.date"), draft.date.isoformat())
    c3.metric(erp._t("sc.field.submitter"), _member_name(session, company_id, draft.created_by_id))

    st.markdown(f"**{erp._t('sc.field.category')}:** {_category_label(session, erp, draft.tx_category_id, draft.tx_subcategory_id)}")
    st.markdown(f"**{erp._t('sc.field.description')}:** {draft.description or '—'}")
    if draft.submitted_note:
        st.markdown(f"**{erp._t('sc.field.submitted_note')}:** {draft.submitted_note}")

    attachments = sc_svc.list_draft_attachments(
        session, company_id, sc_svc.EXPENSE_DRAFT_TYPE, draft_id
    )
    if attachments:
        st.markdown(f"**{erp._t('sc.section.receipts')}**")
        for att in attachments:
            path = resolve_data_path(att.file_path)
            if path.is_file():
                st.download_button(
                    f"{att.original_name}",
                    data=path.read_bytes(),
                    file_name=att.original_name,
                    mime=att.mime,
                    key=f"sc_inbox_dl_{att.id}",
                )

    review_note = st.text_area(erp._t("sc.field.review_note"), key=f"sc_review_note_{draft_id}")

    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button(erp._t("sc.action.approve"), key=f"sc_approve_{draft_id}"):
            result = sc_svc.approve_expense_draft(
                session,
                company_id,
                draft_id,
                reviewer_id,
                post_fn=erp._staff_capture_post_expense_draft,
                performed_by=performed_by,
            )
            _handle_mutation(erp, result)
    with a2:
        if st.button(erp._t("sc.action.return"), key=f"sc_return_{draft_id}"):
            result = sc_svc.return_expense_draft(
                session,
                company_id,
                draft_id,
                reviewer_id,
                review_note,
                performed_by=performed_by,
            )
            _handle_mutation(erp, result)
    with a3:
        if st.button(erp._t("sc.action.reject"), key=f"sc_reject_{draft_id}"):
            result = sc_svc.reject_expense_draft(
                session,
                company_id,
                draft_id,
                reviewer_id,
                review_note=review_note or None,
                performed_by=performed_by,
            )
            _handle_mutation(erp, result)


def render_staff_expense_capture(session) -> None:
    """Staff expense drafts — submit, my submissions, approval inbox."""
    erp = _erp()
    can_submit = erp._can("submit_expense_drafts")
    can_approve = erp._can("approve_expense_drafts")

    if not (can_submit or can_approve):
        st.error(erp._t("sc.no_permission"))
        return

    user = erp._current_user()
    if not user:
        st.error(erp._t("sc.no_permission"))
        return

    company_id = erp.current_company_required()
    actor_id, performed_by = _actor(session)

    st.markdown(
        section_header_html(erp._t("sc.title"), accent="info"),
        unsafe_allow_html=True,
    )
    st.caption(erp._t("sc.subtitle"))

    tab_labels: list[str] = []
    if can_submit:
        tab_labels.append(erp._t("sc.tab.submit"))
        tab_labels.append(erp._t("sc.tab.my_submissions"))
    if can_approve:
        tab_labels.append(erp._t("sc.tab.inbox"))

    tabs = st.tabs(tab_labels)
    idx = 0
    if can_submit:
        with tabs[idx]:
            _render_submit_form(session, company_id, actor_id, performed_by)
        idx += 1
        with tabs[idx]:
            _render_my_submissions(session, company_id, actor_id)
        idx += 1
    if can_approve:
        with tabs[idx]:
            _render_inbox(session, company_id, reviewer_id=actor_id, performed_by=performed_by)
