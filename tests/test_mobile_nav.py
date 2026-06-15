"""Mobile hub config — visibility helpers (no Streamlit runtime)."""
from __future__ import annotations

import inspect

import pytest

# Import after pytest collection path is set (project root)
import app as erp
from registry.nav_keys import (
    NAV_BALANCE_SHEET,
    NAV_CASH_FLOW,
    NAV_GENERAL_LEDGER,
    NAV_PROFIT_LOSS,
    NAV_RECON_HEALTH,
    NAV_RECURRING_EXPENSES,
    NAV_TXN_LEDGER,
)

_ACCORDION_BY_KEY = {
    "transactions": ("Record transactions", [
        (None, "Sales"),
        (None, "Expenses"),
    ]),
    "people": ("Customers & suppliers", [
        (None, "Customers"),
        (None, "Vendors"),
    ]),
    "statements": ("Financial Statements", [
        (None, NAV_PROFIT_LOSS),
        (None, NAV_BALANCE_SHEET),
        (None, NAV_CASH_FLOW),
    ]),
    "accounting": ("Books", [
        (None, NAV_GENERAL_LEDGER),
        (None, NAV_RECON_HEALTH),
        (None, "Budget"),
    ]),
}


def test_viewer_only_reports_hub_has_entries():
    allowed = {
        "Home",
        "Reports",
        NAV_PROFIT_LOSS,
        NAV_BALANCE_SHEET,
        NAV_CASH_FLOW,
        "My Account",
    }
    assert erp._mobile_hub_has_entries("reports", allowed, _ACCORDION_BY_KEY)
    assert not erp._mobile_hub_has_entries("money", allowed, _ACCORDION_BY_KEY)
    # Viewer reaches statements via Reports hub; More has no visible entries for this role set.
    assert not erp._mobile_hub_has_entries("more", allowed, _ACCORDION_BY_KEY)
    assert erp._mobile_hub_entry_visible(
        "more", "accordion", "accounting", allowed, _ACCORDION_BY_KEY
    ) is False


def test_owner_all_hubs_have_entries():
    allowed = {
        "Home",
        "New Transaction",
        "Banking",
        "Reports",
        "Customers",
        "Sales",
        NAV_GENERAL_LEDGER,
        NAV_RECON_HEALTH,
        "Inventory",
        "Company Settings",
    }
    for hub in ("money", "reports", "more"):
        assert erp._mobile_hub_has_entries(hub, allowed, _ACCORDION_BY_KEY)


def test_module_hidden_inventory_removed_from_more():
    allowed = {
        "Home",
        "Sales",
        NAV_GENERAL_LEDGER,
        "Company Settings",
    }
    assert erp._mobile_hub_entry_visible(
        "more", "page", "Inventory", allowed, _ACCORDION_BY_KEY
    ) is False
    assert erp._mobile_hub_entry_visible(
        "more", "accordion", "transactions", allowed, _ACCORDION_BY_KEY
    )


def test_sales_only_in_more_transactions_not_bottom_direct():
    bottom_pages = {payload for kind, payload, _, _, _, _ in erp._MOBILE_BOTTOM_NAV if kind in ("home", "new")}
    assert "Sales" not in bottom_pages
    more_pages = [
        p for k, p, _, _ in erp._MOBILE_HUB_CONFIG["more"] if k == "accordion" and p == "transactions"
    ]
    assert more_pages == ["transactions"]


def test_mobile_hub_keys_frozenset():
    assert erp._MOBILE_HUB_KEYS == frozenset({"money", "reports", "more", "people", "banking"})


def test_people_hub_open_from_more_not_duplicated():
    more = erp._MOBILE_HUB_CONFIG["more"]
    assert ("open_hub", "people", None, "nav.mobile.hub.people") in more
    page_keys = [p for k, p, *_ in more if k == "page"]
    assert "Customers" not in page_keys
    assert "Members" in page_keys
    people_pages = [p for k, p, *_ in erp._MOBILE_HUB_CONFIG["people"] if k == "page"]
    assert "Members" not in people_pages


def test_statement_reports_in_reports_hub_only():
    reports_pages = {p for k, p, *_ in erp._MOBILE_HUB_CONFIG["reports"] if k == "page"}
    more_accordions = {p for k, p, *_ in erp._MOBILE_HUB_CONFIG["more"] if k == "accordion"}
    statement_keys = {NAV_PROFIT_LOSS, NAV_BALANCE_SHEET, NAV_CASH_FLOW}

    assert statement_keys <= reports_pages
    assert "statements" not in more_accordions
    assert NAV_TXN_LEDGER not in {
        p for k, p, *_ in erp._MOBILE_HUB_CONFIG["more"] if k == "page"
    }


def test_desktop_nav_statements_unchanged():
    """Desktop sidebar still exposes Financial Statements before Reports."""
    src = inspect.getsource(erp._render_navigation_tree)
    assert '_nav_group("statements"' in src
    assert '_nav_direct(NAV_REPORTS)' in src
    stmt_pos = src.index('_nav_group("statements"')
    reports_pos = src.index('_nav_direct(NAV_REPORTS)')
    assert stmt_pos < reports_pos


def test_partner_cashier_hub_visibility():
    partner_allowed = {"Home", "Reports", NAV_PROFIT_LOSS, "Partner Accounts", "My Account"}
    assert erp._mobile_hub_has_entries("reports", partner_allowed, _ACCORDION_BY_KEY)
    assert erp._mobile_hub_has_entries("more", partner_allowed, _ACCORDION_BY_KEY)
    assert not erp._mobile_hub_has_entries("money", partner_allowed, _ACCORDION_BY_KEY)
    assert "New Transaction" not in partner_allowed
