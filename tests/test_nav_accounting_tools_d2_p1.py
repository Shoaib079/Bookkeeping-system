"""AD-UI-001 D2-P1 — Accounting Tools tab rename and Books dedup."""

from __future__ import annotations

import inspect

import app as erp
from registry.i18n import t
from registry.nav_keys import NAV_GENERAL_LEDGER

_BOOKS_PAGES = (
    "Budget",
    "Trial Balance",
    NAV_GENERAL_LEDGER,
)
_REMOVED_PICKER_IDS = frozenset({"budget", "trial_balance", "general_ledger"})
_REMAINING_PICKER_IDS = frozenset({"txn_ledger", "today_summary"})


def _exec_picker_ids() -> set[str]:
    from tests.test_nav_statements_d1 import _exec_picker_ids_from_source

    return _exec_picker_ids_from_source()


def test_reports_tab_label_accounting_tools():
    assert t("reports.tab.exec", "en") == "Accounting Tools"
    assert t("reports.tab.exec", "tr") == "Muhasebe Araçları"
    assert "Executive" not in t("reports.tab.exec", "en")
    assert "Yönetici" not in t("reports.tab.exec", "tr")


def test_accounting_tools_picker_excludes_books_dupes():
    ids = _exec_picker_ids()
    assert ids == _REMAINING_PICKER_IDS
    assert not ids & _REMOVED_PICKER_IDS


def test_books_pages_still_in_sidebar_accordion():
    accounting_pages = [key for _lbl, key in erp._NAV_ACCORDION_BY_KEY["accounting"][1]]
    for page in _BOOKS_PAGES:
        assert page in accounting_pages


def test_legacy_rpt_exec_sel_redirects_to_books():
    assert set(erp._LEGACY_RPT_EXEC_TO_BOOKS.keys()) == _REMOVED_PICKER_IDS
    assert erp._LEGACY_RPT_EXEC_TO_BOOKS["trial_balance"] == "Trial Balance"
    assert erp._LEGACY_RPT_EXEC_TO_BOOKS["general_ledger"] == NAV_GENERAL_LEDGER
    assert erp._LEGACY_RPT_EXEC_TO_BOOKS["budget"] == "Budget"
    main_src = inspect.getsource(erp.main)
    assert "_LEGACY_RPT_EXEC_TO_BOOKS" in main_src
    assert "elif _legacy_exec in _LEGACY_RPT_EXEC_TO_BOOKS:" in main_src


def test_accounting_tools_still_has_ledger_and_today():
    src = inspect.getsource(erp.render_reports)
    assert '("txn_ledger", "reports.exec.txn_ledger")' in src
    assert '("today_summary", "reports.exec.today_summary")' in src
    assert "render_transaction_history(session)" in src
    assert "render_today_summary(session)" in src


def test_no_budget_tb_gl_render_branches_in_accounting_tools():
    src = inspect.getsource(erp.render_reports)
    assert 'if exec_sel == "budget"' not in src
    assert 'elif exec_sel == "trial_balance"' not in src
    assert 'elif exec_sel == "general_ledger"' not in src
