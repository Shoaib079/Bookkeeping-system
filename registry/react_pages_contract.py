"""FASTAPI-REACT-06 — frozen first React pages contract.

Machine-readable mirror of ``docs/FASTAPI_REACT_06_REACT_PAGES_AUDIT.md``.
"""

from __future__ import annotations

from typing import Final

CONTRACT_DOC: Final[str] = "docs/FASTAPI_REACT_06_REACT_PAGES_AUDIT.md"
BOOTSTRAP_CONTRACT: Final[str] = "registry/react_bootstrap_contract.py"
READ_CONTRACT: Final[str] = "registry/api_read_contract.py"

# Operator / build-time gate — default off; PlaceholderPage remains for gated routes.
FEATURE_FLAG_ENV: Final[str] = "ERP_REACT_PAGES"
VITE_FEATURE_FLAG_ENV: Final[str] = "VITE_ERP_REACT_PAGES"

# (react_path, page_component, page_key)
REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/", "HomePage", "home"),
    ("/books/general-ledger", "LedgerPage", "ledger"),
    ("/books/trial-balance", "TrialBalancePage", "trial_balance"),
    ("/reports/balance-sheet", "BalanceSheetPage", "balance_sheet"),
    ("/receivables", "ReceivablesPage", "receivables"),
    ("/payables", "PayablesPage", "payables"),
    ("/partners", "PartnerStatementPage", "partners"),
    ("/banking", "BankingReadinessPage", "banking"),
    ("/reports", "ReportsPage", "reports"),
    ("/reports/profit-loss", "ProfitLossPage", "profit_loss"),
    ("/reports/cash-flow", "CashFlowPage", "cash_flow"),
    ("/transactions/ledger", "TransactionLedgerPage", "transaction_ledger"),
    ("/books/chart-of-accounts", "ChartOfAccountsPage", "chart_of_accounts"),
    ("/vendors", "VendorsPage", "vendors"),
    ("/sales", "SalesPage", "sales"),
    ("/expenses", "ExpensesPage", "expenses"),
    ("/workers", "WorkersPage", "workers"),
    ("/customers", "CustomersPage", "customers"),
    ("/purchases", "PurchasesPage", "purchases"),
    ("/banking/accounts", "BankAccountsPage", "bank_accounts"),
    ("/books/fiscal-periods", "FiscalPeriodsPage", "fiscal_periods"),
    ("/books/journal-entries", "JournalEntriesPage", "journal_entries"),
    ("/books/recon-health", "ReconHealthPage", "recon_health"),
    ("/books/opening-balances", "OpeningBalancesPage", "opening_balances"),
    ("/settings/audit-log", "AuditLogPage", "audit_log"),
    ("/settings/members", "MembersPage", "members"),
    ("/inventory", "InventoryPage", "inventory"),
    ("/books/budget", "BudgetPage", "budget"),
    ("/settings/permissions", "PermissionsPage", "permissions"),
)

HOME_READ_API_PATHS: tuple[str, ...] = (
    "/auth/me",
    "/auth/companies",
    "/api/v1/reports/profit-loss",
)

LEDGER_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/ledger",
)

TRIAL_BALANCE_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/reports/trial-balance",
)

RECON_HEALTH_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/reconciliation/health",
)

OPENING_BALANCES_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/opening-balances",
)

AUDIT_LOG_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/audit-log",
)

MEMBERS_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/members",
)

INVENTORY_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/products",
)

BUDGET_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/reports/budget-vs-actual",
)

PERMISSIONS_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/permissions/members",
    "/api/v1/permissions/effective",
)

BALANCE_SHEET_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/reports/balance-sheet",
)

RECEIVABLES_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/receivables",
)

PAYABLES_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/payables",
)

PARTNER_STATEMENT_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/partners/{partner_id}/statement",
)

BANKING_READINESS_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/banking/readiness",
)

BANK_ACCOUNTS_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/bank-accounts",
)

FISCAL_PERIODS_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/fiscal-periods",
)

