"""UA-P1b — Permission management presentation (no business logic).

Calls services.user_access only for reads and mutations.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services import user_access as ua_svc
from ui.section import section_header_html


def _erp():
    import app as app_module

    return app_module


def _permission_label(erp, key: str) -> str:
    entry = ua_svc.PERMISSION_REGISTRY.get(key)
    if entry is None:
        return key
    label = erp._t(entry.i18n_key)
    return label if label != entry.i18n_key else key.replace("_", " ").title()


def _member_label(member: ua_svc.CompanyMemberView) -> str:
    return f"{member.display_name} ({member.username}) — {member.role}"


def _provenance_dataframe(erp, view: ua_svc.EffectivePermissionsView) -> pd.DataFrame:
    keys = sorted(
        view.template_keys | view.grants | view.denies | view.effective_keys
    )
    rows = []
    for key in keys:
        rows.append(
            {
                erp._t("ua.col.permission"): _permission_label(erp, key),
                erp._t("ua.col.template"): key in view.template_keys,
                erp._t("ua.col.grant"): key in view.grants,
                erp._t("ua.col.deny"): key in view.denies,
                erp._t("ua.col.effective"): key in view.effective_keys,
            }
        )
    return pd.DataFrame(rows)


def _render_member_summary(erp, view: ua_svc.EffectivePermissionsView) -> None:
    st.markdown(f"**{erp._t('ua.field.role')}:** {view.role or '—'}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(erp._t("ua.metric.template"), len(view.template_keys))
    c2.metric(erp._t("ua.metric.grants"), len(view.grants))
    c3.metric(erp._t("ua.metric.denies"), len(view.denies))
    c4.metric(erp._t("ua.metric.effective"), len(view.effective_keys))
    st.caption(erp._t("ua.provenance.formula"))


def _handle_mutation(erp, result: ua_svc.MutationResult) -> None:
    if result.error:
        st.error(result.error)
        return
    erp._clear_permission_cache()
    st.success(erp._t("ua.msg.saved"))


def _render_actions(session, company_id: int, actor_id: int, target_user_id: int) -> None:
    erp = _erp()
    user = erp._current_user()
    performed_by = (user or {}).get("username")

    registry = ua_svc.list_registry()
    key_options = [entry.key for entry in registry]
    labels = {_permission_label(erp, k): k for k in key_options}
    label_list = sorted(labels.keys())
    selected_label = st.selectbox(
        erp._t("ua.field.permission"),
        label_list,
        key="ua_perm_key_select",
    )
    permission_key = labels[selected_label]

    a1, a2, a3, a4 = st.columns(4)
    if a1.button(erp._t("ua.action.grant"), key="ua_btn_grant", use_container_width=True):
        result = ua_svc.set_override(
            session,
            company_id,
            target_user_id,
            permission_key,
            "grant",
            actor_id,
            performed_by=performed_by,
        )
        _handle_mutation(erp, result)
        st.rerun()
    if a2.button(erp._t("ua.action.deny"), key="ua_btn_deny", use_container_width=True):
        result = ua_svc.set_override(
            session,
            company_id,
            target_user_id,
            permission_key,
            "deny",
            actor_id,
            performed_by=performed_by,
        )
        _handle_mutation(erp, result)
        st.rerun()
    if a3.button(erp._t("ua.action.clear"), key="ua_btn_clear", use_container_width=True):
        result = ua_svc.clear_override(
            session,
            company_id,
            target_user_id,
            permission_key,
            actor_id,
            performed_by=performed_by,
        )
        _handle_mutation(erp, result)
        st.rerun()
    if a4.button(
        erp._t("ua.action.reset"),
        key="ua_btn_reset",
        use_container_width=True,
        type="primary",
    ):
        result = ua_svc.reset_to_template(
            session,
            company_id,
            target_user_id,
            actor_id,
            performed_by=performed_by,
        )
        _handle_mutation(erp, result)
        st.rerun()


def _render_audit_tab(session, company_id: int, target_user_id: int | None) -> None:
    erp = _erp()
    entries = ua_svc.list_permission_audit(
        session,
        company_id,
        target_user_id=target_user_id,
        limit=50,
    )
    if not entries:
        st.info(erp._t("ua.audit.empty"))
        return
    rows = []
    for entry in entries:
        rows.append(
            {
                erp._t("ua.col.when"): entry.timestamp.strftime("%Y-%m-%d %H:%M"),
                erp._t("ua.col.action"): entry.action,
                erp._t("ua.col.target_user"): entry.target_user_id or "—",
                erp._t("ua.col.performed_by"): entry.performed_by or "—",
                erp._t("ua.col.details"): entry.description,
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_permissions_management(session) -> None:
    """Owner permission overrides — grant, deny, clear, reset to template."""
    erp = _erp()
    if not erp._can("manage_permissions"):
        st.error(erp._t("ua.no_permission"))
        return

    user = erp._current_user()
    if not user:
        st.error(erp._t("ua.no_permission"))
        return

    company_id = erp.current_company_required()

    st.markdown(
        section_header_html(erp._t("ua.title"), accent="info"),
        unsafe_allow_html=True,
    )
    st.caption(erp._t("ua.subtitle"))

    members = ua_svc.list_active_members(session, company_id)
    if not members:
        st.info(erp._t("ua.members.empty"))
        return

    member_by_label = {_member_label(m): m for m in members}
    selected_label = st.selectbox(
        erp._t("ua.field.member"),
        sorted(member_by_label.keys()),
        key="ua_member_select",
    )
    member = member_by_label[selected_label]
    view = ua_svc.effective_permissions(session, company_id, member.user_id)

    tab_overview, tab_audit = st.tabs(
        [erp._t("ua.tab.overview"), erp._t("ua.tab.audit")]
    )
    with tab_overview:
        _render_member_summary(erp, view)
        st.markdown(f"**{erp._t('ua.section.provenance')}**")
        df = _provenance_dataframe(erp, view)
        if df.empty:
            st.info(erp._t("ua.provenance.empty"))
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)
        st.divider()
        st.markdown(f"**{erp._t('ua.section.actions')}**")
        _render_actions(session, company_id, user["id"], member.user_id)
    with tab_audit:
        _render_audit_tab(session, company_id, member.user_id)
