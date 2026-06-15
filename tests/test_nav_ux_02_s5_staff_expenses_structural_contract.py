"""NAV-UX-02-S5-IMPL-1 — Staff Expenses permission-derived nav visibility contract."""

from __future__ import annotations

import inspect

import app as erp
from registry.nav_keys import NAV_STAFF_EXPENSE_CAPTURE
from services import user_access as ua
from tests.nav_ux_02_contract import (
    STAFF_EXPENSE_NAV_PERMISSIONS,
    STAFF_EXPENSE_REACT_ROUTE,
)

_NAV_INELIGIBLE_ROLES = ("partner", "viewer")


def test_default_staff_capture_permission_matrix():
    assert ua.STAFF_CAPTURE_PERMISSION_MATRIX["submit_expense_drafts"] == frozenset(
        {"owner", "manager", "cashier"}
    )
    assert ua.STAFF_CAPTURE_PERMISSION_MATRIX["approve_expense_drafts"] == frozenset(
        {"owner", "manager"}
    )
    assert "upload_receipts" in ua.STAFF_CAPTURE_PERMISSION_MATRIX
    for role in _NAV_INELIGIBLE_ROLES:
        assert role not in ua.STAFF_CAPTURE_PERMISSION_MATRIX["submit_expense_drafts"]
        assert role not in ua.STAFF_CAPTURE_PERMISSION_MATRIX["approve_expense_drafts"]


def test_nav_eligible_roles_from_default_matrix():
    eligible = (
        ua.STAFF_CAPTURE_PERMISSION_MATRIX["submit_expense_drafts"]
        | ua.STAFF_CAPTURE_PERMISSION_MATRIX["approve_expense_drafts"]
    )
    assert eligible == frozenset({"owner", "manager", "cashier"})


def test_static_role_pages_do_not_gate_staff_expenses_to_owner_only():
    assert NAV_STAFF_EXPENSE_CAPTURE in erp._NAV_ROLE_PAGES["owner"]
    assert NAV_STAFF_EXPENSE_CAPTURE not in erp._NAV_ROLE_PAGES["manager"]
    assert NAV_STAFF_EXPENSE_CAPTURE not in erp._NAV_ROLE_PAGES["cashier"]
    for role in _NAV_INELIGIBLE_ROLES:
        assert NAV_STAFF_EXPENSE_CAPTURE not in erp._NAV_ROLE_PAGES[role]


def test_can_view_staff_expense_capture_matches_page_permissions():
    src = inspect.getsource(erp._can_view_staff_expense_capture)
    assert '_can("submit_expense_drafts")' in src
    assert '_can("approve_expense_drafts")' in src
    assert STAFF_EXPENSE_NAV_PERMISSIONS == frozenset(
        {"submit_expense_drafts", "approve_expense_drafts"}
    )


def test_main_applies_permission_nav_override():
    main_src = inspect.getsource(erp.main)
    assert "_apply_permission_nav_overrides" in main_src
    assert "hidden=_hidden_nav" in main_src or "_hidden_nav" in main_src


def test_apply_permission_nav_overrides_adds_when_permitted(monkeypatch):
    monkeypatch.setattr(erp, "_can_view_staff_expense_capture", lambda: True)
    allowed = {"Home", "Expenses"}
    result = erp._apply_permission_nav_overrides(allowed)
    assert NAV_STAFF_EXPENSE_CAPTURE in result


def test_apply_permission_nav_overrides_removes_when_denied(monkeypatch):
    monkeypatch.setattr(erp, "_can_view_staff_expense_capture", lambda: False)
    allowed = {"Home", NAV_STAFF_EXPENSE_CAPTURE}
    result = erp._apply_permission_nav_overrides(allowed)
    assert NAV_STAFF_EXPENSE_CAPTURE not in result


def test_apply_permission_nav_overrides_respects_module_hidden(monkeypatch):
    monkeypatch.setattr(erp, "_can_view_staff_expense_capture", lambda: True)
    allowed = {"Home", NAV_STAFF_EXPENSE_CAPTURE}
    hidden = {NAV_STAFF_EXPENSE_CAPTURE}
    result = erp._apply_permission_nav_overrides(allowed, hidden=hidden)
    assert NAV_STAFF_EXPENSE_CAPTURE not in result


def test_page_render_still_permission_gated():
    from ui import staff_capture

    ui_src = inspect.getsource(staff_capture.render_staff_expense_capture)
    assert '_can("submit_expense_drafts")' in ui_src
    assert '_can("approve_expense_drafts")' in ui_src
    assert "sc.no_permission" in ui_src


def test_staff_expenses_react_route_not_payroll_workers():
    assert STAFF_EXPENSE_REACT_ROUTE == "/expenses/staff-capture"
    assert "/people/" not in STAFF_EXPENSE_REACT_ROUTE
    assert "/workers" not in STAFF_EXPENSE_REACT_ROUTE
