"""Read-only bank accounts list endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_read_access
from api.serialization import bank_accounts_list_to_dict
from services import read_bank_accounts
from services.context import RequestContext

router = APIRouter(tags=["bank-accounts"])


@router.get(
    "",
    summary="Bank accounts",
    description="Active bank accounts for the active company (picker / list read).",
)
def get_bank_accounts(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
    active_only: Annotated[
        bool,
        Query(description="When true, return only active accounts"),
    ] = True,
    exclude_kind: Annotated[
        str | None,
        Query(
            description="Omit accounts of this kind (e.g. credit_card for card-sale deposit targets)"
        ),
    ] = None,
    kind: Annotated[
        str | None,
        Query(description="Return only accounts of this kind (e.g. credit_card)"),
    ] = None,
) -> dict:
    company_id = require_company_read_access(
        session,
        context,
        "create_transaction",
        "manage_banking",
        "view_bank_statement_import",
        "view_management_reports",
    )
    page = read_bank_accounts.compute_bank_accounts_list(
        session,
        company_id=company_id,
        active_only=active_only,
        exclude_kind=exclude_kind,
        kind=kind,
    )
    return bank_accounts_list_to_dict(page)
