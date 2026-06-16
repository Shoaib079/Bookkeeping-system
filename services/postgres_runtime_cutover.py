"""POSTGRES runtime cutover — flag-gated PostgreSQL ``DATABASE_URL`` resolution.

When all gates pass, ``paths.get_database_url()`` returns ``ERP_POSTGRES_RUNTIME_URL``.
Default remains SQLite ``erp_data.db``. Separate from ``ERP_MONEY_NUMERIC_CUTOVER``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

RUNTIME_CUTOVER_ENV_VAR = "ERP_POSTGRES_RUNTIME_CUTOVER"
RUNTIME_CUTOVER_APPROVAL_ENV_VAR = "ERP_POSTGRES_RUNTIME_APPROVAL"
RUNTIME_CUTOVER_APPROVAL_PHRASE = "APPROVE PRODUCTION POSTGRES CUTOVER"
RUNTIME_URL_ENV_VAR = "ERP_POSTGRES_RUNTIME_URL"
BACKUP_PATH_ENV_VAR = "ERP_POSTGRES_CUTOVER_BACKUP_PATH"

_TRUE_FLAG_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_FLAG_VALUES = frozenset({"0", "false", "no", "off"})

_POSTGRES_SCHEMES = frozenset(
    {
        "postgresql",
        "postgresql+psycopg2",
        "postgresql+psycopg",
        "postgres",
    }
)

_FORBIDDEN_RUNTIME_URL_FRAGMENTS = (
    "erp_data.db",
)


class InvalidPostgresRuntimeUrlError(ValueError):
    """Raised when a runtime PostgreSQL URL fails safety checks."""


@dataclass(frozen=True, slots=True)
class RuntimeCutoverEvaluation:
    enabled: bool
    approval_given: bool
    backup_path: str | None
    backup_valid: bool
    runtime_url: str | None
    runtime_url_valid: bool
    effective_url: str | None
    blocked_reason: str | None


def parse_postgres_runtime_cutover_flag(value: str | None) -> bool:
    """Parse ``ERP_POSTGRES_RUNTIME_CUTOVER`` (default off)."""
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


def is_postgres_runtime_cutover_enabled(
    environ: Mapping[str, str] | None = None,
) -> bool:
    source = os.environ if environ is None else environ
    return parse_postgres_runtime_cutover_flag(source.get(RUNTIME_CUTOVER_ENV_VAR))


def is_postgres_runtime_approval_given(
    environ: Mapping[str, str] | None = None,
) -> bool:
    source = os.environ if environ is None else environ
    value = source.get(RUNTIME_CUTOVER_APPROVAL_ENV_VAR)
    if value is None:
        return False
    return value.strip() == RUNTIME_CUTOVER_APPROVAL_PHRASE


def is_postgresql_database_url(url: str) -> bool:
    scheme = (urlparse(url.strip()).scheme or "").lower()
    return scheme in _POSTGRES_SCHEMES


def is_sqlite_database_url(url: str) -> bool:
    return url.strip().lower().startswith("sqlite:")


def validate_postgres_runtime_url(url: str) -> str:
    """Validate an operator-supplied PostgreSQL runtime URL."""
    stripped = url.strip()
    if not stripped:
        raise InvalidPostgresRuntimeUrlError("Runtime PostgreSQL URL is empty")
    if is_sqlite_database_url(stripped):
        raise InvalidPostgresRuntimeUrlError("Runtime URL must be PostgreSQL, not SQLite")
    scheme = (urlparse(stripped).scheme or "").lower()
    if scheme not in _POSTGRES_SCHEMES:
        raise InvalidPostgresRuntimeUrlError(
            f"Runtime URL scheme must be PostgreSQL (got {scheme!r})"
        )
    lowered = stripped.lower()
    for forbidden in _FORBIDDEN_RUNTIME_URL_FRAGMENTS:
        if forbidden in lowered:
            raise InvalidPostgresRuntimeUrlError(
                f"Runtime URL must not reference {forbidden!r}"
            )
    db_name = (urlparse(stripped).path or "").lstrip("/").split("?")[0]
    if not db_name:
        raise InvalidPostgresRuntimeUrlError("Runtime URL must include a database name")
    return stripped


def validate_cutover_backup_path(path: str | None) -> tuple[bool, str | None]:
    if not path or not str(path).strip():
        return False, None
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        return False, None
    if resolved.suffix.lower() != ".db":
        return False, None
    return True, str(resolved)


def runtime_cutover_blocked_reason(
    *,
    cutover_flag: bool,
    approval_given: bool,
    backup_valid: bool,
    runtime_url_valid: bool,
    target_is_sqlite: bool,
) -> str | None:
    """Return a human-readable block reason, or None when all gates pass."""
    if not cutover_flag:
        return "ERP_POSTGRES_RUNTIME_CUTOVER is off (default)."
    if not approval_given:
        return (
            f"Operator approval required: set {RUNTIME_CUTOVER_APPROVAL_ENV_VAR}="
            f"{RUNTIME_CUTOVER_APPROVAL_PHRASE!r}"
        )
    if not backup_valid:
        return (
            f"Valid SQLite backup file required at {BACKUP_PATH_ENV_VAR} "
            "(pre-cutover copy of erp_data.db)."
        )
    if not runtime_url_valid:
        return (
            f"Valid PostgreSQL runtime URL required at {RUNTIME_URL_ENV_VAR}."
        )
    if target_is_sqlite:
        return "Target DATABASE_URL is still SQLite; runtime cutover not applied."
    return None


def evaluate_runtime_cutover(
    *,
    environ: Mapping[str, str] | None = None,
    explicit_database_url: str | None = None,
) -> RuntimeCutoverEvaluation:
    source = os.environ if environ is None else environ
    enabled = is_postgres_runtime_cutover_enabled(source)
    approval_given = is_postgres_runtime_approval_given(source)
    backup_valid, backup_path = validate_cutover_backup_path(
        source.get(BACKUP_PATH_ENV_VAR)
    )
    raw_runtime_url = (source.get(RUNTIME_URL_ENV_VAR) or "").strip() or None
    runtime_url: str | None = None
    runtime_url_valid = False
    if raw_runtime_url:
        try:
            runtime_url = validate_postgres_runtime_url(raw_runtime_url)
            runtime_url_valid = True
        except InvalidPostgresRuntimeUrlError:
            runtime_url = raw_runtime_url

    explicit = (explicit_database_url or source.get("DATABASE_URL") or "").strip()
    effective_url: str | None = None
    if enabled and approval_given and backup_valid and runtime_url_valid:
        effective_url = runtime_url

    target_is_sqlite = not explicit or is_sqlite_database_url(explicit)
    if effective_url and explicit and is_postgresql_database_url(explicit):
        effective_url = explicit

    blocked = runtime_cutover_blocked_reason(
        cutover_flag=enabled,
        approval_given=approval_given,
        backup_valid=backup_valid,
        runtime_url_valid=runtime_url_valid,
        target_is_sqlite=target_is_sqlite and effective_url is None,
    )
    if enabled and approval_given and backup_valid and runtime_url_valid and effective_url:
        blocked = None

    return RuntimeCutoverEvaluation(
        enabled=enabled,
        approval_given=approval_given,
        backup_path=backup_path,
        backup_valid=backup_valid,
        runtime_url=runtime_url,
        runtime_url_valid=runtime_url_valid,
        effective_url=effective_url,
        blocked_reason=blocked,
    )


def resolve_runtime_database_url(
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Return PostgreSQL runtime URL when all cutover gates pass, else None."""
    evaluation = evaluate_runtime_cutover(environ=environ)
    return evaluation.effective_url
