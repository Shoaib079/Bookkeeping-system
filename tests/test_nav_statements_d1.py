"""AD-UI-001 D1 — Financial Statements navigation contract tests."""
from __future__ import annotations

import ast
import inspect
from unittest.mock import MagicMock

import pytest

import app as erp
from registry.i18n import t
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR


from registry.nav_keys import NAV_BALANCE_SHEET, NAV_CASH_FLOW, NAV_PROFIT_LOSS, NAV_REPORTS
from tests.nav_ux_02_contract import page_dispatch_from_main

_STATEMENT_KEYS = (
    NAV_PROFIT_LOSS,
    NAV_BALANCE_SHEET,
    NAV_CASH_FLOW,
)

_EXEC_REMOVED = frozenset({"pnl", "balance_sheet", "cash_flow"})
_EXEC_REMAINING = frozenset({
    "txn_ledger",
    "today_summary",
})
_EXEC_REMOVED_BOOKS = frozenset({"budget", "trial_balance", "general_ledger"})


def _exec_picker_ids_from_source() -> set[str]:
    """Parse rpt_exec_sel option ids from render_reports (no Streamlit run)."""
    source = inspect.getsource(erp.render_reports)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (
            isinstance(func, ast.Name)
            and func.id == "_mgmt_report_select"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "rpt_exec_sel"
        ):
            continue
        options = node.args[1]
        if not isinstance(options, ast.List):
            continue
        return {
            elt.elts[0].value
            for elt in options.elts
            if isinstance(elt, ast.Tuple)
            and len(elt.elts) >= 1
            and isinstance(elt.elts[0], ast.Constant)
        }
    raise AssertionError("Could not find _mgmt_report_select('rpt_exec_sel', ...) in render_reports")


def test_statement_routes_exist_in_page_dispatch():
    dispatch = page_dispatch_from_main()
    for key in _STATEMENT_KEYS:
        assert key in dispatch


def test_statement_pages_dispatch_to_wrappers():
    dispatch = page_dispatch_from_main()
    assert dispatch[NAV_PROFIT_LOSS] == "render_profit_loss_page"
    assert dispatch[NAV_BALANCE_SHEET] == "render_balance_sheet_page"
    assert dispatch[NAV_CASH_FLOW] == "render_cash_flow_page"


def test_accounting_tools_picker_excludes_statements_and_books_dupes():
    ids = _exec_picker_ids_from_source()
    assert ids == _EXEC_REMAINING
    assert not ids & _EXEC_REMOVED
    assert not ids & _EXEC_REMOVED_BOOKS


def test_mobile_reports_hub_contains_statement_entries():
    reports = erp._MOBILE_HUB_CONFIG["reports"]
    kinds_pages = [(k, p) for k, p, *_ in reports if k == "page"]
    for key in _STATEMENT_KEYS:
        assert ("page", key) in kinds_pages
    exec_rows = [p for k, p, *_ in reports if k == "report_exec"]
    assert exec_rows == []


def test_mobile_more_hub_excludes_statements_section():
    more = erp._MOBILE_HUB_CONFIG["more"]
    assert ("section", "statements", None, "nav.mobile.section.statements") not in more
    assert ("accordion", "statements", None, None) not in more


def test_nav_group_statements_i18n_not_raw_key():
    """Sidebar/mobile statements labels resolve from transactional catalog."""
    assert TRANSACTIONAL_EN["nav.group.statements"] == "Financial Statements"
    assert TRANSACTIONAL_TR["nav.group.statements"] == "Finansal Tablolar"
    assert t("nav.group.statements", "en") == "Financial Statements"
    assert t("nav.group.statements", "tr") == "Finansal Tablolar"
    assert t("nav.mobile.section.statements", "en") == "Financial Statements"
    assert t("nav.mobile.section.statements", "tr") == "Finansal Tablolar"
    for _gkey, msg_key in erp._NAV_GROUP_KEYS.items():
        assert t(msg_key, "en") != msg_key
        assert t(msg_key, "tr") != msg_key