JOURNAL_ENTRIES_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/journal-entries",
)

REPORTS_HUB_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/reports/profit-loss",
)

PROFIT_LOSS_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/reports/profit-loss",
)

CASH_FLOW_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/reports/cash-flow",
)

TRANSACTION_LEDGER_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/transactions",
)

CHART_OF_ACCOUNTS_LIST_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/chart-of-accounts",
)

CHART_OF_ACCOUNTS_READ_API_PATHS: tuple[str, ...] = CHART_OF_ACCOUNTS_LIST_READ_API_PATHS

VENDORS_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/vendors",
)

SALES_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/sales",
)

EXPENSES_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/expenses",
)

WORKERS_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/workers",
)

CUSTOMERS_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/customers",
)

PURCHASES_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/purchases",
)

PARTNERS_LIST_READ_API_PATHS: tuple[str, ...] = (
    "/api/v1/partners",
)

PICKER_FRONTEND_FILES: tuple[str, ...] = (
    "frontend/src/components/CoaAccountPicker.tsx",
    "frontend/src/components/PartnerPicker.tsx",
)

REQUIRED_FRONTEND_FILES: tuple[str, ...] = (
    "frontend/src/config/featureFlags.ts",
    "frontend/src/lib/api/session.ts",
    "frontend/src/lib/api/types.ts",
    "frontend/src/pages/HomePage.tsx",
    "frontend/src/pages/LedgerPage.tsx",
    "frontend/src/pages/TrialBalancePage.tsx",
    "frontend/src/pages/BalanceSheetPage.tsx",
    "frontend/src/pages/ReceivablesPage.tsx",
    "frontend/src/pages/PayablesPage.tsx",
    "frontend/src/pages/PartnerStatementPage.tsx",
    "frontend/src/pages/BankingReadinessPage.tsx",
    "frontend/src/pages/ReportsPage.tsx",
    "frontend/src/pages/ProfitLossPage.tsx",
    "frontend/src/pages/CashFlowPage.tsx",
    "frontend/src/pages/TransactionLedgerPage.tsx",
    "frontend/src/pages/ChartOfAccountsPage.tsx",
    "frontend/src/pages/VendorsPage.tsx",
    "frontend/src/pages/SalesPage.tsx",
    "frontend/src/pages/ExpensesPage.tsx",
    "frontend/src/pages/WorkersPage.tsx",
    "frontend/src/pages/CustomersPage.tsx",
    "frontend/src/pages/PurchasesPage.tsx",
    "frontend/src/pages/BankAccountsPage.tsx",
    "frontend/src/pages/FiscalPeriodsPage.tsx",
    "frontend/src/pages/JournalEntriesPage.tsx",
    "frontend/src/pages/ReconHealthPage.tsx",
    "frontend/src/pages/OpeningBalancesPage.tsx",
    "frontend/src/pages/AuditLogPage.tsx",
    "frontend/src/pages/MembersPage.tsx",
    "frontend/src/pages/InventoryPage.tsx",
    "frontend/src/pages/BudgetPage.tsx",
    "frontend/src/pages/PermissionsPage.tsx",
    "frontend/src/components/ReadApiSetup.tsx",
    *PICKER_FRONTEND_FILES,
)

FORBIDDEN_FRONTEND_PATTERNS: tuple[str, ...] = (
    "create_journal_entry",
    "post_cash_sale",
    "services/posting",
    "streamlit",
    "apiPut",
    "apiDelete",
)

# Frozen for FR-06 audit tests (do not mutate).
FR06_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/", "HomePage", "home"),
    ("/books/general-ledger", "LedgerPage", "ledger"),
)

FR06_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-17",
    "TD-PS-01",
    "chart-of-accounts picker",
)

# Frozen for FR-17 audit tests (do not mutate).
FR17_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/reports/balance-sheet", "BalanceSheetPage", "balance_sheet"),
    ("/receivables", "ReceivablesPage", "receivables"),
    ("/payables", "PayablesPage", "payables"),
)

