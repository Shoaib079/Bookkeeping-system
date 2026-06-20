"""BANKING-UX-04 — workflow-mode presentation helpers (Banking + Add Transaction).

Lightweight module: no reconciliation or posting-kernel imports. Consumed by ``app.py``
and re-exported from ``ui.banking`` for tests.
"""

from __future__ import annotations

import streamlit as st

from registry.banking_config import (
    BANKING_WORKFLOW_MODE_DEFAULT,
    banking_default_import_tab,
    banking_normalize_workflow_mode,
    banking_resolve_landing,
)
from registry.nav_keys import NAV_BANKING


def _erp():
    import app as app_module

    return app_module


AT_BANK_TXN_TYPE_IDX = 5


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


def at_primary_type_indices(workflow_mode: str, *, total_types: int = 6) -> list[int]:
    """Desktop/mobile primary type chip order — visibility/routing only (BANKING-UX-04-S3)."""
    mode = banking_normalize_workflow_mode(workflow_mode)
    all_idx = list(range(total_types))
    if mode == "statement_first":
        return [i for i in all_idx if i != AT_BANK_TXN_TYPE_IDX]
    if mode == "manual_first":
        return [AT_BANK_TXN_TYPE_IDX] + [i for i in all_idx if i != AT_BANK_TXN_TYPE_IDX]
    return all_idx


def at_mobile_type_picker_split(
    workflow_mode: str,
    rows: list[tuple[int, str, str]],
) -> tuple[list[tuple[int, str, str]], list[tuple[int, str, str]]]:
    """Split mobile type picker rows into primary vs Advanced (statement-first bank type)."""
    mode = banking_normalize_workflow_mode(workflow_mode)
    bank_rows = [r for r in rows if r[0] == AT_BANK_TXN_TYPE_IDX]
    other_rows = [r for r in rows if r[0] != AT_BANK_TXN_TYPE_IDX]
    if mode == "statement_first":
        return other_rows, bank_rows
    if mode == "manual_first":
        return bank_rows + other_rows, []
    return rows, []


def at_show_statement_callout(workflow_mode: str) -> bool:
    mode = banking_normalize_workflow_mode(workflow_mode)
    return mode in ("statement_first", "manual_first")


def at_show_manual_bank_advanced(workflow_mode: str, current_type_idx: int) -> bool:
    return (
        banking_normalize_workflow_mode(workflow_mode) == "statement_first"
        and current_type_idx != AT_BANK_TXN_TYPE_IDX
    )


def at_apply_add_transaction_landing(workflow_mode: str) -> None:
    """One-shot default type for manual-first (UI landing only)."""
    if st.session_state.get("at_workflow_landing_applied"):
        return
    if banking_normalize_workflow_mode(workflow_mode) == "manual_first":
        st.session_state["at_type_idx"] = AT_BANK_TXN_TYPE_IDX
        st.session_state["mob_at_tab"] = 3
        st.session_state["mob_at_more_idx"] = AT_BANK_TXN_TYPE_IDX
    st.session_state["at_workflow_landing_applied"] = True


def at_navigate_banking_statement_import() -> None:
    from ui.banking import banking_navigate_statement_import_upload

    st.session_state["nav_selection"] = NAV_BANKING
    st.session_state.pop("banking_landing_applied", None)
    banking_navigate_statement_import_upload()


def at_render_statement_workflow_callout(
    *,
    workflow_mode: str,
    show_import_link: bool,
) -> None:
    """Statement-first / manual-first callout on Add Transaction — presentation only."""
    erp = _erp()
    mode = banking_normalize_workflow_mode(workflow_mode)
    if not at_show_statement_callout(mode):
        return
    if mode == "statement_first":
        st.info(erp._t("txn.bank_workflow.statement_callout"))
    else:
        st.caption(erp._t("txn.bank_workflow.statement_alt"))
    if show_import_link:
        if st.button(
            erp._t("txn.bank_workflow.open_statement_import"),
            key="at_open_statement_import",
            use_container_width=True,
            type="secondary",
        ):
            at_navigate_banking_statement_import()


def at_render_manual_bank_advanced_gate() -> None:
    """Statement-first: manual bank transaction type under Advanced."""
    erp = _erp()
    with st.expander(erp._t("bank.advanced.section"), expanded=False):
        st.caption(erp._t("txn.bank_workflow.manual_advanced_caption"))
        if st.button(
            erp._t("txn.bank_workflow.open_manual_bank"),
            key="at_adv_open_manual_bank",
            use_container_width=True,
        ):
            st.session_state["at_type_idx"] = AT_BANK_TXN_TYPE_IDX
            st.session_state["mob_at_tab"] = 3
            st.session_state["mob_at_more_idx"] = AT_BANK_TXN_TYPE_IDX
            st.rerun()
