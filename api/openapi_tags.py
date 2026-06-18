"""OpenAPI tag metadata for the read-only API."""

from __future__ import annotations

OPENAPI_TAGS: list[dict[str, str]] = [
    {
        "name": "health",
        "description": "Liveness and readiness probes. No authentication required.",
    },
    {
        "name": "auth",
        "description": "Authentication — bearer tokens, identity, and company access.",
    },
    {
        "name": "reports",
        "description": "Financial statements (profit & loss, balance sheet, cash flow).",
    },
    {
        "name": "chart-of-accounts",
        "description": "Chart of accounts list for pickers and read-only views.",
    },
    {
        "name": "ledger",
        "description": (
            "General ledger lines for one account. "
            "Unpaginated in P1; pagination may be added later."
        ),
    },
    {
        "name": "receivables",
        "description": "Accounts receivable listing and aging summary.",
    },
    {
        "name": "payables",
        "description": "Accounts payable listing and aging summary.",
    },
    {
        "name": "partners",
        "description": "Partner directory and settlement statements.",
    },
    {
        "name": "banking",
        "description": "Bank statement import reconciliation readiness.",
    },
    {
        "name": "reconciliation-health",
        "description": "GL-vs-subledger reconciliation health checks.",
    },
    {
        "name": "opening-balances",
        "description": "Opening balance equity summary and OB posting status.",
    },
    {
        "name": "audit-log",
        "description": "Company audit trail entries (owner/manager read).",
    },
    {
        "name": "members",
        "description": "Company membership roster (owner read).",
    },
    {
        "name": "permissions",
        "description": "Effective permission provenance for members (owner read).",
    },
    {
        "name": "company-settings",
        "description": "Company profile and financial settings snapshot (owner read).",
    },
    {
        "name": "backup-status",
        "description": "Local backup inventory snapshot (owner read).",
    },
    {
        "name": "my-account",
        "description": "Self profile snapshot for the active company context.",
    },
    {
        "name": "end-of-day-closes",
        "description": "End-of-day close history for the active company.",
    },
    {
        "name": "cash-reconciliations",
        "description": "Daily cash reconciliation history for the active company.",
    },
    {
        "name": "external-sales-verifications",
        "description": "External sales verification history for the active company.",
    },
    {
        "name": "recurring-expenses",
        "description": "Recurring expense templates and drafts for the active company.",
    },
    {
        "name": "bank-accounts",
        "description": "Bank account directory for write-tab pickers and read-only views.",
    },
    {
        "name": "workers",
        "description": "Staff directory for write-tab pickers.",
    },
    {
        "name": "bank-statement-rows",
        "description": "Imported bank statement rows for reconciliation pickers.",
    },
    {
        "name": "fiscal-periods",
        "description": "Fiscal period directory for closing pickers.",
    },
    {
        "name": "year-end-closes",
        "description": "Year-end close history for the active company.",
    },
    {
        "name": "journal-entries",
        "description": "Posted journal entries with debit/credit lines.",
    },
    {
        "name": "vendors",
        "description": "Vendor directory for reconciliation pickers.",
    },
    {
        "name": "customers",
        "description": "Customer directory read-only list.",
    },
    {
        "name": "products",
        "description": "Product catalog for inventory read-only views.",
    },
    {
        "name": "receivable-sales",
        "description": "Open credit sales for receivable payment pickers.",
    },
    {
        "name": "sales",
        "description": "Sales register read-only list.",
    },
    {
        "name": "expenses",
        "description": "Expense register read-only list.",
    },
    {
        "name": "purchases",
        "description": "Purchase register read-only list.",
    },
    {
        "name": "profit-allocations",
        "description": "Profit allocation directory for closing void pickers.",
    },
    {
        "name": "transactions",
        "description": "Cross-module transaction history for a date range.",
    },
    {
        "name": "writes",
        "description": "Transactional write endpoints (feature-flagged per slice).",
    },
]