FR17_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-18",
    "partner statement page",
    "banking readiness page",
    "chart-of-accounts picker",
)

# Frozen for FR-18 audit tests (do not mutate).
FR18_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-19",
    "chart-of-accounts picker",
    "partner picker",
    "transaction ledger read page",
)

FR18_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/partners", "PartnerStatementPage", "partners"),
    ("/banking", "BankingReadinessPage", "banking"),
)

# Frozen for FR-19 audit tests (do not mutate).
FR19_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-20",
    "transaction ledger read page",
    "cash flow read page",
    "chart-of-accounts picker",
)

FR19_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/reports", "ReportsPage", "reports"),
    ("/reports/profit-loss", "ProfitLossPage", "profit_loss"),
)

DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-41",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-24 audit tests (pages contract; do not mutate).
FR24_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-25",
)

# Frozen for FR-25 audit tests (do not mutate).
FR25_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/books/chart-of-accounts", "ChartOfAccountsPage", "chart_of_accounts"),
    ("/vendors", "VendorsPage", "vendors"),
)

FR25_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-26",
    "sales read page",
    "expenses read page",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-26 audit tests (do not mutate).
FR26_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/sales", "SalesPage", "sales"),
    ("/expenses", "ExpensesPage", "expenses"),
)

FR26_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-27",
    "workers read page",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-27 audit tests (do not mutate).
FR27_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/workers", "WorkersPage", "workers"),
)

FR27_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-28",
    "customers read page",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-28 audit tests (do not mutate).
FR28_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/customers", "CustomersPage", "customers"),
)

FR28_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-29",
    "purchases read page",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-29 audit tests (do not mutate).
FR29_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/purchases", "PurchasesPage", "purchases"),
)

FR29_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-30",
    "bank accounts read page",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-30 audit tests (do not mutate).
FR30_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/banking/accounts", "BankAccountsPage", "bank_accounts"),
)

FR30_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-31",
    "fiscal periods read page",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-31 audit tests (do not mutate).
FR31_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/books/fiscal-periods", "FiscalPeriodsPage", "fiscal_periods"),
)

FR31_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-32",
    "journal entries read page",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-32 audit tests (do not mutate).
FR32_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/books/journal-entries", "JournalEntriesPage", "journal_entries"),
)

FR32_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-33",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-33 audit tests (do not mutate).
FR33_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/books/trial-balance", "TrialBalancePage", "trial_balance"),
)

FR33_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-34",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-34 audit tests (do not mutate).
FR34_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/books/recon-health", "ReconHealthPage", "recon_health"),
)

FR34_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-35",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-35 audit tests (do not mutate).
FR35_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/books/opening-balances", "OpeningBalancesPage", "opening_balances"),
)

FR35_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-36",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-36 audit tests (do not mutate).
FR36_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/settings/audit-log", "AuditLogPage", "audit_log"),
)

FR36_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-37",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-37 audit tests (do not mutate).
FR37_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/settings/members", "MembersPage", "members"),
)

FR37_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-38",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-38 audit tests (do not mutate).
FR38_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/inventory", "InventoryPage", "inventory"),
)

FR38_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-39",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-39 audit tests (do not mutate).
FR39_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/books/budget", "BudgetPage", "budget"),
)

FR39_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-40",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-40 audit tests (do not mutate).
FR40_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/settings/permissions", "PermissionsPage", "permissions"),
)

FR40_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-41",
    "production COMMIT_MODE_* flip",
)

# Frozen for FR-21 audit tests (do not mutate).
FR21_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-22",
    "bank account picker",
    "worker picker",
)

# Frozen for FR-20 audit tests (do not mutate).
FR20_DEFERRED_ITEMS: tuple[str, ...] = (
    "FASTAPI-REACT-21",
    "chart-of-accounts picker",
    "partner picker",
)

FR20_REAL_PAGE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("/reports/cash-flow", "CashFlowPage", "cash_flow"),
    ("/transactions/ledger", "TransactionLedgerPage", "transaction_ledger"),
)
