"""FASTAPI-REACT-28 — read-only customers list DTOs and compute."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import Customer


@dataclass(frozen=True, slots=True)
class CustomerListRow:
    id: int
    name: str
    contact: str | None
    phone: str | None
    email: str | None
    address: str | None
    is_active: bool
    company_id: int


@dataclass(frozen=True, slots=True)
class CustomersListPage:
    rows: tuple[CustomerListRow, ...]
    row_count: int


def compute_customers_list(
    session: Session,
    *,
    company_id: int,
    active_only: bool = True,
) -> CustomersListPage:
    query = (
        session.query(Customer)
        .filter(Customer.company_id == company_id)
        .order_by(Customer.name, Customer.id)
    )
    if active_only:
        query = query.filter(Customer.is_active == True)  # noqa: E712
    rows = tuple(
        CustomerListRow(
            id=customer.id,
            name=customer.name,
            contact=customer.contact,
            phone=customer.phone,
            email=customer.email,
            address=customer.address,
            is_active=bool(customer.is_active),
            company_id=company_id,
        )
        for customer in query.all()
    )
    return CustomersListPage(rows=rows, row_count=len(rows))
