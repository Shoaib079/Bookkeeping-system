"""Merchant settlement statement import — Phase 18-MVP-4."""

from __future__ import annotations

import datetime
import hashlib
import os
import uuid

from models import SettlementStatementImport, SettlementStatementRow
from reconciliation.settlement_parse import mapping_to_json, parse_settlement_statement

from paths import UPLOADS_DIR

SETTLEMENT_UPLOAD_ROOT = str(UPLOADS_DIR / "settlements")
MAX_SETTLEMENT_BYTES = 10 * 1024 * 1024


class SettlementImportError(Exception):
    """Raised when settlement import cannot proceed."""


class DuplicateSettlementWarning(SettlementImportError):
    """Same file hash already imported."""

    def __init__(self, existing_import: SettlementStatementImport):
        self.existing_import = existing_import
        super().__init__(
            f"Duplicate settlement file (import #{existing_import.id} on {existing_import.import_date})"
        )


def _store_file(company_id: int, file_bytes: bytes, filename: str, file_hash: str) -> str:
    folder = os.path.join(SETTLEMENT_UPLOAD_ROOT, str(company_id))
    os.makedirs(folder, exist_ok=True)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    stored_name = f"{uuid.uuid4().hex[:12]}_{file_hash[:12]}.{ext}"
    path = os.path.join(folder, stored_name)
    with open(path, "wb") as fh:
        fh.write(file_bytes)
    return path


def find_existing_settlement_import(session, company_id: int, file_hash: str):
    return (
        session.query(SettlementStatementImport)
        .filter_by(company_id=company_id, file_hash=file_hash)
        .order_by(SettlementStatementImport.created_at.desc())
        .first()
    )


def import_settlement_statement_file(
    session,
    *,
    company_id: int,
    file_bytes: bytes,
    filename: str,
    column_mapping: dict[str, str | None],
    user_id: int | None,
    currency: str = "TRY",
    force_duplicate: bool = False,
    header_row: int = 1,
    sheet_name: str | None = None,
    notes: str | None = None,
) -> SettlementStatementImport:
    """Parse a merchant settlement file into staging tables. Never posts to the GL."""
    if len(file_bytes) > MAX_SETTLEMENT_BYTES:
        raise SettlementImportError("File exceeds 10 MB limit")
    if not file_bytes:
        raise SettlementImportError("File is empty")

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    existing = find_existing_settlement_import(session, company_id, file_hash)
    if existing and not force_duplicate:
        raise DuplicateSettlementWarning(existing)

    parsed_rows = parse_settlement_statement(
        file_bytes,
        filename,
        column_mapping,
        currency=currency,
        header_row=header_row,
        sheet_name=sheet_name,
    )

    file_path = _store_file(company_id, file_bytes, filename, file_hash)
    now = datetime.datetime.now()
    today = datetime.date.today()

    valid_dates = [r["date"] for r in parsed_rows if r.get("date")]
    start_date = min(valid_dates) if valid_dates else None
    end_date = max(valid_dates) if valid_dates else None

    valid_count = sum(1 for r in parsed_rows if r.get("parsed_successfully"))
    error_count = sum(1 for r in parsed_rows if not r.get("parsed_successfully"))

    imp = SettlementStatementImport(
        company_id=company_id,
        file_name=filename,
        file_hash=file_hash,
        file_size=len(file_bytes),
        file_path=file_path,
        status="staging",
        import_date=today,
        start_date=start_date,
        end_date=end_date,
        row_count=len(parsed_rows),
        valid_count=valid_count,
        error_count=error_count,
        currency=currency,
        column_mapping_json=mapping_to_json(column_mapping),
        sheet_name=sheet_name,
        header_row=header_row,
        created_by_user_id=user_id,
        created_at=now,
        notes=notes,
    )
    session.add(imp)
    session.flush()

    for row_data in parsed_rows:
        row = SettlementStatementRow(
            settlement_statement_import_id=imp.id,
            status=row_data.get("status", "staging"),
            import_row_index=row_data["import_row_index"],
            date=row_data.get("date"),
            description=row_data.get("description", ""),
            batch_reference=row_data.get("batch_reference"),
            gross_amount=row_data.get("gross_amount", 0.0),
            fee_amount=row_data.get("fee_amount", 0.0),
            net_amount=row_data.get("net_amount", 0.0),
            currency=row_data.get("currency", currency),
            raw_line_text=row_data.get("raw_line_text"),
            parsed_successfully=bool(row_data.get("parsed_successfully")),
            parse_error=row_data.get("parse_error"),
            created_at=now,
        )
        session.add(row)

    session.commit()
    session.refresh(imp)
    return imp


def delete_settlement_statement_import(session, import_id: int, company_id: int) -> bool:
    """Remove a settlement import, its rows, and stored file."""
    imp = session.get(SettlementStatementImport, import_id)
    if not imp or imp.company_id != company_id:
        return False
    session.query(SettlementStatementRow).filter_by(
        settlement_statement_import_id=import_id
    ).delete()
    file_path = imp.file_path
    session.delete(imp)
    session.commit()
    if file_path and os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
    return True


def get_matching_settlement_rows(
    session,
    company_id: int,
    deposit_date: datetime.date,
    deposit_amount: float,
    *,
    days: int = 7,
) -> list[SettlementStatementRow]:
    """Staging settlement batches whose net matches a bank deposit within the date window."""
    window_start = deposit_date - datetime.timedelta(days=days)
    window_end = deposit_date + datetime.timedelta(days=days)
    amt = round(float(deposit_amount), 2)
    candidates = (
        session.query(SettlementStatementRow)
        .join(SettlementStatementImport)
        .filter(
            SettlementStatementImport.company_id == company_id,
            SettlementStatementRow.status == "staging",
            SettlementStatementRow.parsed_successfully == True,  # noqa: E712
            SettlementStatementRow.date >= window_start,
            SettlementStatementRow.date <= window_end,
        )
        .order_by(SettlementStatementRow.date, SettlementStatementRow.import_row_index)
        .all()
    )
    return [r for r in candidates if abs(round(float(r.net_amount), 2) - amt) <= 0.01]
