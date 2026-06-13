"""UI-STAB-02 — Banking presentation layer (no posting / no JE mutations).

Business logic: reconciliation/* and app.py orchestration.
Posting: app.py + reconciliation/match_post.py only.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from reconciliation.clearing import fetch_unsettled_card_sales_for_visibility
from reconciliation.match_post import (
    card_deposit_style,
    looks_like_credit_card_bill_payment,
    looks_like_statement_bank_fee,
    looks_like_worker_payroll,
)
from reconciliation.clearing_visibility import ClearingVisibilitySnapshot, compute_clearing_visibility
from reconciliation.unsettled_card_sales_list import (
    DEFAULT_LIST_LIMIT,
    apply_list_limit,
    enrich_unsettled_sale_row,
    filter_unsettled_by_date,
    list_total_mismatch,
    sum_unsettled_card_sales,
)
from registry.nav_keys import NAV_BANKING
from ui.section import financial_section_header_html


def _erp():
    import app as app_module

    return app_module


def banking_section_select(widget_key: str, options: list[tuple[str, str]]) -> str:
    """Banking chip grid — canonical section selector (BANKING-DESKTOP-01 B1)."""
    erp = _erp()
    ids = [opt_id for opt_id, _ in options]
    if widget_key not in st.session_state or st.session_state[widget_key] not in ids:
        st.session_state[widget_key] = ids[0]
    cur = st.session_state[widget_key]

    with st.container(border=False, key=f"bank_sec_sel_{widget_key}"):
        st.markdown('<div class="erp-bank-sel-chip-host"></div>', unsafe_allow_html=True)
        for i in range(0, len(options), 2):
            chunk = options[i : i + 2]
            cols = st.columns(len(chunk), gap="small")
            for col, (opt_id, msg_key) in zip(cols, chunk):
                if col.button(
                    erp._t(msg_key),
                    key=f"bank_sec_pick_{widget_key}_{opt_id}",
                    use_container_width=True,
                    type="primary" if cur == opt_id else "secondary",
                ):
                    st.session_state[widget_key] = opt_id
                    st.rerun()

    return st.session_state[widget_key]


def banking_match_kind_confidence(
    detected_kind: str,
    description: str,
    *,
    is_deposit: bool,
) -> str:
    """Presentation-only confidence band: high | medium | low."""
    if is_deposit:
        if detected_kind == "card_clearing":
            style = card_deposit_style(description)
            if style in ("net", "gross"):
                return "high"
            if style == "card":
                return "medium"
        return "low"

    if detected_kind == "cc_bill" and looks_like_credit_card_bill_payment(description):
        return "high"
    if detected_kind == "bank_fee" and looks_like_statement_bank_fee(description):
        return "high"
    if detected_kind == "worker_payroll" and looks_like_worker_payroll(description):
        return "high"
    return "low"


def render_banking_match_suggestion_chip(
    *,
    detected_kind: str,
    kind_label: str,
    confidence: str,
    accept_key: str,
    kind_state_key: str,
) -> None:
    """Detected match kind + confidence — Accept only updates per-row kind state."""
    erp = _erp()
    conf_text = erp._t(f"banking.import.match.confidence.{confidence}")
    detected = erp._t("banking.import.match.detected_kind", kind=kind_label)
    conf_label = erp._t("banking.import.match.confidence_label", level=conf_text)
    c_main, c_btn = st.columns([5, 1])
    with c_main:
        st.info(f"{detected} · {conf_label}")
    with c_btn:
        if st.button(
            erp._t("banking.import.match.accept_suggestion"),
            key=accept_key,
            use_container_width=True,
        ):
            st.session_state[kind_state_key] = detected_kind
            st.rerun()


def render_banking_match_queue_list(
    queue_rows: list[dict],
    *,
    selected_row_id: int,
) -> None:
    """Scannable postable-row list — selecting a row opens the detail fragment."""
    erp = _erp()
    st.markdown(f"**{erp._t('banking.import.match.queue_heading')}**")
    for item in queue_rows:
        row_id = item["row_id"]
        is_sel = row_id == selected_row_id
        conf_text = erp._t(f"banking.import.match.confidence.{item['confidence']}")
        c_line, c_kind, c_btn = st.columns([4, 2, 1])
        with c_line:
            prefix = "**" if is_sel else ""
            suffix = "**" if is_sel else ""
            st.markdown(f"{prefix}{item['summary']}{suffix}")
        with c_kind:
            st.caption(f"{item['kind_label']} · {conf_text}")
        with c_btn:
            if st.button(
                erp._t("banking.import.match.queue_review"),
                key=f"bsi_queue_pick_{row_id}",
                type="primary" if is_sel else "secondary",
                use_container_width=True,
            ):
                st.session_state["bsi_queue_sel_row"] = row_id
                st.rerun()
    st.divider()


def banking_pos_settlement_route_keys() -> dict[str, Any]:
    """Session keys for BANKING-UX-02 P1B → focused POS settlement section."""
    return {
        "nav_selection": NAV_BANKING,
        "banking_section": "pos_settlement",
        "bsi_section": "match",
        "bsi_match_kind": "card_clearing",
        "bsi_pos_entry": True,
    }


def apply_banking_pos_settlement_route() -> None:
    for k, v in banking_pos_settlement_route_keys().items():
        st.session_state[k] = v
    st.rerun()


def render_pos_settlement_preview_block(preview, currency: str) -> None:
    """Read-only POS settlement preview (BANKING-UX-02 P1)."""
    erp = _erp()
    st.markdown(
        financial_section_header_html(
            erp._t("banking.pos_preview.section_title"), accent="info"
        ),
        unsafe_allow_html=True,
    )
    st.caption(erp._t("banking.pos_preview.revenue_note"))
    with st.container(border=True):
        p1, p2, p3 = st.columns(3)
        p1.metric(
            erp._t("banking.pos_preview.available_clearing"),
            f"{currency} {preview.available_clearing:,.2f}",
        )
        p2.metric(
            erp._t("banking.pos_preview.settlement_amount"),
            f"{currency} {preview.settlement_amount:,.2f}",
        )
        p3.metric(
            erp._t("banking.pos_preview.bank_charges"),
            f"{currency} {preview.bank_charges:,.2f}",
        )
        p4, p5 = st.columns(2)
        p4.metric(
            erp._t("banking.pos_preview.expected_deposit"),
            f"{currency} {preview.expected_bank_deposit:,.2f}",
        )
        p5.metric(
            erp._t("banking.pos_preview.remaining_clearing"),
            f"{currency} {preview.remaining_clearing:,.2f}",
        )
    for warn in preview.warnings:
        st.warning(erp._t(warn.key, currency=currency, **warn.kwargs))


def banking_match_failure_label(key: str, **kwargs) -> str:
    """Resolve banking.match_failure.* — same catalogs as P1–P3 (_t + transactional fallback)."""
    erp = _erp()
    text = erp._t(key, **kwargs)
    if text != key:
        return text
    from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR

    cat = TRANSACTIONAL_TR if erp._ui_locale() == "tr" else TRANSACTIONAL_EN
    raw = cat.get(key) or TRANSACTIONAL_EN.get(key) or key
    if kwargs and raw != key:
        try:
            return raw.format(**kwargs)
        except KeyError:
            return raw
    return raw


def render_pos_match_failure_block(check, currency: str) -> None:
    """Read-only match guidance before post (BANKING-UX-02 P4)."""
    st.markdown(
        financial_section_header_html(
            banking_match_failure_label("banking.match_failure.section_title"),
            accent="info",
        ),
        unsafe_allow_html=True,
    )
    status_keys = {
        "ready": "banking.match_failure.status.ready",
        "attention": "banking.match_failure.status.attention",
        "cannot_post": "banking.match_failure.status.cannot_post",
    }
    status_key = status_keys[check.status]
    if check.status == "ready":
        st.success(banking_match_failure_label(status_key))
    elif check.status == "attention":
        st.warning(banking_match_failure_label(status_key))
    else:
        st.error(banking_match_failure_label(status_key))
    if not check.items:
        return
    with st.container(border=True):
        for item in check.items:
            text = banking_match_failure_label(
                item.key, currency=currency, **item.kwargs
            )
            if item.blocking:
                st.error(f"• {text}")
            else:
                st.warning(f"• {text}")


def render_card_sales_clearing_visibility_block(
    session,
    cid: int,
    *,
    clearing_acct,
    currency: str,
) -> ClearingVisibilitySnapshot | None:
    """Read-only Card Sales Clearing visibility (BANKING-UX-02 P2)."""
    erp = _erp()
    if not clearing_acct:
        return None
    available_clearing = erp.calculate_account_balance(session, clearing_acct)
    snapshot = compute_clearing_visibility(
        session,
        cid,
        clearing_account_id=clearing_acct.id,
        current_clearing_balance=available_clearing,
        get_unsettled_card_sales=erp.get_unsettled_card_sales,
        get_account_by_name=erp.get_account_by_name,
    )
    st.markdown(
        financial_section_header_html(
            erp._t("banking.clearing_visibility.section_title"), accent="info"
        ),
        unsafe_allow_html=True,
    )
    st.caption(erp._t("banking.clearing_visibility.explainer"))
    with st.container(border=True):
        v1, v2 = st.columns(2)
        v1.metric(
            erp._t("banking.clearing_visibility.current_balance"),
            f"{currency} {snapshot.current_clearing_balance:,.2f}",
        )
        v2.metric(
            erp._t("banking.clearing_visibility.unsettled_sales"),
            f"{currency} {snapshot.unsettled_card_sales_total:,.2f}",
        )
        v3, v4 = st.columns(2)
        v3.metric(
            erp._t("banking.clearing_visibility.settlements_posted"),
            f"{currency} {snapshot.settlements_posted_total:,.2f}",
        )
        v4.metric(
            erp._t("banking.clearing_visibility.remaining_clearing"),
            f"{currency} {snapshot.remaining_clearing:,.2f}",
        )
    if snapshot.reconciliation_mismatch:
        st.warning(
            erp._t(
                "banking.clearing_visibility.warn_reconciliation",
                remaining=f"{snapshot.remaining_clearing:,.2f}",
                current=f"{snapshot.current_clearing_balance:,.2f}",
                currency=currency,
            )
        )
    return snapshot


def render_unsettled_card_sales_list_block(
    session,
    cid: int,
    *,
    currency: str,
    visibility_unsettled_total: float,
) -> None:
    """Read-only unsettled card sales table (BANKING-UX-02 P3)."""
    erp = _erp()
    rows = fetch_unsettled_card_sales_for_visibility(
        session,
        cid,
        get_unsettled_card_sales=erp.get_unsettled_card_sales,
        get_account_by_name=erp.get_account_by_name,
    )
    st.markdown(
        financial_section_header_html(
            erp._t("banking.unsettled_card_sales.section_title"), accent="info"
        ),
        unsafe_allow_html=True,
    )
    if not rows:
        st.info(erp._t("banking.unsettled_card_sales.empty"))
        return

    from ui import date_input as date_ui

    _min_d = min(r["date"] for r in rows if r.get("date"))
    _max_d = max(r["date"] for r in rows if r.get("date"))
    _inv = erp._t("txn.date_invalid")
    f1, f2, f3 = st.columns([1, 1, 1])
    with f1:
        date_ui.render_preferred_date_input(
            erp._t("banking.unsettled_card_sales.filter_from"),
            "bank_unsettled_from",
            default=_min_d,
            invalid_message=_inv,
        )
    with f2:
        date_ui.render_preferred_date_input(
            erp._t("banking.unsettled_card_sales.filter_to"),
            "bank_unsettled_to",
            default=_max_d,
            invalid_message=_inv,
        )
    date_from = date_ui.parse_bound_date("bank_unsettled_from") or _min_d
    date_to = date_ui.parse_bound_date("bank_unsettled_to") or _max_d
    with f3:
        show_all = st.checkbox(
            erp._t("banking.unsettled_card_sales.show_all"),
            value=False,
            key="bank_unsettled_show_all",
        )

    list_total = sum_unsettled_card_sales(rows)
    filtered = filter_unsettled_by_date(rows, date_from=date_from, date_to=date_to)
    visible, truncated = apply_list_limit(
        filtered, show_all=show_all, limit=DEFAULT_LIST_LIMIT
    )
    if list_total_mismatch(list_total, visibility_unsettled_total):
        st.warning(
            erp._t(
                "banking.unsettled_card_sales.warn_total_mismatch",
                list_total=f"{list_total:,.2f}",
                visibility_total=f"{visibility_unsettled_total:,.2f}",
                currency=currency,
            )
        )
    if truncated:
        st.caption(
            erp._t(
                "banking.unsettled_card_sales.latest_limit",
                limit=DEFAULT_LIST_LIMIT,
                total=len(filtered),
            )
        )

    table_rows = []
    for row in visible:
        enriched = enrich_unsettled_sale_row(
            session, row, default_currency=currency
        )
        table_rows.append(
            {
                erp._t("banking.unsettled_card_sales.col.date"): enriched["date"],
                erp._t("banking.unsettled_card_sales.col.reference"): enriched[
                    "reference"
                ],
                erp._t("banking.unsettled_card_sales.col.amount"): enriched["amount"],
                erp._t("banking.unsettled_card_sales.col.currency"): enriched[
                    "currency"
                ],
                erp._t("banking.unsettled_card_sales.col.payment_method"): erp._i18n_db(
                    erp.SALE_TYPE_I18N, enriched["payment_method"]
                ),
                erp._t("banking.unsettled_card_sales.col.notes"): enriched["notes"],
                erp._t("banking.unsettled_card_sales.col.status"): erp._t(
                    "banking.unsettled_card_sales.status.unsettled"
                ),
            }
        )
    erp._render_readable_df(pd.DataFrame(table_rows))


def render_banking_pos_settlement_entry(session) -> None:
    """BANKING-UX-02 P1B — visible shortcut to focused POS settlement section."""
    erp = _erp()
    if not erp._banking_pos_settlement_enabled(session):
        return
    if st.session_state.get("banking_section") == "pos_settlement":
        return
    cid = erp.current_company_required()
    with st.container(border=True):
        st.markdown(
            financial_section_header_html(
                erp._t("banking.pos_entry.title"), accent="info"
            ),
            unsafe_allow_html=True,
        )
        st.caption(erp._t("banking.pos_entry.hint"))
        if not erp._postable_deposit_rows(session, cid):
            st.info(erp._t("banking.pos_entry.no_rows"))
        if st.button(
            erp._t("banking.pos_entry.open"),
            type="primary",
            key="bank_pos_settlement_open",
        ):
            apply_banking_pos_settlement_route()


def render_banking_pos_settlement_section(session) -> None:
    """BANKING-UX-02 P1B — focused POS / Card Settlement (no import chrome)."""
    erp = _erp()
    from models import BankStatementRow

    if not erp._banking_pos_settlement_enabled(session):
        st.caption(erp._t("form.access_denied"))
        return
    cid = erp.current_company_required()
    st.markdown(
        financial_section_header_html(
            erp._t("banking.pos_entry.title"), accent="info"
        ),
        unsafe_allow_html=True,
    )
    st.caption(erp._t("banking.pos_entry.hint"))
    deposit_rows = erp._postable_deposit_rows(session, cid)
    if not deposit_rows:
        st.info(erp._t("banking.pos_entry.no_rows_focused"))
        if st.button(
            erp._t("banking.pos_entry.go_import"),
            type="primary",
            key="bank_pos_go_import",
        ):
            st.session_state["banking_section"] = "import"
            st.rerun()
        return
    row_labels = {
        r.id: (
            f"#{r.import_row_index} · {r.date} · "
            f"+{r.amount:,.2f} · {(r.description or '')[:40]}"
        )
        for r in deposit_rows
    }
    if st.session_state.pop("bsi_pos_entry", False):
        st.session_state["bsi_match_kind"] = "card_clearing"
    sel_row_id = st.selectbox(
        erp._t("banking.import.match.select_row"),
        options=list(row_labels.keys()),
        format_func=lambda i: row_labels[i],
        key="bsi_match_row",
    )
    sel_row = session.get(BankStatementRow, sel_row_id)
    if sel_row:
        st.session_state["bsi_match_kind_row"] = sel_row_id
        erp._render_bsi_deposit_clearing_panel(session, sel_row, cid)
