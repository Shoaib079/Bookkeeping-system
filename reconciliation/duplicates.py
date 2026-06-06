"""Soft duplicate detection for bank statement imports — Phase 18-MVP-2."""

from __future__ import annotations

from reconciliation.normalize import duplicate_row_key, normalize_description

_SKIP_STATUSES = frozenset({"skipped"})


def find_existing_file_import(session, company_id: int, file_hash: str):
    """Return a prior import with the same file hash for this company, if any."""
    from models import BankStatementImport

    return (
        session.query(BankStatementImport)
        .filter_by(company_id=company_id, file_hash=file_hash)
        .order_by(BankStatementImport.created_at.desc())
        .first()
    )


def flag_within_import_duplicates(parsed_rows: list[dict]) -> None:
    """Mark later rows that repeat the composite key within the same file."""
    seen: dict[tuple, int] = {}
    for row in parsed_rows:
        if not row.get("parsed_successfully"):
            continue
        key = duplicate_row_key(
            row_date=row["date"],
            amount=row["amount"],
            normalized_description=row["normalized_description"],
            balance_after=row.get("balance_after"),
        )
        if key in seen:
            row["status"] = "duplicate_flagged"
            row["duplicate_reason"] = "within_import"
            row["duplicate_of_index"] = seen[key]
        else:
            seen[key] = row["import_row_index"]


def flag_cross_import_duplicates(
    session,
    *,
    company_id: int,
    bank_account_id: int,
    parsed_rows: list[dict],
) -> None:
    """Flag rows matching prior staged imports or existing bank transactions."""
    from models import BankStatementImport, BankStatementRow, BankTransaction

    prior_keys: set[tuple] = set()
    prior_rows = (
        session.query(BankStatementRow)
        .join(BankStatementImport)
        .filter(
            BankStatementImport.company_id == company_id,
            BankStatementImport.bank_account_id == bank_account_id,
            BankStatementRow.status.notin_(list(_SKIP_STATUSES)),
            BankStatementRow.parsed_successfully == True,  # noqa: E712
        )
        .all()
    )
    def _add_keys(d: set, row_date, amount, norm_desc, balance_after):
        d.add(
            duplicate_row_key(
                row_date=row_date,
                amount=amount,
                normalized_description=norm_desc,
                balance_after=balance_after,
            )
        )
        if balance_after is not None:
            d.add(
                duplicate_row_key(
                    row_date=row_date,
                    amount=amount,
                    normalized_description=norm_desc,
                    balance_after=None,
                )
            )

    for pr in prior_rows:
        if pr.date is None:
            continue
        _add_keys(
            prior_keys,
            pr.date,
            pr.amount,
            pr.normalized_description or "",
            pr.balance_after,
        )

    bank_txns = (
        session.query(BankTransaction)
        .filter_by(company_id=company_id, account_id=bank_account_id, is_void=False)
        .all()
    )
    for bt in bank_txns:
        _add_keys(
            prior_keys,
            bt.date,
            abs(bt.amount or 0),
            normalize_description(bt.description),
            None,
        )

    for row in parsed_rows:
        if not row.get("parsed_successfully") or row.get("status") == "duplicate_flagged":
            continue
        key = duplicate_row_key(
            row_date=row["date"],
            amount=row["amount"],
            normalized_description=row["normalized_description"],
            balance_after=row.get("balance_after"),
        )
        key_no_bal = duplicate_row_key(
            row_date=row["date"],
            amount=row["amount"],
            normalized_description=row["normalized_description"],
            balance_after=None,
        )
        if key in prior_keys or key_no_bal in prior_keys:
            row["status"] = "duplicate_flagged"
            row["duplicate_reason"] = "prior_import"


def apply_duplicate_checks(
    session,
    *,
    company_id: int,
    bank_account_id: int,
    parsed_rows: list[dict],
) -> None:
    flag_within_import_duplicates(parsed_rows)
    flag_cross_import_duplicates(
        session,
        company_id=company_id,
        bank_account_id=bank_account_id,
        parsed_rows=parsed_rows,
    )
