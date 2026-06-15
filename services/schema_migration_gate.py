"""P3.8-I — backup / confirmation gate for future Alembic-authoritative startup.

Validation only — never creates backups, runs Alembic, or mutates the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

MigrationAction = Literal["upgrade_head", "stamp", "verify_only"]

ACTION_UPGRADE_HEAD: MigrationAction = "upgrade_head"
ACTION_STAMP: MigrationAction = "stamp"
ACTION_VERIFY_ONLY: MigrationAction = "verify_only"

REQUIRED_CONFIRMATION_PHRASE = "I HAVE BACKED UP THIS DATABASE"

_PRODUCTION_DB_MARKERS: tuple[str, ...] = (
    "erp_data.db",
    "/production/",
    "production.db",
    "prod.db",
)

_KNOWN_ACTIONS: frozenset[str] = frozenset(
    {ACTION_UPGRADE_HEAD, ACTION_STAMP, ACTION_VERIFY_ONLY}
)


@dataclass(frozen=True, slots=True)
class BackupStatus:
    path: str | None
    valid: bool
    message: str


@dataclass(frozen=True, slots=True)
class ConfirmationStatus:
    provided: bool
    valid: bool
    message: str


@dataclass(frozen=True, slots=True)
class MigrationGateDecision:
    allowed: bool
    message: str
    requires_backup: bool
    requires_confirmation: bool
    backup_valid: bool
    confirmation_valid: bool
    action: str
    is_populated: bool
    production_database: bool


def is_production_database_path(db_path_or_url: str | None) -> bool:
    if not db_path_or_url or not str(db_path_or_url).strip():
        return False
    lowered = str(db_path_or_url).strip().lower()
    return any(marker in lowered for marker in _PRODUCTION_DB_MARKERS)


def validate_backup_path(
    backup_path: str | Path | None,
    *,
    strict: bool = False,
) -> BackupStatus:
    """Path validation only; does not create or restore backups."""
    if backup_path is None or not str(backup_path).strip():
        return BackupStatus(
            path=None,
            valid=False,
            message="Backup path not provided.",
        )
    path = Path(str(backup_path)).expanduser()
    path_str = str(path)
    if not path.exists():
        return BackupStatus(path=path_str, valid=False, message="Backup path does not exist.")
    if not path.is_file():
        return BackupStatus(path=path_str, valid=False, message="Backup path is not a regular file.")
    if strict and path.stat().st_size <= 0:
        return BackupStatus(path=path_str, valid=False, message="Backup file is empty.")
    return BackupStatus(path=path_str, valid=True, message="Backup path is valid.")


def validate_confirmation_phrase(confirmation_value: str | None) -> ConfirmationStatus:
    """Require exact operator phrase; no mutation."""
    if confirmation_value is None or not confirmation_value.strip():
        return ConfirmationStatus(
            provided=False,
            valid=False,
            message="Confirmation phrase not provided.",
        )
    if confirmation_value.strip() != REQUIRED_CONFIRMATION_PHRASE:
        return ConfirmationStatus(
            provided=True,
            valid=False,
            message=(
                f'Confirmation must exactly match: "{REQUIRED_CONFIRMATION_PHRASE}".'
            ),
        )
    return ConfirmationStatus(
        provided=True,
        valid=True,
        message="Confirmation phrase accepted.",
    )


def _gate_requirements(
    *,
    action: str,
    is_populated: bool,
    require_backup: bool,
    require_confirmation: bool,
    production_database: bool,
) -> tuple[bool, bool]:
    if action == ACTION_VERIFY_ONLY:
        return False, False

    if action == ACTION_UPGRADE_HEAD and not is_populated:
        if production_database:
            return True, True
        return False, False

    needs_backup = require_backup
    needs_confirmation = require_confirmation

    if action == ACTION_STAMP:
        needs_backup = True
        needs_confirmation = True

    if action == ACTION_UPGRADE_HEAD and is_populated:
        needs_backup = require_backup or needs_backup
        needs_confirmation = require_confirmation or needs_confirmation
        if production_database:
            needs_backup = True
            needs_confirmation = True

    if production_database and action in {ACTION_UPGRADE_HEAD, ACTION_STAMP}:
        needs_backup = True
        needs_confirmation = True

    return needs_backup, needs_confirmation


def evaluate_migration_gate(
    *,
    db_path_or_url: str,
    action: str,
    is_populated: bool,
    backup_path: str | Path | None = None,
    confirmation_value: str | None = None,
    require_backup: bool = False,
    require_confirmation: bool = False,
) -> MigrationGateDecision:
    """Validate backup/confirmation preconditions; does not execute migrations."""
    action_norm = action.strip().lower()
    production_database = is_production_database_path(db_path_or_url)

    if action_norm not in _KNOWN_ACTIONS:
        return MigrationGateDecision(
            allowed=False,
            message=f"Unknown migration action: {action!r}.",
            requires_backup=False,
            requires_confirmation=False,
            backup_valid=False,
            confirmation_valid=False,
            action=action_norm,
            is_populated=is_populated,
            production_database=production_database,
        )

    needs_backup, needs_confirmation = _gate_requirements(
        action=action_norm,
        is_populated=is_populated,
        require_backup=require_backup,
        require_confirmation=require_confirmation,
        production_database=production_database,
    )

    backup_status = validate_backup_path(
        backup_path,
        strict=production_database or is_populated,
    )
    confirmation_status = validate_confirmation_phrase(confirmation_value)

    backup_valid = backup_status.valid if needs_backup else True
    confirmation_valid = confirmation_status.valid if needs_confirmation else True

    if action_norm == ACTION_VERIFY_ONLY:
        return MigrationGateDecision(
            allowed=True,
            message="verify_only does not require backup or confirmation.",
            requires_backup=False,
            requires_confirmation=False,
            backup_valid=True,
            confirmation_valid=True,
            action=action_norm,
            is_populated=is_populated,
            production_database=production_database,
        )

    if action_norm == ACTION_UPGRADE_HEAD and not is_populated and not production_database:
        return MigrationGateDecision(
            allowed=True,
            message="Empty database upgrade allowed without backup or confirmation.",
            requires_backup=False,
            requires_confirmation=False,
            backup_valid=True,
            confirmation_valid=True,
            action=action_norm,
            is_populated=is_populated,
            production_database=production_database,
        )

    blockers: list[str] = []
    if needs_backup and not backup_status.valid:
        blockers.append(backup_status.message)
    if needs_confirmation and not confirmation_status.valid:
        blockers.append(confirmation_status.message)

    if blockers:
        return MigrationGateDecision(
            allowed=False,
            message="Migration gate blocked: " + " ".join(blockers),
            requires_backup=needs_backup,
            requires_confirmation=needs_confirmation,
            backup_valid=backup_valid,
            confirmation_valid=confirmation_valid,
            action=action_norm,
            is_populated=is_populated,
            production_database=production_database,
        )

    return MigrationGateDecision(
        allowed=True,
        message="Migration gate passed; backup and confirmation requirements satisfied.",
        requires_backup=needs_backup,
        requires_confirmation=needs_confirmation,
        backup_valid=backup_valid,
        confirmation_valid=confirmation_valid,
        action=action_norm,
        is_populated=is_populated,
        production_database=production_database,
    )
