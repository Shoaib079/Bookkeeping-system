"""Read-only report endpoints."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import balance_sheet_to_dict, cash_flow_to_dict, profit_loss_to_dict, trial_balance_to_dict
from services import read_reports, read_trial_balance
from services.context import RequestContext

router = APIRouter(tags=["reports"])


@router.get(
    "/profit-loss",
    summary="Profit and loss statement",
    description="Income and expense totals for an inclusive date range.",
)
def get_profit_loss(
    start_date: datetime.date,
    end_date: datetime.date,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session, context, "view_management_reports",
    )
    stmt = read_reports.compute_profit_loss(
        session,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
    )
    return profit_loss_to_dict(stmt)


@router.get(
    "/balance-sheet",
    summary="Balance sheet",
    description="Assets, liabilities, and equity as of a single date.",
)
def get_balance_sheet(
    as_of: datetime.date,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session, context, "view_management_reports",
    )
    stmt = read_reports.compute_balance_sheet(
        session,
        company_id=company_id,
        as_of=as_of,
    )
    return balance_sheet_to_dict(stmt)


@router.get(
    "/cash-flow",
    summary="Cash flow statement",
    description="Operating and financing cash movements for an inclusive date range.",
)
def get_cash_flow(
    start_date: datetime.date,
    end_date: datetime.date,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session, context, "view_management_reports",
    )
    stmt = read_reports.compute_cash_flow(
        session,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
    )
    return cash_flow_to_dict(stmt)


@router.get(
    "/trial-balance",
    summary="Trial balance",
    description="Active accounts with debit/credit columns and GL line verification.",
)
def get_trial_balance(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "view_ledger",
        "view_management_reports",
    )
    stmt = read_trial_balance.compute_trial_balance(
        session,
        company_id=company_id,
    )
    return trial_balance_to_dict(stmt)
