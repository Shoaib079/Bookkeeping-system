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
from registry.banking_config import (
    BANKING_WORKFLOW_MODE_DEFAULT,
    BANKING_WORKFLOW_MODE_IDS,
    banking_default_import_tab,
    banking_normalize_workflow_mode,
    banking_resolve_landing,
)
from registry.nav_keys import NAV_BANKING
from services import read_reconciliation as _read_recon_svc
from services.money import money_to_float
from ui.section import financial_section_header_html


def _erp():
    import app as app_module

    return app_module


def banking_build_section_options(
    *,
    workflow_mode: str,
    show_cockpit: bool,
    show_pos_settlement: bool,
    show_settings: bool,
) -> list[tuple[str, str]]:
    """Ordered Banking chip options — visibility/routing only (BANKING-UX-04)."""
    mode = banking_normalize_workflow_mode(workflow_mode)
    opts: list[tuple[str, str]] = []

    def _cockpit() -> None:
        if show_cockpit:
            opts.append(("cockpit", "bank.section.cockpit"))

    def _accounts() -> None:
        opts.append(("accounts", "bank.section.accounts"))

    def _import() -> None:
        opts.append(("import", "bank.section.import"))

    def _pos() -> None:
        if show_pos_settlement:
            opts.append(("pos_settlement", "banking.pos_entry.title"))

    def _settings() -> None:
        if show_settings:
            opts.append(("settings", "bank.section.settings"))

    if mode == "manual_first":
        _accounts()
        _cockpit()
        _import()
        _pos()
        _settings()
    elif mode == "statement_first":
        _cockpit()
        _import()
        _pos()
        _settings()
    else:
        _cockpit()
        _accounts()
        _import()
        _pos()
        _settings()
    return opts


def banking_section_extra_valid(workflow_mode: str) -> frozenset[str]:
    """Sections valid in session but hidden from chips (statement-first manual path)."""
    if banking_normalize_workflow_mode(workflow_mode) == "statement_first":
        return frozenset({"accounts"})
    return frozenset()


def banking_workflow_default_section(
    section_opts: list[tuple[str, str]],
    workflow_mode: str,
) -> str:
    """Mode-specific default chip when workflow landing applies."""
    mode = banking_normalize_workflow_mode(workflow_mode)
    ids = [opt_id for opt_id, _ in section_opts]
    if not ids:
        return "import"
    if mode == "manual_first" and "accounts" in ids:
        return "accounts"
    if mode == "statement_first":
        if "cockpit" in ids:
            return "cockpit"
        if "import" in ids:
            return "import"
        return ids[0]
    return ids[0]


def banking_apply_session_landing(
    session,
    company_id: int,
    *,
    user_id: int | None = None,
    workflow_mode: str | None = None,
    section_opts: list[tuple[str, str]] | None = None,
) -> None:
    """Apply company/user landing preference once per session."""
    if st.session_state.get("banking_landing_applied"):
        return
    mode = banking_normalize_workflow_mode(workflow_mode or BANKING_WORKFLOW_MODE_DEFAULT)
    opts = section_opts or []
    if mode in ("statement_first", "manual_first") and opts:
        st.session_state["banking_section"] = banking_workflow_default_section(opts, mode)
    else:
        landing = banking_resolve_landing(session, company_id, user_id=user_id)
        if landing == "queue":
            st.session_state["banking_section"] = "import"
            st.session_state["bsi_section"] = "match"
        elif landing in ("cockpit", "accounts"):
            st.session_state["banking_section"] = landing
    st.session_state["banking_landing_applied"] = True


def banking_apply_default_import_tab(
    session,
    company_id: int,
    *,
    user_id: int | None = None,
) -> None:
    """Apply user default import tab once per session."""
    if st.session_state.get("bsi_import_tab_applied"):
        return
    st.session_state["bsi_section"] = banking_default_import_tab(
        session, company_id, user_id=user_id
    )
    st.session_state["bsi_import_tab_applied"] = True


def banking_section_select(
    widget_key: str,
    options: list[tuple[str, str]],
    *,
    extra_valid: frozenset[str] | None = None,
) -> str:
    """Banking chip grid — canonical section selector (BANKING-DESKTOP-01 B1)."""
    erp = _erp()
    ids = [opt_id for opt_id, _ in options]
    valid = frozenset(ids) | (extra_valid or frozenset())
    if widget_key not in st.session_state or st.session_state[widget_key] not in valid:
        st.session_state[widget_key] = ids[0] if ids else "import"
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


