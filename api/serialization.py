"""JSON serialization helpers for read-service DTOs (API layer only)."""

from __future__ import annotations

import datetime
from typing import Any

from registry.partner_statement import (
    PartnerStatementData,
    PartnerStatementDetailLine,
    PartnerStatementWarning,
)
from services.read_ar_ap import PayablesPage, ReceivableRow, ReceivablesPage, PayableRow
from services.read_ledger import LedgerPage, LedgerRow
from services.read_reconciliation import ReadinessBlocker, StatementReadiness
from services.read_reports import (
    BalanceSheetStatement,
    CashFlowRow,
    CashFlowStatement,
    FinancialStatementLine,
    ProfitLossStatement,
)
from services.read_coa import CoaListPage, CoaRow
from services.read_customers import CustomerListRow, CustomersListPage
from services.read_bank_accounts import BankAccountListRow, BankAccountsListPage
from services.read_bank_statement_rows import (
    BankStatementRowListItem,
    BankStatementRowsListPage,
)
from services.read_fiscal_periods import FiscalPeriodListRow, FiscalPeriodsListPage
from services.read_profit_allocations import ProfitAllocationListRow, ProfitAllocationsListPage
from services.read_purchases import PurchaseListRow, PurchasesListPage
from services.read_receivable_sales import ReceivableSaleListRow, ReceivableSalesListPage
from services.read_sales import SalesListPage, SalesListRow
from services.read_expenses import ExpenseListRow, ExpensesListPage
from services.read_vendors import VendorListRow, VendorsListPage
from services.read_workers import WorkerListRow, WorkersListPage
from services.read_transaction_history import TransactionHistoryPage, TransactionHistoryRow


def _line_to_dict(line: FinancialStatementLine) -> dict[str, Any]:
    return {
        "code": line.code,
        "account_name": line.account_name,
        "amount": line.amount,
    }


def profit_loss_to_dict(stmt: ProfitLossStatement) -> dict[str, Any]:
    return {
        "start_date": stmt.start_date.isoformat(),
        "end_date": stmt.end_date.isoformat(),
        "income_lines": [_line_to_dict(l) for l in stmt.income_lines],
        "expense_lines": [_line_to_dict(l) for l in stmt.expense_lines],
        "total_income": stmt.total_income,
        "total_expenses": stmt.total_expenses,
        "net": stmt.net,
        "margin_pct": stmt.margin_pct,
        "is_profit": stmt.is_profit,
    }


def balance_sheet_to_dict(stmt: BalanceSheetStatement) -> dict[str, Any]:
    return {
        "as_of": stmt.as_of.isoformat(),
        "asset_lines": [_line_to_dict(l) for l in stmt.asset_lines],
        "liability_lines": [_line_to_dict(l) for l in stmt.liability_lines],
        "equity_lines": [_line_to_dict(l) for l in stmt.equity_lines],
        "net_income": stmt.net_income,
        "total_assets": stmt.total_assets,
        "total_liabilities": stmt.total_liabilities,
        "base_equity": stmt.base_equity,
        "total_equity": stmt.total_equity,
        "balanced": stmt.balanced,
        "imbalance": stmt.imbalance,
    }


def _cf_row_to_dict(row: CashFlowRow) -> dict[str, Any]:
    return {
        "date": row.date.isoformat(),
        "description": row.description,
        "type": row.type,
        "inflow": row.inflow,
        "outflow": row.outflow,
    }


def cash_flow_to_dict(stmt: CashFlowStatement) -> dict[str, Any]:
    return {
        "start_date": stmt.start_date.isoformat(),
        "end_date": stmt.end_date.isoformat(),
        "operating_rows": [_cf_row_to_dict(r) for r in stmt.operating_rows],
        "financing_rows": [_cf_row_to_dict(r) for r in stmt.financing_rows],
        "op_in": stmt.op_in,
        "op_out": stmt.op_out,
        "fin_in": stmt.fin_in,
        "fin_out": stmt.fin_out,
        "net_op": stmt.net_op,
        "net_fin": stmt.net_fin,
        "net_total": stmt.net_total,
        "has_cash_accounts": stmt.has_cash_accounts,
    }


def _transaction_history_row_to_dict(row: TransactionHistoryRow) -> dict[str, Any]:
    return {
        "date": row.date.isoformat(),
        "type": row.type,
        "reference": row.reference,
        "party": row.party,
        "category": row.category,
        "subcategory": row.subcategory,
        "amount": row.amount,
        "currency": row.currency,
        "method": row.method,
        "description": row.description,
        "status": row.status,
        "created_by": row.created_by,
        "source_type": row.source_type,
        "source_id": row.source_id,
        "company_id": row.company_id,
    }


