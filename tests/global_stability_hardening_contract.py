"""GLOBAL-STABILITY-HARDENING-01 — shared no-bypass contract constants and scanners.

Contract-test-only layer derived from ``docs/GLOBAL_STABILITY_AUDIT_01_STOP_REPORT.md``.
Runtime code must not import this module.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]

AUDIT_STOP_REPORT = ROOT / "docs" / "GLOBAL_STABILITY_AUDIT_01_STOP_REPORT.md"

# ── S1 Date — canonical owners + scoped surfaces ─────────────────────────────

DATE_UTILS_MODULE = ROOT / "registry" / "date_utils.py"
DATE_INPUT_MODULE = ROOT / "ui" / "date_input.py"
AT_DATE_OWNERSHIP_MODULE = ROOT / "services" / "at_date_ownership.py"

DATE_CANONICAL_MARKERS = (
    "parse_bound_date",
    "render_preferred_date_input",
    "resolve_submit_date",
    "capture_submit_resolved_date",
)

# (label, resolver) → resolver returns source text to scan.
DATE_SCOPED_SURFACES: tuple[tuple[str, Callable[[], str]], ...] = (
    (
        "Add Transaction desktop date",
        lambda: inspect.getsource(__import__("app", fromlist=["_at_render_desktop_date_field"])._at_render_desktop_date_field),
    ),
    (
        "Add Transaction submit resolve",
        lambda: inspect.getsource(__import__("app", fromlist=["_at_resolve_submit_date"])._at_resolve_submit_date),
    ),
    (
        "Transaction History date filters",
        lambda: inspect.getsource(__import__("app", fromlist=["_render_txh_date_filters"])._render_txh_date_filters),
    ),
    (
        "Transaction History edit row",
        lambda: inspect.getsource(__import__("app", fromlist=["_txh_render_row_panels"])._txh_render_row_panels),
    ),
    (
        "Staff Capture submit form date",
        lambda: inspect.getsource(
            __import__("ui.staff_capture", fromlist=["_render_submit_form"])._render_submit_form
        ),
    ),
    (
        "Banking unsettled card sales date range",
        lambda: inspect.getsource(
            __import__("ui.banking", fromlist=["render_unsettled_card_sales_list_block"]).render_unsettled_card_sales_list_block
        ),
    ),
)

# Explicit native-calendar exceptions (classified debt — must not grow silently).
DATE_NATIVE_CALENDAR_EXCEPTIONS: dict[str, str] = {
    "_at_render_desktop_date_field": "OBS-004 AT SSOT — native st.date_input + at_date_ownership",
    "_txh_render_row_panels": "TXH inline edit — native calendar; amount uses amount_input",
    "_mob_at_render_date_picker_sheet": "Mobile AT native picker delegates to at_date_ownership",
}

DATE_SCOPED_REQUIRED: dict[str, tuple[str, ...]] = {
    "Add Transaction desktop date": ('key="at_date"', "st.date_input"),
    "Add Transaction submit resolve": ("resolve_submit_date",),
    "Transaction History date filters": ("parse_bound_date", "render_preferred_date_input"),
    "Transaction History edit row": ("date_input", "edit_date_"),
    "Staff Capture submit form date": ("parse_bound_date", "render_preferred_date_input"),
    "Banking unsettled card sales date range": ("parse_bound_date", "render_preferred_date_input"),
}

# Forbidden in AT submit/gather paths (bypasses ownership SSOT).
AT_DATE_SUBMIT_FORBIDDEN = (
    "datetime.strptime",
    "parse_date_text(",
    'st.session_state["at_date"] =',
)

# ── S2 Money — canonical amount_input path ───────────────────────────────────

AMOUNT_INPUT_DEF = "def amount_input"
PARSE_AMOUNT_DEF = "def _parse_amount_str"

MONEY_SCOPED_SURFACES: tuple[tuple[str, Callable[[], str]], ...] = (
    (
        "TXH edit panels",
        lambda: inspect.getsource(__import__("app", fromlist=["_txh_render_row_panels"])._txh_render_row_panels),
    ),
    (
        "Add Transaction submit",
        lambda: inspect.getsource(__import__("app", fromlist=["_at_process_submit"])._at_process_submit),
    ),
    (
        "Staff Capture submit amounts",
        lambda: inspect.getsource(
            __import__("ui.staff_capture", fromlist=["_render_submit_form"])._render_submit_form
        ),
    ),
)

MONEY_SCOPED_REQUIRED: dict[str, tuple[str, ...]] = {
    "TXH edit panels": ("amount_input", "_txh_edit_amount_changed"),
    "Add Transaction submit": ("_parse_amount_str", "_at_gather_submit_fields"),
    "Staff Capture submit amounts": ("amount_input",),
}

# st.number_input allowed in money-adjacent surfaces (key, reason).
MONEY_NUMBER_INPUT_EXCEPTIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "render_cash_reconciliation": (
        ("actual_cash_input", "physical cash count — not a GL posting amount field"),
    ),
    "render_bank_statement_import": (
        ("bsi_header_row", "spreadsheet header row index — not money"),
        ("stl_header_row", "settlement header row index — not money"),
    ),
    "render_journal_entries": (
        ("__no_key__", "line count widget may omit explicit key — classified non-money"),
    ),
}

MONEY_SCAN_APP_FUNCTIONS = (
    "_txh_render_row_panels",
    "_at_process_submit",
    "amount_input",
    "_parse_amount_str",
)

# ── S3 Error formatting ──────────────────────────────────────────────────────

REACT_API_ERROR = ROOT / "frontend" / "src" / "lib" / "api" / "apiError.ts"
REACT_READ_CLIENT = ROOT / "frontend" / "src" / "lib" / "api" / "client.ts"
REACT_WRITE_CLIENT = ROOT / "frontend" / "src" / "lib" / "api" / "writeClient.ts"
REACT_PAGES_DIR = ROOT / "frontend" / "src" / "pages"

REACT_LEGACY_STRING_DETAIL = 'String((err as { detail: string }).detail)'

# Frozen debt baseline (2026-06-20) — read pages not yet migrated to errorMessageFromCatch.
REACT_LEGACY_ERROR_PAGES_FROZEN: frozenset[str] = frozenset(
    {
        "AuditLogPage.tsx",
        "BackupRestorePage.tsx",
        "BalanceSheetPage.tsx",
        "BankAccountsPage.tsx",
        "BankingReadinessPage.tsx",
        "BudgetPage.tsx",
        "CashFlowPage.tsx",
        "CashReconPage.tsx",
        "ChartOfAccountsPage.tsx",
        "CompanySettingsPage.tsx",
        "CustomersPage.tsx",
        "EodClosePage.tsx",
        "ExpensesPage.tsx",
        "ExternalSalesPage.tsx",
        "FiscalPeriodsPage.tsx",
        "InventoryPage.tsx",
        "JournalEntriesPage.tsx",
        "LedgerPage.tsx",
        "MembersPage.tsx",
        "MyAccountPage.tsx",
        "OpeningBalancesPage.tsx",
        "PartnerStatementPage.tsx",
        "PayablesPage.tsx",
        "PermissionsPage.tsx",
        "ProfitLossPage.tsx",
        "PurchasesPage.tsx",
        "ReceivablesPage.tsx",
        "RecipeCostBreakdownPage.tsx",
        "RecipeIngredientsPage.tsx",
        "RecipeMenuItemsPage.tsx",
        "RecipesPage.tsx",
        "ReconHealthPage.tsx",
        "RecurringExpensesPage.tsx",
        "ReportsPage.tsx",
        "SalesPage.tsx",
        "StaffCapturePage.tsx",
        "TransactionLedgerPage.tsx",
        "TrialBalancePage.tsx",
        "VendorsPage.tsx",
        "WorkersPage.tsx",
        "YearEndClosePage.tsx",
    }
)

REACT_WRITE_ERROR_EXCEPTIONS: dict[str, str] = {
    "NewTransactionPage.tsx": "writeClient normalizes detail before apiErr.detail display",
    "HomePage.tsx": "errorMessageFromCatch (REACT-LOCAL-OBS-02 canonical)",
    "PlaceholderPage.tsx": "no API error surface",
}

PYTHON_ERROR_HELPERS: tuple[str, ...] = (
    "_bsi_statement_post_error_message",
)

# ── S4 Banking import ownership ──────────────────────────────────────────────

BANKING_IMPORT_CANONICAL = (
    "banking_apply_statement_import_upload_route",
    "banking_navigate_statement_import_upload",
    "render_bank_statement_import",
    "bsi_file_uploader",
)


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def find_st_number_input_keys(src: str) -> list[str]:
    keys: list[str] = []
    for match in re.finditer(r"st\.number_input\(", src):
        chunk = src[match.start() : match.start() + 400]
        key_match = re.search(r"key=[\"']([^\"']+)[\"']", chunk)
        keys.append(key_match.group(1) if key_match else "__no_key__")
    return keys


def react_pages_with_legacy_error_pattern() -> set[str]:
    found: set[str] = set()
    for path in REACT_PAGES_DIR.glob("*Page.tsx"):
        if REACT_LEGACY_STRING_DETAIL in path.read_text(encoding="utf-8"):
            found.add(path.name)
    return found
