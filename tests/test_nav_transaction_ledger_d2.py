"""AD-UI-001 D2-P0 — Transaction Ledger navigation promotion."""

from __future__ import annotations

import ast
import inspect
from unittest.mock import MagicMock

import app as erp
from registry.i18n import nav_display, t

_TXN_LEDGER_KEY = "📒 Transaction Ledger"


def _page_dispatch_from_main() -> dict[str, str]:
    source = inspect.getsource(erp.main)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_PAGE_DISPATCH":
                if not isinstance(node.value, ast.Dict):
                    continue
                out: dict[str, str] = {}
                for k, v in zip(node.value.keys, node.value.values):
                    if isinstance(k, ast.Constant) and isinstance(v, ast.Name):
                        out[k.value] = v.id
                return out
    raise AssertionError("Could not find _PAGE_DISPATCH in main()")


def test_sidebar_contains_transaction_ledger_after_new_transaction():
    src = inspect.getsource(erp._render_navigation_tree)
    new_pos = src.index('_nav_direct("➕ New Transaction")')
    ledger_pos = src.index("_nav_direct(_TXN_LEDGER_PAGE_KEY)")
    work_pos = src.index('_nav_section_caption("nav.sidebar.section_work")')
    assert new_pos < ledger_pos < work_pos


def test_transaction_ledger_route_dispatches_to_wrapper():
    main_src = inspect.getsource(erp.main)
    assert "_TXN_LEDGER_PAGE_KEY:  render_transaction_ledger_page" in main_src
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
    main_src = inspect.getsource(erp.main)
    assert main_src.count("render_transaction_ledger_page") == 1
    assert main_src.count("_TXN_LEDGER_PAGE_KEY:") == 1


def test_mobile_hubs_include_transaction_ledger():
    reports = erp._MOBILE_HUB_CONFIG["reports"]
    more = erp._MOBILE_HUB_CONFIG["more"]
    assert ("page", _TXN_LEDGER_KEY, None, None) in reports
    assert ("page", _TXN_LEDGER_KEY, None, None) in more
    allowed = {"🏠 Home", "📊 Reports", _TXN_LEDGER_KEY, "👤 My Account"}
    accordion = dict(erp._NAV_ACCORDION_BY_KEY)
    assert erp._mobile_hub_entry_visible("reports", "page", _TXN_LEDGER_KEY, allowed, accordion)


def test_transaction_ledger_label_consistent():
    assert nav_display(_TXN_LEDGER_KEY, "en") == "📒 Transaction Ledger"
    assert nav_display(_TXN_LEDGER_KEY, "tr") == "📒 İşlem Defteri"
    assert t("txn.page_banner", "en") == "Transaction Ledger"
    assert t("reports.exec.txn_ledger", "en") == "Transaction Ledger"
    assert t("dash.view_all_transactions", "en") == "View All Transactions"


def test_role_visibility_matches_reports_access():
    for role, pages in erp._NAV_ROLE_PAGES.items():
        if role == "owner":
            assert _TXN_LEDGER_KEY in pages
            continue
        has_reports = "📊 Reports" in pages
        assert (_TXN_LEDGER_KEY in pages) == has_reports, f"{role}: ledger vs Reports mismatch"