def transaction_history_page_to_dict(page: TransactionHistoryPage) -> dict[str, Any]:
    return {
        "rows": [_transaction_history_row_to_dict(r) for r in page.rows],
        "filters": {
            "start_date": page.filters.start_date.isoformat(),
            "end_date": page.filters.end_date.isoformat(),
            "search_keyword": page.filters.search_keyword,
            "type_filter": page.filters.type_filter,
            "show_voided": page.filters.show_voided,
        },
        "row_count": page.row_count,
    }


def _coa_row_to_dict(row: CoaRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "account_code": row.account_code,
        "account_name": row.account_name,
        "account_type": row.account_type,
        "currency": row.currency,
        "is_active": row.is_active,
        "company_id": row.company_id,
    }


def coa_list_to_dict(page: CoaListPage) -> dict[str, Any]:
    return {
        "rows": [_coa_row_to_dict(r) for r in page.rows],
        "row_count": page.row_count,
    }


def _partner_list_row_to_dict(row: PartnerListRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "profit_share_pct": row.profit_share_pct,
        "is_active": row.is_active,
        "company_id": row.company_id,
    }


def partners_list_to_dict(page: PartnersListPage) -> dict[str, Any]:
    return {
        "rows": [_partner_list_row_to_dict(r) for r in page.rows],
        "row_count": page.row_count,
    }


def _bank_account_list_row_to_dict(row: BankAccountListRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "bank_name": row.bank_name,
        "kind": row.kind,
        "currency": row.currency,
        "is_active": row.is_active,
        "company_id": row.company_id,
    }


def bank_accounts_list_to_dict(page: BankAccountsListPage) -> dict[str, Any]:
    return {
        "rows": [_bank_account_list_row_to_dict(r) for r in page.rows],
        "row_count": page.row_count,
    }


def _worker_list_row_to_dict(row: WorkerListRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "role": row.role,
        "is_active": row.is_active,
        "company_id": row.company_id,
    }


def workers_list_to_dict(page: WorkersListPage) -> dict[str, Any]:
    return {
        "rows": [_worker_list_row_to_dict(r) for r in page.rows],
        "row_count": page.row_count,
    }


def _bank_statement_row_list_item_to_dict(row: BankStatementRowListItem) -> dict[str, Any]:
    return {
        "id": row.id,
        "import_row_index": row.import_row_index,
        "date": row.date.isoformat() if row.date is not None else None,
        "description": row.description,
        "amount": row.amount,
        "status": row.status,
        "currency": row.currency,
        "bank_statement_import_id": row.bank_statement_import_id,
        "company_id": row.company_id,
    }


def bank_statement_rows_list_to_dict(page: BankStatementRowsListPage) -> dict[str, Any]:
    return {
        "rows": [_bank_statement_row_list_item_to_dict(r) for r in page.rows],
        "row_count": page.row_count,
    }


def _fiscal_period_list_row_to_dict(row: FiscalPeriodListRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "start_date": row.start_date.isoformat(),
        "end_date": row.end_date.isoformat(),
        "is_closed": row.is_closed,
        "company_id": row.company_id,
    }


def fiscal_periods_list_to_dict(page: FiscalPeriodsListPage) -> dict[str, Any]:
    return {
        "rows": [_fiscal_period_list_row_to_dict(r) for r in page.rows],
        "row_count": page.row_count,
    }


def _vendor_list_row_to_dict(row: VendorListRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "is_active": row.is_active,
        "company_id": row.company_id,
    }


def vendors_list_to_dict(page: VendorsListPage) -> dict[str, Any]:
    return {
        "rows": [_vendor_list_row_to_dict(r) for r in page.rows],
        "row_count": page.row_count,
    }


def _customer_list_row_to_dict(row: CustomerListRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "contact": row.contact,
        "phone": row.phone,
        "email": row.email,
        "address": row.address,
        "is_active": row.is_active,
        "company_id": row.company_id,
    }


def customers_list_to_dict(page: CustomersListPage) -> dict[str, Any]:
    return {
        "rows": [_customer_list_row_to_dict(r) for r in page.rows],
        "row_count": page.row_count,
    }


