"""P3.8-H — safe Alembic command wrapper (dry-run by default).

Centralizes Alembic CLI argv building and optional execution. Not wired into startup.
Never shells out with ``shell=True``; never exposes downgrade or arbitrary commands.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from paths import PROJECT_ROOT
from services.schema_version import discover_local_revisions, resolve_head_revision

_LOG = logging.getLogger(__name__)

DEFAULT_ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"

_PRODUCTION_DB_MARKERS: tuple[str, ...] = (
    "erp_data.db",
    "/production/",
    "production.db",
    "prod.db",
)

_BLOCKED_COMMANDS: frozenset[str] = frozenset({"downgrade", "drop", "destroy"})


@dataclass(frozen=True, slots=True)
class AlembicCommandResult:
    """Outcome of a wrapped Alembic command (dry-run or executed)."""

    command: str
    target: str
    success: bool
    message: str
    dry_run: bool
    executed: bool
    argv: tuple[str, ...]
    stdout: str | None = None
    stderr: str | None = None


def is_allowed_database_url(
    database_url: str | None,
    *,
    allow_production: bool = False,
) -> bool:
    """Fail-safe URL guard; production paths rejected unless explicitly allowed."""
    if database_url is None or not str(database_url).strip():
        return False
    if allow_production:
        return True
    lowered = str(database_url).strip().lower()
    return not any(marker in lowered for marker in _PRODUCTION_DB_MARKERS)


def _require_allowed_database_url(
    database_url: str,
    *,
    allow_production: bool = False,
) -> str:
    url = str(database_url).strip()
    if not is_allowed_database_url(url, allow_production=allow_production):
        raise ValueError(
            f"Refusing Alembic operation on disallowed database URL: {url!r}. "
            "Production paths (e.g. erp_data.db) are blocked."
        )
    return url


def _reject_blocked_subcommand(argv: tuple[str, ...] | list[str]) -> None:
    lowered = [part.lower() for part in argv]
    for blocked in _BLOCKED_COMMANDS:
        if blocked in lowered:
            raise ValueError(f"Blocked Alembic subcommand: {blocked!r}")


def get_alembic_heads(
    *,
    versions_dir: Path | None = None,
) -> tuple[str, ...]:
    """Return local Alembic head revision ids from ``alembic/versions`` (read-only)."""
    revisions = discover_local_revisions(versions_dir)
    if not revisions:
        return ()
    referenced = {down for down in revisions.values() if down}
    heads = [rev for rev in revisions if rev not in referenced]
    if not heads:
        head = resolve_head_revision(revisions)
        return (head,) if head else ()
    return tuple(sorted(heads))


def _engine_for_revision_read(url: str):
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    if url == "sqlite://":
        return create_engine(url, connect_args=connect_args, poolclass=StaticPool)
    return create_engine(url, connect_args=connect_args)


def get_current_revision(
    database_url: str,
    *,
    allow_production: bool = False,
) -> str | None:
    """Read-only current ``alembic_version.version_num``; does not run Alembic CLI."""
    url = _require_allowed_database_url(database_url, allow_production=allow_production)
    engine = _engine_for_revision_read(url)
    try:
        with engine.connect() as connection:
            if not inspect(connection).has_table("alembic_version"):
                return None
            row = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).fetchone()
            return str(row[0]) if row and row[0] is not None else None
    finally:
        engine.dispose()


def _alembic_argv_prefix() -> list[str]:
    """Prefer ``alembic`` on PATH; fall back to ``python -m alembic``."""
    alembic_bin = shutil.which("alembic")
    if alembic_bin:
        return [alembic_bin]
    return [sys.executable, "-m", "alembic"]


def _base_argv(
    *,
    database_url: str,
    alembic_ini: Path | None = None,
) -> list[str]:
    ini = alembic_ini or DEFAULT_ALEMBIC_INI
    return [
        *_alembic_argv_prefix(),
        "-c",
        str(ini),
        "-x",
        f"sqlalchemy.url={database_url}",
    ]


def build_upgrade_head_command(
    *,
    database_url: str,
    alembic_ini: Path | None = None,
    allow_production: bool = False,
) -> tuple[str, ...]:
    """Build argv for ``alembic upgrade head`` (no execution)."""
    url = _require_allowed_database_url(database_url, allow_production=allow_production)
    argv = [*_base_argv(database_url=url, alembic_ini=alembic_ini), "upgrade", "head"]
    _reject_blocked_subcommand(argv)
    return tuple(argv)


def build_stamp_command(
    *,
    database_url: str,
    revision: str,
    alembic_ini: Path | None = None,
    allow_production: bool = False,
) -> tuple[str, ...]:
    """Build argv for ``alembic stamp <revision>`` (no execution)."""
    url = _require_allowed_database_url(database_url, allow_production=allow_production)
    rev = revision.strip()
    if not rev:
        raise ValueError("stamp revision must be non-empty")
    argv = [*_base_argv(database_url=url, alembic_ini=alembic_ini), "stamp", rev]
    _reject_blocked_subcommand(argv)
    return tuple(argv)


def _dry_run_result(
    *,
    command: str,
    target: str,
    argv: tuple[str, ...],
) -> AlembicCommandResult:
    _LOG.info(
        "[alembic] dry-run %s %s — argv=%s",
        command,
        target,
        list(argv),
    )
    return AlembicCommandResult(
        command=command,
        target=target,
        success=True,
        message=f"Dry-run: alembic {command} {target} not executed.",
        dry_run=True,
        executed=False,
        argv=argv,
    )


def _execute_argv(
    *,
    command: str,
    target: str,
    argv: tuple[str, ...],
    database_url: str | None = None,
) -> AlembicCommandResult:
    _reject_blocked_subcommand(argv)
    env = os.environ.copy()
    if database_url:
        env["DATABASE_URL"] = database_url
    completed = subprocess.run(
        list(argv),
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        shell=False,
        check=False,
        env=env,
    )
    success = completed.returncode == 0
    message = (
        f"Executed alembic {command} {target} (exit {completed.returncode})."
        if success
        else f"Alembic {command} {target} failed (exit {completed.returncode})."
    )
    if success:
        _LOG.info("[alembic] %s", message)
    else:
        _LOG.warning("[alembic] %s", message)
    return AlembicCommandResult(
        command=command,
        target=target,
        success=success,
        message=message,
        dry_run=False,
        executed=True,
        argv=argv,
        stdout=completed.stdout or None,
        stderr=completed.stderr or None,
    )


def run_upgrade_head(
    *,
    database_url: str,
    allow_execute: bool = False,
    alembic_ini: Path | None = None,
    allow_production: bool = False,
) -> AlembicCommandResult:
    """Run or dry-run ``alembic upgrade head``; execution requires ``allow_execute=True``."""
    argv = build_upgrade_head_command(
        database_url=database_url,
        alembic_ini=alembic_ini,
        allow_production=allow_production,
    )
    if not allow_execute:
        return _dry_run_result(command="upgrade", target="head", argv=argv)
    return _execute_argv(
        command="upgrade",
        target="head",
        argv=argv,
        database_url=database_url,
    )


def run_stamp(
    *,
    database_url: str,
    revision: str,
    allow_execute: bool = False,
    alembic_ini: Path | None = None,
    allow_production: bool = False,
) -> AlembicCommandResult:
    """Run or dry-run ``alembic stamp``; execution requires ``allow_execute=True``."""
    argv = build_stamp_command(
        database_url=database_url,
        revision=revision,
        alembic_ini=alembic_ini,
        allow_production=allow_production,
    )
    target = revision.strip()
    if not allow_execute:
        return _dry_run_result(command="stamp", target=target, argv=argv)
    return _execute_argv(
        command="stamp",
        target=target,
        argv=argv,
        database_url=database_url,
    )
