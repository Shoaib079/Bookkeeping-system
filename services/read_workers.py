"""FASTAPI-REACT-22 — read-only workers list DTOs and compute."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import Worker


@dataclass(frozen=True, slots=True)
class WorkerListRow:
    id: int
    name: str
    role: str | None
    is_active: bool
    company_id: int


@dataclass(frozen=True, slots=True)
class WorkersListPage:
    rows: tuple[WorkerListRow, ...]
    row_count: int


def compute_workers_list(
    session: Session,
    *,
    company_id: int,
    active_only: bool = True,
) -> WorkersListPage:
    query = (
        session.query(Worker)
        .filter(Worker.company_id == company_id)
        .order_by(Worker.name, Worker.id)
    )
    if active_only:
        query = query.filter(Worker.is_active == True)  # noqa: E712
    rows = tuple(
        WorkerListRow(
            id=worker.id,
            name=worker.name,
            role=worker.role,
            is_active=bool(worker.is_active),
            company_id=company_id,
        )
        for worker in query.all()
    )
    return WorkersListPage(rows=rows, row_count=len(rows))