def _receivable_sale_list_row_to_dict(row: ReceivableSaleListRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "invoice_number": row.invoice_number,
        "customer_name": row.customer_name,
        "date": row.date.isoformat(),
        "due_date": row.due_date.isoformat() if row.due_date is not None else None,
        "balance": row.balance,
        "status": row.status,
        "currency": row.currency,
        "company_id": row.company_id,
    }


def receivable_sales_list_to_dict(page: ReceivableSalesListPage) -> dict[str, Any]:
    return {
        "rows": [_receivable_sale_list_row_to_dict(r) for r in page.rows],
        "row_count": page.row_count,
    }


def _sales_list_row_to_dict(row: SalesListRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "date": row.date.isoformat(),
        "invoice_number": row.invoice_number,
        "customer_name": row.customer_name,
        "description": row.description,
        "amount": row.amount,
        "sale_type": row.sale_type,
        "paid_amount": row.paid_amount,
        "balance": row.balance,
        "due_date": row.due_date.isoformat() if row.due_date is not None else None,
        "status": row.status,
        "is_void": row.is_void,
        "currency": row.currency,
        "company_id": row.company_id,
    }


def sales_list_to_dict(page: SalesListPage) -> dict[str, Any]:
    return {
        "rows": [_sales_list_row_to_dict(r) for r in page.rows],
        "row_count": page.row_count,
    }


def _expense_list_row_to_dict(row: ExpenseListRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "date": row.date.isoformat(),
        "expense_type": row.expense_type,
        "category": row.category,
        "description": row.description,
        "amount": row.amount,
        "payment_method": row.payment_method,
        "employee_name": row.employee_name,
        "is_void": row.is_void,
        "currency": row.currency,
        "company_id": row.company_id,
    }


def expenses_list_to_dict(page: ExpensesListPage) -> dict[str, Any]:
    return {
        "rows": [_expense_list_row_to_dict(r) for r in page.rows],
        "row_count": page.row_count,
    }


def _purchase_list_row_to_dict(row: PurchaseListRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "date": row.date.isoformat(),
        "vendor_name": row.vendor_name,
        "purchase_number": row.purchase_number,
        "purchase_type": row.purchase_type,
        "gl_debit": row.gl_debit,
        "amount": row.amount,
        "description": row.description,
        "is_void": row.is_void,
        "currency": row.currency,
        "company_id": row.company_id,
    }


def purchases_list_to_dict(page: PurchasesListPage) -> dict[str, Any]:
    return {
        "rows": [_purchase_list_row_to_dict(r) for r in page.rows],
        "row_count": page.row_count,
    }


def _profit_allocation_list_row_to_dict(row: ProfitAllocationListRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "fiscal_period_id": row.fiscal_period_id,
        "period_name": row.period_name,
        "allocated_at": row.allocated_at.isoformat(),
        "total_net_income": row.total_net_income,
        "is_void": row.is_void,
        "company_id": row.company_id,
    }


def profit_allocations_list_to_dict(page: ProfitAllocationsListPage) -> dict[str, Any]:
    return {
        "rows": [_profit_allocation_list_row_to_dict(r) for r in page.rows],
        "row_count": page.row_count,
    }


def _optional_date(value: datetime.date | None) -> str | None:
    return value.isoformat() if value is not None else None


def ledger_row_to_dict(row: LedgerRow) -> dict[str, Any]:
    return {
        "date": row.date.isoformat(),
        "reference": row.reference,
        "description": row.description,
        "debit": row.debit,
        "credit": row.credit,
        "running_balance": row.running_balance,
        "account_id": row.account_id,
        "account_code": row.account_code,
        "account_name": row.account_name,
        "journal_entry_id": row.journal_entry_id,
        "company_id": row.company_id,
        "journal_entry_line_id": row.journal_entry_line_id,
    }


def ledger_page_to_dict(page: LedgerPage) -> dict[str, Any]:
    return {
        "rows": [ledger_row_to_dict(r) for r in page.rows],
        "filters": {
            "account_id": page.filters.account_id,
            "start_date": _optional_date(page.filters.start_date),
            "end_date": _optional_date(page.filters.end_date),
            "search_keyword": page.filters.search_keyword,
        },
        "opening_balance": page.opening_balance,
        "closing_balance": page.closing_balance,
        "row_count": page.row_count,
        "total_debit": page.total_debit,
        "total_credit": page.total_credit,
        "account_type": page.account_type,
        "current_balance": page.current_balance,
    }


