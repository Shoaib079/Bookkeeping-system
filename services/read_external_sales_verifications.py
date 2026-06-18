"""FASTAPI-REACT-47 — read-only external sales verification history."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from services import daily_sales_close as esv_svc


@dataclass(frozen=True, slots=True)
class ExternalSalesVerificationsListPage:
    rows: tuple[esv_svc.VerificationRecord, ...]
    row_count: int
    company_id: int
    start_date: datetime.date | None
    end_date: datetime.date | None


def compute_external_sales_verifications_list(
    session: Session,
    *,
    company_id: int,
    start_date: datetime.date | None = None,
    end_date: datetime.date | None = None,
) -> ExternalSalesVerificationsListPage:
    if start_date is None or end_date is None:
        rows = tuple(
            esv_svc.list_verifications(
                session,
                company_id,
                datetime.date.min,
                datetime.date.max,
            )
        )
    else:
        rows = tuple(
            esv_svc.list_verifications(session, company_id, start_date, end_date)
        )
    return ExternalSalesVerificationsListPage(
        rows=rows,
        row_count=len(rows),
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
    )
