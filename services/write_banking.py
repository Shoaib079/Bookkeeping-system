"""FASTAPI-P2.7 — manual bank deposit/withdrawal/transfer writes (Banking page parity)."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import BankAccount, BankTransaction, JournalEntry
from reconciliation.company_card import apply_account_balance_delta, is_credit_card_account
from services import audit as audit_svc
from services import commit_modes
from services import posting as posting_svc
from services.commit_modes import POST_BANK_TRANSACTION_FAMILY
from services.unit_of_work import boundary_commit_scope

# Pinned EN transactional strings — must match registry/locales/transactional.py.
INVALID_AMOUNT_MSG = "Please enter a valid amount."
INVALID_TXN_TYPE_MSG = "Unknown transaction type: {transaction_type}"
BANK_NOT_FOUND_MSG = "Bank account not found."
DEST_ACCOUNT_MSG = "Choose a different destination account for transfer."
CC_MANUAL_DEPOSIT_MSG = (
    "Use **Banking → Statement import** to record a card bill payment (bank debit), "
    "not a manual deposit on the card account."
)
CC_TRANSFER_MSG = (
    "Transfers between bank and credit card accounts are not supported here — "
    "use Match & post for bill payments."
)
DEPOSIT_RECORDED_MSG = "Bank deposit of {amount:,.2f} recorded."
WITHDRAWAL_RECORDED_MSG = "Bank withdrawal of {amount:,.2f} recorded."
TRANSFER_RECORDED_MSG = (
    "Transfer of {amount:,.2f} from {from_acct} to {to_acct} recorded."
)
TXN_ADDED_MSG = "Transaction recorded."

SUPPORTED_TXN_TYPES = frozenset({"deposit", "withdrawal", "transfer"})

_REF_TYPE_BY_TXN = {
    "deposit": "BankDeposit",
    "withdrawal": "BankWithdrawal",
    "transfer": "BankTransfer",
}


@dataclass(frozen=True, slots=True)
class BankTransactionWriteResult:
    bank_transaction_id: int
    paired_transaction_id: int | None
    journal_entry_id: int | None
    message: str


def _resolve_bank_account(
    session: Session,
    *,
    company_id: int,
    bank_account_id: int,
) -> BankAccount:
    ba = (
        session.query(BankAccount)
        .filter_by(id=bank_account_id, company_id=company_id, is_active=True)
        .first()
    )
    if ba is None:
        raise ValueError(BANK_NOT_FOUND_MSG)
    return ba


def _journal_entry_for_txn(
    session: Session,
    *,
    reference_type: str,
    bank_transaction_id: int,
    company_id: int,
) -> JournalEntry | None:
    return (
        session.query(JournalEntry)
        .filter_by(
            reference_type=reference_type,
            reference_id=bank_transaction_id,
            company_id=company_id,
        )
        .order_by(JournalEntry.id.desc())
        .first()
    )


def _audit_description_deposit_withdrawal(
    txn_type: str,
    amount: float,
    currency: str,
    account_name: str,
) -> str:
    title = txn_type.title()
    return f"Bank {title} {amount:,.2f} {currency} — {account_name}"


def _audit_description_transfer(
    amount: float,
    source_name: str,
    dest_name: str,
) -> str:
    return f"Transfer {amount:,.2f} from {source_name} → {dest_name}"


def _persist_subledger(
    session: Session,
    *,
    in_boundary: bool,
) -> None:
    if in_boundary:
        session.flush()
    else:
        session.commit()


def create_manual_bank_transaction(
    session: Session,
    *,
    company_id: int,
    performed_by: str | None,
    entry_date: datetime.date,
    amount: float,
    transaction_type: str,
    bank_account_id: int,
    destination_bank_account_id: int | None = None,
    currency: str | None = None,
    notes: str | None = None,
) -> BankTransactionWriteResult:
    """Create manual bank movement — mirrors Banking page form + Add Transaction audit."""
    txn_type = (transaction_type or "").strip().lower()
    if txn_type not in SUPPORTED_TXN_TYPES:
        raise ValueError(INVALID_TXN_TYPE_MSG.format(transaction_type=transaction_type))
    if amount is None or amount <= 0:
        raise ValueError(INVALID_AMOUNT_MSG)

    source = _resolve_bank_account(
        session, company_id=company_id, bank_account_id=bank_account_id
    )
    ccy = (currency or source.currency or "TRY").strip()
    cleaned_notes = (notes or "").strip()

    in_boundary = commit_modes.is_boundary_mode(POST_BANK_TRANSACTION_FAMILY)
    family = POST_BANK_TRANSACTION_FAMILY if in_boundary else None

    def _run() -> BankTransactionWriteResult:
        if txn_type == "transfer":
            return _create_transfer(
                session,
                company_id=company_id,
                performed_by=performed_by,
                entry_date=entry_date,
                amount=amount,
                source=source,
                destination_bank_account_id=destination_bank_account_id,
                cleaned_notes=cleaned_notes,
                in_boundary=in_boundary,
                family=family,
            )
        return _create_deposit_or_withdrawal(
            session,
            company_id=company_id,
            performed_by=performed_by,
            entry_date=entry_date,
            amount=amount,
            txn_type=txn_type,
            source=source,
            currency=ccy,
            cleaned_notes=cleaned_notes,
            in_boundary=in_boundary,
            family=family,
        )

    if in_boundary:
        with boundary_commit_scope(session, POST_BANK_TRANSACTION_FAMILY):
            return _run()
    return _run()


def _create_deposit_or_withdrawal(
    session: Session,
    *,
    company_id: int,
    performed_by: str | None,
    entry_date: datetime.date,
    amount: float,
    txn_type: str,
    source: BankAccount,
    currency: str,
    cleaned_notes: str,
    in_boundary: bool,
    family: str | None,
) -> BankTransactionWriteResult:
    if txn_type == "deposit" and is_credit_card_account(source):
        raise ValueError(CC_MANUAL_DEPOSIT_MSG)

    apply_account_balance_delta(source, txn_type, amount)
    txn = BankTransaction(
        account_id=source.id,
        date=entry_date,
        amount=amount,
        type=txn_type,
        description=cleaned_notes,
        company_id=company_id,
    )
    session.add(txn)
    session.add(source)
    _persist_subledger(session, in_boundary=in_boundary)

    journal_entry_id: int | None = None
    if not (txn_type == "withdrawal" and is_credit_card_account(source)):
        posting_svc.post_bank_transaction(
            session,
            txn.id,
            amount,
            entry_date,
            txn_type,
            currency=currency,
            company_id=company_id,
            commit_family=family,
        )
        entry = _journal_entry_for_txn(
            session,
            reference_type=_REF_TYPE_BY_TXN[txn_type],
            bank_transaction_id=txn.id,
            company_id=company_id,
        )
        journal_entry_id = entry.id if entry else None

    audit_svc.record_audit(
        session,
        action=audit_svc.ACTION_CREATE,
        entity_type=audit_svc.ENTITY_BANK_TRANSACTION,
        entity_id=txn.id,
        description=_audit_description_deposit_withdrawal(
            txn_type, amount, currency, source.name
        ),
        performed_by=performed_by,
        company_id=company_id,
        commit_family=family,
    )

    if txn_type == "deposit":
        message = DEPOSIT_RECORDED_MSG.format(amount=amount)
    elif txn_type == "withdrawal":
        message = WITHDRAWAL_RECORDED_MSG.format(amount=amount)
    else:
        message = TXN_ADDED_MSG

    return BankTransactionWriteResult(
        bank_transaction_id=txn.id,
        paired_transaction_id=None,
        journal_entry_id=journal_entry_id,
        message=message,
    )


def _create_transfer(
    session: Session,
    *,
    company_id: int,
    performed_by: str | None,
    entry_date: datetime.date,
    amount: float,
    source: BankAccount,
    destination_bank_account_id: int | None,
    cleaned_notes: str,
    in_boundary: bool,
    family: str | None,
) -> BankTransactionWriteResult:
    if destination_bank_account_id is None:
        raise ValueError(DEST_ACCOUNT_MSG)
    if destination_bank_account_id == source.id:
        raise ValueError(DEST_ACCOUNT_MSG)
    if is_credit_card_account(source):
        raise ValueError(CC_TRANSFER_MSG)

    dest = _resolve_bank_account(
        session,
        company_id=company_id,
        bank_account_id=destination_bank_account_id,
    )
    if is_credit_card_account(dest):
        raise ValueError(CC_TRANSFER_MSG)

    apply_account_balance_delta(source, "withdrawal", amount)
    apply_account_balance_delta(dest, "deposit", amount)
    src_txn = BankTransaction(
        account_id=source.id,
        date=entry_date,
        amount=amount,
        type="transfer",
        description=cleaned_notes,
        company_id=company_id,
    )
    dest_txn = BankTransaction(
        account_id=dest.id,
        date=entry_date,
        amount=amount,
        type="transfer",
        description=f"Transfer from {source.name}: {cleaned_notes}",
        company_id=company_id,
    )
    session.add_all([src_txn, dest_txn, source, dest])
    _persist_subledger(session, in_boundary=in_boundary)

    posting_svc.post_bank_transfer(
        session,
        src_txn.id,
        amount,
        entry_date,
        source.name,
        dest.name,
        company_id=company_id,
        commit_family=family,
    )
    entry = _journal_entry_for_txn(
        session,
        reference_type="BankTransfer",
        bank_transaction_id=src_txn.id,
        company_id=company_id,
    )
    journal_entry_id = entry.id if entry else None

    audit_svc.record_audit(
        session,
        action=audit_svc.ACTION_CREATE,
        entity_type=audit_svc.ENTITY_BANK_TRANSACTION,
        entity_id=src_txn.id,
        description=_audit_description_transfer(amount, source.name, dest.name),
        performed_by=performed_by,
        company_id=company_id,
        commit_family=family,
    )

    return BankTransactionWriteResult(
        bank_transaction_id=src_txn.id,
        paired_transaction_id=dest_txn.id,
        journal_entry_id=journal_entry_id,
        message=TRANSFER_RECORDED_MSG.format(
            amount=amount,
            from_acct=source.name,
            to_acct=dest.name,
        ),
    )
