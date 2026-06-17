"""MOBILE-UX-01-A — mobile navigation cleanup contract."""
from __future__ import annotations

import inspect
from pathlib import Path

import app as erp
from registry.nav_keys import (
    NAV_BALANCE_SHEET,
    NAV_CASH_FLOW,
    NAV_PROFIT_LOSS,
    NAV_RECON_HEALTH,
    NAV_REPORTS,
    NAV_TXN_LEDGER,
)

_STATEMENT_KEYS = (NAV_PROFIT_LOSS, NAV_BALANCE_SHEET, NAV_CASH_FLOW)
_ROOT = Path(__file__).resolve().parents[1]


def test_mobile_main_skips_desktop_sidebar():
    src = (_ROOT / "app.py").read_text(encoding="utf-8")
    assert "if not _is_mobile_ui():" in src
    block = src.split("if not _is_mobile_ui():", 1)[1]
    assert "_render_navigation_tree(" in block
    assert "render_sidebar_filters()" in block


def test_reports_hub_contains_financial_statements():
    reports_pages = [p for k, p, *_ in erp._MOBILE_HUB_CONFIG["reports"] if k == "page"]
    for key in _STATEMENT_KEYS:
        assert key in reports_pages
    assert NAV_TXN_LEDGER in reports_pages


def test_more_hub_does_not_duplicate_financial_statements():
    more = erp._MOBILE_HUB_CONFIG["more"]
    more_pages = {p for k, p, *_ in more if k == "page"}
    more_accordions = {p for k, p, *_ in more if k == "accordion"}
    for key in _STATEMENT_KEYS:
        assert key not in more_pages
    assert "statements" not in more_accordions


def test_more_hub_does_not_duplicate_transaction_ledger():
    more_pages = {p for k, p, *_ in erp._MOBILE_HUB_CONFIG["more"] if k == "page"}
    assert NAV_TXN_LEDGER not in more_pages


def test_recon_health_in_money_hub_not_more_books():
    money_pages = {p for k, p, *_ in erp._MOBILE_HUB_CONFIG["money"] if k == "page"}
    assert NAV_RECON_HEALTH in money_pages
    assert NAV_RECON_HEALTH in erp._MOBILE_MORE_ACCORDION_EXCLUDE["accounting"]
    more_accordions = {p for k, p, *_ in erp._MOBILE_HUB_CONFIG["more"] if k == "accordion"}
    assert "accounting" in more_accordions


def test_money_hub_groups_close_and_bank_sections():
    money = erp._MOBILE_HUB_CONFIG["money"]
    sections = [(p, lk) for k, p, _, lk in money if k == "section"]
    assert ("close", "nav.mobile.section.close") in sections
    assert ("bank", "nav.mobile.section.bank") in sections


def test_bottom_nav_uses_money_hub_not_banking():
    hub_keys = {p for k, p, *_ in erp._MOBILE_BOTTOM_NAV if k == "hub"}
    assert "money" in hub_keys
    assert "banking" not in hub_keys
    money_row = next(r for r in erp._MOBILE_BOTTOM_NAV if r[1] == "money")
    assert money_row[2] == "nav.bottom.money"


def test_legacy_banking_hub_key_resolves_to_money():
    assert erp._mobile_resolve_hub_key("banking") == "money"
    assert erp._mobile_resolve_hub_key("money") == "money"


def test_desktop_sidebar_nav_unchanged():
    from registry.nav_keys import NAV_REPORTS, NAV_RECON_HEALTH
    from registry.sidebar_layout import flatten_sidebar_layout_keys

    keys = flatten_sidebar_layout_keys()
    assert ("accordion", "statements") in keys
    assert ("accordion", "accounting") in keys
    assert ("direct", NAV_REPORTS) in keys
    main_src = (_ROOT / "app.py").read_text(encoding="utf-8")
    assert "NAV_RECON_HEALTH" in main_src
    accounting_pages = [k for _, k in erp._NAV_ACCORDION_BY_KEY["accounting"][1]]
    assert NAV_RECON_HEALTH in accounting_pages
    src = inspect.getsource(erp._render_navigation_tree)
    assert "SIDEBAR_LAYOUT" in src
