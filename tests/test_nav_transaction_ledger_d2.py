"""AD-UI-001 D2-P0 — Transaction Ledger navigation promotion."""

from __future__ import annotations

import ast
import inspect
from unittest.mock import MagicMock

import app as erp
from registry.i18n import nav_display, t
from registry.nav_keys import NAV_NEW_TRANSACTION, NAV_TXN_LEDGER
from registry.navigation import dispatch_render_spec
from tests.nav_ux_02_contract import page_dispatch_from_main
_TXN_LEDGER_KEY = NAV_TXN_LEDGER


def test_sidebar_contains_transaction_ledger_after_new_transaction():
    from registry.sidebar_layout import flatten_sidebar_layout_keys

    keys = flatten_sidebar_layout_keys()
    direct = [k for kind, k in keys if kind == "direct"]
    new_idx = direct.index(NAV_NEW_TRANSACTION)
    ledger_idx = direct.index(_TXN_LEDGER_KEY)
    assert new_idx < ledger_idx
    work_pos = keys.index(("section", "nav.sidebar.section_work"))
    ledger_flat = keys.index(("direct", _TXN_LEDGER_KEY))
    assert ledger_flat < work_pos


def test_transaction_ledger_route_dispatches_to_wrapper():
    dispatch = page_dispatch_from_main()
    assert dispatch[_TXN_LEDGER_KEY] == "render_transaction_ledger_page"
    assert erp._TXN_LEDGER_PAGE_KEY == _TXN_LEDGER_KEY
    assert _TXN_LEDGER_KEY in erp._NAV_DIRECT_PAGES


def test_wrapper_calls_existing_renderer(monkeypatch):
    session = MagicMock()
    calls: list[object] = []

    def _capture(sess):
        calls.append(sess)

    monkeypatch.setattr(erp, "render_transaction_history", _capture)
    erp.render_transaction_ledger_page(session)
    assert calls == [session]


def test_home_view_all_transactions_deep_link():
    src = inspect.getsource(erp.render_dashboard)
    assert 'key="dash_view_all_txn"' in src
    assert 'st.session_state["nav_selection"] = _TXN_LEDGER_PAGE_KEY' in src
    assert "_t(\"dash.view_all_transactions\")" in src


def test_executive_legacy_path_still_renders_ledger():
    src = inspect.getsource(erp.render_reports)
    assert '("txn_ledger", "reports.exec.txn_ledger")' in src
    assert 'exec_sel == "txn_ledger"' in src
    assert "render_transaction_history(session)" in src
    assert "D2-P0 legacy path" in src
    assert "D2-P2+" in src


def test_no_duplicate_page_dispatch_keys():
    spec = dispatch_render_spec()
    ledger_handlers = [h for h in spec.values() if h == "render_transaction_ledger_page"]
    assert len(ledger_handlers) == 1
    assert spec[_TXN_LEDGER_KEY] == "render_transaction_ledger_page"


def test_mobile_hubs_include_transaction_ledger_in_reports_only():
    reports = erp._MOBILE_HUB_CONFIG["reports"]
    more = erp._MOBILE_HUB_CONFIG["more"]
    assert ("page", _TXN_LEDGER_KEY, None, None) in reports
    more_pages = {p for k, p, *_ in more if k == "page"}
    assert _TXN_LEDGER_KEY not in more_pages
    allowed = {"Home", "Reports", _TXN_LEDGER_KEY, "My Account"}
    accordion = dict(erp._NAV_ACCORDION_BY_KEY)
    assert erp._mobile_hub_entry_visible("reports", "page", _TXN_LEDGER_KEY, allowed, accordion)


def test_transaction_ledger_label_consistent():
    assert nav_display(_TXN_LEDGER_KEY, "en") == "Transaction Ledger"
    assert nav_display(_TXN_LEDGER_KEY, "tr") == "İşlem Defteri"
    assert t("txn.page_banner", "en") == "Transaction Ledger"
    assert t("reports.exec.txn_ledger", "en") == "Transaction Ledger"
    assert t("dash.view_all_transactions", "en") == "View All Transactions"


def test_role_visibility_matches_reports_access():
    manager = set(erp._NAV_ROLE_PAGES["manager"])
    viewer = set(erp._NAV_ROLE_PAGES["viewer"])
    assert _TXN_LEDGER_KEY in manager
    assert _TXN_LEDGER_KEY in viewer
    assert "Reports" in manager
    assert "Reports" in viewer
