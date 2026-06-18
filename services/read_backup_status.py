"""FASTAPI-REACT-42 — read-only backup inventory DTOs and compute."""

from __future__ import annotations

import datetime
import os
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import CompanySetting
from paths import BACKUPS_DIR, DB_PATH


@dataclass(frozen=True, slots=True)
class BackupFileRow:
    name: str
    size_kb: float
    modified: datetime.datetime
    has_uploads_zip: bool


@dataclass(frozen=True, slots=True)
class BackupStatusPage:
    rows: tuple[BackupFileRow, ...]
    row_count: int
    last_backup: datetime.datetime | None
    db_size_kb: float
    cloud_folder: str | None
    cloud_folder_exists: bool
    company_id: int


def _uploads_zip_path(db_path: str) -> str:
    return db_path.replace(".db", ".uploads.zip")


def _read_cloud_folder(session: Session, company_id: int) -> str | None:
    row = (
        session.query(CompanySetting)
        .filter_by(company_id=company_id, key="cloud_backup_folder")
        .first()
    )
    if row is None or not row.value:
        return None
    text = str(row.value).strip()
    return text or None


def _list_backup_files() -> list[BackupFileRow]:
    backup_dir = str(BACKUPS_DIR)
    os.makedirs(backup_dir, exist_ok=True)
    rows: list[BackupFileRow] = []
    for name in os.listdir(backup_dir):
        if not name.endswith(".db"):
            continue
        path = os.path.join(backup_dir, name)
        zip_path = _uploads_zip_path(path)
        stat = os.stat(path)
        modified = datetime.datetime.fromtimestamp(stat.st_mtime)
        if modified.tzinfo:
            modified = modified.replace(tzinfo=None)
        rows.append(
            BackupFileRow(
                name=name,
                size_kb=round(stat.st_size / 1024, 1),
                modified=modified,
                has_uploads_zip=os.path.exists(zip_path),
            )
        )
    rows.sort(key=lambda row: row.modified, reverse=True)
    return rows


def compute_backup_status_page(
    session: Session,
    *,
    company_id: int,
) -> BackupStatusPage:
    rows = tuple(_list_backup_files())
    cloud_folder = _read_cloud_folder(session, company_id)
    db_size_kb = (
        round(os.path.getsize(DB_PATH) / 1024, 1) if DB_PATH.exists() else 0.0
    )
    return BackupStatusPage(
        rows=rows,
        row_count=len(rows),
        last_backup=rows[0].modified if rows else None,
        db_size_kb=db_size_kb,
        cloud_folder=cloud_folder,
        cloud_folder_exists=bool(cloud_folder and os.path.isdir(cloud_folder)),
        company_id=company_id,
    )
