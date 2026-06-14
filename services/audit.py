"""FASTAPI-P0.3 — audit record service (Streamlit-free)."""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from models import AuditLog

# Canonical action strings (no DB enum — values unchanged from legacy call sites).
ACTION_CREATE = "Create"
ACTION_EDIT = "Edit"
ACTION_VOID = "Void"
ACTION_POST = "Post"
ACTION_SUBMIT = "Submit"
ACTION_APPROVE = "Approve"
ACTION_REJECT = "Reject"
ACTION_PERIOD_CLOSE = "PeriodClose"
ACTION_YEAR_END_CLOSE = "YearEndClose"
ACTION_VOID_YEAR_END_CLOSE = "VoidYearEndClose"
ACTION_PROFIT_ALLOCATION = "ProfitAllocation"
ACTION_UPLOAD = "Upload"
ACTION_DELETE = "Delete"
ACTION_PAYMENT = "Payment"

# Canonical entity_type strings (no DB enum).
ENTITY_SALE = "Sale"
ENTITY_EXPENSE_RECORD = "ExpenseRecord"
ENTITY_PURCHASE = "Purchase"
ENTITY_PAYABLE = "Payable"
ENTITY_BANK_TRANSACTION = "BankTransaction"
ENTITY_BANK_STATEMENT_ROW = "BankStatementRow"
ENTITY_DAILY_CASH_RECONCILIATION = "DailyCashReconciliation"
ENTITY_END_OF_DAY_CLOSE = "EndOfDayClose"
ENTITY_FISCAL_PERIOD = "FiscalPeriod"
ENTITY_YEAR_END_CLOSE = "YearEndClose"
ENTITY_PARTNER = "Partner"
ENTITY_WORKER = "Worker"
ENTITY_PARTNER_MOVEMENT = "PartnerMovement"
ENTITY_WORKER_MOVEMENT = "WorkerMovement"
ENTITY_EQUITY_MOVEMENT = "EquityMovement"
ENTITY_INVENTORY_TRANSACTION = "InventoryTransaction"
ENTITY_CHART_OF_ACCOUNTS = "ChartOfAccounts"
ENTITY_ATTACHMENT = "Attachment"
ENTITY_PARTNER_PROFIT_ALLOCATION = "PartnerProfitAllocation"


def record_audit(
    session: Session,
    *,
    action: str,
    entity_type: str | None,
    entity_id: int | None,
    description: str | None,
    performed_by: str | None,
    company_id: int | None,
) -> AuditLog:
    """Persist one AuditLog row and commit (legacy log_audit commit ownership)."""
    entry = AuditLog(
        timestamp=datetime.datetime.now(),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        performed_by=performed_by,
        company_id=company_id,
    )
    session.add(entry)
    session.commit()
    return entry
