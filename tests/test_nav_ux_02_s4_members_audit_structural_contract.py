"""NAV-UX-02-S4-IMPL-1 — Members mobile relocation to More/Admin contract."""

from __future__ import annotations

import app as erp
from registry.nav_keys import (
    NAV_AUDIT_LOG,
    NAV_BACKUP_RESTORE,
    NAV_COMPANY_SETTINGS,
    NAV_MEMBERS,
    NAV_PERMISSIONS,
)
from tests.nav_ux_02_contract import (
    PEOPLE_HUB_OPERATIONAL_KEYS,
    SETTINGS_ADMIN_REACT_ROUTES,
    accordion_page_keys,
)

_NON_OWNER_ROLES = ("manager", "cashier", "partner", "viewer")
_SETTINGS_ACCORDION_KEYS = frozenset(
    {
        NAV_COMPANY_SETTINGS,
        NAV_MEMBERS,
        NAV_PERMISSIONS,
        NAV_AUDIT_LOG,
        NAV_BACKUP_RESTORE,
    }
)


def _hub_page_keys(hub_key: str) -> list[str]:
    return [
        payload
        for kind, payload, *_rest in erp._MOBILE_HUB_CONFIG[hub_key]
        if kind == "page"
    ]


def _more_admin_page_keys() -> list[str]:
    entries = erp._MOBILE_HUB_CONFIG["more"]
    admin_idx = next(
        i for i, row in enumerate(entries) if row[0] == "section" and row[1] == "admin"
    )
    return [
        payload
        for kind, payload, *_rest in entries[admin_idx + 1 :]
        if kind == "page"
    ]


def test_members_owner_only():
    assert NAV_MEMBERS in erp._NAV_ROLE_PAGES["owner"]
    for role in _NON_OWNER_ROLES:
        assert NAV_MEMBERS not in erp._NAV_ROLE_PAGES[role]


def test_audit_log_owner_and_manager_only():
    assert NAV_AUDIT_LOG in erp._NAV_ROLE_PAGES["owner"]
    assert NAV_AUDIT_LOG in erp._NAV_ROLE_PAGES["manager"]
    for role in ("cashier", "partner", "viewer"):
        assert NAV_AUDIT_LOG not in erp._NAV_ROLE_PAGES[role]


def test_people_hub_excludes_members():
    people_pages = set(_hub_page_keys("people"))
    assert NAV_MEMBERS not in people_pages


def test_people_hub_operational_records_only():
    people_pages = set(_hub_page_keys("people"))
    assert people_pages == PEOPLE_HUB_OPERATIONAL_KEYS


def test_more_admin_includes_members():
    admin_pages = _more_admin_page_keys()
    assert NAV_MEMBERS in admin_pages


def test_more_admin_section_order():
    admin_pages = _more_admin_page_keys()
    assert admin_pages == [
        NAV_COMPANY_SETTINGS,
        NAV_MEMBERS,
        NAV_BACKUP_RESTORE,
        NAV_AUDIT_LOG,
    ]


def test_settings_accordion_includes_members_and_audit_log():
    settings_pages = {
        page_key
        for group_key, page_key in accordion_page_keys()
        if group_key == "settings"
    }
    assert settings_pages == _SETTINGS_ACCORDION_KEYS
    assert NAV_MEMBERS in settings_pages
    assert NAV_AUDIT_LOG in settings_pages


def test_members_react_route_under_settings_not_people():
    assert SETTINGS_ADMIN_REACT_ROUTES[NAV_MEMBERS] == "/settings/members"
    assert "/people/members" not in SETTINGS_ADMIN_REACT_ROUTES.values()
    assert all(path.startswith("/settings/") for path in SETTINGS_ADMIN_REACT_ROUTES.values())
