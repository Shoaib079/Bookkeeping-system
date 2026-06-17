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
        "name": "vendors",
        "description": "Vendor directory for reconciliation pickers.",
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
