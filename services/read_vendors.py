"""FASTAPI-REACT-23 — read-only vendors list DTOs and compute."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import Vendor


@dataclass(frozen=True, slots=True)
class VendorListRow:
    id: int
    name: str
    is_active: bool
    company_id: int


@dataclass(frozen=True, slots=True)
class VendorsListPage:
    rows: tuple[VendorListRow, ...]
    row_count: int


def compute_vendors_list(
    session: Session,
    *,
    company_id: int,
    active_only: bool = True,
) -> VendorsListPage:
    query = (
        session.query(Vendor)
        .filter(Vendor.company_id == company_id)
        .order_by(Vendor.name, Vendor.id)
    )
    if active_only:
        query = query.filter(Vendor.is_active == True)  # noqa: E712
    rows = tuple(
        VendorListRow(
            id=vendor.id,
            name=vendor.name,
            is_active=bool(vendor.is_active),
            company_id=company_id,
        )
        for vendor in query.all()
    )
    return VendorsListPage(rows=rows, row_count=len(rows))
