"""NAV-ARCH-S3C — mobile navigation derived from registry."""

from __future__ import annotations

import app as erp
from registry.nav_keys import (
    NAV_AUDIT_LOG,
    NAV_BACKUP_RESTORE,
    NAV_BALANCE_SHEET,
    NAV_CASH_FLOW,
    NAV_COMPANY_SETTINGS,
    NAV_END_OF_DAY_CLOSE,
    NAV_EXTERNAL_SALES_VERIFICATION,
    NAV_HOME,
    NAV_INVENTORY,
    NAV_MEMBERS,
    NAV_NEW_TRANSACTION,
    NAV_PROFIT_LOSS,
    NAV_REPORTS,
    NAV_TXN_LEDGER,
)
from registry.navigation import (
    build_mobile_bottom_nav,
    build_mobile_hub_config,
    build_mobile_hub_keys,
    dispatch_render_spec,
    validate_mobile_surfaces,
)

LEGACY_BOTTOM_SLOTS: tuple[tuple[str, str, str, str, str, str], ...] = (
    ("home", NAV_HOME, "nav.bottom.home", "home", NAV_HOME, "home"),
    ("hub", "money", "nav.bottom.money", "money", "Money", "landmark"),
    ("new", NAV_NEW_TRANSACTION, "nav.bottom.new", "new", "New", "plus"),
    ("hub", "reports", "nav.bottom.reports", "reports", NAV_REPORTS, "bar-chart"),
    ("hub", "more", "nav.bottom.more", "more", "More", "menu"),
)

LEGACY_HUB_KEYS = frozenset({"money", "reports", "more", "people", "banking"})

LEGACY_HUB_PAGE_KEYS: dict[str, list[str]] = {
    "money": [
        "Cash Reconciliation",
        "External Sales Verification",
        "End-of-Day Close",
        "Banking",
        "Recon Health",
    ],
    "reports": [
        "Profit & Loss",
        "Balance Sheet",
        "Cash Flow",
        "Transaction Ledger",
    ],
    "people": [
        "Customers",
        "Vendors",
        "Receivables",
        "Payables",
        "Workers",
        "Partner Accounts",
    ],
    "more": [
        "Inventory",
        "Company Settings",
        "Members",
        "Backup & Restore",
        "Audit Log",
    ],
}


def _hub_page_keys(hub_key: str) -> list[str]:
    return [payload for kind, payload, *_ in erp._MOBILE_HUB_CONFIG[hub_key] if kind == "page"]


def test_validate_mobile_surfaces_passes():
    validate_mobile_surfaces()


def test_bottom_nav_exactly_five_slots():
    assert len(build_mobile_bottom_nav()) == 5
    assert len(erp._MOBILE_BOTTOM_NAV) == 5


def test_bottom_nav_matches_legacy():
    assert build_mobile_bottom_nav() == LEGACY_BOTTOM_SLOTS
    assert erp._MOBILE_BOTTOM_NAV == LEGACY_BOTTOM_SLOTS


def test_hub_keys_include_legacy_session_aliases():
    assert build_mobile_hub_keys() == LEGACY_HUB_KEYS
    assert erp._MOBILE_HUB_KEYS == LEGACY_HUB_KEYS


def test_hub_config_page_keys_match_legacy():
    built = build_mobile_hub_config()
    for hub_key, pages in LEGACY_HUB_PAGE_KEYS.items():
        assert _hub_page_keys(hub_key) == pages
        built_pages = [p for k, p, *_ in built[hub_key] if k == "page"]
        assert built_pages == pages


def test_bottom_hub_targets_in_hub_config():
    config_keys = set(erp._MOBILE_HUB_CONFIG)
    missing = [
        payload
        for kind, payload, *_ in erp._MOBILE_BOTTOM_NAV
        if kind == "hub" and payload not in config_keys
    ]
    assert not missing, missing


def test_all_mobile_hub_page_keys_in_dispatch():
    dispatch = set(dispatch_render_spec())
    missing = [
        f"{hub}:{page}"
        for hub, pages in LEGACY_HUB_PAGE_KEYS.items()
        for page in pages
        if page not in dispatch
    ]
    assert not missing, missing


def test_no_duplicate_pages_within_single_hub():
    for hub_key, entries in erp._MOBILE_HUB_CONFIG.items():
        pages = [payload for kind, payload, *_ in entries if kind == "page"]
        assert len(pages) == len(set(pages)), f"duplicate pages in hub {hub_key!r}"


def test_money_reports_people_more_hubs_present():
    assert set(erp._MOBILE_HUB_CONFIG) >= {"money", "reports", "people", "more"}


def test_reports_hub_statement_shortcuts():
    reports_pages = set(_hub_page_keys("reports"))
    assert {NAV_PROFIT_LOSS, NAV_BALANCE_SHEET, NAV_CASH_FLOW, NAV_TXN_LEDGER} <= reports_pages


def test_more_hub_members_not_in_people_hub():
    people_pages = set(_hub_page_keys("people"))
    more_pages = set(_hub_page_keys("more"))
    assert NAV_MEMBERS in more_pages
    assert NAV_MEMBERS not in people_pages


def test_more_hub_open_people_entry():
    entries = erp._MOBILE_HUB_CONFIG["more"]
    assert ("open_hub", "people", None, "nav.mobile.hub.people") in entries
