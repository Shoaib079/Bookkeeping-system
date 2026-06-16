"""MD-05 — authoritative money-column tier classification for Alembic 0002.

Single source of truth for Float → Numeric migration targets per
``docs/MONEY_DECIMAL_05_NUMERIC_MIGRATION_PLAN.md``. ``models.py`` uses
``Numeric(asdecimal=True)`` per tier since MD-05-IMPL-2; this module drives
revision ``0002_money_numeric`` and ORM column types.

Tier rules (MD-05):
  - ``Numeric(19, 2)`` — currency amounts and balances
  - ``Numeric(19, 4)`` — ``amount_native`` / ``native_amount`` FX reporting amounts;
    ``ingredients.cost_per_base_unit`` (sub-cent recipe unit costs)
  - ``Numeric(19, 8)`` — ``fx_rate``
  - remain ``Float`` — quantities, percentages, ML confidence scores (not money)
"""

from __future__ import annotations

from typing import Literal

Scale = Literal[2, 4, 8]

# (table_name, column_name)
NUMERIC_19_4: frozenset[tuple[str, str]] = frozenset(
    {
        ("journal_entry_lines", "amount_native"),
        ("sales", "native_amount"),
        ("expense_records", "native_amount"),
        ("purchases", "native_amount"),
        ("ingredients", "cost_per_base_unit"),
    }
)

NUMERIC_19_8: frozenset[tuple[str, str]] = frozenset(
    {
        ("sales", "fx_rate"),
        ("expense_records", "fx_rate"),
        ("purchases", "fx_rate"),
    }
)

# Out of scope for money migration — stay Float per MD-05 do-not-touch list.
FLOAT_REMAIN: frozenset[tuple[str, str]] = frozenset(
    {
        ("partners", "profit_share_pct"),
        ("partner_profit_allocation_lines", "share_pct"),
        ("products", "quantity"),
        ("products", "min_stock"),
        ("inventory_transactions", "change"),
        ("recipe_lines", "quantity"),
        ("recipe_lines", "waste_percent"),
        ("recipes", "yield_quantity"),
        ("receipt_draft_suggestions", "suggested_payment_confidence"),
        ("receipt_draft_suggestions", "extraction_confidence"),
        ("receipt_learning_map", "confidence_cached"),
    }
)

# All other Float money columns from models.py (99 total Float columns).
NUMERIC_19_2: frozenset[tuple[str, str]] = frozenset(
    {
        ("bank_accounts", "balance"),
        ("bank_statement_imports", "starting_balance"),
        ("bank_statement_imports", "ending_balance"),
        ("bank_statement_rows", "debit_amount"),
        ("bank_statement_rows", "credit_amount"),
        ("bank_statement_rows", "amount"),
        ("bank_statement_rows", "balance_after"),
        ("bank_statement_rows", "original_amount"),
        ("bank_transactions", "amount"),
        ("budgets", "amount"),
        ("cash_sales", "amount"),
        ("chart_of_accounts", "balance"),
        ("credit_sales", "amount"),
        ("customer_ledger", "amount"),
        ("daily_cash_reconciliation", "opening_cash"),
        ("daily_cash_reconciliation", "expected_cash"),
        ("daily_cash_reconciliation", "actual_cash"),
        ("daily_cash_reconciliation", "difference"),
        ("end_of_day_closes", "cash_sales"),
        ("end_of_day_closes", "card_sales"),
        ("end_of_day_closes", "credit_sales"),
        ("end_of_day_closes", "total_sales"),
        ("end_of_day_closes", "total_expenses"),
        ("end_of_day_closes", "total_purchases"),
        ("end_of_day_closes", "customer_payments"),
        ("end_of_day_closes", "supplier_payments"),
        ("end_of_day_closes", "bank_deposits"),
        ("end_of_day_closes", "bank_withdrawals"),
        ("end_of_day_closes", "net_cash_movement"),
        ("end_of_day_closes", "daily_profit_estimate"),
        ("end_of_day_closes", "recon_variance"),
        ("expense_drafts", "amount"),
        ("expense_records", "amount"),
        ("expense_records", "gross_salary"),
        ("expense_records", "deductions"),
        ("expense_records", "net_salary"),
        ("expenses", "amount"),
        ("external_sales_verifications", "external_total"),
        ("external_sales_verifications", "z_report_total"),
        ("external_sales_verifications", "external_cash"),
        ("external_sales_verifications", "external_card"),
        ("external_sales_verifications", "external_online"),
        ("external_sales_verifications", "erp_total"),
        ("external_sales_verifications", "erp_cash"),
        ("external_sales_verifications", "erp_card"),
        ("external_sales_verifications", "erp_credit"),
        ("external_sales_verifications", "variance_total"),
        ("external_sales_verifications", "variance_cash"),
        ("external_sales_verifications", "variance_card"),
        ("external_sales_verifications", "variance_online"),
        ("external_sales_verifications", "z_report_variance"),
        ("journal_entry_lines", "debit"),
        ("journal_entry_lines", "credit"),
        ("menu_price_history", "price_gross"),
        ("partner_movements", "amount"),
        ("partner_profit_allocation_lines", "amount"),
        ("partner_profit_allocations", "total_net_income"),
        ("payables", "amount"),
        ("payables", "paid_amount"),
        ("payables", "balance"),
        ("products", "cost_price"),
        ("products", "unit_price"),
        ("purchases", "amount"),
        ("recurring_expense_drafts", "amount"),
        ("recurring_expense_templates", "amount"),
        ("salaries", "amount"),
        ("sales", "amount"),
        ("sales", "paid_amount"),
        ("sales", "balance"),
        ("settlement_statement_rows", "gross_amount"),
        ("settlement_statement_rows", "fee_amount"),
        ("settlement_statement_rows", "net_amount"),
        ("workers", "base_salary"),
        ("worker_movements", "amount"),
        ("worker_movements", "gross_salary"),
        ("worker_movements", "deductions"),
        ("worker_movements", "advance_recovery"),
        ("worker_movements", "net_paid"),
        ("year_end_closes", "net_income_snapshot"),
        ("year_end_closes", "re_balance_at_close"),
    }
)


def scale_for(table: str, column: str) -> Scale | None:
    """Return target Numeric scale, or ``None`` if the column stays Float."""
    key = (table, column)
    if key in FLOAT_REMAIN:
        return None
    if key in NUMERIC_19_4:
        return 4
    if key in NUMERIC_19_8:
        return 8
    if key in NUMERIC_19_2:
        return 2
    raise KeyError(f"Unclassified money column: {table}.{column}")


def iter_alter_targets() -> tuple[tuple[str, str, Scale], ...]:
    """Sorted (table, column, scale) for every column upgraded by 0002."""
    items: list[tuple[str, str, Scale]] = []
    for table, column in sorted(NUMERIC_19_2 | NUMERIC_19_4 | NUMERIC_19_8):
        items.append((table, column, scale_for(table, column)))  # type: ignore[arg-type]
    return tuple(items)


def grouped_by_table() -> dict[str, list[tuple[str, Scale]]]:
    """Table → [(column, scale), …] for migration batching."""
    grouped: dict[str, list[tuple[str, Scale]]] = {}
    for table, column, scale in iter_alter_targets():
        grouped.setdefault(table, []).append((column, scale))
    for cols in grouped.values():
        cols.sort(key=lambda pair: pair[0])
    return dict(sorted(grouped.items()))
