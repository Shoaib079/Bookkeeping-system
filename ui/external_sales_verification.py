"""DSC-P2 — External Sales Verification presentation (no business logic).

Calls services.daily_sales_close only for reads/writes and preview math.
"""

from __future__ import annotations

import datetime
from typing import Any

import pandas as pd
import streamlit as st

from services import daily_sales_close as esv_svc
from ui import date_input as date_ui
from ui.section import section_header_html

_SOURCE_TYPE_ORDER = (
    "POS",
    "ERP",
    "MANUAL",
    "Z_REPORT",
    "EXCEL_UPLOAD",
    "OTHER",
)


def _erp():
    import app as app_module

    return app_module


def _fmt_amount(currency: str, value: float | None) -> str:
    if value is None:
        return "—"
    return f"{currency} {value:,.2f}"


def _parse_business_date(default: datetime.date) -> datetime.date:
    parsed = date_ui.parse_bound_date("esv_business_date")
    return parsed or default


def _history_date_range(
    default_from: datetime.date,
    default_to: datetime.date,
) -> tuple[datetime.date, datetime.date]:
    erp = _erp()
    c1, c2 = st.columns(2)
    inv = erp._t("txn.date_invalid")
    with c1:
        date_ui.render_preferred_date_input(
            erp._t("form.from"),
            "esv_hist_from",
            default=default_from,
            label_visibility="collapsed",
            invalid_message=inv,
        )
    with c2:
        date_ui.render_preferred_date_input(
            erp._t("form.to"),
            "esv_hist_to",
            default=default_to,
            label_visibility="collapsed",
            invalid_message=inv,
        )
    d_from = date_ui.parse_bound_date("esv_hist_from") or default_from
    d_to = date_ui.parse_bound_date("esv_hist_to") or default_to
    if d_from > d_to:
        d_from, d_to = d_to, d_from
    return d_from, d_to


def _seed_form_from_record(record: esv_svc.VerificationRecord | None) -> None:
    """Load active record into widget session keys when business date changes."""
    st.session_state["esv_source_name"] = record.source_name if record else ""
    st.session_state["esv_branch"] = record.branch_location or "" if record else ""
    st.session_state["esv_notes"] = record.notes or "" if record else ""
    st.session_state["esv_ack_note"] = record.variance_ack_note or "" if record else ""
    st.session_state["esv_void_reason"] = ""
    st.session_state["esv_source_type"] = record.source_type if record and record.source_type else ""
    for key, attr in (
        ("esv_external_total", "external_total"),
        ("esv_z_report_total", "z_report_total"),
        ("esv_external_cash", "external_cash"),
        ("esv_external_card", "external_card"),
        ("esv_external_online", "external_online"),
    ):
        val = getattr(record, attr, None) if record else None
        st.session_state[key] = "" if val is None else str(val)


def _collect_source() -> esv_svc.ExternalSalesSource:
    source_type = (st.session_state.get("esv_source_type") or "").strip() or None
    return esv_svc.ExternalSalesSource(
        source_name=(st.session_state.get("esv_source_name") or "").strip(),
        source_type=source_type,
        branch_location=(st.session_state.get("esv_branch") or "").strip() or None,
    )


def _collect_external(erp) -> esv_svc.ExternalSalesTotals:
    return esv_svc.ExternalSalesTotals(
        external_total=erp.amount_input(
            erp._t("esv.field.external_total"),
            key="esv_external_total",
        ),
        z_report_total=erp.amount_input(
            erp._t("esv.field.z_report_total"),
            key="esv_z_report_total",
        ),
        cash=erp.amount_input(erp._t("esv.field.cash"), key="esv_external_cash"),
        card=erp.amount_input(erp._t("esv.field.card"), key="esv_external_card"),
        online=erp.amount_input(erp._t("esv.field.online"), key="esv_external_online"),
    )


