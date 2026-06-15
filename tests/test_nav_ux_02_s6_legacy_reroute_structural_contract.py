"""NAV-UX-02-S6-IMPL-1 — legacy nav reroute validity + telemetry contract."""

from __future__ import annotations

import inspect
import logging

import app as erp
from registry.nav_keys import (
    ALL_NAV_PAGE_KEYS,
    LEGACY_NAV_ALIASES,
    NAV_BANKING,
    NAV_HOME,
    NAV_REPORTS,
    NAV_TODAY_SUMMARY,
    normalize_nav_key,
)
from tests.nav_ux_02_contract import page_dispatch_from_main

_VALID_REPORTS_EXEC = frozenset({"today_summary", "txn_ledger"})


def test_all_legacy_nav_alias_targets_in_all_nav_page_keys():
    missing = {
        alias: target
        for alias, target in LEGACY_NAV_ALIASES.items()
        if target not in ALL_NAV_PAGE_KEYS
    }
    assert not missing, f"LEGACY_NAV_ALIASES targets missing from ALL_NAV_PAGE_KEYS: {missing}"


def test_legacy_reroute_targets_in_page_dispatch():
    dispatch = set(page_dispatch_from_main())
    for target in erp._LEGACY_RPT_EXEC_TO_STATEMENT.values():
        assert target in dispatch
    for target in erp._LEGACY_RPT_EXEC_TO_BOOKS.values():
        assert target in dispatch
    assert NAV_REPORTS in dispatch
    assert NAV_BANKING in dispatch


def test_legacy_reports_exec_values_are_valid_exec_options():
    values = set(erp._LEGACY_NAV_TO_REPORTS_EXEC.values())
    assert values <= _VALID_REPORTS_EXEC
    assert "today_summary" in values


def test_today_summary_still_reroutes_to_reports_exec():
    assert NAV_TODAY_SUMMARY in erp._LEGACY_NAV_TO_REPORTS_EXEC
    assert erp._LEGACY_NAV_TO_REPORTS_EXEC[NAV_TODAY_SUMMARY] == "today_summary"
    assert normalize_nav_key("Today's Summary") == NAV_REPORTS
    assert normalize_nav_key("📅 Today's Summary") == NAV_REPORTS
    main_src = inspect.getsource(erp.main)
    assert "_LEGACY_NAV_TO_REPORTS_EXEC" in main_src
    assert 'st.session_state["rpt_exec_sel"]' in main_src


def test_bank_statement_import_reroute_preserves_import_section():
    main_src = inspect.getsource(erp.main)
    assert '"Bank Statement Import"' in main_src
    assert 'st.session_state["banking_section"] = "import"' in main_src
    assert LEGACY_NAV_ALIASES["Bank Statement Import"] == NAV_BANKING
    assert LEGACY_NAV_ALIASES["📥 Bank Statement Import"] == NAV_BANKING


def test_unknown_nav_falls_back_to_home_guard():
    main_src = inspect.getsource(erp.main)
    assert "normalize_nav_key(_raw_nav)" in main_src
    assert "if selection not in _allowed" in main_src
    assert 'st.session_state["nav_selection"] = NAV_HOME' in main_src
    assert normalize_nav_key("Totally Unknown Legacy Page") == "Totally Unknown Legacy Page"


def test_normalize_nav_key_idempotent():
    for raw in ("💼 Sales", "Bank Statement Import", NAV_HOME):
        once = normalize_nav_key(raw)
        twice = normalize_nav_key(once)
        assert twice == once
    assert normalize_nav_key("Sales") == "Sales"


def test_legacy_rpt_exec_maps_are_idempotent_after_pop():
    """Reroute branches pop rpt_exec_sel so a second pass cannot re-fire."""
    main_src = inspect.getsource(erp.main)
    assert 'st.session_state.pop("rpt_exec_sel", None)' in main_src


def test_nav_legacy_logger_configured():
    assert erp._NAV_LEGACY_LOGGER.name == "nav.legacy"
    main_src = inspect.getsource(erp.main)
    assert "_log_legacy_nav_hit" in main_src
    for kind in (
        "reports_exec",
        "alias_normalize",
        "bank_statement_import",
        "rpt_exec_statement",
        "rpt_exec_books",
    ):
        assert f'"{kind}"' in main_src or f"'{kind}'" in main_src


def test_legacy_log_emits_on_hit(caplog):
    with caplog.at_level(logging.INFO, logger="nav.legacy"):
        erp._log_legacy_nav_hit(
            "alias_normalize",
            raw_key="💼 Sales",
            canonical_key="Sales",
        )
    assert len(caplog.records) == 1
    assert caplog.records[0].name == "nav.legacy"
    assert "legacy_nav_hit kind=alias_normalize" in caplog.records[0].message
    assert "raw_key='💼 Sales'" in caplog.records[0].message


def test_legacy_log_silent_without_legacy_hit(caplog):
    """Canonical keys that need no substitution must not emit nav.legacy lines from helpers."""
    with caplog.at_level(logging.INFO, logger="nav.legacy"):
        caplog.clear()
        # Simulate no-op path: caller only logs when substitution occurs (main guard).
        assert normalize_nav_key("Sales") == "Sales"
    assert [r for r in caplog.records if r.name == "nav.legacy"] == []


def test_legacy_log_each_kind(caplog):
    cases = (
        ("reports_exec", {"raw_key": NAV_TODAY_SUMMARY, "exec_sel": "today_summary", "target": NAV_REPORTS}),
        ("alias_normalize", {"raw_key": "🏦 Banking", "canonical_key": NAV_BANKING}),
        ("bank_statement_import", {"raw_key": "Bank Statement Import", "target": NAV_BANKING, "banking_section": "import"}),
        ("rpt_exec_statement", {"rpt_exec_sel": "pnl", "target": erp.NAV_PROFIT_LOSS}),
        ("rpt_exec_books", {"rpt_exec_sel": "budget", "target": "Budget"}),
    )
    for kind, fields in cases:
        with caplog.at_level(logging.INFO, logger="nav.legacy"):
            caplog.clear()
            erp._log_legacy_nav_hit(kind, **fields)
        assert len(caplog.records) == 1
        assert f"legacy_nav_hit kind={kind}" in caplog.records[0].message
