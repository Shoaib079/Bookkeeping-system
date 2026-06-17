"""NAV-ARCH-S3B — role gates derived from registry."""

from __future__ import annotations

import app as erp
from registry.nav_keys import (
    NAV_AUDIT_LOG,
    NAV_BACKUP_RESTORE,
    NAV_COMPANY_SETTINGS,
    NAV_MEMBERS,
    NAV_MY_ACCOUNT,
    NAV_PERMISSIONS,
    NAV_STAFF_EXPENSE_CAPTURE,
)
from registry.navigation import (
    NAV_ROLE_NAMES,
    build_nav_role_pages,
    dispatch_render_spec,
    nav_page_by_key,
    validate_role_gates,
)

# Frozen legacy static role allow-lists (pre-S3B hand-edited app.py) — set parity.
LEGACY_ROLE_PAGE_SETS: dict[str, frozenset[str]] = {
    "owner": frozenset(
        {
            "Home",
            "New Transaction",
            "Transaction Ledger",
            "Sales",
            "Expenses",
            "Staff Expenses",
            "Recurring Expenses",
            "Purchases",
            "Cash Reconciliation",
            "External Sales Verification",
            "Ingredients",
            "Recipes",
            "Cost Breakdown",
            "Menu Items",
            "End-of-Day Close",
            "Customers",
            "Vendors",
            "Receivables",
            "Payables",
            "Inventory",
            "Banking",
            "Reports",
            "Profit & Loss",
            "Balance Sheet",
            "Cash Flow",
            "General Ledger",
            "Trial Balance",
            "Journal Entries",
            "Fiscal Periods",
            "Year-End Close",
            "Budget",
            "Chart of Accounts",
            "Recon Health",
            "Partner Accounts",
            "Workers",
            "Company Settings",
            "Members",
            "Permissions",
            "Audit Log",
            "Backup & Restore",
            "Opening Balances",
            "My Account",
        }
    ),
    "manager": frozenset(
        {
            "Home",
            "New Transaction",
            "Transaction Ledger",
            "Sales",
            "Expenses",
            "Recurring Expenses",
            "Purchases",
            "Cash Reconciliation",
            "External Sales Verification",
            "End-of-Day Close",
            "Ingredients",
            "Recipes",
            "Cost Breakdown",
            "Menu Items",
            "Customers",
            "Vendors",
            "Receivables",
            "Payables",
            "Inventory",
            "Banking",
            "Reports",
            "Profit & Loss",
            "Balance Sheet",
            "Cash Flow",
            "General Ledger",
            "Trial Balance",
            "Journal Entries",
            "Fiscal Periods",
            "Year-End Close",
            "Budget",
            "Chart of Accounts",
            "Recon Health",
            "Partner Accounts",
            "Workers",
            "Audit Log",
            "Opening Balances",
            "My Account",
        }
    ),
    "cashier": frozenset(
        {
            "Home",
            "New Transaction",
            "Transaction Ledger",
            "Sales",
            "Expenses",
            "Recurring Expenses",
            "Purchases",
            "Cash Reconciliation",
            "External Sales Verification",
            "End-of-Day Close",
            "Receivables",
            "Payables",
            "Banking",
            "Reports",
            "Profit & Loss",
            "Balance Sheet",
            "Cash Flow",
            "My Account",
        }
    ),
    "partner": frozenset(
        {
            "Home",
            "Sales",
            "Receivables",
            "Transaction Ledger",
            "Reports",
            "Profit & Loss",
            "Balance Sheet",
            "Cash Flow",
            "Partner Accounts",
            "My Account",
        }
    ),
    "viewer": frozenset(
        {
            "Home",
            "Transaction Ledger",
            "Reports",
            "Profit & Loss",
            "Balance Sheet",
            "Cash Flow",
            "My Account",
        }
    ),
}


def test_validate_role_gates_passes():
    validate_role_gates()


def test_role_names_complete():
    assert NAV_ROLE_NAMES == ("owner", "manager", "cashier", "partner", "viewer")


def test_role_page_sets_match_legacy():
    built = build_nav_role_pages()
    for role in NAV_ROLE_NAMES:
        assert set(built[role]) == LEGACY_ROLE_PAGE_SETS[role]
        assert set(erp._NAV_ROLE_PAGES[role]) == LEGACY_ROLE_PAGE_SETS[role]


def test_owner_includes_all_sidebar_pages_plus_my_account():
    built = build_nav_role_pages()
    owner = set(built["owner"])
    assert erp._NAV_ALL_PAGES
    assert set(erp._NAV_ALL_PAGES).issubset(owner)
    assert NAV_MY_ACCOUNT in owner


def test_all_role_routes_valid_in_dispatch():
    dispatch = set(dispatch_render_spec())
    missing: list[str] = []
    for role, pages in erp._NAV_ROLE_PAGES.items():
        for page_key in pages:
            if page_key not in dispatch:
                missing.append(f"{role}:{page_key}")
    assert not missing, missing


def test_restricted_owner_only_pages():
    for key in (
        NAV_COMPANY_SETTINGS,
        NAV_MEMBERS,
        NAV_PERMISSIONS,
        NAV_BACKUP_RESTORE,
    ):
        assert key in erp._NAV_ROLE_PAGES["owner"]
        for role in ("manager", "cashier", "partner", "viewer"):
            assert key not in erp._NAV_ROLE_PAGES[role]


def test_staff_expenses_static_owner_only_permission_gated():
    staff = nav_page_by_key(NAV_STAFF_EXPENSE_CAPTURE)
    assert staff.permission_gate == frozenset(
        {"submit_expense_drafts", "approve_expense_drafts"}
    )
    assert NAV_STAFF_EXPENSE_CAPTURE in erp._NAV_ROLE_PAGES["owner"]
    for role in ("manager", "cashier", "partner", "viewer"):
        assert NAV_STAFF_EXPENSE_CAPTURE not in erp._NAV_ROLE_PAGES[role]


def test_audit_log_manager_not_cashier():
    assert NAV_AUDIT_LOG in erp._NAV_ROLE_PAGES["owner"]
    assert NAV_AUDIT_LOG in erp._NAV_ROLE_PAGES["manager"]
    for role in ("cashier", "partner", "viewer"):
        assert NAV_AUDIT_LOG not in erp._NAV_ROLE_PAGES[role]


def test_permission_override_helper_unchanged():
    import inspect

    src = inspect.getsource(erp._apply_permission_nav_overrides)
    assert "NAV_STAFF_EXPENSE_CAPTURE" in src
    assert "_can_view_staff_expense_capture" in src
