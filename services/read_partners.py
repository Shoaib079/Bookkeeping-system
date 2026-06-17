"""FASTAPI-P0.2-H — read-only partners list DTOs and compute."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import Partner


@dataclass(frozen=True, slots=True)
class PartnerListRow:
    id: int
    name: str
    profit_share_pct: float
    is_active: bool
    company_id: int


@dataclass(frozen=True, slots=True)
class PartnersListPage:
    rows: tuple[PartnerListRow, ...]
    row_count: int


def compute_partners_list(
    session: Session,
    *,
    company_id: int,
    active_only: bool = True,
) -> PartnersListPage:
    query = (
        session.query(Partner)
        .filter(Partner.company_id == company_id)
        .order_by(Partner.name, Partner.id)
    )
    if active_only:
        query = query.filter(Partner.is_active == True)  # noqa: E712
    rows = tuple(
        PartnerListRow(
            id=partner.id,
            name=partner.name,
            profit_share_pct=float(partner.profit_share_pct or 0),
            is_active=bool(partner.is_active),
            company_id=company_id,
        )
        for partner in query.all()
    )
    return PartnersListPage(rows=rows, row_count=len(rows))
