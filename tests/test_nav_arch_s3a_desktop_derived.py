"""NAV-ARCH-S3A — desktop navigation derived from registry."""

from __future__ import annotations

import inspect

import app as erp
from registry.nav_keys import (
    NAV_AUDIT_LOG,
    NAV_BACKUP_RESTORE,
    NAV_BANKING,
    NAV_COMPANY_SETTINGS,
    NAV_HOME,
    NAV_INVENTORY,
    NAV_MEMBERS,
    NAV_MY_ACCOUNT,
    NAV_NEW_TRANSACTION,
    NAV_PERMISSIONS,
    NAV_REPORTS,
    NAV_TXN_LEDGER,
)
from registry.navigation import (
    NAV_ACCORDION_GROUPS,
    build_nav_accordion,
    build_nav_accordion_by_key,
    build_nav_direct_pages,
    dispatch_render_spec,
    validate_desktop_surfaces,
)

# Frozen legacy desktop shapes (pre-S3A hand-edited app.py).
LEGACY_DIRECT_PAGES: list[str] = [
    NAV_HOME,
    NAV_NEW_TRANSACTION,
    NAV_TXN_LEDGER,
    NAV_INVENTORY,
    NAV_BANKING,
    NAV_REPORTS,
]

LEGACY_ACCORDION_GROUP_KEYS: list[str] = [
    "transactions",
    "people",
    "close_day",
    "recipe_costing",
    "statements",
    "accounting",
    "team",
    "settings",
]

LEGACY_ACCORDION_PAGES: dict[str, list[str]] = {
    "transactions": [
        "Sales",
        "Expenses",
        "Staff Expenses",
        "Purchases",
        "Recurring Expenses",
    ],
    "people": ["Customers", "Vendors", "Receivables", "Payables"],
    "close_day": [
        "Cash Reconciliation",
        "External Sales Verification",
        "End-of-Day Close",
    ],
    "recipe_costing": ["Ingredients", "Recipes", "Cost Breakdown", "Menu Items"],
    "statements": ["Profit & Loss", "Balance Sheet", "Cash Flow"],
    "accounting": [
        "General Ledger",
        "Chart of Accounts",
        "Journal Entries",
        "Trial Balance",
        "Fiscal Periods",
        "Year-End Close",
        "Budget",
        "Recon Health",
        "Opening Balances",
    ],
    "team": ["Partner Accounts", "Workers"],
    "settings": [
        "Company Settings",
        "Members",
        "Permissions",
        "Audit Log",
        "Backup & Restore",
    ],
}


def _accordion_page_keys() -> dict[str, list[str]]:
    return {
        group_key: [page_key for _icon, page_key in pages]
        for group_key, _label, pages in erp._NAV_ACCORDION
    }


def test_validate_desktop_surfaces_passes():
    validate_desktop_surfaces()


def test_direct_pages_match_legacy():
    assert build_nav_direct_pages() == LEGACY_DIRECT_PAGES
    assert erp._NAV_DIRECT_PAGES == LEGACY_DIRECT_PAGES


def test_accordion_group_keys_match_legacy():
    built = build_nav_accordion()
    assert [row[0] for row in built] == LEGACY_ACCORDION_GROUP_KEYS
    assert [row[0] for row in erp._NAV_ACCORDION] == LEGACY_ACCORDION_GROUP_KEYS


def test_accordion_pages_match_legacy_per_group():
    built = _accordion_page_keys()
    registry = {
        group_key: [page_key for _icon, page_key in pages]
        for group_key, _label, pages in build_nav_accordion()
    }
    assert built == LEGACY_ACCORDION_PAGES
    assert registry == LEGACY_ACCORDION_PAGES


def test_accordion_by_key_matches_build_helper():
    assert erp._NAV_ACCORDION_BY_KEY == build_nav_accordion_by_key()


def test_no_duplicate_direct_pages():
    assert len(erp._NAV_DIRECT_PAGES) == len(set(erp._NAV_DIRECT_PAGES))


def test_no_duplicate_accordion_entries():
    seen: set[str] = set()
    dupes: set[str] = set()
    for _gk, _label, pages in erp._NAV_ACCORDION:
        for _icon, page_key in pages:
            if page_key in seen:
                dupes.add(page_key)
            seen.add(page_key)
    assert not dupes, f"Duplicate accordion page keys: {dupes}"


def test_every_accordion_page_in_dispatch():
    dispatch = set(dispatch_render_spec())
    missing = [
        page_key
        for _gk, _label, pages in erp._NAV_ACCORDION
        for _icon, page_key in pages
        if page_key not in dispatch
    ]
    assert not missing, missing


def test_every_direct_page_in_dispatch():
    dispatch = set(dispatch_render_spec())
    missing = [k for k in erp._NAV_DIRECT_PAGES if k not in dispatch]
    assert not missing, missing


def test_settings_group_is_distinct_admin_pages_not_nested():
    """Settings accordion holds admin pages — no self-referential settings route."""
    settings_pages = _accordion_page_keys()["settings"]
    assert NAV_COMPANY_SETTINGS in settings_pages
    assert NAV_MEMBERS in settings_pages
    assert NAV_PERMISSIONS in settings_pages
    assert NAV_AUDIT_LOG in settings_pages
    assert NAV_BACKUP_RESTORE in settings_pages
    assert "Settings" not in settings_pages


def test_my_account_not_in_desktop_sidebar_lists():
    assert NAV_MY_ACCOUNT not in erp._NAV_DIRECT_PAGES
    assert NAV_MY_ACCOUNT not in {
        page_key
        for _gk, _label, pages in erp._NAV_ACCORDION
        for _icon, page_key in pages
    }


def test_registry_accordion_group_count():
    assert len(NAV_ACCORDION_GROUPS) == 8


def test_render_tree_layout_unchanged():
    """S3 preserves frozen sidebar render sequence via registry/sidebar_layout.py."""
    from registry.nav_keys import NAV_BANKING, NAV_HOME, NAV_INVENTORY, NAV_NEW_TRANSACTION, NAV_REPORTS
    from registry.sidebar_layout import flatten_sidebar_layout_keys

    keys = flatten_sidebar_layout_keys()
    direct = [k for kind, k in keys if kind == "direct"]
    assert direct.index(NAV_HOME) < direct.index(NAV_NEW_TRANSACTION)
    assert direct.index(NAV_NEW_TRANSACTION) < direct.index(NAV_TXN_LEDGER)
    assert direct.index(NAV_BANKING) < direct.index(NAV_INVENTORY)
    assert direct.index(NAV_INVENTORY) < direct.index(NAV_REPORTS)
    assert ("accordion", "settings") in keys
