"""ICON-MODERNIZE-01 — inline SVG icon helper (no CDN, no icon fonts, currentColor)."""

from __future__ import annotations

import html

from registry.nav_keys import (
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
    NAV_PROFIT_LOSS,
    NAV_PURCHASES,
    NAV_RECEIVABLES,
    NAV_RECON_HEALTH,
    NAV_RECURRING_EXPENSES,
    NAV_REPORTS,
    NAV_SALES,
    NAV_TODAY_SUMMARY,
    NAV_TRIAL_BALANCE,
    NAV_TXN_LEDGER,
    NAV_VENDORS,
    NAV_WORKERS,
    NAV_YEAR_END_CLOSE,
)

# Lucide-style stroke paths (24×24 viewBox).
_ICON_PATHS: dict[str, str] = {
    "home": '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "plus": '<path d="M5 12h14"/><path d="M12 5v14"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    "briefcase": '<rect width="20" height="14" x="2" y="7" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    "card": '<rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/>',
    "repeat": '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
    "cart": '<circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/>',
    "wallet": '<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>',
    "moon": '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "building": '<rect width="16" height="20" x="4" y="2" rx="2" ry="2"/><path d="M9 22v-4h6v4"/><path d="M8 6h.01"/><path d="M16 6h.01"/><path d="M12 6h.01"/><path d="M12 10h.01"/><path d="M12 14h.01"/><path d="M16 10h.01"/><path d="M16 14h.01"/><path d="M8 10h.01"/><path d="M8 14h.01"/>',
    "file": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/>',
    "pin": '<line x1="12" x2="12" y1="17" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/>',
    "package": '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
    "landmark": '<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>',
    "bank": '<line x1="2" x2="22" y1="12" y2="12"/><path d="M12 2v20"/><path d="m17 7 5 5-5 5"/><path d="m7 7-5 5 5 5"/>',
    "bar-chart": '<line x1="12" x2="12" y1="20" y2="10"/><line x1="18" x2="18" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="16"/>',
    "menu": '<line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="18" y2="18"/>',
    "dollar": '<line x1="12" x2="12" y1="2" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    "trending": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "folder": '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "notebook": '<path d="M2 6h4"/><path d="M2 10h4"/><path d="M2 14h4"/><path d="M2 18h4"/><rect width="16" height="20" x="4" y="2" rx="2"/><path d="M16 2v20"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>',
    "calendar-check": '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/><path d="m9 16 2 2 4-4"/>',
    "scale": '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "user": '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    "settings": '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "save": '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "hard-hat": '<path d="M2 18a1 1 0 0 0 1 1h18a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v2z"/><path d="M10 10V5a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v5"/><path d="M4 15v-3a6 6 0 0 1 6-6h0"/><path d="M14 6h0a6 6 0 0 1 6 6v3"/>',
    "circle": '<circle cx="12" cy="12" r="10"/>',
}

_ICON_SIZES_PX: dict[str, int] = {
    "nav": 16,
    "action": 12,
    "tab": 15,
    "inline": 14,
}

PAGE_ICON: dict[str, str] = {
    NAV_HOME: "home",
    NAV_TODAY_SUMMARY: "calendar",
    NAV_NEW_TRANSACTION: "plus",
    NAV_TXN_LEDGER: "book",
    NAV_SALES: "briefcase",
    NAV_EXPENSES: "card",
    NAV_RECURRING_EXPENSES: "repeat",
    NAV_PURCHASES: "cart",
    NAV_CASH_RECONCILIATION: "wallet",
    NAV_EXTERNAL_SALES_VERIFICATION: "scale",
    NAV_END_OF_DAY_CLOSE: "moon",
    NAV_CUSTOMERS: "users",
    NAV_VENDORS: "building",
    NAV_RECEIVABLES: "file",
    NAV_PAYABLES: "pin",
    NAV_INVENTORY: "package",
    NAV_BANKING: "bank",
    NAV_REPORTS: "bar-chart",
    NAV_PROFIT_LOSS: "dollar",
    NAV_BALANCE_SHEET: "landmark",
    NAV_CASH_FLOW: "trending",
    NAV_GENERAL_LEDGER: "folder",
    NAV_TRIAL_BALANCE: "scale",
    NAV_JOURNAL_ENTRIES: "notebook",
    NAV_FISCAL_PERIODS: "calendar",
    NAV_YEAR_END_CLOSE: "calendar-check",
    NAV_BUDGET: "dollar",
    NAV_CHART_OF_ACCOUNTS: "search",
    NAV_RECON_HEALTH: "activity",
    NAV_PARTNER_ACCOUNTS: "bank",
    NAV_WORKERS: "hard-hat",
    NAV_COMPANY_SETTINGS: "settings",
    NAV_MEMBERS: "user",
    NAV_AUDIT_LOG: "shield",
    NAV_BACKUP_RESTORE: "save",
    NAV_OPENING_BALANCES: "zap",
    NAV_MY_ACCOUNT: "user",
}

# TXH — plain-text action labels (st.button cannot safely embed SVG).
TXH_ACTION_VIEW = "View"
TXH_ACTION_EDIT = "Edit"
TXH_ACTION_REPEAT = "Repeat"
TXH_ACTION_DUPLICATE = "Copy"
TXH_ACTION_VOID = "Void"

TXH_ACTION_LABELS: dict[str, str] = {
    "view": TXH_ACTION_VIEW,
    "edit": TXH_ACTION_EDIT,
    "repeat": TXH_ACTION_REPEAT,
    "duplicate": TXH_ACTION_DUPLICATE,
    "void": TXH_ACTION_VOID,
}


def icon_svg(
    name: str,
    *,
    size: str = "nav",
    decorative: bool = True,
    title: str | None = None,
) -> str:
    """Return inline SVG markup using currentColor (safe inside st.markdown)."""
    paths = _ICON_PATHS.get(name, _ICON_PATHS["circle"])
    px = _ICON_SIZES_PX.get(size, 16)
    if decorative and not title:
        aria = ' aria-hidden="true"'
        title_el = ""
    elif title:
        aria = f' role="img" aria-label="{html.escape(title)}"'
        title_el = f"<title>{html.escape(title)}</title>"
    else:
        aria = ""
        title_el = ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{px}" height="{px}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'class="erp-icon erp-icon--{size}"{aria}>{title_el}{paths}</svg>'
    )


def nav_page_icon_html(page_key: str, *, title: str | None = None) -> str:
    """Sidebar / mobile nav leading icon for a canonical page key."""
    icon_name = PAGE_ICON.get(page_key, "circle")
    return f'<span class="erp-nav-icon">{icon_svg(icon_name, size="nav", title=title)}</span>'
