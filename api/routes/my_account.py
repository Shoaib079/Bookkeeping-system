"""Read-only my-account profile endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.serialization import my_account_page_to_dict
from services import permissions as perms
from services import read_my_account
from services.context import RequestContext
from services.permissions import PermissionDenied

router = APIRouter(tags=["my-account"])


@router.get(
    "",
    summary="My account",
    description=(
        "Self profile snapshot for the bearer user in the active company context. "
        "Profile and security writes remain Streamlit-only."
    ),
)
def get_my_account(
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> dict:
    try:
        perms.require_company_membership(session, context)
        company_id = perms.require_company(context)
    except PermissionDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    page = read_my_account.compute_my_account_page(
        session,
        user_id=context.user_id,
        company_id=company_id,
        company_role=context.role,
    )
    return my_account_page_to_dict(page)