def receivable_row_to_dict(row: ReceivableRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "invoice_number": row.invoice_number,
        "customer_name": row.customer_name,
        "date": row.date.isoformat(),
        "due_date": _optional_date(row.due_date),
        "amount": row.amount,
        "paid_amount": row.paid_amount,
        "balance": row.balance,
        "status": row.status,
        "description": row.description,
        "currency": row.currency,
        "company_id": row.company_id,
    }


def receivables_page_to_dict(page: ReceivablesPage) -> dict[str, Any]:
    return {
        "rows": [receivable_row_to_dict(r) for r in page.rows],
        "filters": {
            "search_keyword": page.filters.search_keyword,
            "customer_filter": page.filters.customer_filter,
            "status_filter": page.filters.status_filter,
        },
        "outstanding": page.outstanding,
        "overdue": page.overdue,
        "open_count": page.open_count,
        "showing_count": page.showing_count,
        "aging": dict(page.aging),
    }


def payable_row_to_dict(row: PayableRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "date": row.date.isoformat(),
        "vendor_id": row.vendor_id,
        "vendor_name": row.vendor_name,
        "invoice_amount": row.invoice_amount,
        "paid_amount": row.paid_amount,
        "balance": row.balance,
        "due_date": row.due_date.isoformat(),
        "status": row.status,
        "source": row.source,
        "is_void": row.is_void,
        "paid": row.paid,
        "description": row.description,
        "company_id": row.company_id,
    }


def payables_page_to_dict(page: PayablesPage) -> dict[str, Any]:
    return {
        "rows": [payable_row_to_dict(r) for r in page.rows],
        "filters": {
            "search_keyword": page.filters.search_keyword,
            "vendor_filter": page.filters.vendor_filter,
            "paid_filter": page.filters.paid_filter,
            "show_voided": page.filters.show_voided,
        },
        "total_outstanding": page.total_outstanding,
        "overdue": page.overdue,
        "showing_count": page.showing_count,
        "aging": dict(page.aging),
    }


def _partner_warning_to_dict(warning: PartnerStatementWarning) -> dict[str, Any]:
    return {"key": warning.key, "kwargs": dict(warning.kwargs)}


def _partner_detail_line_to_dict(line: PartnerStatementDetailLine) -> dict[str, Any]:
    return {
        "line_date": _optional_date(line.line_date),
        "section_key": line.section_key,
        "type_key": line.type_key,
        "description": line.description,
        "reference": line.reference,
        "gross_amount": line.gross_amount,
        "inflow": line.inflow,
        "outflow": line.outflow,
        "signed_amount": line.signed_amount,
        "net_effect": line.net_effect,
        "running_position": line.running_position,
        "source_id": line.source_id,
    }


def partner_statement_to_dict(data: PartnerStatementData) -> dict[str, Any]:
    return {
        "partner_id": data.partner_id,
        "partner_name": data.partner_name,
        "partner_is_active": data.partner_is_active,
        "from_date": data.from_date.isoformat(),
        "to_date": data.to_date.isoformat(),
        "opening_position": data.opening_position,
        "opening_capital": data.opening_capital,
        "opening_current": data.opening_current,
        "opening_advances": data.opening_advances,
        "capital_contributions": data.capital_contributions,
        "profit_allocated": data.profit_allocated,
        "repayments": data.repayments,
        "drawings": data.drawings,
        "salary": data.salary,
        "advances_taken": data.advances_taken,
        "loss_allocated": data.loss_allocated,
        "advance_offsets": data.advance_offsets,
        "closing_position": data.closing_position,
        "closing_capital": data.closing_capital,
        "closing_current": data.closing_current,
        "closing_advances": data.closing_advances,
        "net_position_change": data.net_position_change,
        "status": data.status,
        "status_amount": data.status_amount,
        "warnings": [_partner_warning_to_dict(w) for w in data.warnings],
        "reconciliation_ok": data.reconciliation_ok,
        "detail_lines": [_partner_detail_line_to_dict(l) for l in data.detail_lines],
        "company_id": data.company_id,
    }


def readiness_blocker_to_dict(blocker: ReadinessBlocker) -> dict[str, Any]:
    return {"kind": blocker.kind, "count": blocker.count}


def statement_readiness_to_dict(item: StatementReadiness) -> dict[str, Any]:
    base = item.to_dict()
    base["blockers"] = [readiness_blocker_to_dict(b) for b in item.blockers]
    return base


def statement_readiness_list_to_dict(
    items: tuple[StatementReadiness, ...],
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "items": [statement_readiness_to_dict(i) for i in items],
    }
    if limit is not None:
        payload["meta"] = {"limit": limit, "count": len(items)}
    return payload
