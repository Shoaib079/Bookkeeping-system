"""FASTAPI-P2.3 — purchase write endpoint."""

from __future__ import annotations

import datetime
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_request_context
from api.guards import require_company_write_access
from models import User
from services.context import RequestContext
from services.write_purchases import PurchaseWriteResult, create_and_post_purchase

router = APIRouter(tags=["writes"])

WRITE_PURCHASES_ENV = "ERP_API_WRITE_PURCHASES"


class CreatePurchaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: datetime.date
    amount: float
    currency: str = "TRY"
    payment_method: str = Field(..., description="Cash, Bank, or Credit")
    notes: str = ""
    vendor_id: int | None = None
    vendor_name: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    subcategory_id: int | None = None
    subcategory_name: str | None = None
    bank_account_id: int | None = Field(
        default=None,
        description="Bank account for Bank payment method",
    )


class CreatePurchaseResponse(BaseModel):
    purchase_id: int
    payable_id: int | None
    journal_entry_id: int | None
    message: str
    status: str = "ok"


def _write_purchases_enabled() -> bool:
    return os.getenv(WRITE_PURCHASES_ENV, "").strip().lower() in ("1", "true", "yes")


def _require_write_purchases_feature() -> None:
    if not _write_purchases_enabled():
        raise HTTPException(status_code=404, detail="Not Found")


def _result_to_response(result: PurchaseWriteResult) -> CreatePurchaseResponse:
    return CreatePurchaseResponse(
        purchase_id=result.purchase_id,
        payable_id=result.payable_id,
        journal_entry_id=result.journal_entry_id,
        message=result.message,
    )


@router.post(
    "",
    status_code=201,
    summary="Create and post a purchase",
    description=(
        "Records a cash, bank, or credit purchase and posts the GL entry. "
        "Credit purchases also create a linked payable. "
        "Requires ``ERP_API_WRITE_PURCHASES=1``. Company scope comes from "
        "``X-Company-Id`` only — never from the request body."
    ),
    response_model=CreatePurchaseResponse,
    responses={
        400: {"description": "Business validation failure."},
        401: {"description": "Missing or invalid bearer token."},
        403: {"description": "Membership or create_transaction permission denied."},
        404: {"description": "Write API disabled or not found."},
        422: {"description": "Request schema validation failure."},
    },
)
def post_purchase(
    body: CreatePurchaseRequest,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> CreatePurchaseResponse:
    _require_write_purchases_feature()
    company_id = require_company_write_access(session, context, "create_transaction")
    user = session.get(User, context.user_id)
    performed_by = user.username if user is not None else None
    try:
        result = create_and_post_purchase(
            session,
            company_id=company_id,
            user_id=context.user_id,
            performed_by=performed_by,
            entry_date=body.date,
            amount=body.amount,
            currency=body.currency,
            payment_method=body.payment_method,
            notes=body.notes,
            vendor_id=body.vendor_id,
            vendor_name=body.vendor_name,
            category_id=body.category_id,
            category_name=body.category_name,
            subcategory_id=body.subcategory_id,
            subcategory_name=body.subcategory_name,
            bank_account_id=body.bank_account_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _result_to_response(result)
