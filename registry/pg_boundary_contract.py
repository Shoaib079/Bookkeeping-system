"""FASTAPI-REACT-07 — PG / API boundary matrix contract (TD-PS-01).

Machine-readable mirror of ``docs/FASTAPI_REACT_07_PG_BOUNDARY_MATRIX_AUDIT.md``.
"""

from __future__ import annotations

from typing import Final

CONTRACT_DOC: Final[str] = "docs/FASTAPI_REACT_07_PG_BOUNDARY_MATRIX_AUDIT.md"
COMMIT_CONTRACT: Final[str] = "registry/commit_boundary_contract.py"
POSTING_BOUNDARY_MODULE: Final[str] = "services/posting_boundary.py"
COMMIT_MODES_MODULE: Final[str] = "services/commit_modes.py"
UNIT_OF_WORK_MODULE: Final[str] = "services/unit_of_work.py"

FEATURE_FLAG_ENV_PREFIX: Final[str] = "COMMIT_MODE_"
DEFAULT_COMMIT_MODE: Final[str] = "internal"

# API write path modules that must wire ``is_boundary_mode`` + ``boundary_commit_scope``.
API_WRITE_MODULES: tuple[str, ...] = (
    "services/write_sales.py",
    "services/write_expenses.py",
    "services/write_purchases.py",
    "services/write_receivable_payments.py",
    "services/write_voids.py",
    "services/write_banking.py",
    "services/write_partner_worker.py",
    "services/write_reconciliation.py",
    "services/write_closing.py",
)

POSTING_BOUNDARY_SCOPES: tuple[str, ...] = (
    "posting_boundary_scope",
    "recon_boundary_scope",
    "void_boundary_scope",
)

# Families pinned for API-style matrix (posting + void spine).
API_MATRIX_POSTING_FAMILIES: tuple[str, ...] = (
    "post_cash_sale",
    "post_expense",
)

API_MATRIX_VOID_FAMILY: Final[str] = "void_cascade"

API_MATRIX_TEST: Final[str] = "tests/test_fastapi_react_07_api_boundary_matrix.py"
PG_MATRIX_TEST: Final[str] = "tests/test_fastapi_react_07_pg_boundary_matrix.py"
API_MATRIX_HELPER: Final[str] = "tests/helpers/api_boundary_matrix.py"

# P2 write suites with boundary commit characterization.
P2_BOUNDARY_COMMIT_TEST_FILES: tuple[str, ...] = (
    "tests/test_fastapi_p2_sales_write.py",
    "tests/test_fastapi_p2_expense_write.py",
    "tests/test_fastapi_p2_purchase_write.py",
    "tests/test_fastapi_p2_receivable_payment_write.py",
    "tests/test_fastapi_p2_void_write.py",
    "tests/test_fastapi_p2_banking_write.py",
    "tests/test_fastapi_p2_partner_worker_write.py",
    "tests/test_fastapi_p2_reconciliation_write.py",
    "tests/test_fastapi_p2_closing_write.py",
)

P2_BOUNDARY_TEST_CLASS_MARKERS: tuple[str, ...] = (
    "TestSalesWriteBoundaryCommit",
    "TestExpenseWriteBoundaryCommit",
    "TestPurchaseWriteBoundaryCommit",
    "TestReceivablePaymentWriteBoundaryCommit",
    "TestVoidWriteBoundaryCommit",
    "TestBankingWriteBoundaryCommit",
    "TestPartnerWorkerWriteBoundaryCommit",
    "TestReconciliationWriteBoundaryCommit",
    "TestBoundaryCommit",
)

POSTGRES_OPTIONAL_ENV: Final[str] = "ERP_TEST_POSTGRES_URL"
POSTGRES_OPTIONAL_DOC: Final[str] = "docs/POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md"

DEFERRED_ITEMS: tuple[str, ...] = (
    "production COMMIT_MODE_* flip",
    "React write pages",
    "TD-PS-03",
    "bank_transaction PG matrix",
    "equity_movement PG matrix",
)

REMAINING_RISKS: tuple[str, ...] = (
    "Float money on PostgreSQL",
    "scaffold-only families",
    "nested boundary depth",
    "operator env flip without dual-run green",
)
