"""ICON-MODERNIZE-01 — canonical text-only nav page keys (routing / dispatch)."""

from __future__ import annotations

# ── Core nav page keys (no emoji — icons via registry/icon_svg.py) ────────────
NAV_HOME = "Home"
NAV_TODAY_SUMMARY = "Today's Summary"
NAV_NEW_TRANSACTION = "New Transaction"
NAV_TXN_LEDGER = "Transaction Ledger"
NAV_SALES = "Sales"
NAV_EXPENSES = "Expenses"
NAV_RECURRING_EXPENSES = "Recurring Expenses"
NAV_PURCHASES = "Purchases"
NAV_CASH_RECONCILIATION = "Cash Reconciliation"
NAV_END_OF_DAY_CLOSE = "End-of-Day Close"
NAV_CUSTOMERS = "Customers"
NAV_VENDORS = "Vendors"
NAV_RECEIVABLES = "Receivables"
NAV_PAYABLES = "Payables"
NAV_INVENTORY = "Inventory"
NAV_BANKING = "Banking"
NAV_REPORTS = "Reports"
NAV_PROFIT_LOSS = "Profit & Loss"
NAV_BALANCE_SHEET = "Balance Sheet"
NAV_CASH_FLOW = "Cash Flow"
NAV_GENERAL_LEDGER = "General Ledger"
NAV_TRIAL_BALANCE = "Trial Balance"
NAV_JOURNAL_ENTRIES = "Journal Entries"
NAV_FISCAL_PERIODS = "Fiscal Periods"
NAV_YEAR_END_CLOSE = "Year-End Close"
NAV_BUDGET = "Budget"
NAV_CHART_OF_ACCOUNTS = "Chart of Accounts"
NAV_RECON_HEALTH = "Recon Health"
NAV_PARTNER_ACCOUNTS = "Partner Accounts"
NAV_WORKERS = "Workers"
NAV_COMPANY_SETTINGS = "Company Settings"
NAV_MEMBERS = "Members"
NAV_AUDIT_LOG = "Audit Log"
NAV_BACKUP_RESTORE = "Backup & Restore"
NAV_OPENING_BALANCES = "Opening Balances"
NAV_MY_ACCOUNT = "My Account"

ALL_NAV_PAGE_KEYS: frozenset[str] = frozenset(
    {
        NAV_HOME,
        NAV_TODAY_SUMMARY,
        NAV_NEW_TRANSACTION,
        NAV_TXN_LEDGER,
        NAV_SALES,
        NAV_EXPENSES,
        NAV_RECURRING_EXPENSES,
        NAV_PURCHASES,
        NAV_CASH_RECONCILIATION,
        NAV_END_OF_DAY_CLOSE,
        NAV_CUSTOMERS,
        NAV_VENDORS,
        NAV_RECEIVABLES,
        NAV_PAYABLES,
        NAV_INVENTORY,
        NAV_BANKING,
        NAV_REPORTS,
        NAV_PROFIT_LOSS,
        NAV_BALANCE_SHEET,
        NAV_CASH_FLOW,
        NAV_GENERAL_LEDGER,
        NAV_TRIAL_BALANCE,
        NAV_JOURNAL_ENTRIES,
        NAV_FISCAL_PERIODS,
        NAV_YEAR_END_CLOSE,
        NAV_BUDGET,
        NAV_CHART_OF_ACCOUNTS,
        NAV_RECON_HEALTH,
        NAV_PARTNER_ACCOUNTS,
        NAV_WORKERS,
        NAV_COMPANY_SETTINGS,
        NAV_MEMBERS,
        NAV_AUDIT_LOG,
        NAV_BACKUP_RESTORE,
        NAV_OPENING_BALANCES,
        NAV_MY_ACCOUNT,
    }
)

# Migrate persisted nav_selection / bookmarks from emoji-prefixed keys (LOGO-BUG / ICON-SWEEP).
LEGACY_NAV_ALIASES: dict[str, str] = {
    "🏠 Home": NAV_HOME,
    "📅 Today's Summary": NAV_TODAY_SUMMARY,
    "➕ New Transaction": NAV_NEW_TRANSACTION,
    "📒 Transaction Ledger": NAV_TXN_LEDGER,
    "📒️ Transaction Ledger": NAV_TXN_LEDGER,
    "💼 Sales": NAV_SALES,
    "💳 Expenses": NAV_EXPENSES,
    "🔁 Recurring Expenses": NAV_RECURRING_EXPENSES,
    "🛒 Purchases": NAV_PURCHASES,
    "💸 Cash Reconciliation": NAV_CASH_RECONCILIATION,
    "🌙 End-of-Day Close": NAV_END_OF_DAY_CLOSE,
    "👥 Customers": NAV_CUSTOMERS,
    "🏢 Vendors": NAV_VENDORS,
    "📄 Receivables": NAV_RECEIVABLES,
    "📌 Payables": NAV_PAYABLES,
    "📦 Inventory": NAV_INVENTORY,
    "🏦 Banking": NAV_BANKING,
    "📊 Reports": NAV_REPORTS,
    "💰 Profit & Loss": NAV_PROFIT_LOSS,
    "🏛 Balance Sheet": NAV_BALANCE_SHEET,
    "🏛️ Balance Sheet": NAV_BALANCE_SHEET,
    "💸 Cash Flow": NAV_CASH_FLOW,
    "🗂 General Ledger": NAV_GENERAL_LEDGER,
    "🗂️ General Ledger": NAV_GENERAL_LEDGER,
    "⚖ Trial Balance": NAV_TRIAL_BALANCE,
    "⚖️ Trial Balance": NAV_TRIAL_BALANCE,
    "📓 Journal Entries": NAV_JOURNAL_ENTRIES,
    "📓️ Journal Entries": NAV_JOURNAL_ENTRIES,
    "🗓 Fiscal Periods": NAV_FISCAL_PERIODS,
    "🗓️ Fiscal Periods": NAV_FISCAL_PERIODS,
    "📆 Year-End Close": NAV_YEAR_END_CLOSE,
    "💰 Budget": NAV_BUDGET,
    "🔍 Chart of Accounts": NAV_CHART_OF_ACCOUNTS,
    "🔍️ Chart of Accounts": NAV_CHART_OF_ACCOUNTS,
    "🩺 Recon Health": NAV_RECON_HEALTH,
    "🏦 Partner Accounts": NAV_PARTNER_ACCOUNTS,
    "👷 Workers": NAV_WORKERS,
    "🏢 Company Settings": NAV_COMPANY_SETTINGS,
    "👤 Members": NAV_MEMBERS,
    "🕵 Audit Log": NAV_AUDIT_LOG,
    "🕵️ Audit Log": NAV_AUDIT_LOG,
    "💾 Backup & Restore": NAV_BACKUP_RESTORE,
    "⚡ Opening Balances": NAV_OPENING_BALANCES,
    "👤 My Account": NAV_MY_ACCOUNT,
    "📥 Bank Statement Import": NAV_BANKING,
    "Bank Statement Import": NAV_BANKING,
}


def normalize_nav_key(page_key: str | None) -> str:
    """Map legacy emoji nav keys to canonical text-only keys."""
    if not page_key:
        return NAV_HOME
    return LEGACY_NAV_ALIASES.get(page_key, page_key)
