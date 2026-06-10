"""Canonical nav page keys → i18n message keys (Phase 15)."""

from __future__ import annotations

from registry.icon_glyphs import (
    NAV_CHART_OF_ACCOUNTS,
    NAV_FISCAL_PERIODS,
    NAV_GENERAL_LEDGER,
    NAV_JOURNAL_ENTRIES,
    NAV_RECURRING_EXPENSES,
    NAV_TXN_LEDGER,
)

# Streamlit nav_selection / _PAGE_DISPATCH keys (emoji + English title).
NAV_PAGE_I18N: dict[str, str] = {
    "🏠 Home": "nav.home",
    "📅 Today's Summary": "nav.today_summary",
    "➕ New Transaction": "nav.new_transaction",
    NAV_TXN_LEDGER: "nav.transaction_ledger",
    "💼 Sales": "nav.sales",
    "💳 Expenses": "nav.expenses",
    NAV_RECURRING_EXPENSES: "nav.recurring_expenses",
    "🛒 Purchases": "nav.purchases",
    "💸 Cash Reconciliation": "nav.cash_reconciliation",
    "🌙 End-of-Day Close": "nav.end_of_day_close",
    "👥 Customers": "nav.customers",
    "🏢 Vendors": "nav.vendors",
    "📄 Receivables": "nav.receivables",
    "📌 Payables": "nav.payables",
    "📦 Inventory": "nav.inventory",
    "🏦 Banking": "nav.banking",
    "📊 Reports": "nav.reports",
    "💰 Profit & Loss": "nav.profit_loss",
    "🏛️ Balance Sheet": "nav.balance_sheet",
    "💸 Cash Flow": "nav.cash_flow",
    NAV_GENERAL_LEDGER: "nav.general_ledger",
    "⚖️ Trial Balance": "nav.trial_balance",
    NAV_JOURNAL_ENTRIES: "nav.journal_entries",
    NAV_FISCAL_PERIODS: "nav.fiscal_periods",
    "📆 Year-End Close": "nav.year_end_close",
    "💰 Budget": "nav.budget",
    NAV_CHART_OF_ACCOUNTS: "nav.chart_of_accounts",
    "🩺 Recon Health": "nav.recon_health",
    "🏦 Partner Accounts": "nav.partner_accounts",
    "👷 Workers": "nav.workers",
    "🏢 Company Settings": "nav.company_settings",
    "👤 Members": "nav.members",
    "🕵️ Audit Log": "nav.audit_log",
    "💾 Backup & Restore": "nav.backup_restore",
    "⚡ Opening Balances": "nav.opening_balances",
    "👤 My Account": "nav.my_account",
}
