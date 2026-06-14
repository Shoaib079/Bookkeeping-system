"""P3.7 — read-only Alembic schema version detection.

Inspects ``alembic_version`` and local revision files only. Never upgrades, stamps,
or mutates the database. ``migrate_schema()`` remains authoritative until cutover.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session

from paths import PROJECT_ROOT

ALEMBIC_VERSION_TABLE = "alembic_version"

Status = Literal["unstamped", "at_head", "behind_head", "ahead_of_code", "unknown"]

STATUS_UNSTAMPED: Status = "unstamped"
STATUS_AT_HEAD: Status = "at_head"
STATUS_BEHIND_HEAD: Status = "behind_head"
STATUS_AHEAD_OF_CODE: Status = "ahead_of_code"
STATUS_UNKNOWN: Status = "unknown"

DEFAULT_VERSIONS_DIR = PROJECT_ROOT / "alembic" / "versions"

_REVISION_RE = re.compile(r"""^revision\s*=\s*["']([^"']+)["']""", re.MULTILINE)
_DOWN_REVISION_RE = re.compile(
    r"""^down_revision\s*=\s*(None|["']([^"']+)["'])""",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class SchemaVersionInfo:
    """Read-only snapshot of DB migration state vs local Alembic revisions."""

    status: Status
    alembic_version_table_exists: bool
    db_revision: str | None
    head_revision: str | None
    known_revisions: tuple[str, ...]
    row_count: int
    message: str

    def is_unstamped(self) -> bool:
        return self.status == STATUS_UNSTAMPED

    def is_at_head(self) -> bool:
        return self.status == STATUS_AT_HEAD


def discover_local_revisions(
    versions_dir: Path | None = None,
) -> dict[str, str | None]:
    """Parse revision ids from local Alembic ``versions/*.py`` files (no CLI/import)."""
    root = versions_dir or DEFAULT_VERSIONS_DIR
    revisions: dict[str, str | None] = {}
    if not root.is_dir():
        return revisions

    for path in sorted(root.glob("*.py")):
        if path.name == "__init__.py":
            continue
        source = path.read_text(encoding="utf-8")
        rev_match = _REVISION_RE.search(source)
        if not rev_match:
            continue
        revision = rev_match.group(1)
        down_match = _DOWN_REVISION_RE.search(source)
        down_revision: str | None = None
        if down_match and down_match.group(1) != "None":
            down_revision = down_match.group(2)
        revisions[revision] = down_revision
    return revisions


def resolve_head_revision(
    revisions: dict[str, str | None] | None = None,
    *,
    versions_dir: Path | None = None,
) -> str | None:
    """Return the Alembic head revision id from local files (single-head repos only)."""
    rev_map = revisions if revisions is not None else discover_local_revisions(versions_dir)
    if not rev_map:
        return None

    referenced = {down for down in rev_map.values() if down}
    heads = [rev for rev in rev_map if rev not in referenced]
    if len(heads) == 1:
        return heads[0]
    if len(heads) > 1:
        return max(heads)
    return max(rev_map)


def _connection_from_bind(bind: Engine | Connection) -> Connection:
    if isinstance(bind, Connection):
        return bind
    return bind.connect()


def _read_db_versions(connection: Connection) -> tuple[bool, list[str]]:
    inspector = inspect(connection)
    if not inspector.has_table(ALEMBIC_VERSION_TABLE):
        return False, []

    rows = connection.execute(
        text(f"SELECT version_num FROM {ALEMBIC_VERSION_TABLE}")
    ).fetchall()
    versions = [str(row[0]) for row in rows if row[0] is not None]
    return True, versions


def _classify_revision(
    db_revision: str,
    *,
    head_revision: str | None,
    known_revisions: set[str],
) -> Status:
    if head_revision and db_revision == head_revision:
        return STATUS_AT_HEAD
    if db_revision in known_revisions:
        return STATUS_BEHIND_HEAD
    if head_revision and db_revision > head_revision:
        return STATUS_AHEAD_OF_CODE
    return STATUS_UNKNOWN


def _build_message(
    status: Status,
    *,
    db_revision: str | None,
    head_revision: str | None,
    row_count: int,
    table_exists: bool,
) -> str:
    if status == STATUS_UNSTAMPED:
        if not table_exists:
            return (
                "Database has no alembic_version table; Alembic has not stamped this DB."
            )
        return "alembic_version table exists but has no rows; database is unstamped."

    if status == STATUS_AT_HEAD:
        return f"Database is stamped at Alembic head revision {db_revision!r}."

    if status == STATUS_BEHIND_HEAD:
        return (
            f"Database revision {db_revision!r} is behind local head "
            f"{head_revision!r}; run upgrade after cutover planning."
        )

    if status == STATUS_AHEAD_OF_CODE:
        return (
            f"Database revision {db_revision!r} is ahead of local code head "
            f"{head_revision!r}; deployment may be stale."
        )

    if row_count > 1:
        return (
            f"alembic_version has {row_count} rows; expected exactly one. "
            "Treat migration state as unknown."
        )

    return (
        f"Unrecognized alembic_version value {db_revision!r}; "
        f"local head is {head_revision!r}."
    )


def detect_schema_version(
    bind: Engine | Connection,
    *,
    versions_dir: Path | None = None,
) -> SchemaVersionInfo:
    """Read-only detection of DB migration state vs local Alembic revisions."""
    rev_map = discover_local_revisions(versions_dir)
    known = tuple(sorted(rev_map))
    head_revision = resolve_head_revision(rev_map)

    connection = _connection_from_bind(bind)
    owns_connection = not isinstance(bind, Connection)
    try:
        table_exists, versions = _read_db_versions(connection)
    finally:
        if owns_connection:
            connection.close()

    row_count = len(versions)

    if not table_exists or row_count == 0:
        return SchemaVersionInfo(
            status=STATUS_UNSTAMPED,
            alembic_version_table_exists=table_exists,
            db_revision=None,
            head_revision=head_revision,
            known_revisions=known,
            row_count=row_count,
            message=_build_message(
                STATUS_UNSTAMPED,
                db_revision=None,
                head_revision=head_revision,
                row_count=row_count,
                table_exists=table_exists,
            ),
        )

    if row_count != 1:
        return SchemaVersionInfo(
            status=STATUS_UNKNOWN,
            alembic_version_table_exists=True,
            db_revision=versions[0] if versions else None,
            head_revision=head_revision,
            known_revisions=known,
            row_count=row_count,
            message=_build_message(
                STATUS_UNKNOWN,
                db_revision=versions[0] if versions else None,
                head_revision=head_revision,
                row_count=row_count,
                table_exists=True,
            ),
        )

    db_revision = versions[0].strip()
    if not db_revision:
        status = STATUS_UNKNOWN
    else:
        status = _classify_revision(
            db_revision,
            head_revision=head_revision,
            known_revisions=set(rev_map),
        )

    return SchemaVersionInfo(
        status=status,
        alembic_version_table_exists=True,
        db_revision=db_revision or None,
        head_revision=head_revision,
        known_revisions=known,
        row_count=1,
        message=_build_message(
            status,
            db_revision=db_revision or None,
            head_revision=head_revision,
            row_count=1,
            table_exists=True,
        ),
    )


def detect_schema_version_from_session(
    session: Session,
    *,
    versions_dir: Path | None = None,
) -> SchemaVersionInfo:
    """Convenience wrapper using the session's bound engine/connection."""
    return detect_schema_version(session.get_bind(), versions_dir=versions_dir)


def format_schema_version_summary(info: SchemaVersionInfo) -> str:
    """Human-readable one-line summary for logs or startup banners."""
    parts = [
        f"schema_version={info.status}",
        f"db_revision={info.db_revision!r}",
        f"head_revision={info.head_revision!r}",
    ]
    if info.row_count:
        parts.append(f"rows={info.row_count}")
    return "; ".join(parts)
