"""NAV-ARCH — navigation registry (single source of truth).

S2: derives ``_PAGE_DISPATCH``.
S3A: derives ``_NAV_ACCORDION`` and ``_NAV_DIRECT_PAGES``.
S3B: derives ``_NAV_ROLE_PAGES`` (static role gates; permission overrides stay in app.py).
S3C: derives ``_MOBILE_BOTTOM_NAV`` and ``_MOBILE_HUB_CONFIG``.
S4: freezes ``react_route`` contract — see ``docs/NAV_ARCH_REACT_ROUTE_CONTRACT.md``.
"""

from __future__ import annotations

import re
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

NAV_ROLE_NAMES: tuple[RoleName, ...] = (
    "owner",
    "manager",
    "cashier",
    "partner",
    "viewer",
)

AccordionPage = tuple[None, str]
NavAccordionRow = tuple[str, str, list[AccordionPage]]
NavAccordionByKey = dict[str, tuple[str, list[AccordionPage]]]


@dataclass(frozen=True)
class NavAccordionGroupDef:
    """Desktop sidebar accordion group metadata (S3A)."""

    group_key: str
    legacy_label: str
    label_i18n: str
    list_order: int


NAV_ACCORDION_GROUPS: tuple[NavAccordionGroupDef, ...] = (
    NavAccordionGroupDef("transactions", "Record transactions", "nav.group.transactions", 0),
    NavAccordionGroupDef("people", "Customers & suppliers", "nav.group.people", 1),
    NavAccordionGroupDef("close_day", "Closings", "nav.group.close_day", 2),
    NavAccordionGroupDef("recipe_costing", "Recipe Costing", "nav.group.recipe_costing", 3),
    NavAccordionGroupDef("statements", "Financial Statements", "nav.group.statements", 4),
    NavAccordionGroupDef("accounting", "Books", "nav.group.accounting", 5),
    NavAccordionGroupDef("team", "Team & partners", "nav.group.team", 6),
    NavAccordionGroupDef("settings", "Settings", "nav.group.settings", 7),
)


@dataclass(frozen=True)
class NavPageDef:
    """Per-page navigation metadata — dispatch + desktop surfaces."""

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
    sidebar_direct_order: int | None = None
    accordion_group: str | None = None
    accordion_order: int | None = None
    permission_gate: frozenset[str] | None = None


def _page(
    route_key: str,
    render_fn: str,
    react_route: str,
    order: int,
    *,
    roles: frozenset[RoleName] = frozenset(),
    session_arg: bool = True,
    sidebar_direct: bool = False,
    sidebar_direct_order: int | None = None,
    accordion_group: str | None = None,
    accordion_order: int | None = None,
    permission_gate: frozenset[str] | None = None,
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
        sidebar_direct_order=sidebar_direct_order,
        accordion_group=accordion_group,
        accordion_order=accordion_order,
        permission_gate=permission_gate,
    )