def _render_erp_preview(
    session,
    company_id: int,
    business_date: datetime.date,
    currency: str,
) -> esv_svc.ErpSalesTotals:
    erp = _erp()
    totals = esv_svc.compute_erp_sales_totals(session, company_id, business_date)
    st.markdown(f"**{erp._t('esv.section.erp')}**")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(erp._t("esv.erp.total"), _fmt_amount(currency, totals.total))
    c2.metric(erp._t("esv.erp.cash"), _fmt_amount(currency, totals.cash))
    c3.metric(erp._t("esv.erp.card"), _fmt_amount(currency, totals.card))
    c4.metric(erp._t("esv.erp.credit"), _fmt_amount(currency, totals.credit))
    c5.metric(erp._t("esv.erp.sale_count"), str(totals.sale_count))
    return totals


def _render_variance_preview(
    external: esv_svc.ExternalSalesTotals,
    erp_totals: esv_svc.ErpSalesTotals,
    currency: str,
) -> esv_svc.SalesVarianceResult:
    erp = _erp()
    variance = esv_svc.compute_variance(external, erp_totals)
    if (
        external.external_total is None
        and external.z_report_total is None
        and external.cash is None
        and external.card is None
        and external.online is None
    ):
        st.caption(erp._t("esv.variance.enter_totals"))
        return variance

    st.markdown(f"**{erp._t('esv.section.variance')}**")
    if external.external_total is not None:
        st.metric(
            erp._t("esv.variance.primary"),
            _fmt_amount(currency, variance.variance_total),
        )
    else:
        st.caption(f"{erp._t('esv.variance.primary')}: —")
    if external.z_report_total is not None:
        st.metric(
            erp._t("esv.variance.z_report"),
            _fmt_amount(currency, variance.z_report_variance),
        )
    st.caption(
        erp._t(
            "esv.variance.type_label",
            variance_type=variance.variance_type,
            within="yes" if variance.within_tolerance else "no",
        )
    )
    for warn in variance.breakdown_warnings:
        st.warning(warn)
    return variance


def _render_verify_tab(session, company_id: int, user: dict[str, Any], currency: str) -> None:
    erp = _erp()
    today = datetime.date.today()

    date_ui.render_preferred_date_input(
        erp._t("esv.field.business_date"),
        "esv_business_date",
        default=today,
        invalid_message=erp._t("txn.date_invalid"),
    )
    business_date = _parse_business_date(today)

    active = esv_svc.get_active_verification(session, company_id, business_date)
    loaded_for = st.session_state.get("esv_form_loaded_for")
    if loaded_for != business_date.isoformat():
        st.session_state["esv_form_loaded_for"] = business_date.isoformat()
        _seed_form_from_record(active)

    if active:
        if active.status == "verified":
            st.success(erp._t("esv.status.verified", date=business_date.isoformat()))
            if esv_svc.is_verification_stale(session, company_id, active):
                st.warning(erp._t("esv.status.stale"))
        else:
            st.info(erp._t("esv.status.draft", date=business_date.isoformat()))

    st.text_input(
        erp._t("esv.field.source_name"),
        key="esv_source_name",
        placeholder=erp._t("esv.field.source_name_ph"),
    )
    type_options = [""] + list(_SOURCE_TYPE_ORDER)
    type_labels = [erp._t("esv.source_type.none")] + list(_SOURCE_TYPE_ORDER)
    current_type = st.session_state.get("esv_source_type", "")
    type_index = type_options.index(current_type) if current_type in type_options else 0
    picked_label = st.selectbox(
        erp._t("esv.field.source_type"),
        options=type_labels,
        index=type_index,
        key="esv_source_type_pick",
    )
    st.session_state["esv_source_type"] = type_options[type_labels.index(picked_label)]
    st.text_input(erp._t("esv.field.branch"), key="esv_branch")

    external = _collect_external(erp)
    erp_totals = _render_erp_preview(session, company_id, business_date, currency)
    variance = _render_variance_preview(external, erp_totals, currency)

    st.text_area(erp._t("esv.field.notes"), key="esv_notes")

    if not variance.within_tolerance and (
        external.external_total is not None or external.z_report_total is not None
    ):
        st.text_area(
            erp._t("esv.field.ack_note"),
            key="esv_ack_note",
            help=erp._t("esv.field.ack_note_help"),
        )

    can_edit = erp._can("verify_external_sales") and (
        active is None or active.status == "draft"
    )

    if can_edit:
        b1, b2 = st.columns(2)
        with b1:
            if st.button(erp._t("esv.action.save_draft"), key="esv_save_draft"):
                result = esv_svc.save_draft(
                    session,
                    company_id,
                    business_date,
                    _collect_source(),
                    external,
                    user["id"],
                    st.session_state.get("esv_notes"),
                    performed_by=user.get("username"),
                )
                if result.ok:
                    st.success(erp._t("esv.msg.draft_saved"))
                    st.session_state.pop("esv_form_loaded_for", None)
                    st.rerun()
                else:
                    st.error(result.error)
        with b2:
            if st.button(erp._t("esv.action.verify"), type="primary", key="esv_verify"):
                if active is None or active.status != "draft":
                    st.error(erp._t("esv.msg.save_draft_first"))
                else:
                    verify_result = esv_svc.verify_external_sales(
                        session,
                        company_id,
                        active.id,
                        user["id"],
                        ack_note=st.session_state.get("esv_ack_note"),
                        performed_by=user.get("username"),
                    )
                    if verify_result.ok:
                        st.success(erp._t("esv.msg.verified"))
                        st.session_state.pop("esv_form_loaded_for", None)
                        st.rerun()
                    else:
                        st.error(verify_result.error)
    elif active and active.status == "verified":
        st.caption(erp._t("esv.msg.verified_readonly"))

    if active and not active.is_void and erp._can("void_external_sales_verification"):
        with st.expander(erp._t("esv.void.expander")):
            st.text_input(erp._t("esv.void.reason"), key="esv_void_reason")
            if st.button(erp._t("esv.void.btn"), key="esv_void_btn"):
                reason = (st.session_state.get("esv_void_reason") or "").strip()
                err = esv_svc.void_verification(
                    session,
                    company_id,
                    active.id,
                    user["id"],
                    reason,
                    performed_by=user.get("username"),
                )
                if err:
                    st.error(err)
                else:
                    st.success(erp._t("esv.msg.voided"))
                    st.session_state.pop("esv_form_loaded_for", None)
                    st.rerun()


