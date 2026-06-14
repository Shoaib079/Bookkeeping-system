"""P3.8-A — read-only schema startup diagnostics.

Wraps ``services.schema_version`` for startup/dev logging. Never upgrades, stamps,
or blocks startup. ``migrate_schema()`` remains authoritative.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict

from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from services.schema_version import (
    STATUS_AHEAD_OF_CODE,
    STATUS_AT_HEAD,
    STATUS_BEHIND_HEAD,
    STATUS_UNKNOWN,
    STATUS_UNSTAMPED,
    SchemaVersionInfo,
    detect_schema_version,
    detect_schema_version_from_session,
)

_LOG = logging.getLogger(__name__)

ALEMBIC_AUTHORITATIVE_ENV_VAR = "ERP_ALEMBIC_AUTHORITATIVE"

_TRUE_FLAG_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_FLAG_VALUES = frozenset({"0", "false", "no", "off"})


def parse_alembic_authoritative_flag(value: str | None) -> bool:
    """Parse ``ERP_ALEMBIC_AUTHORITATIVE``; fail-safe ``False`` when unset or invalid."""
    if value is None:
        return False
    normalized = value.strip().lower()
    if not normalized:
        return False
    if normalized in _TRUE_FLAG_VALUES:
        return True
    if normalized in _FALSE_FLAG_VALUES:
        return False
    return False


def is_alembic_authoritative_enabled(
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Read ``ERP_ALEMBIC_AUTHORITATIVE`` from *environ* (default: ``os.environ``)."""
    source = os.environ if environ is None else environ
    return parse_alembic_authoritative_flag(source.get(ALEMBIC_AUTHORITATIVE_ENV_VAR))


class SchemaStartupDiagnostic(TypedDict):
    status: str
    db_revision: str | None
    head_revision: str | None
    message: str
    detail: str
    read_only: bool
    blocks_startup: bool


def startup_message_for_status(
    status: str,
    *,
    head_revision: str | None,
) -> str:
    """Safe human-readable startup message for each schema status."""
    head = head_revision or "unknown"
    if status == STATUS_AT_HEAD:
        return f"Database schema is stamped at Alembic head {head}."
    if status == STATUS_UNSTAMPED:
        return "Database is not Alembic-stamped; migrate_schema remains active."
    if status == STATUS_BEHIND_HEAD:
        return "Database schema is behind Alembic head; no automatic upgrade will run."
    if status == STATUS_AHEAD_OF_CODE:
        return "Database schema is newer than this code; no migration will run."
    return "Database schema version could not be determined safely."


def _diagnostic_from_info(info: SchemaVersionInfo) -> SchemaStartupDiagnostic:
    return SchemaStartupDiagnostic(
        status=info.status,
        db_revision=info.db_revision,
        head_revision=info.head_revision,
        message=startup_message_for_status(
            info.status,
            head_revision=info.head_revision,
        ),
        detail=info.message,
        read_only=True,
        blocks_startup=False,
    )


def get_schema_startup_diagnostic(
    session_or_engine: Session | Engine | Connection,
    *,
    versions_dir: Path | None = None,
) -> SchemaStartupDiagnostic:
    """Read-only startup diagnostic dict; does not mutate the database."""
    if isinstance(session_or_engine, Session):
        info = detect_schema_version_from_session(
            session_or_engine,
            versions_dir=versions_dir,
        )
    else:
        info = detect_schema_version(
            session_or_engine,
            versions_dir=versions_dir,
        )
    return _diagnostic_from_info(info)


def log_schema_startup_diagnostic(
    session_or_engine: Session | Engine | Connection,
    *,
    versions_dir: Path | None = None,
    logger: logging.Logger | None = None,
) -> SchemaStartupDiagnostic:
    """Log a single read-only schema status line; never blocks startup."""
    diagnostic = get_schema_startup_diagnostic(
        session_or_engine,
        versions_dir=versions_dir,
    )
    (logger or _LOG).info("[schema] %s", diagnostic["message"])
    return diagnostic


def format_schema_startup_line(diagnostic: SchemaStartupDiagnostic) -> str:
    """Compact line for logs or dev consoles."""
    return (
        f"[schema] status={diagnostic['status']} "
        f"db_revision={diagnostic['db_revision']!r} "
        f"head_revision={diagnostic['head_revision']!r} — "
        f"{diagnostic['message']}"
    )