def banking_show_manual_advanced_panel(workflow_mode: str, current_section: str) -> bool:
    """Statement-first: manual entry lives under Advanced when not on accounts."""
    return (
        banking_normalize_workflow_mode(workflow_mode) == "statement_first"
        and current_section != "accounts"
    )


def banking_render_manual_advanced_gate(workflow_mode: str) -> None:
    """Advanced expander — routes to manual accounts without removing the workflow."""
    erp = _erp()
    with st.expander(erp._t("bank.advanced.section"), expanded=False):
        st.caption(erp._t("bank.advanced.manual_caption"))
        if st.button(
            erp._t("bank.advanced.open_manual"),
            key="bank_adv_open_manual",
            use_container_width=True,
        ):
            st.session_state["banking_section"] = "accounts"
            st.rerun()


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
    show_confidence: bool = True,
    density: str = "comfortable",
) -> None:
    """Scannable postable-row list — selecting a row opens the detail fragment."""
    erp = _erp()
    st.markdown(f"**{erp._t('banking.import.match.queue_heading')}**")
    compact = density == "compact"
    for item in queue_rows:
        row_id = item["row_id"]
        is_sel = row_id == selected_row_id
        conf_text = erp._t(f"banking.import.match.confidence.{item['confidence']}")
        if show_confidence:
            c_line, c_kind, c_btn = st.columns([4, 2, 1])
        else:
            c_line, c_btn = st.columns([5, 1])
            c_kind = None
        with c_line:
            prefix = "**" if is_sel else ""
            suffix = "**" if is_sel else ""
            line = f"{prefix}{item['summary']}{suffix}"
            if compact:
                st.caption(line.replace("**", ""))
            else:
                st.markdown(line)
        if c_kind is not None:
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


def banking_bank_fee_batch_candidates(
    session, company_id: int, postable
) -> list[dict]:
    """High-confidence bank_fee rows only."""
    return _erp()._bsi_bank_fee_batch_candidates(session, company_id, postable)


def banking_bank_fee_batch_partition(
    session, company_id: int, postable
) -> dict:
    """Eligible vs needs-review rows for conservative batch posting."""
    return _erp()._bsi_bank_fee_batch_partition(session, company_id, postable)


def banking_bank_fee_batch_review_reason(session, company_id: int, row) -> str | None:
    """Expose eligibility check for tests."""
    return _erp()._bsi_bank_fee_batch_review_reason(session, company_id, row)


def render_banking_bank_fee_batch_panel(
    session,
    company_id: int,
    partition: dict,
) -> None:
    """Confirm + batch-post high-confidence bank fees only (P2.2-A)."""
    erp = _erp()
    eligible = partition.get("eligible") or []
    needs_review = partition.get("needs_review") or []
    if not eligible and not needs_review:
        return

    results_key = "bsi_bank_fee_batch_results"
    skipped_key = "bsi_bank_fee_batch_skipped_count"
    if results_key in st.session_state:
        results = st.session_state[results_key]
        posted = sum(1 for r in results if r["status"] == "posted")
        failed = sum(1 for r in results if r["status"] == "failed")
        already = sum(1 for r in results if r["status"] == "already_posted")
        skipped = st.session_state.get(skipped_key, 0) + sum(
            1 for r in results if r["status"] == "skipped"
        )
        st.markdown(f"**{erp._t('banking.batch.bank_fee.results_title')}**")
        st.caption(
            erp._t(
                "banking.batch.bank_fee.summary",
                posted=posted,
                failed=failed,
                already=already,
                skipped=skipped,
            )
        )
        for row in results:
            if row["status"] == "posted":
                status = erp._t("banking.batch.bank_fee.status.posted")
            elif row["status"] == "already_posted":
                status = erp._t("banking.batch.bank_fee.status.already_posted")
            elif row["status"] == "skipped":
                reason_key = f"banking.batch.bank_fee.reason.{row.get('error', '')}"
                reason = erp._t(reason_key) if row.get("error") else ""
                status = erp._t("banking.import.status.skipped")
                detail = f" — {reason}" if reason else ""
                st.caption(f"{row['label']}: {status}{detail}")
                continue
            else:
                status = erp._t("banking.batch.bank_fee.status.failed")
            detail = f" — {row['error']}" if row.get("error") else ""
            st.caption(f"{row['label']}: {status}{detail}")
        if st.button(
            erp._t("banking.batch.bank_fee.dismiss"),
            key="bsi_bank_fee_batch_dismiss",
        ):
            del st.session_state[results_key]
            st.session_state.pop(skipped_key, None)
            st.rerun()
        st.divider()
        return

    if needs_review:
        st.markdown(f"**{erp._t('banking.batch.bank_fee.needs_review_title')}**")
        st.caption(
            erp._t(
                "banking.batch.bank_fee.needs_review_desc",
                count=len(needs_review),
            )
        )
        for item in needs_review:
            reason_key = f"banking.batch.bank_fee.reason.{item['review_reason']}"
            reason = erp._t(reason_key)
            st.caption(
                erp._t(
                    "banking.batch.bank_fee.needs_review_line",
                    label=item["label"],
                    reason=reason,
                )
            )

    if not eligible:
        st.divider()
        return

    with st.container(border=True):
        st.markdown(f"**{erp._t('banking.batch.bank_fee.title')}**")
        st.caption(
            erp._t(
                "banking.batch.bank_fee.desc",
                count=len(eligible),
            )
        )
        for item in eligible:
            st.caption(
                erp._t(
                    "banking.batch.bank_fee.confirm_detail",
                    date=item["date"],
                    amount=f"{item['amount']:,.2f}",
                    description=(item["description"] or "")[:60],
                    subtype=item["subtype_label"],
                    impact=item["account_impact"],
                )
            )
        if st.button(
            erp._t("banking.batch.bank_fee.confirm"),
            key="bsi_bank_fee_batch_confirm",
            type="primary",
        ):
            uid = (erp._current_user() or {}).get("id")
            st.session_state[results_key] = erp._bsi_execute_bank_fee_batch_post(
                session,
                company_id,
                [c["row_id"] for c in eligible],
                uid,
            )
            st.session_state[skipped_key] = len(needs_review)
            st.rerun()
    st.divider()


