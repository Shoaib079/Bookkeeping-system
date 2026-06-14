"""FASTAPI-P2.8 — reconciliation match/unmatch via existing match_post kernels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from models import BankStatementImport, BankStatementRow
from reconciliation.company_card import (
    post_credit_card_bill_payment,
    void_credit_card_bill_payment,
)
from reconciliation.match_post import (
    MatchPostError,
    post_bank_charge_outflow,
    post_deposit_clearing_match,
    post_equity_statement_match,
    post_generic_deposit,
    post_partner_statement_match,
    post_vendor_outflow,
    post_worker_statement_match,
)
from services import audit as audit_svc
from services import commit_modes
from services.commit_modes import RECONCILIATION_FAMILY, VOID_CASCADE_FAMILY
from services.unit_of_work import boundary_commit_scope

# Pinned EN transactional strings — must match registry/locales/transactional.py.
POSTED_OK_MSG = "Posted row #{row} to the general ledger."
UNPOSTED_OK_MSG = "Bill payment unposted."
VOID_REASON_REQUIRED_MSG = "Void reason is required."
INVALID_MATCH_TYPE_MSG = "Unknown reconciliation match type: {match_type}"
UNMATCH_NOT_SUPPORTED_MSG = (
    "Only credit card bill payment rows can be unposted with this action."
)

SUPPORTED_MATCH_TYPES = frozenset(
    {
        "generic_deposit",
        "bank_charge",
        "deposit_clearing",
        "vendor_outflow",
        "partner",
        "worker",
        "equity",
        "cc_bill_payment",
    }
)


@dataclass(frozen=True, slots=True)
class ReconciliationMatchResult:
    statement_row_id: int
    match_id: int
    journal_entry_id: int | None
    message: str
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ReconciliationUnmatchResult:
    statement_row_id: int
    message: str
    details: dict[str, Any]


def _validate_void_reason(reason: str | None) -> str:
    cleaned = (reason or "").strip()
    if not cleaned:
        raise ValueError(VOID_REASON_REQUIRED_MSG)
    return cleaned


def _row_amount_and_index(session: Session, row_id: int) -> tuple[float, int]:
    row = session.get(BankStatementRow, row_id)
    if row is None:
        raise MatchPostError("Statement row not found")
    return round(float(row.amount), 2), row.import_row_index


def _audit_description(match_type: str, *, amount: float, **ctx: Any) -> str:
    if match_type == "generic_deposit":
        return f"Deposit · {amount:,.2f} · CR {ctx['credit_account_name']}"
    if match_type == "bank_charge":
        return f"Bank charge · {amount:,.2f}"
    if match_type == "deposit_clearing":
        return f"Clearing match · {amount:,.2f}"
    if match_type == "vendor_outflow":
        return f"Payment · {amount:,.2f}"
    if match_type == "partner":
        return f"Partner {ctx['movement_type']} · {amount:,.2f}"
    if match_type == "worker":
        label = "salary" if ctx.get("movement_type") == "Salary" else "advance"
        return f"Worker {label} · {amount:,.2f}"
    if match_type == "equity":
        return f"Equity {ctx['equity_kind']} · {amount:,.2f}"
    if match_type == "cc_bill_payment":
        return f"CC bill payment · {amount:,.2f}"
    raise ValueError(INVALID_MATCH_TYPE_MSG.format(match_type=match_type))


def _dispatch_match(
    session: Session,
    *,
    company_id: int,
    user_id: int | None,
    statement_row_id: int,
    match_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if match_type == "generic_deposit":
        return post_generic_deposit(
            session,
            row_id=statement_row_id,
            company_id=company_id,
            credit_account_name=payload["credit_account_name"],
            user_id=user_id,
        )
    if match_type == "bank_charge":
        return post_bank_charge_outflow(
            session,
            row_id=statement_row_id,
            company_id=company_id,
            user_id=user_id,
            charge_subtype=payload.get("charge_subtype"),
        )
    if match_type == "deposit_clearing":
        return post_deposit_clearing_match(
            session,
            row_id=statement_row_id,
            company_id=company_id,
            sale_ids=payload["sale_ids"],
            user_id=user_id,
            settlement_row_id=payload.get("settlement_row_id"),
            confirm_inferred_fee=bool(payload.get("confirm_inferred_fee")),
        )
    if match_type == "vendor_outflow":
        return post_vendor_outflow(
            session,
            row_id=statement_row_id,
            company_id=company_id,
            vendor_id=payload["vendor_id"],
            user_id=user_id,
            payable_id=payload.get("payable_id"),
            expense_category=payload.get("expense_category") or "Office Expense",
            create_expense=bool(payload.get("create_expense")),
        )
    if match_type == "partner":
        return post_partner_statement_match(
            session,
            row_id=statement_row_id,
            company_id=company_id,
            partner_id=payload["partner_id"],
            movement_type=payload["movement_type"],
            user_id=user_id,
        )
    if match_type == "worker":
        return post_worker_statement_match(
            session,
            row_id=statement_row_id,
            company_id=company_id,
            worker_id=payload["worker_id"],
            movement_type=payload["movement_type"],
            user_id=user_id,
            gross_salary=payload.get("gross_salary"),
            deductions=payload.get("deductions") or 0.0,
            advance_recovery=payload.get("advance_recovery") or 0.0,
            pay_period=payload.get("pay_period"),
        )
    if match_type == "equity":
        return post_equity_statement_match(
            session,
            row_id=statement_row_id,
            company_id=company_id,
            equity_kind=payload["equity_kind"],
            user_id=user_id,
        )
    if match_type == "cc_bill_payment":
        return post_credit_card_bill_payment(
            session,
            row_id=statement_row_id,
            company_id=company_id,
            credit_card_account_id=payload["credit_card_account_id"],
            user_id=user_id,
        )
    raise ValueError(INVALID_MATCH_TYPE_MSG.format(match_type=match_type))


def _uses_recon_boundary(match_type: str) -> bool:
    return match_type != "cc_bill_payment"


def match_statement_row(
    session: Session,
    *,
    company_id: int,
    user_id: int | None,
    performed_by: str | None,
    statement_row_id: int,
    match_type: str,
    **payload: Any,
) -> ReconciliationMatchResult:
    """Match/post one bank statement row — mirrors Streamlit match posters + audit."""
    try:
        cleaned_type = (match_type or "").strip().lower()
        if cleaned_type not in SUPPORTED_MATCH_TYPES:
            raise ValueError(INVALID_MATCH_TYPE_MSG.format(match_type=match_type))

        immutable_snapshot = _immutable_row_snapshot(
            session, statement_row_id, company_id
        )

        def _run() -> dict[str, Any]:
            result = _dispatch_match(
                session,
                company_id=company_id,
                user_id=user_id,
                statement_row_id=statement_row_id,
                match_type=cleaned_type,
                payload=payload,
            )
            amount, _row_index = _row_amount_and_index(session, statement_row_id)
            audit_svc.record_audit(
                session,
                action=audit_svc.ACTION_POST,
                entity_type=audit_svc.ENTITY_BANK_STATEMENT_ROW,
                entity_id=statement_row_id,
                description=_audit_description(
                    cleaned_type,
                    amount=amount,
                    credit_account_name=payload.get("credit_account_name"),
                    movement_type=payload.get("movement_type"),
                    equity_kind=payload.get("equity_kind"),
                ),
                performed_by=performed_by,
                company_id=company_id,
                commit_family=(
                    RECONCILIATION_FAMILY
                    if _uses_recon_boundary(cleaned_type)
                    and commit_modes.is_boundary_mode(RECONCILIATION_FAMILY)
                    else None
                ),
            )
            _assert_row_history_immutable(session, statement_row_id, immutable_snapshot)
            return result

        if (
            _uses_recon_boundary(cleaned_type)
            and commit_modes.is_boundary_mode(RECONCILIATION_FAMILY)
        ):
            with boundary_commit_scope(session, RECONCILIATION_FAMILY):
                result = _run()
        else:
            result = _run()
    except MatchPostError as exc:
        raise ValueError(str(exc)) from exc

    _, row_index = _row_amount_and_index(session, statement_row_id)
    return ReconciliationMatchResult(
        statement_row_id=statement_row_id,
        match_id=statement_row_id,
        journal_entry_id=result.get("journal_entry_id"),
        message=POSTED_OK_MSG.format(row=row_index),
        details=result,
    )


def unmatch_statement_row(
    session: Session,
    *,
    company_id: int,
    performed_by: str | None,
    statement_row_id: int,
    reason: str,
) -> ReconciliationUnmatchResult:
    """Unpost a posted cc_bill_payment row — mirrors Review unpost control."""
    cleaned_reason = _validate_void_reason(reason)
    row = session.get(BankStatementRow, statement_row_id)
    if row is None:
        raise ValueError("Statement row not found")
    imp = session.get(BankStatementImport, row.bank_statement_import_id)
    if imp is None or imp.company_id != company_id:
        raise ValueError("Import not found for this company")
    if row.match_type != "cc_bill_payment":
        raise ValueError(UNMATCH_NOT_SUPPORTED_MSG)

    immutable_snapshot = _immutable_row_snapshot(session, statement_row_id, company_id)

    def _run() -> dict[str, Any]:
        result = void_credit_card_bill_payment(
            session,
            statement_row_id,
            company_id,
            cleaned_reason,
            performed_by=performed_by,
        )
        _assert_row_history_immutable(session, statement_row_id, immutable_snapshot)
        return result

    try:
        if commit_modes.is_boundary_mode(VOID_CASCADE_FAMILY):
            with boundary_commit_scope(session, VOID_CASCADE_FAMILY):
                details = _run()
        else:
            details = _run()
    except MatchPostError as exc:
        raise ValueError(str(exc)) from exc

    return ReconciliationUnmatchResult(
        statement_row_id=statement_row_id,
        message=UNPOSTED_OK_MSG,
        details=details,
    )


def _immutable_row_snapshot(
    session: Session,
    row_id: int,
    company_id: int,
) -> dict[str, Any]:
    row = session.get(BankStatementRow, row_id)
    if row is None:
        raise MatchPostError("Statement row not found")
    imp = session.get(BankStatementImport, row.bank_statement_import_id)
    if imp is None or imp.company_id != company_id:
        raise MatchPostError("Import not found for this company")
    return {
        "import_row_index": row.import_row_index,
        "date": row.date,
        "description": row.description,
        "debit_amount": row.debit_amount,
        "credit_amount": row.credit_amount,
        "amount": row.amount,
        "balance_after": row.balance_after,
        "currency": row.currency,
        "original_amount": row.original_amount,
        "bank_reference": row.bank_reference,
        "raw_line_text": row.raw_line_text,
        "normalized_description": row.normalized_description,
        "parsed_successfully": row.parsed_successfully,
        "parse_error": row.parse_error,
        "duplicate_reason": row.duplicate_reason,
        "duplicate_of_row_id": row.duplicate_of_row_id,
    }


def _assert_row_history_immutable(
    session: Session,
    row_id: int,
    snapshot: dict[str, Any],
) -> None:
    row = session.get(BankStatementRow, row_id)
    if row is None:
        raise MatchPostError("Statement row not found")
    for key, expected in snapshot.items():
        actual = getattr(row, key)
        if actual != expected:
            raise MatchPostError(
                f"Statement row history field '{key}' must remain immutable after reconciliation."
            )
