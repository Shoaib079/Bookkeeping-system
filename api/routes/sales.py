"""FASTAPI-P2.1 — sales write endpoint."""

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
from services.write_sales import SaleWriteResult, create_and_post_sale

router = APIRouter(tags=["writes"])

WRITE_SALES_ENV = "ERP_API_WRITE_SALES"


class CreateSaleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: datetime.date
    amount: float
    currency: str = "TRY"
    payment_method: str = Field(..., description="Cash, Card, or Credit")
    notes: str = ""
    customer_name: str | None = None
    card_bank_account_id: int | None = Field(
        default=None,
        description="Bank account for card deposit when card settlement is off",
    )


class CreateSaleResponse(BaseModel):
    sale_id: int
    journal_entry_id: int | None
    invoice_number: str
    message: str
    status: str = "ok"


def _write_sales_enabled() -> bool:
    return os.getenv(WRITE_SALES_ENV, "").strip().lower() in ("1", "true", "yes")


def _require_write_sales_feature() -> None:
    if not _write_sales_enabled():
        raise HTTPException(status_code=404, detail="Not Found")


def _result_to_response(result: SaleWriteResult) -> CreateSaleResponse:
    return CreateSaleResponse(
        sale_id=result.sale_id,
        journal_entry_id=result.journal_entry_id,
        invoice_number=result.invoice_number,
        message=result.message,
    )


@router.post(
    "",
    status_code=201,
    summary="Create and post a sale",
    description=(
        "Records a cash, card, or credit sale and posts the GL entry. "
        "Requires ``ERP_API_WRITE_SALES=1``. Company scope comes from "
        "``X-Company-Id`` only — never from the request body."
    ),
    response_model=CreateSaleResponse,
    responses={
        400: {"description": "Business validation failure (amount, payment method, customer)."},
        401: {"description": "Missing or invalid bearer token."},
        403: {"description": "Membership or create_transaction permission denied."},
        404: {"description": "Write API disabled or not found."},
        422: {"description": "Request schema validation failure."},
    },
)
def post_sale(
    body: CreateSaleRequest,
    session: Annotated[Session, Depends(get_db)],
    context: Annotated[RequestContext, Depends(get_request_context)],
) -> CreateSaleResponse:
    _require_write_sales_feature()
    company_id = require_company_write_access(session, context, "create_transaction")
    user = session.get(User, context.user_id)
    performed_by = user.username if user is not None else None
    try:
        result = create_and_post_sale(
            session,
            company_id=company_id,
            user_id=context.user_id,
            performed_by=performed_by,
            entry_date=body.date,
            amount=body.amount,
            currency=body.currency,
            payment_method=body.payment_method,
            notes=body.notes,
            customer_name=body.customer_name,
            card_bank_account_id=body.card_bank_account_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _result_to_response(result)