def _render_history_tab(session, company_id: int, currency: str) -> None:
    erp = _erp()
    today = datetime.date.today()
    month_start = today.replace(day=1)
    d_from, d_to = _history_date_range(month_start, today)

    rows = esv_svc.list_verifications(session, company_id, d_from, d_to)
    if not rows:
        st.info(erp._t("esv.history.empty"))
        return

    data = []
    for row in rows:
        data.append(
            {
                erp._t("esv.history.date"): row.business_date.isoformat(),
                erp._t("esv.history.source"): row.source_name,
                erp._t("esv.history.type"): row.source_type or "",
                erp._t("esv.history.branch"): row.branch_location or "",
                erp._t("esv.history.external"): row.external_total,
                erp._t("esv.history.z_report"): row.z_report_total,
                erp._t("esv.history.erp"): row.erp_total,
                erp._t("esv.history.variance"): row.variance_total,
                erp._t("esv.history.z_variance"): row.z_report_variance,
                erp._t("esv.history.status"): row.status,
            }
        )
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


def render_external_sales_verification(session) -> None:
    """External Sales Verification — verify tab + history tab."""
    erp = _erp()
    if not erp._can("view_external_sales_verification"):
        st.error(erp._t("esv.no_permission"))
        return

    user = erp._current_user()
    if not user:
        st.error(erp._t("esv.no_permission"))
        return

    company_id = erp.current_company_required()
    settings = erp.load_settings()
    currency = settings.get("currency", "TRY")

    st.markdown(
        section_header_html(erp._t("esv.title"), accent="info"),
        unsafe_allow_html=True,
    )
    st.caption(erp._t("esv.subtitle"))

    tab_verify, tab_history = st.tabs(
        [
            erp._t("esv.tab.verify"),
            erp._t("esv.tab.history"),
        ]
    )
    with tab_verify:
        _render_verify_tab(session, company_id, user, currency)
    with tab_history:
        _render_history_tab(session, company_id, currency)
