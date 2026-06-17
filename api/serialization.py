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
