"""P3.8-K2 — flag-gated schema startup wiring.

Orchestrates detection → decision → gate → optional Alembic runner before the boot
session opens. Flag off preserves ``migrate_schema()`` then diagnostics.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from paths import DATABASE_URL
from services.alembic_runner import AlembicCommandResult, run_upgrade_head
from services.schema_migration_gate import (
    ACTION_UPGRADE_HEAD,
    evaluate_migration_gate,
    validate_backup_path,
    validate_confirmation_phrase,
)
from services.money_numeric_cutover import (
    evaluate_money_numeric_cutover_gate,
    is_money_numeric_cutover_authorized,
    is_money_numeric_cutover_eligible,
    is_money_numeric_cutover_enabled,
    resolve_money_numeric_allow_production,
    run_money_numeric_post_cutover,
)
from services.schema_startup import (
    ACTION_ALEMBIC_UPGRADE_HEAD,
    ACTION_FAIL_CLOSED,
    ACTION_REQUIRE_STAMP,
    ACTION_VERIFY_ONLY,
    SchemaStartupDecision,
    build_schema_startup_decision,
    infer_is_new_database,
    is_alembic_authoritative_enabled,
    is_production_runner_authorized,
    log_schema_startup_decision_diagnostics,
)

_LOG = logging.getLogger(__name__)

BACKUP_PATH_ENV_VAR = "ERP_SCHEMA_BACKUP_PATH"
CONFIRMATION_ENV_VAR = "ERP_SCHEMA_MIGRATION_CONFIRMATION"

MigrateSchemaFn = Callable[[Session], Any]
LogDiagnosticsFn = Callable[[Session], Any]
RunUpgradeHeadFn = Callable[..., AlembicCommandResult]


@dataclass(frozen=True, slots=True)
class SchemaStartupSessionPlan:
    flag_authoritative: bool
    skip_migrate_schema: bool
    schema_step_succeeded: bool
    money_numeric_cutover_executed: bool = False


class SchemaStartupError(RuntimeError):
    """Structured startup failure when ``ERP_ALEMBIC_AUTHORITATIVE=1`` blocks."""

    def __init__(
        self,
        message: str,
        *,
        action: str,
        operator_step: str,
    ) -> None:
        self.action = action
        self.operator_step = operator_step
        super().__init__(message)


_session_plan: SchemaStartupSessionPlan | None = None


def reset_schema_startup_plan() -> None:
    """Test helper — clear cached pre-session plan."""
    global _session_plan
    _session_plan = None


def get_schema_startup_plan() -> SchemaStartupSessionPlan | None:
    return _session_plan


def _engine_for_startup_read(database_url: str):
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    if database_url == "sqlite://":
        return create_engine(
            database_url,
            connect_args=connect_args,
            poolclass=StaticPool,
        )
    return create_engine(database_url, connect_args=connect_args)


def _operator_gate_inputs(
    environ: Mapping[str, str] | None,
) -> tuple[bool, bool, str | None, str | None]:
    source = os.environ if environ is None else environ
    backup_path = source.get(BACKUP_PATH_ENV_VAR)
    confirmation = source.get(CONFIRMATION_ENV_VAR)
    backup_available = (
        validate_backup_path(backup_path).valid if backup_path else False
    )
    confirmation_given = validate_confirmation_phrase(confirmation).valid
    return backup_available, confirmation_given, backup_path, confirmation


def _raise_blocked(decision: SchemaStartupDecision) -> None:
    operator_step = decision.message
    if decision.action == ACTION_REQUIRE_STAMP:
        operator_step = (
            "Back up the database, confirm schema equivalence, then run "
            f"alembic stamp {decision.head_revision!r} before restarting with the flag on."
        )
    elif decision.action == ACTION_ALEMBIC_UPGRADE_HEAD:
        operator_step = (
            "Back up the database, confirm with the required phrase, then run "
            "alembic upgrade head manually before restarting with the flag on."
        )
    elif decision.action == ACTION_FAIL_CLOSED:
        operator_step = (
            "Resolve the schema revision mismatch manually; do not downgrade. "
            "Disable ERP_ALEMBIC_AUTHORITATIVE to fall back to migrate_schema()."
        )
    raise SchemaStartupError(
        f"[schema startup] action={decision.action} blocked — {decision.message}",
        action=decision.action,
        operator_step=operator_step,
    )


def _raise_gate_blocked(
    decision: SchemaStartupDecision,
    *,
    gate_message: str,
) -> None:
    raise SchemaStartupError(
        (
            f"[schema startup] action={decision.action} blocked by migration gate — "
            f"{gate_message}"
        ),
        action=decision.action,
        operator_step=gate_message,
    )


def _raise_runner_failed(
    decision: SchemaStartupDecision,
    *,
    runner_message: str,
) -> None:
    raise SchemaStartupError(
        (
            f"[schema startup] action={decision.action} failed — "
            f"{runner_message}"
        ),
        action=decision.action,
        operator_step=(
            "Fix the Alembic upgrade failure, restore from backup if needed, "
            "then restart."
        ),
    )


def prepare_schema_startup_authoritative(
    *,
    database_url: str | None = None,
    environ: Mapping[str, str] | None = None,
    run_upgrade_head_fn: RunUpgradeHeadFn = run_upgrade_head,
) -> SchemaStartupSessionPlan:
    """Pre-boot-session authoritative schema step; may run Alembic subprocess."""
    global _session_plan

    if not is_alembic_authoritative_enabled(environ):
        _session_plan = SchemaStartupSessionPlan(
            flag_authoritative=False,
            skip_migrate_schema=False,
            schema_step_succeeded=True,
        )
        return _session_plan

    url = database_url or DATABASE_URL
    backup_available, confirmation_given, backup_path, confirmation = (
        _operator_gate_inputs(environ)
    )
    engine = _engine_for_startup_read(url)
    try:
        is_new_db = infer_is_new_database(engine)
        bundle = build_schema_startup_decision(
            engine,
            environ=environ,
            is_new_db=is_new_db,
            backup_available=backup_available,
            confirmation_given=confirmation_given,
        )
        decision = bundle["decision"]

        if decision.action == ACTION_FAIL_CLOSED or decision.blocks_startup:
            _raise_blocked(decision)

        if decision.action == ACTION_VERIFY_ONLY:
            _session_plan = SchemaStartupSessionPlan(
                flag_authoritative=True,
                skip_migrate_schema=True,
                schema_step_succeeded=True,
            )
            return _session_plan

        if decision.action == ACTION_REQUIRE_STAMP:
            _raise_blocked(decision)

        if decision.action == ACTION_ALEMBIC_UPGRADE_HEAD:
            if is_new_db:
                gate = evaluate_migration_gate(
                    db_path_or_url=url,
                    action=ACTION_UPGRADE_HEAD,
                    is_populated=False,
                    backup_path=backup_path,
                    confirmation_value=confirmation,
                    is_strict_new_empty=True,
                )
                if not is_production_runner_authorized(True, decision, gate):
                    _raise_gate_blocked(decision, gate_message=gate.message)

                allow_production = is_production_runner_authorized(True, decision, gate)
                result = run_upgrade_head_fn(
                    database_url=url,
                    allow_execute=True,
                    allow_production=allow_production,
                )
                if not result.success:
                    detail = result.message
                    if result.stderr:
                        detail = f"{detail} stderr={result.stderr.strip()}"
                    _raise_runner_failed(decision, runner_message=detail)

                _session_plan = SchemaStartupSessionPlan(
                    flag_authoritative=True,
                    skip_migrate_schema=True,
                    schema_step_succeeded=True,
                )
                return _session_plan

            # Populated behind_head: K2 blocks unless MD-05 money cutover is armed.
            gate = evaluate_migration_gate(
                db_path_or_url=url,
                action=ACTION_UPGRADE_HEAD,
                is_populated=True,
                backup_path=backup_path,
                confirmation_value=confirmation,
                require_backup=True,
                require_confirmation=True,
            )
            if not gate.allowed:
                _raise_gate_blocked(decision, gate_message=gate.message)

            cutover_enabled = is_money_numeric_cutover_enabled(environ)
            cutover_eligible = is_money_numeric_cutover_eligible(
                schema_status=decision.schema_status,
                db_revision=decision.db_revision,
                head_revision=decision.head_revision,
            )
            if cutover_enabled and cutover_eligible:
                money_gate = evaluate_money_numeric_cutover_gate(
                    db_path_or_url=url,
                    backup_path=backup_path,
                    confirmation_value=confirmation,
                )
                allow_production = resolve_money_numeric_allow_production(
                    url,
                    environ=environ,
                )
                if is_money_numeric_cutover_authorized(
                    cutover_enabled=True,
                    eligible=True,
                    gate_decision=money_gate,
                    allow_production=allow_production,
                    database_url=url,
                ):
                    result = run_upgrade_head_fn(
                        database_url=url,
                        allow_execute=True,
                        allow_production=allow_production,
                    )
                    if not result.success:
                        detail = result.message
                        if result.stderr:
                            detail = f"{detail} stderr={result.stderr.strip()}"
                        _raise_runner_failed(decision, runner_message=detail)

                    _LOG.info(
                        "[schema] MD-05 money NUMERIC cutover executed "
                        "(%s → %s).",
                        "0001",
                        "0002",
                    )
                    _session_plan = SchemaStartupSessionPlan(
                        flag_authoritative=True,
                        skip_migrate_schema=True,
                        schema_step_succeeded=True,
                        money_numeric_cutover_executed=True,
                    )
                    return _session_plan

                if not money_gate.allowed:
                    _raise_gate_blocked(decision, gate_message=money_gate.message)

            _raise_blocked(decision)

        _raise_blocked(decision)
    finally:
        engine.dispose()


def run_schema_startup_in_session(
    session: Session,
    *,
    migrate_schema_fn: MigrateSchemaFn,
    log_diagnostics_fn: LogDiagnosticsFn | None = None,
    environ: Mapping[str, str] | None = None,
) -> None:
    """In-session schema step after ``prepare_schema_startup_authoritative()``."""
    plan = _session_plan
    if plan is None:
        prepare_schema_startup_authoritative(environ=environ)
        plan = _session_plan
    assert plan is not None

    log_fn = log_diagnostics_fn or (
        lambda s: log_schema_startup_decision_diagnostics(s, environ=environ)
    )

    if not plan.flag_authoritative:
        migrate_schema_fn(session)
        log_fn(session)
        return

    if not plan.skip_migrate_schema:
        migrate_schema_fn(session)
    log_fn(session)

    if plan.money_numeric_cutover_executed:
        run_money_numeric_post_cutover(session)
