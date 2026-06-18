"""FASTAPI-REACT-36 — read-only audit log list DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import AuditLog

_DEFAULT_LIMIT = 2000
_MAX_LIMIT = 2000


@dataclass(frozen=True, slots=True)
class AuditLogListRow:
    id: int
    timestamp: datetime.datetime
    action: str
    entity_type: str | None
    entity_id: int | None
    description: str
    performed_by: str | None
    company_id: int


@dataclass(frozen=True, slots=True)
class AuditLogListPage:
    rows: tuple[AuditLogListRow, ...]
    row_count: int
    limit: int


def compute_audit_log_list(
    session: Session,
    *,
    company_id: int,
    limit: int = _DEFAULT_LIMIT,
) -> AuditLogListPage:
    capped_limit = max(1, min(limit, _MAX_LIMIT))
    logs = (
        session.query(AuditLog)
        .filter(AuditLog.company_id == company_id)
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .limit(capped_limit)
        .all()
    )
    rows = tuple(
        AuditLogListRow(
            id=log.id,
            timestamp=log.timestamp,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            description=log.description or "",
            performed_by=log.performed_by,
            company_id=company_id,
        )
        for log in logs
    )
    return AuditLogListPage(rows=rows, row_count=len(rows), limit=capped_limit)