def test_mobile_statement_entries_in_reports_not_more():
    allowed = {
        "Home",
        NAV_REPORTS,
        NAV_PROFIT_LOSS,
        NAV_BALANCE_SHEET,
        NAV_CASH_FLOW,
        "My Account",
    }
    accordion = {k: v for k, v in erp._NAV_ACCORDION_BY_KEY.items()}
    reports_pages = {p for k, p, *_ in erp._MOBILE_HUB_CONFIG["reports"] if k == "page"}
    for key in _STATEMENT_KEYS:
        assert key in reports_pages
    more_accordions = {p for k, p, *_ in erp._MOBILE_HUB_CONFIG["more"] if k == "accordion"}
    assert "statements" not in more_accordions


def test_date_filter_pages_include_statements():
    assert erp._DATE_FILTER_PAGE_KEYS == frozenset({NAV_REPORTS}) | erp._STATEMENT_PAGE_KEYS
    for key in _STATEMENT_KEYS:
        assert key in erp._DATE_FILTER_PAGE_KEYS


def test_role_visibility_matches_reports_access():
    for role, pages in erp._NAV_ROLE_PAGES.items():
        if role == "owner":
            continue
        has_reports = NAV_REPORTS in pages
        for key in _STATEMENT_KEYS:
            assert (key in pages) == has_reports, f"{role}: {key} vs Reports mismatch"


def test_pre_d2_cleanup_no_orphan_nav_renderers():
    assert not hasattr(erp, "render_advanced")
    assert not hasattr(erp, "render_customer_ledger")
    assert not hasattr(erp, "render_settings")


def test_pre_d2_cleanup_no_report_exec_in_hub_config_or_source():
    for hub_rows in erp._MOBILE_HUB_CONFIG.values():
        assert not any(k == "report_exec" for k, *_ in hub_rows)
    source = inspect.getsource(erp._render_mobile_hub_sheet)
    assert "report_exec" not in source
    vis_source = inspect.getsource(erp._mobile_hub_entry_visible)
    assert "report_exec" not in vis_source


def test_legacy_exec_sel_redirect_map():
    assert set(erp._LEGACY_RPT_EXEC_TO_STATEMENT.keys()) == _EXEC_REMOVED
    assert set(erp._LEGACY_RPT_EXEC_TO_STATEMENT.values()) == set(_STATEMENT_KEYS)


def test_desktop_nav_statements_group_before_reports():
    from registry.sidebar_layout import flatten_sidebar_layout_keys

    keys = flatten_sidebar_layout_keys()
    stmt_pos = keys.index(("accordion", "statements"))
    reports_pos = keys.index(("direct", NAV_REPORTS))
    assert stmt_pos < reports_pos


def test_wrapper_pages_call_existing_renderers(monkeypatch):
    """Thin wrappers wire session dates into unchanged render functions."""
    session = MagicMock()
    calls: dict[str, object] = {}

    def _capture_pnl(sess, *, start_date=None, end_date=None):
        calls["pnl"] = (start_date, end_date)

    def _capture_bs(sess, *, end_date=None):
        calls["bs"] = end_date

    def _capture_cf(sess, *, start_date=None, end_date=None):
        calls["cf"] = (start_date, end_date)

    monkeypatch.setattr(erp, "render_mobile_report_filters", lambda: None)
    monkeypatch.setattr(
        erp.st,
        "session_state",
        {
            "date_from": erp.datetime.date(2026, 1, 1),
            "date_to": erp.datetime.date(2026, 6, 5),
        },
    )
    monkeypatch.setattr(erp, "render_profit_loss", _capture_pnl)
    monkeypatch.setattr(erp, "render_balance_sheet", _capture_bs)
    monkeypatch.setattr(erp, "render_cash_flow", _capture_cf)

    erp.render_profit_loss_page(session)
    erp.render_balance_sheet_page(session)
    erp.render_cash_flow_page(session)

    assert calls["pnl"] == (erp.datetime.date(2026, 1, 1), erp.datetime.date(2026, 6, 5))
    assert calls["bs"] == erp.datetime.date(2026, 6, 5)
    assert calls["cf"] == (erp.datetime.date(2026, 1, 1), erp.datetime.date(2026, 6, 5))
