"""DB enum / code → message key maps for transactional UI (Phase 15).

Kept separate from transactional.py so app.py can import maps without
loading the full EN/TR string catalogs (and avoids circular-import edge cases).
"""

from __future__ import annotations

# DB value → message key (expense types stored in English in DB)
EXPENSE_TYPE_I18N: dict[str, str] = {
    "Salary": "expense.type.salary",
    "Rent": "expense.type.rent",
    "Electricity": "expense.type.electricity",
    "Water": "expense.type.water",
    "Internet": "expense.type.internet",
    "Fuel": "expense.type.fuel",
    "Transport": "expense.type.transport",
    "Maintenance": "expense.type.maintenance",
    "Advertising": "expense.type.advertising",
    "Office Supplies": "expense.type.office",
    "Other": "expense.type.other",
}

SALE_TYPE_I18N: dict[str, str] = {
    "Cash": "sales.type.cash",
    "Credit": "sales.type.credit",
}

SALE_STATUS_I18N: dict[str, str] = {
    "Paid": "sales.status.paid",
    "Partial": "sales.status.partial",
    "Open": "sales.status.open",
    "Overdue": "sales.status.overdue",
    "Void": "sales.status.void",
}

PAYABLE_STATUS_I18N: dict[str, str] = {
    "Open": "payable.status.open",
    "Partial": "payable.status.partial",
    "Paid": "payable.status.paid",
}

BANK_TXN_TYPE_I18N: dict[str, str] = {
    "deposit": "bank.type.deposit",
    "withdrawal": "bank.type.withdrawal",
    "transfer": "bank.type.transfer",
}

PURCHASE_TYPE_I18N: dict[str, str] = {
    "Credit": "purchase.type.credit",
    "Cash": "purchase.type.cash",
    "Bank": "purchase.type.bank",
    "Credit Card": "purchase.type.card",
}

PURCHASE_GL_I18N: dict[str, str] = {
    "Inventory": "purchase.gl.inventory",
    **{k: v for k, v in EXPENSE_TYPE_I18N.items() if k != "Salary"},
}
PURCHASE_GL_I18N["Salary"] = "expense.type.salary"

RECON_STATUS_I18N: dict[str, str] = {
    "reconciled": "recon.status.reconciled",
    "pending_approval": "recon.status.pending",
    "rejected": "recon.status.rejected",
    "voided": "recon.status.voided",
}

RECON_VARIANCE_I18N: dict[str, str] = {
    "balanced": "recon.variance.balanced",
    "shortage": "recon.variance.shortage",
    "overage": "recon.variance.overage",
}

EOD_RECON_SNAP_I18N: dict[str, str] = {
    "reconciled": "eod.recon.reconciled",
    "pending_approval": "eod.recon.pending",
    "rejected": "eod.recon.rejected",
    "none": "eod.recon.none",
}

AGING_BUCKET_I18N: dict[str, str] = {
    "Current": "aging.current",
    "1-30 Days": "aging.days_1_30",
    "31-60 Days": "aging.days_31_60",
    "61-90 Days": "aging.days_61_90",
    "90+ Days": "aging.days_90_plus",
}

TXN_TYPE_I18N: dict[str, str] = {
    "Sale": "txn.type.sale",
    "Expense": "txn.type.expense",
    "Purchase": "txn.type.purchase",
    "Supplier Payment": "txn.type.supplier_payment",
    "Customer Payment": "txn.type.customer_payment",
    "Bank Transaction": "txn.type.bank",
}

# Payment-method values stored in English across sales/expenses/purchases/payments.
PAYMENT_METHOD_I18N: dict[str, str] = {
    "Cash": "expense.pay.cash",
    "Bank": "expense.pay.bank",
    "Card": "expense.pay.card_payment",
    "Credit": "expense.pay.credit",
    "Credit Card": "expense.pay.company_cc",
    "Mobile Money": "expense.pay.mobile",
    "Other": "expense.pay.other",
}

# Partner movement types stored in English (PascalCase enum values).
PARTNER_MOVEMENT_TYPE_I18N: dict[str, str] = {
    "CapitalContribution": "pmov.capital_contribution",
    "Drawing": "pmov.drawing",
    "Salary": "pmov.salary",
    "Advance": "pmov.advance",
    "Repayment": "pmov.repayment",
    "AdvanceOffset": "pmov.advance_offset",
}

WORKER_MOVEMENT_TYPE_I18N: dict[str, str] = {
    "Salary": "wmov.salary",
    "Advance": "wmov.advance",
    "Repayment": "wmov.repayment",
}

COMPANY_ROLE_I18N: dict[str, str] = {
    "owner": "members.role.owner",
    "manager": "members.role.manager",
    "partner": "members.role.partner",
    "cashier": "members.role.cashier",
    "viewer": "members.role.viewer",
}

AUDIT_ACTION_I18N: dict[str, str] = {
    "Create": "audit.action.create",
    "Void": "audit.action.void",
    "Edit": "audit.action.edit",
    "Payment": "audit.action.payment",
    "Submit": "audit.action.submit",
    "Approve": "audit.action.approve",
    "Reject": "audit.action.reject",
    "Upload": "audit.action.upload",
    "Delete": "audit.action.delete",
    "Close": "audit.action.close",
    "PeriodClose": "audit.action.period_close",
    "PeriodReopen": "audit.action.period_reopen",
    "ProfitAllocation": "audit.action.profit_allocation",
}

AUDIT_ENTITY_I18N: dict[str, str] = {
    "Sale": "audit.entity.sale",
    "ExpenseRecord": "audit.entity.expense",
    "Purchase": "audit.entity.purchase",
    "Payable": "audit.entity.payable",
    "BankTransaction": "audit.entity.bank_txn",
    "InventoryTransaction": "audit.entity.inventory_txn",
    "EquityMovement": "audit.entity.equity_movement",
    "DailyCashReconciliation": "audit.entity.daily_cash_recon",
    "Partner": "audit.entity.partner",
    "PartnerMovement": "audit.entity.partner_movement",
    "PartnerProfitAllocation": "audit.entity.partner_profit_alloc",
    "Attachment": "audit.entity.attachment",
    "BankAccount": "audit.entity.bank_account",
    "ChartOfAccounts": "audit.entity.chart_of_accounts",
    "EndOfDayClose": "audit.entity.eod_close",
    "FiscalPeriod": "audit.entity.fiscal_period",
    "CompanyUser": "audit.entity.company_user",
    "Customer": "audit.entity.customer",
    "Vendor": "audit.entity.vendor",
    "JournalEntry": "audit.entity.journal_entry",
    "RecurringExpenseTemplate": "audit.entity.recurring_expense",
}

__all__ = [
    "AGING_BUCKET_I18N",
    "AUDIT_ACTION_I18N",
    "AUDIT_ENTITY_I18N",
    "EOD_RECON_SNAP_I18N",
    "RECON_STATUS_I18N",
    "RECON_VARIANCE_I18N",
    "BANK_TXN_TYPE_I18N",
    "COMPANY_ROLE_I18N",
    "EXPENSE_TYPE_I18N",
    "PAYABLE_STATUS_I18N",
    "PARTNER_MOVEMENT_TYPE_I18N",
    "WORKER_MOVEMENT_TYPE_I18N",
    "PAYMENT_METHOD_I18N",
    "PURCHASE_GL_I18N",
    "PURCHASE_TYPE_I18N",
    "SALE_STATUS_I18N",
    "SALE_TYPE_I18N",
    "TXN_TYPE_I18N",
]
