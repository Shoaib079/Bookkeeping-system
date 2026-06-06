"""Orchestrate bank statement import — Phase 18-MVP-2 (no GL posting)."""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import uuid

from models import BankAccount, BankStatementImport, BankStatementRow
from reconciliation.duplicates import (
    apply_duplicate_checks,
    find_existing_file_import,
)
from reconciliation.statement_parse import mapping_to_json, parse_bank_statement

from paths import UPLOADS_DIR

STATEMENT_UPLOAD_ROOT = str(UPLOADS_DIR / "statements")
MAX_STATEMENT_BYTES = 10 * 1024 * 1024  # 10 MB


class StatementImportError(Exception):
    """Raised when import cannot proceed."""


class DuplicateFileWarning(StatementImportError):
    """Same file hash already imported; caller may retry with force_duplicate=True."""

    def __init__(self, existing_import: BankStatementImport):
        self.existing_import = existing_import
        super().__init__(
            f"Duplicate file (import #{existing_import.id} on {existing_import.import_date})"
        )


def _store_file(company_id: int, file_bytes: bytes, filename: str, file_hash: str) -> str:
    folder = os.path.join(STATEMENT_UPLOAD_ROOT, str(company_id))
    os.makedirs(folder, exist_ok=True)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    stored_name = f"{uuid.uuid4().hex[:12]}_{file_hash[:12]}.{ext}"
    path = os.path.join(folder, stored_name)
    with open(path, "wb") as fh:
        fh.write(file_bytes)
    return path


def import_bank_statement_file(
    session,
    *,
    company_id: int,
    bank_account_id: int,
    file_bytes: bytes,
    filename: str,
    column_mapping: dict[str, str | None],
    user_id: int | None,
    force_duplicate: bool = False,
    header_row: int = 1,
    sheet_name: str | None = None,
    notes: str | None = None,
) -> BankStatementImport:
    # sheet_name: Excel worksheet when workbook has multiple tabs
    """Parse a bank statement into staging tables. Never posts to the GL."""
    if len(file_bytes) > MAX_STATEMENT_BYTES:
        raise StatementImportError("File exceeds 10 MB limit")
    if not file_bytes:
        raise StatementImportError("File is empty")

    bank_acct = session.get(BankAccount, bank_account_id)
    if not bank_acct or bank_acct.company_id != company_id:
        raise StatementImportError("Bank account not found for this company")

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    existing = find_existing_file_import(session, company_id, file_hash)
    if existing and not force_duplicate:
        raise DuplicateFileWarning(existing)

    currency = bank_acct.currency or "TRY"
    parsed_rows = parse_bank_statement(
        file_bytes,
        filename,
        column_mapping,
        currency=currency,
        header_row=header_row,
        sheet_name=sheet_name or None,
    )
    apply_duplicate_checks(
        session,
        company_id=company_id,
        bank_account_id=bank_account_id,
        parsed_rows=parsed_rows,
    )

    file_path = _store_file(company_id, file_bytes, filename, file_hash)
    now = datetime.datetime.now()
    today = datetime.date.today()

    valid_dates = [r["date"] for r in parsed_rows if r.get("date")]
    start_date = min(valid_dates) if valid_dates else None
    end_date = max(valid_dates) if valid_dates else None

    valid_count = sum(1 for r in parsed_rows if r.get("parsed_successfully"))
    error_count = sum(1 for r in parsed_rows if not r.get("parsed_successfully"))
    flagged_count = sum(1 for r in parsed_rows if r.get("status") == "duplicate_flagged")

    imp = BankStatementImport(
        company_id=company_id,
        bank_account_id=bank_account_id,
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
        flagged_count=flagged_count,
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

    index_to_id: dict[int, int] = {}
    for row_data in parsed_rows:
        row = BankStatementRow(
            bank_statement_import_id=imp.id,
            status=row_data.get("status", "staging"),
            import_row_index=row_data["import_row_index"],
            date=row_data.get("date"),
            description=row_data.get("description", ""),
            debit_amount=row_data.get("debit_amount"),
            credit_amount=row_data.get("credit_amount"),
            amount=row_data.get("amount", 0.0),
            balance_after=row_data.get("balance_after"),
            currency=row_data.get("currency", currency),
            original_amount=row_data.get("original_amount", 0.0),
            bank_reference=row_data.get("bank_reference"),
            raw_line_text=row_data.get("raw_line_text"),
            normalized_description=row_data.get("normalized_description"),
            parsed_successfully=bool(row_data.get("parsed_successfully")),
            parse_error=row_data.get("parse_error"),
            duplicate_reason=row_data.get("duplicate_reason"),
            created_at=now,
        )
        session.add(row)
        session.flush()
        index_to_id[row_data["import_row_index"]] = row.id

    for row_data in parsed_rows:
        dup_idx = row_data.get("duplicate_of_index")
        if dup_idx and dup_idx in index_to_id:
            row_id = index_to_id[row_data["import_row_index"]]
            dup_of_id = index_to_id[dup_idx]
            db_row = session.get(BankStatementRow, row_id)
            if db_row:
                db_row.duplicate_of_row_id = dup_of_id

    session.commit()
    session.refresh(imp)
    return imp


def delete_bank_statement_import(session, import_id: int, company_id: int) -> bool:
    """Remove a staged import, its rows, and the stored file on disk."""
    imp = session.get(BankStatementImport, import_id)
    if not imp or imp.company_id != company_id:
        return False
    rows = (
        session.query(BankStatementRow)
        .filter_by(bank_statement_import_id=import_id)
        .all()
    )
    for row in rows:
        row.duplicate_of_row_id = None
    session.flush()
    session.query(BankStatementRow).filter_by(bank_statement_import_id=import_id).delete()
    file_path = imp.file_path
    session.delete(imp)
    session.commit()
    if file_path and os.path.isfile(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass
    return True


def skip_statement_row(session, row_id: int, company_id: int) -> bool:
    """Mark a staged row as skipped."""
    row = session.get(BankStatementRow, row_id)
    if not row:
        return False
    imp = session.get(BankStatementImport, row.bank_statement_import_id)
    if not imp or imp.company_id != company_id:
        return False
    row.status = "skipped"
    session.commit()
    return True
