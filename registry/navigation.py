"""NAV-ARCH-S2 — navigation registry (single source of truth for page dispatch).

Derives ``_PAGE_DISPATCH`` only. Desktop accordion/direct, role gates, and mobile
config remain hand-edited in ``app.py`` until NAV-ARCH-S3A/S3B/S3C.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from registry.icon_svg import PAGE_ICON
from registry.nav_keys import (
    ALL_NAV_PAGE_KEYS,
    NAV_AUDIT_LOG,
    NAV_BACKUP_RESTORE,
    NAV_BALANCE_SHEET,
    NAV_BANKING,
    NAV_BUDGET,
    NAV_CASH_FLOW,
    NAV_CASH_RECONCILIATION,
    NAV_CHART_OF_ACCOUNTS,
    NAV_COMPANY_SETTINGS,
    NAV_CUSTOMERS,
    NAV_END_OF_DAY_CLOSE,
    NAV_EXPENSES,
    NAV_EXTERNAL_SALES_VERIFICATION,
    NAV_FISCAL_PERIODS,
    NAV_GENERAL_LEDGER,
    NAV_HOME,
    NAV_INVENTORY,
    NAV_JOURNAL_ENTRIES,
    NAV_MEMBERS,
    NAV_MY_ACCOUNT,
    NAV_NEW_TRANSACTION,
    NAV_OPENING_BALANCES,
    NAV_PARTNER_ACCOUNTS,
    NAV_PAYABLES,
    NAV_PERMISSIONS,
    NAV_PROFIT_LOSS,
    NAV_PURCHASES,
    NAV_RC_COST_BREAKDOWN,
    NAV_RC_INGREDIENTS,
    NAV_RC_MENU_ITEMS,
    NAV_RC_RECIPES,
    NAV_RECEIVABLES,
    NAV_RECON_HEALTH,
    NAV_RECURRING_EXPENSES,
    NAV_REPORTS,
    NAV_SALES,
    NAV_STAFF_EXPENSE_CAPTURE,
    NAV_TRIAL_BALANCE,
    NAV_TXN_LEDGER,
    NAV_VENDORS,
    NAV_WORKERS,
    NAV_YEAR_END_CLOSE,
)
from registry.nav_labels import NAV_PAGE_I18N

RoleName = str

_ALL_ROLES: frozenset[RoleName] = frozenset(
    {"owner", "manager", "cashier", "partner", "viewer"}
)
_OM: frozenset[RoleName] = frozenset({"owner", "manager"})
_OMC: frozenset[RoleName] = frozenset({"owner", "manager", "cashier"})
_OMCP: frozenset[RoleName] = frozenset({"owner", "manager", "cashier", "partner"})
_OMCPV: frozenset[RoleName] = frozenset(
    {"owner", "manager", "cashier", "partner", "viewer"}
)
_OWNER_ONLY: frozenset[RoleName] = frozenset({"owner"})


@dataclass(frozen=True)
class NavPageDef:
    """Per-page navigation metadata — dispatch SSOT; surfaces derived in S3."""

    route_key: str
    label_i18n: str
    render_fn: str
    react_route: str
    order: int
    icon: str | None = None
    hidden: bool = False
    legacy: bool = False
    session_arg: bool = True
    roles: frozenset[RoleName] = frozenset()
    sidebar_direct: bool = False
    accordion_group: str | None = None


def _page(
    route_key: str,
    render_fn: str,
    react_route: str,
    order: int,
    *,
    roles: frozenset[RoleName] = frozenset(),
    session_arg: bool = True,
    sidebar_direct: bool = False,
    accordion_group: str | None = None,
    hidden: bool = False,
    legacy: bool = False,
) -> NavPageDef:
    return NavPageDef(
        route_key=route_key,
        label_i18n=NAV_PAGE_I18N[route_key],
        render_fn=render_fn,
        react_route=react_route,
        order=order,
        icon=PAGE_ICON.get(route_key),
        hidden=hidden,
        legacy=legacy,
        session_arg=session_arg,
        roles=roles,
        sidebar_direct=sidebar_direct,
        accordion_group=accordion_group,
    )


# Order matches legacy ``_PAGE_DISPATCH`` in app.py (NAV-ARCH-S2 parity).
NAV_PAGES: tuple[NavPageDef, ...] = (
    _page(NAV_HOME, "render_dashboard", "/", 0, roles=_ALL_ROLES, sidebar_direct=True),
    _page(
        NAV_NEW_TRANSACTION,
        "render_add_transaction",
        "/transactions/new",
        1,
        roles=_OMC,
        sidebar_direct=True,
    ),
    _page(
        NAV_TXN_LEDGER,
        "render_transaction_ledger_page",
        "/transactions/ledger",
        2,
        roles=_OMCPV,
        sidebar_direct=True,
    ),
    _page(NAV_SALES, "render_sales", "/sales", 3, roles=_OMCP, accordion_group="transactions"),
    _page(NAV_EXPENSES, "render_expenses", "/expenses", 4, roles=_OMC, accordion_group="transactions"),
    _page(
        NAV_STAFF_EXPENSE_CAPTURE,
        "render_staff_expense_capture",
        "/expenses/staff-capture",
        5,
        roles=_OWNER_ONLY,
        accordion_group="transactions",
    ),
    _page(
        NAV_RECURRING_EXPENSES,
        "render_recurring_expenses",
        "/expenses/recurring",
        6,
        roles=_OMC,
        accordion_group="transactions",
    ),
    _page(NAV_PURCHASES, "render_purchases", "/purchases", 7, roles=_OMC, accordion_group="transactions"),
    _page(
        NAV_CASH_RECONCILIATION,
        "render_cash_reconciliation",
        "/closings/cash-recon",
        8,
        roles=_OMC,
        accordion_group="close_day",
    ),
    _page(
        NAV_EXTERNAL_SALES_VERIFICATION,
        "render_external_sales_verification",
        "/closings/external-sales",
        9,
        roles=_OMC,
        accordion_group="close_day",
    ),
    _page(NAV_RC_INGREDIENTS, "render_recipe_ingredients", "/recipes/ingredients", 10, roles=_OM, accordion_group="recipe_costing"),
    _page(NAV_RC_RECIPES, "render_recipe_recipes", "/recipes", 11, roles=_OM, accordion_group="recipe_costing"),
    _page(
        NAV_RC_COST_BREAKDOWN,
        "render_recipe_cost_breakdown",
        "/recipes/cost-breakdown",
        12,
        roles=_OM,
        accordion_group="recipe_costing",
    ),
    _page(NAV_RC_MENU_ITEMS, "render_recipe_menu_items", "/recipes/menu-items", 13, roles=_OM, accordion_group="recipe_costing"),
    _page(
        NAV_END_OF_DAY_CLOSE,
        "render_end_of_day_close",
        "/closings/eod",
        14,
        roles=_OMC,
        accordion_group="close_day",
    ),
    _page(NAV_CUSTOMERS, "render_customers", "/customers", 15, roles=_OM, accordion_group="people"),
    _page(NAV_VENDORS, "render_vendors", "/vendors", 16, roles=_OM, accordion_group="people"),
    _page(NAV_RECEIVABLES, "render_receivables", "/receivables", 17, roles=_OMCP, accordion_group="people"),
    _page(NAV_PAYABLES, "render_payables", "/payables", 18, roles=_OMC, accordion_group="people"),
    _page(NAV_INVENTORY, "render_inventory", "/inventory", 19, roles=_OM, sidebar_direct=True),
    _page(NAV_BANKING, "render_banking", "/banking", 20, roles=_OMC, sidebar_direct=True),
    _page(NAV_REPORTS, "render_reports", "/reports", 21, roles=_OMCPV, sidebar_direct=True),
    _page(
        NAV_PROFIT_LOSS,
        "render_profit_loss_page",
        "/reports/profit-loss",
        22,
        roles=_OMCPV,
        accordion_group="statements",
    ),
    _page(
        NAV_BALANCE_SHEET,
        "render_balance_sheet_page",
        "/reports/balance-sheet",
        23,
        roles=_OMCPV,
        accordion_group="statements",
    ),
    _page(
        NAV_CASH_FLOW,
        "render_cash_flow_page",
        "/reports/cash-flow",
        24,
        roles=_OMCPV,
        accordion_group="statements",
    ),
    _page(NAV_GENERAL_LEDGER, "render_general_ledger", "/books/general-ledger", 25, roles=_OM, accordion_group="accounting"),
    _page(NAV_TRIAL_BALANCE, "render_trial_balance", "/books/trial-balance", 26, roles=_OM, accordion_group="accounting"),
    _page(NAV_JOURNAL_ENTRIES, "render_journal_entries", "/books/journal-entries", 27, roles=_OM, accordion_group="accounting"),
    _page(NAV_FISCAL_PERIODS, "render_fiscal_periods", "/books/fiscal-periods", 28, roles=_OM, accordion_group="accounting"),
    _page(NAV_YEAR_END_CLOSE, "render_year_end_close", "/books/year-end-close", 29, roles=_OM, accordion_group="accounting"),
    _page(NAV_BUDGET, "render_budget", "/books/budget", 30, roles=_OM, accordion_group="accounting"),
    _page(NAV_CHART_OF_ACCOUNTS, "render_chart_of_accounts", "/books/chart-of-accounts", 31, roles=_OM, accordion_group="accounting"),
    _page(NAV_RECON_HEALTH, "render_reconciliation_health", "/books/recon-health", 32, roles=_OM, accordion_group="accounting"),
    _page(NAV_PARTNER_ACCOUNTS, "render_partner_accounts", "/partners", 33, roles=frozenset({"owner", "manager", "partner"}), accordion_group="team"),
    _page(NAV_WORKERS, "render_workers", "/workers", 34, roles=_OM, accordion_group="team"),
    _page(NAV_COMPANY_SETTINGS, "render_company_settings", "/settings/company", 35, roles=_OWNER_ONLY, accordion_group="settings"),
    _page(NAV_MEMBERS, "render_user_management", "/settings/members", 36, roles=_OWNER_ONLY, accordion_group="settings"),
    _page(NAV_PERMISSIONS, "render_permissions_management", "/settings/permissions", 37, roles=_OWNER_ONLY, accordion_group="settings"),
    _page(NAV_AUDIT_LOG, "render_audit_log", "/settings/audit-log", 38, roles=_OM, accordion_group="settings"),
    _page(
        NAV_BACKUP_RESTORE,
        "render_backup_restore",
        "/settings/backup-restore",
        39,
        roles=_OWNER_ONLY,
        session_arg=False,
        accordion_group="settings",
    ),
    _page(NAV_OPENING_BALANCES, "render_opening_balances", "/books/opening-balances", 40, roles=_OM, accordion_group="accounting"),
    _page(NAV_MY_ACCOUNT, "render_my_account", "/account", 41, roles=_ALL_ROLES),
)


def nav_page_by_key(route_key: str) -> NavPageDef:
    for page in NAV_PAGES:
        if page.route_key == route_key:
            return page
    raise KeyError(route_key)


def dispatch_render_spec() -> dict[str, str]:
    """route_key → render_fn name (``<lambda>`` when session_arg is False)."""
    return {
        p.route_key: ("<lambda>" if not p.session_arg else p.render_fn)
        for p in NAV_PAGES
    }


def react_routes() -> dict[str, str]:
    return {p.route_key: p.react_route for p in NAV_PAGES}


def validate_registry() -> None:
    """Raise ``ValueError`` on duplicate route_key or react_route."""
    keys = [p.route_key for p in NAV_PAGES]
    dup_keys = {k for k in keys if keys.count(k) > 1}
    if dup_keys:
        raise ValueError(f"Duplicate route_key in NAV_PAGES: {dup_keys}")

    paths = [p.react_route for p in NAV_PAGES]
    dup_paths = {p for p in paths if paths.count(p) > 1}
    if dup_paths:
        raise ValueError(f"Duplicate react_route in NAV_PAGES: {dup_paths}")

    missing = {p.route_key for p in NAV_PAGES} - ALL_NAV_PAGE_KEYS
    if missing:
        raise ValueError(f"NAV_PAGES keys missing from ALL_NAV_PAGE_KEYS: {missing}")

    extra = ALL_NAV_PAGE_KEYS - {p.route_key for p in NAV_PAGES}
    if extra:
        raise ValueError(f"ALL_NAV_PAGE_KEYS not in NAV_PAGES dispatch: {extra}")


def build_page_dispatch(
    resolve: Callable[[NavPageDef], Callable[..., Any]],
) -> dict[str, Callable[..., Any]]:
    """Build runtime dispatch map from registry entries."""
    validate_registry()
    return {p.route_key: resolve(p) for p in NAV_PAGES}
