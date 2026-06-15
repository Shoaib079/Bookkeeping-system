"""NAV-UX-02-S1 — structural navigation parity contract tests.

Pure assertions over live navigation structures (_PAGE_DISPATCH, ALL_NAV_PAGE_KEYS,
_NAV_ROLE_PAGES, _NAV_ACCORDION, mobile hubs). No UI/runtime change.
Source plan: docs/NAV_UX_02_AUDIT.md §6.
"""

from __future__ import annotations

import app as erp
from registry.nav_keys import ALL_NAV_PAGE_KEYS, LEGACY_NAV_ALIASES, NAV_TODAY_SUMMARY
from tests.nav_ux_02_contract import (
    KNOWN_HIDDEN,
    accordion_page_keys,
    mobile_bottom_hub_targets,
    mobile_hub_page_keys_flat,
    page_dispatch_from_main,
)


def test_every_page_dispatch_key_in_all_nav_page_keys():
    dispatch = page_dispatch_from_main()
    missing = set(dispatch) - ALL_NAV_PAGE_KEYS
    assert not missing, f"_PAGE_DISPATCH keys missing from ALL_NAV_PAGE_KEYS: {missing}"


def test_every_role_page_key_in_all_nav_page_keys():
    missing: set[str] = set()
    for role, pages in erp._NAV_ROLE_PAGES.items():
        for page_key in pages:
            if page_key not in ALL_NAV_PAGE_KEYS:
                missing.add(f"{role}:{page_key}")
    assert not missing, f"_NAV_ROLE_PAGES keys missing from ALL_NAV_PAGE_KEYS: {missing}"


def test_every_accordion_page_key_in_page_dispatch():
    dispatch = set(page_dispatch_from_main())
    missing = [
        f"{group}:{page_key}"
        for group, page_key in accordion_page_keys()
        if page_key not in dispatch
    ]
    assert not missing, f"Accordion page keys missing from _PAGE_DISPATCH: {missing}"


def test_no_accordion_page_key_in_two_groups():
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for group_key, page_key in accordion_page_keys():
        if page_key in seen:
            duplicates.append(
                f"{page_key!r} in both {seen[page_key]!r} and {group_key!r}"
            )
        else:
            seen[page_key] = group_key
    assert not duplicates, f"Accordion page keys in multiple groups: {duplicates}"


def test_every_mobile_hub_page_key_in_page_dispatch():
    dispatch = set(page_dispatch_from_main())
    missing = [key for key in mobile_hub_page_keys_flat() if key not in dispatch]
    assert not missing, f"Mobile hub page keys missing from _PAGE_DISPATCH: {missing}"


def test_every_mobile_bottom_hub_target_in_hub_config():
    config_keys = set(erp._MOBILE_HUB_CONFIG)
    missing = [
        hub
        for hub in mobile_bottom_hub_targets()
        if hub not in config_keys
    ]
    assert not missing, (
        f"_MOBILE_BOTTOM_NAV hub targets missing from _MOBILE_HUB_CONFIG: {missing}"
    )


def test_every_mobile_bottom_hub_target_in_mobile_hub_keys():
    missing = [
        hub
        for hub in mobile_bottom_hub_targets()
        if hub not in erp._MOBILE_HUB_KEYS
    ]
    assert not missing, (
        f"_MOBILE_BOTTOM_NAV hub targets missing from _MOBILE_HUB_KEYS: {missing}"
    )


def test_every_legacy_alias_target_in_all_nav_page_keys():
    missing = {
        alias: target
        for alias, target in LEGACY_NAV_ALIASES.items()
        if target not in ALL_NAV_PAGE_KEYS
    }
    assert not missing, f"LEGACY_NAV_ALIASES targets missing from ALL_NAV_PAGE_KEYS: {missing}"


def test_known_hidden_empty_after_s2_retirement():
    assert KNOWN_HIDDEN == frozenset()


def test_today_summary_retired_from_dispatch_and_nav_keys():
    dispatch = page_dispatch_from_main()
    assert NAV_TODAY_SUMMARY not in dispatch
    assert NAV_TODAY_SUMMARY not in ALL_NAV_PAGE_KEYS


def test_known_hidden_exempt_routes_when_nonempty():
    if not KNOWN_HIDDEN:
        return
    role_keys = {key for pages in erp._NAV_ROLE_PAGES.values() for key in pages}
    accordion_keys = {page_key for _, page_key in accordion_page_keys()}
    mobile_page_keys = set(mobile_hub_page_keys_flat())
    direct_keys = set(erp._NAV_DIRECT_PAGES)

    for hidden in KNOWN_HIDDEN:
        assert hidden not in role_keys, f"{hidden!r} should not be in _NAV_ROLE_PAGES"
        assert hidden not in accordion_keys, f"{hidden!r} should not be in accordion"
        assert hidden not in mobile_page_keys, f"{hidden!r} should not be in mobile hubs"
        assert hidden not in direct_keys, f"{hidden!r} should not be in _NAV_DIRECT_PAGES"
