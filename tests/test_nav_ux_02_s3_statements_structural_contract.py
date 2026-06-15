"""NAV-UX-02-S3-IMPL-1 — financial statements canonical routes + shortcut doors contract."""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import app as erp
from registry.nav_keys import (
    ALL_NAV_PAGE_KEYS,
    NAV_BALANCE_SHEET,
    NAV_CASH_FLOW,
    NAV_PROFIT_LOSS,
)
from tests.nav_ux_02_contract import (
    STATEMENT_CANONICAL_KEYS,
    STATEMENT_DESKTOP_CANONICAL_GROUP,
    STATEMENT_REACT_ROUTES,
    accordion_page_keys,
    page_dispatch_from_main,
)

_ALL_ROLES = ("owner", "manager", "cashier", "partner", "viewer")
_STATEMENT_WRAPPER_CORE = (
    ("render_profit_loss_page", "render_profit_loss"),
    ("render_balance_sheet_page", "render_balance_sheet"),
    ("render_cash_flow_page", "render_cash_flow"),
)
_REPORTS_TAB_IDS = frozenset(
    {"exec", "sales", "expenses", "customers", "vendors", "banking", "eod"}
)
_FORBIDDEN_STATEMENT_TAB_IDS = frozenset(
    {"pnl", "profit_loss", "balance_sheet", "cash_flow", "profit-loss", "balance-sheet", "cash-flow"}
)
_LEGACY_EXEC_STATEMENT_IDS = frozenset({"pnl", "balance_sheet", "cash_flow"})


def test_statement_canonical_keys_match_statement_page_keys():
    assert STATEMENT_CANONICAL_KEYS == erp._STATEMENT_PAGE_KEYS


def test_statement_routes_in_page_dispatch():
    dispatch = page_dispatch_from_main()
    for key in STATEMENT_CANONICAL_KEYS:
        assert key in dispatch


def test_statement_routes_in_all_nav_page_keys():
    for key in STATEMENT_CANONICAL_KEYS:
        assert key in ALL_NAV_PAGE_KEYS


def test_statement_routes_visible_to_all_roles():
    for role in _ALL_ROLES:
        pages = erp._NAV_ROLE_PAGES[role]
        for key in STATEMENT_CANONICAL_KEYS:
            assert key in pages, f"{key!r} missing from role {role!r}"


def test_statement_desktop_accordion_is_canonical_home():
    stmt_pages = {
        page_key
        for group_key, page_key in accordion_page_keys()
        if group_key == STATEMENT_DESKTOP_CANONICAL_GROUP
    }
    assert stmt_pages == STATEMENT_CANONICAL_KEYS


def test_statement_page_wrappers_dispatch_to_wrappers():
    dispatch = page_dispatch_from_main()
    assert dispatch[NAV_PROFIT_LOSS] == "render_profit_loss_page"
    assert dispatch[NAV_BALANCE_SHEET] == "render_balance_sheet_page"
    assert dispatch[NAV_CASH_FLOW] == "render_cash_flow_page"


def test_statement_page_wrappers_delegate_to_core_renderers_source():
    for wrapper_name, core_name in _STATEMENT_WRAPPER_CORE:
        src = inspect.getsource(getattr(erp, wrapper_name))
        assert f"{core_name}(" in src, f"{wrapper_name} must call {core_name}"


def test_statement_page_wrappers_delegate_to_core_renderers_runtime(monkeypatch):
    """Thin wrappers wire session dates into unchanged core render functions."""
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


def test_reports_mobile_tab_ids_exclude_statements():
    tab_ids = {tab_id for tab_id, _msg in erp._REPORTS_MOB_TAB_IDS}
    assert tab_ids == _REPORTS_TAB_IDS
    assert not tab_ids & _FORBIDDEN_STATEMENT_TAB_IDS


def test_render_reports_does_not_render_statements():
    src = inspect.getsource(erp.render_reports)
    for forbidden in (
        "render_profit_loss(",
        "render_balance_sheet(",
        "render_cash_flow(",
        "render_profit_loss_page(",
        "render_balance_sheet_page(",
        "render_cash_flow_page(",
    ):
        assert forbidden not in src, f"Reports page must not call {forbidden}"


def test_mobile_reports_hub_statement_entries_target_canonical_routes():
    dispatch = set(page_dispatch_from_main())
    reports_pages = [
        payload
        for kind, payload, *_rest in erp._MOBILE_HUB_CONFIG["reports"]
        if kind == "page"
    ]
    for key in STATEMENT_CANONICAL_KEYS:
        assert key in reports_pages
        assert key in dispatch


def test_legacy_rpt_exec_to_statement_targets_canonical_routes():
    dispatch = set(page_dispatch_from_main())
    assert set(erp._LEGACY_RPT_EXEC_TO_STATEMENT.keys()) == _LEGACY_EXEC_STATEMENT_IDS
    assert set(erp._LEGACY_RPT_EXEC_TO_STATEMENT.values()) == STATEMENT_CANONICAL_KEYS
    for target in erp._LEGACY_RPT_EXEC_TO_STATEMENT.values():
        assert target in dispatch


def test_statement_react_route_contract_1to1():
    assert set(STATEMENT_REACT_ROUTES.keys()) == STATEMENT_CANONICAL_KEYS
    paths = set(STATEMENT_REACT_ROUTES.values())
    assert len(paths) == len(STATEMENT_CANONICAL_KEYS)
    assert STATEMENT_REACT_ROUTES[NAV_PROFIT_LOSS] == "/reports/profit-loss"
    assert STATEMENT_REACT_ROUTES[NAV_BALANCE_SHEET] == "/reports/balance-sheet"
    assert STATEMENT_REACT_ROUTES[NAV_CASH_FLOW] == "/reports/cash-flow"
