"""FASTAPI-REACT-34 — read-only reconciliation health DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import BankAccount, BankTransaction, ChartOfAccounts, Payable, Sale
from reconciliation.company_card import company_card_enabled, compute_cc_payable_recon_health
from registry.service import get_setting
from services import posting as posting_svc
from services.money import money_to_float
from services.read_balances import calculate_account_balance


def _recon_status(diff: float) -> str:
    magnitude = abs(diff)
    if magnitude < 0.01:
        return "clean"
    if magnitude < 1000.0:
        return "discrepancy"
    return "material"


@dataclass(frozen=True, slots=True)
class ReconHealthSection:
    gl_balance: float
    subledger_balance: float
    difference: float
    status: str


@dataclass(frozen=True, slots=True)
class ReconHealthBankRow:
    account_id: int
    name: str
    currency: str | None
    stored_balance: float
    derived_balance: float
    difference: float
    status: str


@dataclass(frozen=True, slots=True)
class ReconHealthCoaDriftRow:
    account_code: str
    account_name: str
    account_type: str
    cached_balance: float
    expected_balance: float
    delta: float
    status: str


@dataclass(frozen=True, slots=True)
class ReconHealthCreditCardSection:
    enabled: bool
    gl_balance: float
    subledger_total: float
    difference: float
    status: str
    cards: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class ReconHealthPage:
    currency: str
    accounts_receivable: ReconHealthSection
    accounts_payable: ReconHealthSection
    credit_card: ReconHealthCreditCardSection | None
    bank_accounts: tuple[ReconHealthBankRow, ...]
    coa_drift_rows: tuple[ReconHealthCoaDriftRow, ...]
    coa_cache_clean: bool
    company_id: int


def _gl_subsection(
    session: Session,
    *,
    company_id: int,
    account_name: str,
    subledger_balance: float,
) -> ReconHealthSection:
    gl_acct = posting_svc.get_account_by_name(
        session, account_name, company_id=company_id
    )
    gl_balance = (
        round(
            money_to_float(
                calculate_account_balance(session, gl_acct, company_id=company_id)
            ),
            2,
        )
        if gl_acct
        else 0.0
    )
    subledger_balance = round(subledger_balance, 2)
    difference = round(gl_balance - subledger_balance, 2)
    return ReconHealthSection(
        gl_balance=gl_balance,
        subledger_balance=subledger_balance,
        difference=difference,
        status=_recon_status(difference),
    )


def _bank_derived_balance(session: Session, account_id: int) -> float:
    dep = (
        session.query(func.sum(BankTransaction.amount))
        .filter(
            BankTransaction.account_id == account_id,
            BankTransaction.type == "deposit",
            BankTransaction.is_void == False,  # noqa: E712
        )
        .scalar()
        or 0.0
    )
    wd = (
        session.query(func.sum(BankTransaction.amount))
        .filter(
            BankTransaction.account_id == account_id,
            BankTransaction.type == "withdrawal",
            BankTransaction.is_void == False,  # noqa: E712
        )
        .scalar()
        or 0.0
    )
    xfer_in = (
        session.query(func.sum(BankTransaction.amount))
        .filter(
            BankTransaction.account_id == account_id,
            BankTransaction.type == "transfer",
            BankTransaction.is_void == False,  # noqa: E712
            BankTransaction.description.like("Transfer from%"),
        )
        .scalar()
        or 0.0
    )
    xfer_out = (
        session.query(func.sum(BankTransaction.amount))
        .filter(
            BankTransaction.account_id == account_id,
            BankTransaction.type == "transfer",
            BankTransaction.is_void == False,  # noqa: E712
            ~BankTransaction.description.like("Transfer from%"),
        )
        .scalar()
        or 0.0
    )
    return round(money_to_float(dep - wd + xfer_in - xfer_out), 2)


def compute_recon_health(
    session: Session,
    *,
    company_id: int,
) -> ReconHealthPage:
    currency = get_setting(
        session, "accounting.base_currency", company_id=company_id
    ) or "TRY"

    sub_ar_bal = money_to_float(
        session.query(func.sum(Sale.amount - func.coalesce(Sale.paid_amount, 0.0)))
        .filter(
            Sale.company_id == company_id,
            Sale.sale_type == "Credit",
            Sale.is_void == False,  # noqa: E712
        )
        .scalar()
        or 0.0
    )
    accounts_receivable = _gl_subsection(
        session,
        company_id=company_id,
        account_name="Accounts Receivable",
        subledger_balance=sub_ar_bal,
    )

    sub_ap_bal = money_to_float(
        session.query(func.sum(Payable.amount - func.coalesce(Payable.paid_amount, 0.0)))
        .filter(
            Payable.company_id == company_id,
            Payable.is_void == False,  # noqa: E712
        )
        .scalar()
        or 0.0
    )
    accounts_payable = _gl_subsection(
        session,
        company_id=company_id,
        account_name="Accounts Payable",
        subledger_balance=sub_ap_bal,
    )

    credit_card: ReconHealthCreditCardSection | None = None
    if company_card_enabled(session, company_id):
        cc_health = compute_cc_payable_recon_health(session, company_id)
        cards = tuple(
            {
                "id": card["id"],
                "name": card["name"],
                "balance": card["balance"],
                "currency": card.get("currency"),
                "last_activity_date": (
                    card["last_activity_date"].isoformat()
                    if isinstance(card.get("last_activity_date"), datetime.date)
                    else None
                ),
            }
            for card in cc_health["cards"]
        )
        credit_card = ReconHealthCreditCardSection(
            enabled=True,
            gl_balance=cc_health["gl_balance"],
            subledger_total=cc_health["subledger_total"],
            difference=cc_health["difference"],
            status=cc_health["status"],
            cards=cards,
        )

    bank_accounts: list[ReconHealthBankRow] = []
    for bank_account in (
        session.query(BankAccount)
        .filter(BankAccount.company_id == company_id)
        .order_by(BankAccount.name)
        .all()
    ):
        stored = round(money_to_float(bank_account.balance), 2)
        derived = _bank_derived_balance(session, bank_account.id)
        difference = round(stored - derived, 2)
        bank_accounts.append(
            ReconHealthBankRow(
                account_id=bank_account.id,
                name=bank_account.name,
                currency=bank_account.currency,
                stored_balance=stored,
                derived_balance=derived,
                difference=difference,
                status=_recon_status(difference),
            )
        )

    coa_drift_rows: list[ReconHealthCoaDriftRow] = []
    for account in (
        session.query(ChartOfAccounts)
        .filter(ChartOfAccounts.company_id == company_id)
        .order_by(ChartOfAccounts.account_code)
        .all()
    ):
        expected = round(
            money_to_float(
                calculate_account_balance(session, account, company_id=company_id)
            ),
            2,
        )
        cached = round(money_to_float(account.balance), 2)
        delta = round(cached - expected, 2)
        if abs(delta) > 0.01:
            coa_drift_rows.append(
                ReconHealthCoaDriftRow(
                    account_code=account.account_code,
                    account_name=account.account_name,
                    account_type=account.account_type,
                    cached_balance=cached,
                    expected_balance=expected,
                    delta=delta,
                    status=_recon_status(delta),
                )
            )

    return ReconHealthPage(
        currency=str(currency),
        accounts_receivable=accounts_receivable,
        accounts_payable=accounts_payable,
        credit_card=credit_card,
        bank_accounts=tuple(bank_accounts),
        coa_drift_rows=tuple(coa_drift_rows),
        coa_cache_clean=len(coa_drift_rows) == 0,
        company_id=company_id,
    )