def banking_cockpit_drill_to(section: str) -> None:
    """Drill-through to Statement import sub-section (match | review | history)."""
    st.session_state["banking_section"] = "import"
    st.session_state["bsi_section"] = section
    st.rerun()


BANKING_STATEMENT_TIE_OUT_TOLERANCE = _read_recon_svc.TIE_OUT_TOLERANCE
_BANKING_TERMINAL_ROW_STATUSES = _read_recon_svc.TERMINAL_ROW_STATUSES
_BANKING_NON_TERMINAL_ROW_STATUSES = _read_recon_svc.NON_TERMINAL_ROW_STATUSES


def banking_statement_row_signed_amount(row) -> float:
    """Credits increase balance; debits decrease (signed movement)."""
    return _read_recon_svc.statement_row_signed_amount(row)


def banking_statement_row_signed_total(rows) -> float:
    return _read_recon_svc.statement_row_signed_total(rows)


def _banking_readiness_tri_label(erp, tri: str) -> str:
    key = f"banking.readiness.tri.{tri}"
    return erp._t(key) if tri in ("ok", "attention", "unavailable") else tri


def compute_banking_statement_readiness(
    session,
    import_record,
    *,
    rows: list | None = None,
) -> dict[str, Any]:
    """Read-only per-statement workflow + tie-out readiness (advisory only)."""
    readiness = _read_recon_svc.compute_statement_readiness(
        session,
        import_record,
        company_id=import_record.company_id,
        rows=rows,
    )
    if readiness is None:
        return {}
    return readiness.to_dict()


def banking_company_statement_readiness(
    session, company_id: int, *, limit: int = 10
) -> list[dict[str, Any]]:
    """Recent imports with per-statement readiness (company-scoped)."""
    return [
        dto.to_dict()
        for dto in _read_recon_svc.compute_company_statement_readiness(
            session, company_id, limit=limit,
        )
    ]


def banking_readiness_drill_to(section: str, import_id: int | None = None) -> None:
    """Drill-through to Review or Match queue; optionally pre-select import on Review."""
    st.session_state["banking_section"] = "import"
    st.session_state["bsi_section"] = section
    if import_id is not None and section == "review":
        st.session_state["bsi_review_import"] = import_id
    st.rerun()