# Order matches legacy ``_PAGE_DISPATCH`` in app.py (NAV-ARCH-S2 parity).
NAV_PAGES: tuple[NavPageDef, ...] = (
    _page(NAV_HOME, "render_dashboard", "/", 0, roles=_ALL_ROLES, sidebar_direct=True, sidebar_direct_order=0),
    _page(
        NAV_NEW_TRANSACTION,
        "render_add_transaction",
        "/transactions/new",
        1,
        roles=_OMC,
        sidebar_direct=True,
        sidebar_direct_order=1,
    ),
    _page(
        NAV_TXN_LEDGER,
        "render_transaction_ledger_page",
        "/transactions/ledger",
        2,
        roles=_OMCPV,
        sidebar_direct=True,
        sidebar_direct_order=2,
    ),
    _page(NAV_SALES, "render_sales", "/sales", 3, roles=_OMCP, accordion_group="transactions", accordion_order=0),
    _page(NAV_EXPENSES, "render_expenses", "/expenses", 4, roles=_OMC, accordion_group="transactions", accordion_order=1),
    _page(
        NAV_STAFF_EXPENSE_CAPTURE,
        "render_staff_expense_capture",
        "/expenses/staff-capture",
        5,
        roles=_OWNER_ONLY,
        accordion_group="transactions",
        accordion_order=2,
        permission_gate=frozenset({"submit_expense_drafts", "approve_expense_drafts"}),
    ),
    _page(
        NAV_RECURRING_EXPENSES,
        "render_recurring_expenses",
        "/expenses/recurring",
        6,
        roles=_OMC,
        accordion_group="transactions",
        accordion_order=4,
    ),
    _page(NAV_PURCHASES, "render_purchases", "/purchases", 7, roles=_OMC, accordion_group="transactions", accordion_order=3),
    _page(
        NAV_CASH_RECONCILIATION,
        "render_cash_reconciliation",
        "/closings/cash-recon",
        8,
        roles=_OMC,
        accordion_group="close_day",
        accordion_order=0,
    ),
    _page(
        NAV_EXTERNAL_SALES_VERIFICATION,
        "render_external_sales_verification",
        "/closings/external-sales",
        9,
        roles=_OMC,
        accordion_group="close_day",
        accordion_order=1,
    ),
    _page(NAV_RC_INGREDIENTS, "render_recipe_ingredients", "/recipes/ingredients", 10, roles=_OM, accordion_group="recipe_costing", accordion_order=0),
    _page(NAV_RC_RECIPES, "render_recipe_recipes", "/recipes", 11, roles=_OM, accordion_group="recipe_costing", accordion_order=1),
    _page(
        NAV_RC_COST_BREAKDOWN,
        "render_recipe_cost_breakdown",
        "/recipes/cost-breakdown",
        12,
        roles=_OM,
        accordion_group="recipe_costing",
        accordion_order=2,
    ),
    _page(NAV_RC_MENU_ITEMS, "render_recipe_menu_items", "/recipes/menu-items", 13, roles=_OM, accordion_group="recipe_costing", accordion_order=3),
    _page(
        NAV_END_OF_DAY_CLOSE,
        "render_end_of_day_close",
        "/closings/eod",
        14,
        roles=_OMC,
        accordion_group="close_day",
        accordion_order=2,
    ),
    _page(NAV_CUSTOMERS, "render_customers", "/customers", 15, roles=_OM, accordion_group="people", accordion_order=0),
    _page(NAV_VENDORS, "render_vendors", "/vendors", 16, roles=_OM, accordion_group="people", accordion_order=1),
    _page(NAV_RECEIVABLES, "render_receivables", "/receivables", 17, roles=_OMCP, accordion_group="people", accordion_order=2),
    _page(NAV_PAYABLES, "render_payables", "/payables", 18, roles=_OMC, accordion_group="people", accordion_order=3),
    _page(NAV_INVENTORY, "render_inventory", "/inventory", 19, roles=_OM, sidebar_direct=True, sidebar_direct_order=3),
    _page(NAV_BANKING, "render_banking", "/banking", 20, roles=_OMC, sidebar_direct=True, sidebar_direct_order=4),
    _page(NAV_REPORTS, "render_reports", "/reports", 21, roles=_OMCPV, sidebar_direct=True, sidebar_direct_order=5),
    _page(
        NAV_PROFIT_LOSS,
        "render_profit_loss_page",
        "/reports/profit-loss",
        22,
        roles=_OMCPV,
        accordion_group="statements",
        accordion_order=0,
    ),
    _page(
        NAV_BALANCE_SHEET,
        "render_balance_sheet_page",
        "/reports/balance-sheet",
        23,
        roles=_OMCPV,
        accordion_group="statements",
        accordion_order=1,
    ),
    _page(
        NAV_CASH_FLOW,
        "render_cash_flow_page",
        "/reports/cash-flow",
        24,
        roles=_OMCPV,
        accordion_group="statements",
        accordion_order=2,
    ),
    _page(NAV_GENERAL_LEDGER, "render_general_ledger", "/books/general-ledger", 25, roles=_OM, accordion_group="accounting", accordion_order=0),
    _page(NAV_TRIAL_BALANCE, "render_trial_balance", "/books/trial-balance", 26, roles=_OM, accordion_group="accounting", accordion_order=3),
    _page(NAV_JOURNAL_ENTRIES, "render_journal_entries", "/books/journal-entries", 27, roles=_OM, accordion_group="accounting", accordion_order=2),
    _page(NAV_FISCAL_PERIODS, "render_fiscal_periods", "/books/fiscal-periods", 28, roles=_OM, accordion_group="accounting", accordion_order=4),
    _page(NAV_YEAR_END_CLOSE, "render_year_end_close", "/books/year-end-close", 29, roles=_OM, accordion_group="accounting", accordion_order=5),
    _page(NAV_BUDGET, "render_budget", "/books/budget", 30, roles=_OM, accordion_group="accounting", accordion_order=6),
    _page(NAV_CHART_OF_ACCOUNTS, "render_chart_of_accounts", "/books/chart-of-accounts", 31, roles=_OM, accordion_group="accounting", accordion_order=1),
    _page(NAV_RECON_HEALTH, "render_reconciliation_health", "/books/recon-health", 32, roles=_OM, accordion_group="accounting", accordion_order=7),
    _page(NAV_PARTNER_ACCOUNTS, "render_partner_accounts", "/partners", 33, roles=frozenset({"owner", "manager", "partner"}), accordion_group="team", accordion_order=0),
    _page(NAV_WORKERS, "render_workers", "/workers", 34, roles=_OM, accordion_group="team", accordion_order=1),
    _page(NAV_COMPANY_SETTINGS, "render_company_settings", "/settings/company", 35, roles=_OWNER_ONLY, accordion_group="settings", accordion_order=0),
    _page(NAV_MEMBERS, "render_user_management", "/settings/members", 36, roles=_OWNER_ONLY, accordion_group="settings", accordion_order=1),
    _page(NAV_PERMISSIONS, "render_permissions_management", "/settings/permissions", 37, roles=_OWNER_ONLY, accordion_group="settings", accordion_order=2),
    _page(NAV_AUDIT_LOG, "render_audit_log", "/settings/audit-log", 38, roles=_OM, accordion_group="settings", accordion_order=3),
    _page(
        NAV_BACKUP_RESTORE,
        "render_backup_restore",
        "/settings/backup-restore",
        39,
        roles=_OWNER_ONLY,
        session_arg=False,
        accordion_group="settings",
        accordion_order=4,
    ),
    _page(NAV_OPENING_BALANCES, "render_opening_balances", "/books/opening-balances", 40, roles=_OM, accordion_group="accounting", accordion_order=8),
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


REACT_ROUTE_SAFE_RE = re.compile(r"^/(?:[a-z0-9]+(?:/[a-z0-9-]+)*)?$")


def validate_react_route_contract() -> None:
    """Raise ``ValueError`` when the frozen React route contract is violated."""
    validate_registry()
    routes = react_routes()
    if set(routes) != {p.route_key for p in NAV_PAGES}:
        raise ValueError("react_routes() keys must match NAV_PAGES route_key set")

    for page in NAV_PAGES:
        path = page.react_route
        if not path or not path.startswith("/"):
            raise ValueError(f"react_route must be absolute path for {page.route_key!r}")
        if " " in path or "//" in path:
            raise ValueError(f"Unsafe react_route for {page.route_key!r}: {path!r}")
        if not REACT_ROUTE_SAFE_RE.match(path):
            raise ValueError(f"react_route failed safe naming for {page.route_key!r}: {path!r}")

    root_paths = [path for path in routes.values() if path == "/"]
    if len(root_paths) != 1:
        raise ValueError(f"Exactly one root react_route required, got {len(root_paths)}")


def react_route_contract_rows() -> list[tuple[str, str]]:
    """Ordered ``(route_key, react_route)`` rows for docs and migration tooling."""
    validate_react_route_contract()
    return [(p.route_key, p.react_route) for p in NAV_PAGES]


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


def validate_desktop_surfaces() -> None:
    """Raise on invalid or incomplete desktop accordion/direct derivation."""
    group_keys = {g.group_key for g in NAV_ACCORDION_GROUPS}
    direct: list[NavPageDef] = []
    accordion: list[NavPageDef] = []
    for page in NAV_PAGES:
        if page.hidden:
            continue
        if page.sidebar_direct_order is not None:
            direct.append(page)
        if page.accordion_group is not None:
            accordion.append(page)
        if page.sidebar_direct_order is not None and page.accordion_group is not None:
            raise ValueError(f"{page.route_key!r} cannot be both direct and accordion")
        if page.accordion_group is not None:
            if page.accordion_group not in group_keys:
                raise ValueError(f"Unknown accordion_group {page.accordion_group!r} for {page.route_key!r}")
            if page.accordion_order is None:
                raise ValueError(f"Missing accordion_order for {page.route_key!r}")
        if page.sidebar_direct_order is not None and not page.sidebar_direct:
            raise ValueError(f"{page.route_key!r} has sidebar_direct_order without sidebar_direct")

    if not direct:
        raise ValueError("No sidebar direct pages defined")
    if not accordion:
        raise ValueError("No accordion pages defined")

    direct_orders = [p.sidebar_direct_order for p in direct]
    if len(direct_orders) != len(set(direct_orders)):
        raise ValueError("Duplicate sidebar_direct_order values")

    for group in NAV_ACCORDION_GROUPS:
        members = [p for p in accordion if p.accordion_group == group.group_key]
        if not members:
            raise ValueError(f"Accordion group {group.group_key!r} has no pages")
        orders = [p.accordion_order for p in members]
        if len(orders) != len(set(orders)):
            raise ValueError(f"Duplicate accordion_order in group {group.group_key!r}")

    surfaced = {p.route_key for p in direct} | {p.route_key for p in accordion}
    dispatch_keys = {p.route_key for p in NAV_PAGES if not p.hidden}
    missing = dispatch_keys - surfaced - {NAV_MY_ACCOUNT}
    if missing:
        raise ValueError(f"Dispatch routes missing desktop surface: {missing}")


def build_nav_direct_pages() -> list[str]:
    """Derive ``_NAV_DIRECT_PAGES`` from registry."""
    validate_desktop_surfaces()
    pages = [p for p in NAV_PAGES if p.sidebar_direct_order is not None]
    pages.sort(key=lambda p: p.sidebar_direct_order or 0)
    return [p.route_key for p in pages]


def build_nav_accordion() -> list[NavAccordionRow]:
    """Derive ``_NAV_ACCORDION`` from registry."""
    validate_desktop_surfaces()
    rows: list[NavAccordionRow] = []
    for group in sorted(NAV_ACCORDION_GROUPS, key=lambda g: g.list_order):
        members = [p for p in NAV_PAGES if p.accordion_group == group.group_key]
        members.sort(key=lambda p: p.accordion_order or 0)
        rows.append(
            (
                group.group_key,
                group.legacy_label,
                [(None, p.route_key) for p in members],
            )
        )
    return rows


def build_nav_accordion_by_key() -> NavAccordionByKey:
    """Derive ``_NAV_ACCORDION_BY_KEY`` from registry."""
    return {gk: (glabel, gpages) for gk, glabel, gpages in build_nav_accordion()}


def build_nav_all_pages() -> list[str]:
    """All sidebar-routed pages (direct + accordion); excludes ``NAV_MY_ACCOUNT``."""
    return build_nav_direct_pages() + [
        page_key
        for _group_key, _label, pages in build_nav_accordion()
        for _icon, page_key in pages
    ]


def validate_role_gates() -> None:
    """Raise on incomplete or inconsistent static role metadata."""
    validate_registry()
    all_pages = set(build_nav_all_pages())

    for page in NAV_PAGES:
        if page.hidden:
            continue
        if not page.roles:
            raise ValueError(f"Missing roles for {page.route_key!r}")
        unknown = page.roles - set(NAV_ROLE_NAMES)
        if unknown:
            raise ValueError(f"Unknown roles {unknown} on {page.route_key!r}")

    for role in NAV_ROLE_NAMES:
        if role == "owner":
            continue
        derived = {p.route_key for p in NAV_PAGES if role in p.roles}
        if NAV_MY_ACCOUNT not in derived:
            raise ValueError(f"{role!r} missing NAV_MY_ACCOUNT in roles metadata")

    owner_sidebar = set(all_pages)
    owner_derived = {
        p.route_key
        for p in NAV_PAGES
        if "owner" in p.roles and p.route_key != NAV_MY_ACCOUNT
    }
    if owner_derived != owner_sidebar:
        missing = owner_sidebar - owner_derived
        extra = owner_derived - owner_sidebar
        raise ValueError(f"Owner role metadata mismatch: missing={missing}, extra={extra}")

    # NAV-UX-02-S5 — staff expenses: static owner list only; runtime permission override in app.py.
    staff = nav_page_by_key(NAV_STAFF_EXPENSE_CAPTURE)
    if staff.permission_gate is None:
        raise ValueError("Staff Expenses must declare permission_gate")
    if "owner" not in staff.roles or staff.roles != _OWNER_ONLY:
        raise ValueError("Staff Expenses static roles must be owner-only")

    for restricted, roles in (
        (NAV_MEMBERS, _OWNER_ONLY),
        (NAV_PERMISSIONS, _OWNER_ONLY),
        (NAV_BACKUP_RESTORE, _OWNER_ONLY),
        (NAV_COMPANY_SETTINGS, _OWNER_ONLY),
    ):
        page = nav_page_by_key(restricted)
        if page.roles != roles:
            raise ValueError(f"{restricted!r} must remain owner-only in static roles")


def build_nav_role_pages() -> dict[str, list[str]]:
    """Derive ``_NAV_ROLE_PAGES`` static allow-lists from registry role metadata."""
    validate_role_gates()
    all_pages = build_nav_all_pages()
    role_pages: dict[str, list[str]] = {
        "owner": list(all_pages) + [NAV_MY_ACCOUNT],
    }
    for role in NAV_ROLE_NAMES:
        if role == "owner":
            continue
        role_pages[role] = [
            p.route_key for p in sorted(NAV_PAGES, key=lambda row: row.order) if role in p.roles
        ]
    return role_pages


MobileBottomSlot = tuple[str, str, str, str, str, str]
MobileHubEntry = tuple[str, str, str | None, str | None]

# Legacy mobile session hub keys (pre MOBILE-UX-01-A); not bottom-bar slots.
_MOBILE_HUB_LEGACY_SESSION_KEYS = frozenset({"people", "banking"})


def build_mobile_bottom_nav() -> tuple[MobileBottomSlot, ...]:
    """Derive ``_MOBILE_BOTTOM_NAV`` — five slots: Home | Money | New | Reports | More."""
    return (
        ("home", NAV_HOME, "nav.bottom.home", "home", NAV_HOME, "home"),
        ("hub", "money", "nav.bottom.money", "money", "Money", "landmark"),
        ("new", NAV_NEW_TRANSACTION, "nav.bottom.new", "new", "New", "plus"),
        ("hub", "reports", "nav.bottom.reports", "reports", NAV_REPORTS, "bar-chart"),
        ("hub", "more", "nav.bottom.more", "more", "More", "menu"),
    )


def build_mobile_hub_config() -> dict[str, list[MobileHubEntry]]:
    """Derive ``_MOBILE_HUB_CONFIG`` — money / reports / people / more hub entries."""
    return {
        "money": [
            ("section", "close", None, "nav.mobile.section.close"),
            ("page", NAV_CASH_RECONCILIATION, None, None),
            ("page", NAV_EXTERNAL_SALES_VERIFICATION, None, None),
            ("page", NAV_END_OF_DAY_CLOSE, None, None),
            ("section", "bank", None, "nav.mobile.section.bank"),
            ("page", NAV_BANKING, None, None),
            ("page", NAV_RECON_HEALTH, None, None),
            ("banking_import", "import", None, "nav.mobile.banking_import"),
        ],
        "reports": [
            ("page", NAV_PROFIT_LOSS, None, None),
            ("page", NAV_BALANCE_SHEET, None, None),
            ("page", NAV_CASH_FLOW, None, None),
            ("page", NAV_TXN_LEDGER, None, None),
            ("report_sales", "sales", None, "nav.mobile.reports_sales"),
            ("report_expenses", "expenses", None, "nav.mobile.reports_expenses"),
        ],
        "people": [
            ("page", NAV_CUSTOMERS, None, None),
            ("page", NAV_VENDORS, None, "nav.mobile.suppliers"),
            ("page", NAV_RECEIVABLES, None, None),
            ("page", NAV_PAYABLES, None, None),
            ("page", NAV_WORKERS, None, None),
            ("page", NAV_PARTNER_ACCOUNTS, None, None),
        ],
        "more": [
            ("open_hub", "people", None, "nav.mobile.hub.people"),
            ("section", "books", None, "nav.mobile.section.books"),
            ("accordion", "accounting", None, None),
            ("section", "history", None, "nav.mobile.section.history"),
            ("accordion", "transactions", None, None),
            ("page", NAV_INVENTORY, None, None),
            ("section", "admin", None, "nav.mobile.section.admin"),
            ("page", NAV_COMPANY_SETTINGS, None, None),
            ("page", NAV_MEMBERS, None, None),
            ("page", NAV_BACKUP_RESTORE, None, None),
            ("page", NAV_AUDIT_LOG, None, None),
        ],
    }


def build_mobile_hub_keys(
    bottom_nav: tuple[MobileBottomSlot, ...] | None = None,
) -> frozenset[str]:
    """Derive ``_MOBILE_HUB_KEYS`` from bottom-bar hubs + legacy session aliases."""
    validate_mobile_surfaces()
    nav = bottom_nav or build_mobile_bottom_nav()
    bar_hubs = {payload for kind, payload, *_rest in nav if kind == "hub"}
    return frozenset(bar_hubs) | _MOBILE_HUB_LEGACY_SESSION_KEYS


def validate_mobile_surfaces() -> None:
    """Raise on invalid mobile bottom nav / hub configuration."""
    bottom = build_mobile_bottom_nav()
    if len(bottom) != 5:
        raise ValueError(f"Mobile bottom nav must have exactly 5 slots, got {len(bottom)}")

    hub_config = build_mobile_hub_config()
    accordion_groups = {g.group_key for g in NAV_ACCORDION_GROUPS}
    dispatch_keys = {p.route_key for p in NAV_PAGES}

    bar_hub_targets = {payload for kind, payload, *_ in bottom if kind == "hub"}
    missing_hubs = bar_hub_targets - set(hub_config)
    if missing_hubs:
        raise ValueError(f"Bottom hub targets missing from hub config: {missing_hubs}")

    mobile_page_keys: list[str] = []
    for hub_key, entries in hub_config.items():
        for kind, payload, *_rest in entries:
            if kind == "page":
                if payload not in dispatch_keys:
                    raise ValueError(f"Mobile hub page {payload!r} missing from dispatch")
                mobile_page_keys.append(payload)
            elif kind == "accordion":
                if payload not in accordion_groups:
                    raise ValueError(f"Mobile accordion {payload!r} not in NAV_ACCORDION_GROUPS")
            elif kind == "open_hub":
                if payload not in hub_config:
                    raise ValueError(f"open_hub target {payload!r} missing from hub config")

    for hub_key, entries in hub_config.items():
        pages = [payload for kind, payload, *_ in entries if kind == "page"]
        hub_dupes = {p for p in pages if pages.count(p) > 1}
        if hub_dupes:
            raise ValueError(f"Duplicate page entries in hub {hub_key!r}: {hub_dupes}")


def build_page_dispatch(
    resolve: Callable[[NavPageDef], Callable[..., Any]],
) -> dict[str, Callable[..., Any]]:
    """Build runtime dispatch map from registry entries."""
    validate_registry()
    return {p.route_key: resolve(p) for p in NAV_PAGES}
