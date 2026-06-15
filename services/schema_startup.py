"""P3.8-A — read-only schema startup diagnostics.

Wraps ``services.schema_version`` for startup/dev logging. Never upgrades, stamps,
or blocks startup. ``migrate_schema()`` remains authoritative.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

from sqlalchemy import inspect
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from services.schema_migration_gate import MigrationGateDecision
from services.schema_version import (
    ALEMBIC_VERSION_TABLE,
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


StartupAction = Literal[
    "run_migrate_schema",
    "verify_only",
    "alembic_upgrade_head",
    "require_stamp",
    "fail_closed",
]

ACTION_RUN_MIGRATE_SCHEMA: StartupAction = "run_migrate_schema"
ACTION_VERIFY_ONLY: StartupAction = "verify_only"
ACTION_ALEMBIC_UPGRADE_HEAD: StartupAction = "alembic_upgrade_head"
ACTION_REQUIRE_STAMP: StartupAction = "require_stamp"
ACTION_FAIL_CLOSED: StartupAction = "fail_closed"

_KNOWN_SCHEMA_STATUSES = frozenset(
    {
        STATUS_UNSTAMPED,
        "unstamped_legacy",
        STATUS_AT_HEAD,
        STATUS_BEHIND_HEAD,
        STATUS_AHEAD_OF_CODE,
        STATUS_UNKNOWN,
    }
)
_UNSTAMPED_STATUSES = frozenset({STATUS_UNSTAMPED, "unstamped_legacy"})


@dataclass(frozen=True, slots=True)
class SchemaStartupDecision:
    """Pure startup decision — no I/O or migration execution."""

    action: StartupAction
    message: str
    blocks_startup: bool
    requires_backup: bool
    requires_confirmation: bool
    schema_status: str
    db_revision: str | None
    head_revision: str | None
    dialect: str
    flag_authoritative: bool


def _revision_label(revision: str | None) -> str:
    return revision if revision is not None else "unknown"


def _operator_ready(backup_available: bool, confirmation_given: bool) -> bool:
    return backup_available and confirmation_given


def decide_schema_startup_action(
    *,
    flag_authoritative: bool,
    schema_status: str,
    is_new_db: bool,
    dialect: str,
    backup_available: bool = False,
    confirmation_given: bool = False,
    db_revision: str | None = None,
    head_revision: str | None = None,
) -> SchemaStartupDecision:
    """Pure decision for schema startup authority (P3.8-E); no DB/env/Alembic calls."""
    dialect_norm = dialect.strip().lower()
    status_norm = schema_status.strip().lower()

    if not flag_authoritative:
        return SchemaStartupDecision(
            action=ACTION_RUN_MIGRATE_SCHEMA,
            message=(
                "ERP_ALEMBIC_AUTHORITATIVE is off; continue with migrate_schema() "
                f"(status={status_norm}, dialect={dialect_norm})."
            ),
            blocks_startup=False,
            requires_backup=False,
            requires_confirmation=False,
            schema_status=status_norm,
            db_revision=db_revision,
            head_revision=head_revision,
            dialect=dialect_norm,
            flag_authoritative=False,
        )

    if status_norm not in _KNOWN_SCHEMA_STATUSES:
        return _fail_closed_decision(
            message=(
                f"Unrecognized schema status {status_norm!r}; startup blocked until "
                "migration state is resolved."
            ),
            schema_status=status_norm,
            db_revision=db_revision,
            head_revision=head_revision,
            dialect=dialect_norm,
            flag_authoritative=True,
        )

    if status_norm in {STATUS_AHEAD_OF_CODE, STATUS_UNKNOWN}:
        return _fail_closed_decision(
            message=(
                f"Schema status is {status_norm} "
                f"(db_revision={_revision_label(db_revision)}, "
                f"head_revision={_revision_label(head_revision)}); "
                "startup blocked — resolve deployment mismatch manually."
            ),
            schema_status=status_norm,
            db_revision=db_revision,
            head_revision=head_revision,
            dialect=dialect_norm,
            flag_authoritative=True,
        )

    if is_new_db:
        return SchemaStartupDecision(
            action=ACTION_ALEMBIC_UPGRADE_HEAD,
            message=(
                f"New empty database on {dialect_norm}; run alembic upgrade head "
                f"({_revision_label(head_revision)})."
            ),
            blocks_startup=False,
            requires_backup=False,
            requires_confirmation=False,
            schema_status=status_norm,
            db_revision=db_revision,
            head_revision=head_revision,
            dialect=dialect_norm,
            flag_authoritative=True,
        )

    if status_norm == STATUS_AT_HEAD:
        return SchemaStartupDecision(
            action=ACTION_VERIFY_ONLY,
            message=(
                f"Database stamped at Alembic head {_revision_label(head_revision)}; "
                "verify schema and start."
            ),
            blocks_startup=False,
            requires_backup=False,
            requires_confirmation=False,
            schema_status=status_norm,
            db_revision=db_revision,
            head_revision=head_revision,
            dialect=dialect_norm,
            flag_authoritative=True,
        )

    if status_norm in _UNSTAMPED_STATUSES:
        ready = _operator_ready(backup_available, confirmation_given)
        return SchemaStartupDecision(
            action=ACTION_REQUIRE_STAMP,
            message=(
                f"Legacy unstamped database (status={status_norm}); "
                f"back up, confirm equivalence, then alembic stamp "
                f"{_revision_label(head_revision)}."
                if ready
                else (
                    f"Legacy unstamped database (status={status_norm}); "
                    "backup and operator confirmation required before stamp."
                )
            ),
            blocks_startup=not ready,
            requires_backup=True,
            requires_confirmation=True,
            schema_status=status_norm,
            db_revision=db_revision,
            head_revision=head_revision,
            dialect=dialect_norm,
            flag_authoritative=True,
        )

    if status_norm == STATUS_BEHIND_HEAD:
        ready = _operator_ready(backup_available, confirmation_given)
        return SchemaStartupDecision(
            action=ACTION_ALEMBIC_UPGRADE_HEAD,
            message=(
                f"Database behind Alembic head "
                f"(db_revision={_revision_label(db_revision)}, "
                f"head_revision={_revision_label(head_revision)}); "
                "run alembic upgrade head."
                if ready
                else (
                    f"Database behind Alembic head "
                    f"(db_revision={_revision_label(db_revision)}, "
                    f"head_revision={_revision_label(head_revision)}); "
                    "backup and operator confirmation required before upgrade."
                )
            ),
            blocks_startup=not ready,
            requires_backup=True,
            requires_confirmation=True,
            schema_status=status_norm,
            db_revision=db_revision,
            head_revision=head_revision,
            dialect=dialect_norm,
            flag_authoritative=True,
        )

    if dialect_norm == "postgresql":
        return _fail_closed_decision(
            message=(
                f"PostgreSQL with ERP_ALEMBIC_AUTHORITATIVE on cannot use "
                f"migrate_schema for status={status_norm}; startup blocked."
            ),
            schema_status=status_norm,
            db_revision=db_revision,
            head_revision=head_revision,
            dialect=dialect_norm,
            flag_authoritative=True,
        )

    return _fail_closed_decision(
        message=(
            f"Ambiguous schema startup state (status={status_norm}, "
            f"dialect={dialect_norm}); startup blocked."
        ),
        schema_status=status_norm,
        db_revision=db_revision,
        head_revision=head_revision,
        dialect=dialect_norm,
        flag_authoritative=True,
    )


def _fail_closed_decision(
    *,
    message: str,
    schema_status: str,
    db_revision: str | None,
    head_revision: str | None,
    dialect: str,
    flag_authoritative: bool,
) -> SchemaStartupDecision:
    return SchemaStartupDecision(
        action=ACTION_FAIL_CLOSED,
        message=message,
        blocks_startup=True,
        requires_backup=False,
        requires_confirmation=False,
        schema_status=schema_status,
        db_revision=db_revision,
        head_revision=head_revision,
        dialect=dialect,
        flag_authoritative=flag_authoritative,
    )


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



def _application_table_names() -> tuple[str, ...]:
    import inspect

    import db
    import models  # noqa: F401 — register ORM tables on ``db.Base``

    names = tuple(sorted(db.Base.metadata.tables.keys()))
    if names:
        return names

    # ``importlib.reload(db)`` in tests can detach ORM tables; read declared names.
    declared = {
        cls.__tablename__
        for _, cls in inspect.getmembers(models, inspect.isclass)
        if getattr(cls, "__tablename__", None)
    }
    return tuple(sorted(declared))


def count_application_tables(session_or_engine: Session | Engine | Connection) -> int:
    """Read-only count of ORM application tables present in the database."""
    if isinstance(session_or_engine, Session):
        bind = session_or_engine.get_bind()
    else:
        bind = session_or_engine
    connection = _connection_from_bind_for_inspect(bind)
    owns_connection = not isinstance(bind, Connection)
    try:
        inspector = inspect(connection)
        return sum(
            1 for table in _application_table_names() if inspector.has_table(table)
        )
    finally:
        if owns_connection:
            connection.close()


def has_alembic_version_table(session_or_engine: Session | Engine | Connection) -> bool:
    """Read-only check for ``alembic_version`` table presence."""
    if isinstance(session_or_engine, Session):
        bind = session_or_engine.get_bind()
    else:
        bind = session_or_engine
    connection = _connection_from_bind_for_inspect(bind)
    owns_connection = not isinstance(bind, Connection)
    try:
        return inspect(connection).has_table(ALEMBIC_VERSION_TABLE)
    finally:
        if owns_connection:
            connection.close()


def infer_is_new_database(session_or_engine: Session | Engine | Connection) -> bool:
    """Read-only: True only when no ``alembic_version`` and zero ORM app tables."""
    if has_alembic_version_table(session_or_engine):
        return False
    return count_application_tables(session_or_engine) == 0


_RUNNER_DECISION_ACTIONS: frozenset[str] = frozenset(
    {ACTION_ALEMBIC_UPGRADE_HEAD, ACTION_REQUIRE_STAMP}
)


def is_production_runner_authorized(
    flag_authoritative: bool,
    decision: SchemaStartupDecision,
    gate_decision: MigrationGateDecision,
) -> bool:
    """True only when flag is on, decision requires runner execution, and gate allows."""
    return (
        flag_authoritative
        and decision.action in _RUNNER_DECISION_ACTIONS
        and gate_decision.allowed
    )


def _connection_from_bind_for_inspect(bind: Engine | Connection) -> Connection:
    if isinstance(bind, Connection):
        return bind
    return bind.connect()


class SchemaStartupDiagnosticsBundle(TypedDict):
    diagnostic: SchemaStartupDiagnostic
    decision: SchemaStartupDecision
    would_block_startup: bool


def build_schema_startup_decision(
    session_or_engine: Session | Engine | Connection,
    *,
    environ: Mapping[str, str] | None = None,
    is_new_db: bool | None = None,
    backup_available: bool = False,
    confirmation_given: bool = False,
    versions_dir: Path | None = None,
) -> SchemaStartupDiagnosticsBundle:
    """Build diagnostic + pure decision snapshot; does not execute the action."""
    diagnostic = get_schema_startup_diagnostic(
        session_or_engine,
        versions_dir=versions_dir,
    )
    if isinstance(session_or_engine, Session):
        bind = session_or_engine.get_bind()
    else:
        bind = session_or_engine

    resolved_is_new_db = (
        infer_is_new_database(session_or_engine)
        if is_new_db is None
        else is_new_db
    )
    dialect = bind.dialect.name
    decision = decide_schema_startup_action(
        flag_authoritative=is_alembic_authoritative_enabled(environ),
        schema_status=diagnostic["status"],
        is_new_db=resolved_is_new_db,
        dialect=dialect,
        backup_available=backup_available,
        confirmation_given=confirmation_given,
        db_revision=diagnostic["db_revision"],
        head_revision=diagnostic["head_revision"],
    )
    return SchemaStartupDiagnosticsBundle(
        diagnostic=diagnostic,
        decision=decision,
        would_block_startup=decision.blocks_startup,
    )


def log_schema_startup_decision_diagnostics(
    session_or_engine: Session | Engine | Connection,
    *,
    environ: Mapping[str, str] | None = None,
    is_new_db: bool | None = None,
    backup_available: bool = False,
    confirmation_given: bool = False,
    versions_dir: Path | None = None,
    logger: logging.Logger | None = None,
) -> SchemaStartupDiagnosticsBundle:
    """Log schema diagnostic + decision (P3.8-F); never executes or blocks startup."""
    log = logger or _LOG
    bundle = build_schema_startup_decision(
        session_or_engine,
        environ=environ,
        is_new_db=is_new_db,
        backup_available=backup_available,
        confirmation_given=confirmation_given,
        versions_dir=versions_dir,
    )
    diagnostic = bundle["diagnostic"]
    decision = bundle["decision"]
    log.info("[schema] %s", diagnostic["message"])
    log.info(
        "[schema] decision action=%s would_block_startup=%s "
        "(diagnostics only; not enforced) — %s",
        decision.action,
        bundle["would_block_startup"],
        decision.message,
    )
    return bundle