def render_banking_statement_readiness_panel(
    session,
    company_id: int,
    *,
    import_id: int | None = None,
    limit: int = 5,
) -> None:
    """Read-only statement readiness / tie-out (OK · Attention · Unavailable)."""
    erp = _erp()
    st.markdown(
        financial_section_header_html(erp._t("banking.readiness.title"), accent="info"),
        unsafe_allow_html=True,
    )
    st.caption(erp._t("banking.readiness.desc"))

    if import_id is not None:
        imp = session.get(erp.BankStatementImport, import_id)
        if not imp or imp.company_id != company_id:
            return
        items = [compute_banking_statement_readiness(session, imp)]
    else:
        items = banking_company_statement_readiness(session, company_id, limit=limit)

    if not items:
        st.caption(erp._t("banking.readiness.no_imports"))
        return

    for item in items:
        with st.container(border=True):
            title = item["file_name"]
            if item["period"]:
                title = f"{title} · {item['period']}"
            st.markdown(f"**{title}**")
            c1, c2, c3 = st.columns(3)
            c1.caption(
                f"{erp._t('banking.readiness.complete')}: "
                f"{_banking_readiness_tri_label(erp, item['complete_tri'])}"
            )
            c2.caption(
                f"{erp._t('banking.readiness.reconciled')}: "
                f"{_banking_readiness_tri_label(erp, item['reconciled_tri'])}"
            )
            tie_tri = item["tie_out"]
            if tie_tri == "unavailable":
                tie_label = erp._t("banking.readiness.tie_out.unavailable_msg")
            else:
                tie_label = _banking_readiness_tri_label(
                    erp, "ok" if tie_tri == "ok" else "attention"
                )
            c3.caption(f"{erp._t('banking.readiness.tie_out')}: {tie_label}")
            m1, m2, m3 = st.columns(3)
            m1.metric(erp._t("banking.readiness.remaining"), item["remaining_rows"])
            m2.metric(
                erp._t("banking.readiness.review_pending"), item["review_pending"]
            )
            m3.metric(
                erp._t("banking.readiness.failed_blocked"), item["failed_blocked"]
            )
            if item["tie_out_available"] and item["tie_out_delta"] is not None:
                st.caption(
                    erp._t(
                        "banking.readiness.tie_out_detail",
                        declared=f"{item['declared_movement']:,.2f}",
                        rows=f"{item['row_signed_total']:,.2f}",
                        delta=f"{item['tie_out_delta']:,.2f}",
                    )
                )
            b1, b2 = st.columns(2)
            with b1:
                if st.button(
                    erp._t("banking.readiness.drill_queue"),
                    key=f"readiness_drill_match_{item['import_id']}",
                    use_container_width=True,
                ):
                    banking_readiness_drill_to("match")
            with b2:
                if st.button(
                    erp._t("banking.readiness.drill_review"),
                    key=f"readiness_drill_review_{item['import_id']}",
                    use_container_width=True,
                ):
                    banking_readiness_drill_to("review", import_id=item["import_id"])


def banking_recon_cockpit_summary(session, company_id: int) -> dict[str, Any]:
    """Read-only aggregate for Reconciliation Cockpit (company-scoped)."""
    from reconciliation.company_card import compute_cc_payable_recon_health
    from reconciliation.match_post import get_postable_rows

    erp = _erp()
    postable_count = len(get_postable_rows(session, company_id))
    imports = (
        erp.cq(session, erp.BankStatementImport)
        .order_by(erp.BankStatementImport.created_at.desc())
        .limit(5)
        .all()
    )
    recent_imports = [
        {
            "id": imp.id,
            "file_name": imp.file_name,
            "valid_count": imp.valid_count or 0,
            "error_count": imp.error_count or 0,
            "flagged_count": imp.flagged_count or 0,
            "created_at": imp.created_at,
        }
        for imp in imports
    ]
    import_totals = {
        "valid": sum(r["valid_count"] for r in recent_imports),
        "error": sum(r["error_count"] for r in recent_imports),
        "flagged": sum(r["flagged_count"] for r in recent_imports),
        "import_count": len(recent_imports),
    }
    bank_accounts = (
        erp.cq(session, erp.BankAccount)
        .filter_by(is_active=True)
        .order_by(erp.BankAccount.name)
        .all()
    )
    bank_rows: list[dict[str, Any]] = []
    total_stored = 0.0
    for ba in bank_accounts:
        if erp.is_credit_card_account(ba):
            continue
        stored = money_to_float(ba.balance)
        total_stored += stored
        bank_rows.append(
            {
                "id": ba.id,
                "name": ba.name,
                "currency": ba.currency or "TRY",
                "stored_balance": stored,
            }
        )
    show_settlement = erp._card_settlement_on(session) and erp._company_card_on(
        session
    )
    settlement: dict[str, Any] | None = None
    if show_settlement:
        cc_health = compute_cc_payable_recon_health(session, company_id)
        clearing_acct = erp.get_account_by_name(session, "Card Sales Clearing")
        clearing_balance = (
            round(erp.calculate_account_balance(session, clearing_acct), 2)
            if clearing_acct
            else 0.0
        )
        unsettled = fetch_unsettled_card_sales_for_visibility(
            session,
            company_id,
            get_unsettled_card_sales=erp.get_unsettled_card_sales,
            get_account_by_name=erp.get_account_by_name,
        )
        settlement = {
            "cc_health": cc_health,
            "clearing_balance": clearing_balance,
            "unsettled_count": len(unsettled),
            "unsettled_total": round(sum_unsettled_card_sales(unsettled), 2),
        }
    return {
        "company_id": company_id,
        "reconciliation_enabled": erp._banking_reconciliation_on(session),
        "postable_count": postable_count,
        "recent_imports": recent_imports,
        "import_totals": import_totals,
        "bank_accounts": bank_rows,
        "bank_total_stored": round(total_stored, 2),
        "settlement": settlement,
        "show_settlement_tile": show_settlement,
    }


