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
        "description": "Partner settlement statements for a date range.",
    },
    {
        "name": "banking",
        "description": "Bank statement import reconciliation readiness.",
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
