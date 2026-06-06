"""Mobile hub config — visibility helpers (no Streamlit runtime)."""
from __future__ import annotations

import pytest

# Import after pytest collection path is set (project root)
import app as erp


_ACCORDION_BY_KEY = {
    "transactions": ("Record transactions", [
        ("💼  Sales", "💼 Sales"),
        ("💳  Expenses", "💳 Expenses"),
        ("🛒  Purchases", "🛒 Purchases"),
        ("🔁  Recurring Expenses", "🔁 Recurring Expenses"),
    ]),
    "people": ("Customers & suppliers", [
        ("👥  Customers", "👥 Customers"),
        ("🏢  Vendors", "🏢 Vendors"),
    ]),
    "accounting": ("Books", [
        ("🗂  General Ledger", "🗂 General Ledger"),
        ("💰  Budget", "💰 Budget"),
    ]),
}


def test_viewer_only_reports_hub_has_entries():
    allowed = {"🏠 Home", "📊 Reports", "👤 My Account"}
    assert erp._mobile_hub_has_entries("reports", allowed, _ACCORDION_BY_KEY)
    assert not erp._mobile_hub_has_entries("banking", allowed, _ACCORDION_BY_KEY)
    assert not erp._mobile_hub_has_entries("more", allowed, _ACCORDION_BY_KEY)


def test_owner_all_hubs_have_entries():
    allowed = {
        "🏠 Home",
        "➕ New Transaction",
        "🏦 Banking",
        "📊 Reports",
        "👥 Customers",
        "💼 Sales",
        "🗂 General Ledger",
        "📦 Inventory",
        "🏢 Company Settings",
    }
    for hub in ("banking", "reports", "more"):
        assert erp._mobile_hub_has_entries(hub, allowed, _ACCORDION_BY_KEY)


def test_module_hidden_inventory_removed_from_more():
    allowed = {
        "🏠 Home",
        "💼 Sales",
        "🗂 General Ledger",
        "🏢 Company Settings",
    }
    assert erp._mobile_hub_entry_visible(
        "more", "page", "📦 Inventory", allowed, _ACCORDION_BY_KEY
    ) is False
    assert erp._mobile_hub_entry_visible(
        "more", "accordion", "transactions", allowed, _ACCORDION_BY_KEY
    )


def test_sales_only_in_more_transactions_not_bottom_direct():
    bottom_pages = {payload for kind, payload, _, _, _, _ in erp._MOBILE_BOTTOM_NAV if kind in ("home", "new")}
    assert "💼 Sales" not in bottom_pages
    more_pages = [
        p for k, p, _, _ in erp._MOBILE_HUB_CONFIG["more"] if k == "accordion" and p == "transactions"
    ]
    assert more_pages == ["transactions"]


def test_mobile_hub_keys_frozenset():
    assert erp._MOBILE_HUB_KEYS == frozenset({"banking", "reports", "more", "people"})


def test_people_hub_open_from_more_not_duplicated():
    more = erp._MOBILE_HUB_CONFIG["more"]
    assert ("open_hub", "people", None, "nav.mobile.hub.people") in more
    page_keys = [p for k, p, *_ in more if k == "page"]
    assert "👥 Customers" not in page_keys
    assert "👤 Members" not in page_keys


def test_partner_cashier_hub_visibility():
    partner_allowed = {"🏠 Home", "📊 Reports", "🏦 Partner Accounts", "👤 My Account"}
    assert erp._mobile_hub_has_entries("reports", partner_allowed, _ACCORDION_BY_KEY)
    assert erp._mobile_hub_has_entries("more", partner_allowed, _ACCORDION_BY_KEY)
    assert not erp._mobile_hub_has_entries("banking", partner_allowed, _ACCORDION_BY_KEY)
    assert "➕ New Transaction" not in partner_allowed
