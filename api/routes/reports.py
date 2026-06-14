"""Read-only report endpoints."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.serialization import balance_sheet_to_dict, profit_loss_to_dict
from services import permissions as perms
from services import read_reports
from services.context import RequestContext
from services.permissions import PermissionDenied

router = APIRouter(tags=["reports"])


def _guard_report_access(session: Session, context: RequestContext) -> int:
    """Enforce company scope, membership, and view_management_reports."""
    try:
        perms.require_company_membership(session, context)
        perms.require_permission(context, "view_management_reports")
        return perms.require_company(context)
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        msg = str(exc)
        if "require_company_membership" in msg:
            raise HTTPException(status_code=403, detail=msg) from exc
        raise HTTPException(status_code=400, detail=msg) from exc


@router.get("/profit-loss")
def get_profit_loss(
    start_date: datetime.date,
    end_date: datetime.date,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = _guard_report_access(session, context)
    stmt = read_reports.compute_profit_loss(
        session,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
    )
    return profit_loss_to_dict(stmt)


@router.get("/balance-sheet")
def get_balance_sheet(
    as_of: datetime.date,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    company_id = _guard_report_access(session, context)
    stmt = read_reports.compute_balance_sheet(
        session,
        company_id=company_id,
        as_of=as_of,
    )
    return balance_sheet_to_dict(stmt)
