"""NAV-ARCH-S2 — navigation registry derives ``_PAGE_DISPATCH``."""

from __future__ import annotations

import re

import app as erp
from registry.nav_keys import ALL_NAV_PAGE_KEYS
from registry.navigation import (
    NAV_PAGES,
    build_page_dispatch,
    dispatch_render_spec,
    react_routes,
    validate_registry,
)
from tests.nav_ux_02_contract import (
    handler_has_meaningful_body,
    page_dispatch_from_main,
    resolve_dispatch_handler,
)

# Legacy inline dispatch captured before NAV-ARCH-S2 (order + handlers).
LEGACY_DISPATCH_SPEC: dict[str, str] = {
    "Home": "render_dashboard",
    "New Transaction": "render_add_transaction",
    "Transaction Ledger": "render_transaction_ledger_page",
    "Sales": "render_sales",
    "Expenses": "render_expenses",
    "Staff Expenses": "render_staff_expense_capture",
    "Recurring Expenses": "render_recurring_expenses",
    "Purchases": "render_purchases",
    "Cash Reconciliation": "render_cash_reconciliation",
    "External Sales Verification": "render_external_sales_verification",
    "Ingredients": "render_recipe_ingredients",
    "Recipes": "render_recipe_recipes",
    "Cost Breakdown": "render_recipe_cost_breakdown",
    "Menu Items": "render_recipe_menu_items",
    "End-of-Day Close": "render_end_of_day_close",
    "Customers": "render_customers",
    "Vendors": "render_vendors",
    "Receivables": "render_receivables",
    "Payables": "render_payables",
    "Inventory": "render_inventory",
    "Banking": "render_banking",
    "Reports": "render_reports",
    "Profit & Loss": "render_profit_loss_page",
    "Balance Sheet": "render_balance_sheet_page",
    "Cash Flow": "render_cash_flow_page",
    "General Ledger": "render_general_ledger",
    "Trial Balance": "render_trial_balance",
    "Journal Entries": "render_journal_entries",
    "Fiscal Periods": "render_fiscal_periods",
    "Year-End Close": "render_year_end_close",
    "Budget": "render_budget",
    "Chart of Accounts": "render_chart_of_accounts",
    "Recon Health": "render_reconciliation_health",
    "Partner Accounts": "render_partner_accounts",
    "Workers": "render_workers",
    "Company Settings": "render_company_settings",
    "Members": "render_user_management",
    "Permissions": "render_permissions_management",
    "Audit Log": "render_audit_log",
    "Backup & Restore": "<lambda>",
    "Opening Balances": "render_opening_balances",
    "My Account": "render_my_account",
}


def test_registry_validation_passes():
    validate_registry()


def test_no_duplicate_route_keys():
    keys = [p.route_key for p in NAV_PAGES]
    assert len(keys) == len(set(keys))


def test_no_duplicate_react_routes():
    paths = [p.react_route for p in NAV_PAGES]
    assert len(paths) == len(set(paths))


def test_every_route_has_react_route():
    for page in NAV_PAGES:
        assert page.react_route.startswith("/"), page.route_key
        assert " " not in page.react_route, page.route_key


def test_react_route_safe_naming():
    pattern = re.compile(r"^/(?:[a-z0-9]+(?:/[a-z0-9-]+)*)?$")
    for page in NAV_PAGES:
        assert pattern.match(page.react_route), (
            f"Unsafe react_route for {page.route_key!r}: {page.react_route!r}"
        )


def test_dispatch_spec_matches_legacy_handlers():
    assert dispatch_render_spec() == LEGACY_DISPATCH_SPEC


def test_page_dispatch_from_main_matches_registry():
    assert page_dispatch_from_main() == dispatch_render_spec()


def test_app_page_dispatch_keys_match_registry():
    visible = {p.route_key for p in NAV_PAGES if not p.hidden}
    assert set(erp._PAGE_DISPATCH.keys()) == visible


def test_app_page_dispatch_count():
    visible_count = sum(1 for p in NAV_PAGES if not p.hidden)
    assert len(erp._PAGE_DISPATCH) == visible_count
    assert len(ALL_NAV_PAGE_KEYS) == len(NAV_PAGES)


def test_every_registry_render_fn_resolves_in_app():
    failures: list[str] = []
    for page in NAV_PAGES:
        handler_name = "<lambda>" if not page.session_arg else page.render_fn
        fn = resolve_dispatch_handler(handler_name)
        if not callable(fn):
            failures.append(f"{page.route_key}: {handler_name} not callable")
        elif not handler_has_meaningful_body(fn):
            failures.append(f"{page.route_key}: {handler_name} empty stub")
    assert not failures, failures


def test_build_page_dispatch_produces_callables():
    def _resolve(page):
        return resolve_dispatch_handler(
            "<lambda>" if not page.session_arg else page.render_fn
        )

    dispatch = build_page_dispatch(_resolve)
    visible = {p.route_key for p in NAV_PAGES if not p.hidden}
    assert set(dispatch) == visible
    for key, fn in dispatch.items():
        assert callable(fn), key


def test_registry_nav_keys_subset_of_all_nav_page_keys():
    registry_keys = {p.route_key for p in NAV_PAGES}
    assert registry_keys == ALL_NAV_PAGE_KEYS


def test_react_routes_map_complete():
    routes = react_routes()
    assert set(routes) == {p.route_key for p in NAV_PAGES}
    assert len(set(routes.values())) == len(routes)
