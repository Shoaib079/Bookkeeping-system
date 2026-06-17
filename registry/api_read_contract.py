"""FASTAPI-REACT-04 — frozen read API contract (OpenAPI + error mapping).

Machine-readable mirror of ``docs/FASTAPI_REACT_04_READ_API_BOUNDARY_AUDIT.md``.
"""

from __future__ import annotations

from typing import Final

CONTRACT_DOC: Final[str] = "docs/FASTAPI_REACT_04_READ_API_BOUNDARY_AUDIT.md"
P1_CONTRACT_TEST: Final[str] = "tests/test_fastapi_p1_api_contract.py"
P1_READ_TEST: Final[str] = "tests/test_fastapi_p1_read_endpoints.py"

# Stable GET read spine (OpenAPI paths).
READ_API_PATHS: tuple[str, ...] = (
    "/health",
    "/auth/login",
    "/auth/me",
    "/auth/companies",
    "/api/v1/reports/profit-loss",
    "/api/v1/reports/balance-sheet",
    "/api/v1/ledger",
    "/api/v1/receivables",
    "/api/v1/payables",
    "/api/v1/partners/{partner_id}/statement",
    "/api/v1/banking/readiness",
)

READ_API_TAGS: tuple[str, ...] = (
    "health",
    "auth",
    "reports",
    "ledger",
    "receivables",
    "payables",
    "partners",
    "banking",
)

ERROR_CONTRACT_MARKERS: tuple[str, ...] = (
    "401 missing/invalid bearer",
    "400 missing company",
    "403 membership/permission",
    "404 not found",
    "422 validation",
)

HTTP_ERROR_MARKERS: tuple[str, ...] = (
    "active_company_id",
    "require_company_membership",
)

READ_SERVICE_MODULES: tuple[str, ...] = (
    "services/read_reports.py",
    "services/read_ledger.py",
    "services/read_ar_ap.py",
    "services/read_partner_statement.py",
    "services/read_balances.py",
    "services/read_reconciliation.py",
)

SERIALIZATION_MODULE: Final[str] = "api/serialization.py"

DEFERRED_GAP_IDS: tuple[str, ...] = (
    "TD-PS-01",
    "TD-PS-03",
)
