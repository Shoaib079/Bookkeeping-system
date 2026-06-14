"""JSON serialization helpers for read-service DTOs (API layer only)."""

from __future__ import annotations

from typing import Any

from services.read_reports import (
    BalanceSheetStatement,
    FinancialStatementLine,
    ProfitLossStatement,
)


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