def render_banking_recon_cockpit(session, company_id: int) -> None:
    """Read-only Banking landing — tiles drill into Queue / Review / History."""
    erp = _erp()
    if not erp._banking_reconciliation_on(session):
        st.info(erp._t("banking.cockpit.gate_disabled"))
        return
    if not erp._can("view_bank_statement_import"):
        st.caption(erp._t("form.access_denied"))
        return

    summary = banking_recon_cockpit_summary(session, company_id)
    settings = erp.load_settings()
    currency = settings.get("currency", "TRY")
    totals = summary["import_totals"]

    st.markdown(
        financial_section_header_html(erp._t("banking.cockpit.title"), accent="info"),
        unsafe_allow_html=True,
    )
    st.caption(erp._t("banking.cockpit.desc"))

    c_import, c_queue = st.columns(2)
    with c_import:
        with st.container(border=True):
            st.markdown(f"**{erp._t('banking.cockpit.tile.import_health')}**")
            m1, m2, m3 = st.columns(3)
            m1.metric(erp._t("banking.cockpit.valid_rows"), totals["valid"])
            m2.metric(erp._t("banking.cockpit.error_rows"), totals["error"])
            m3.metric(erp._t("banking.cockpit.flagged_rows"), totals["flagged"])
            if st.button(
                erp._t("banking.cockpit.open_review"),
                key="cockpit_drill_review",
                use_container_width=True,
            ):
                banking_cockpit_drill_to("review")

    with c_queue:
        with st.container(border=True):
            st.markdown(f"**{erp._t('banking.cockpit.tile.postable_queue')}**")
            st.metric(
                erp._t("banking.cockpit.postable_count"),
                summary["postable_count"],
            )
            if st.button(
                erp._t("banking.cockpit.open_queue"),
                key="cockpit_drill_match",
                use_container_width=True,
                type="primary",
            ):
                banking_cockpit_drill_to("match")

    c_recent, c_bank = st.columns(2)
    with c_recent:
        with st.container(border=True):
            st.markdown(f"**{erp._t('banking.cockpit.tile.recent_imports')}**")
            if summary["recent_imports"]:
                for imp in summary["recent_imports"]:
                    st.caption(
                        erp._t(
                            "banking.cockpit.recent_import_line",
                            file=imp["file_name"],
                            valid=imp["valid_count"],
                            error=imp["error_count"],
                            flagged=imp["flagged_count"],
                        )
                    )
            else:
                st.caption(erp._t("banking.cockpit.no_imports"))
            if st.button(
                erp._t("banking.cockpit.open_history"),
                key="cockpit_drill_history",
                use_container_width=True,
            ):
                banking_cockpit_drill_to("history")

    with c_bank:
        with st.container(border=True):
            st.markdown(f"**{erp._t('banking.cockpit.tile.bank_balance')}**")
            st.metric(
                erp._t("banking.cockpit.bank_total"),
                f"{currency} {summary['bank_total_stored']:,.2f}",
            )
            for row in summary["bank_accounts"][:4]:
                st.caption(
                    f"{row['name']}: {row['currency']} {row['stored_balance']:,.2f}"
                )

    if summary["show_settlement_tile"] and summary["settlement"]:
        stl = summary["settlement"]
        cc = stl["cc_health"]
        with st.container(border=True):
            st.markdown(f"**{erp._t('banking.cockpit.tile.settlement')}**")
            s1, s2, s3 = st.columns(3)
            s1.metric(
                erp._t("banking.cockpit.clearing_balance"),
                f"{currency} {stl['clearing_balance']:,.2f}",
            )
            s2.metric(
                erp._t("banking.cockpit.unsettled_sales"),
                stl["unsettled_count"],
            )
            s3.metric(
                erp._t("banking.cockpit.cc_difference"),
                f"{currency} {cc['difference']:,.2f}",
            )

    render_banking_statement_readiness_panel(session, company_id)


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
