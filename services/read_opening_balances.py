"""FASTAPI-REACT-35 — read-only opening balances status DTOs and compute."""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import BankAccount, Customer, JournalEntry, JournalEntryLine, Product, Vendor
from reconciliation.company_card import is_credit_card_account
from registry.service import get_setting
from services import posting as posting_svc
from services.money import money_to_float
from services.read_balances import calculate_account_balance


@dataclass(frozen=True, slots=True)
class OpeningBalanceBankRow:
    id: int
    name: str
    kind: str
    currency: str | None
    stored_balance: float
    is_active: bool
    ob_posted: bool
    ob_date: datetime.date | None
    ob_amount: float | None


@dataclass(frozen=True, slots=True)
class OpeningBalanceCustomerRow:
    id: int
    name: str
    ob_posted: bool
    ob_date: datetime.date | None
    ob_amount: float | None


@dataclass(frozen=True, slots=True)
class OpeningBalanceVendorRow:
    id: int
    name: str
    ob_posted: bool
    ob_date: datetime.date | None
    ob_amount: float | None


@dataclass(frozen=True, slots=True)
class OpeningBalanceProductRow:
    id: int
    name: str
    sku: str | None
    quantity: float
    ob_posted: bool
    ob_date: datetime.date | None
    ob_cost: float | None


@dataclass(frozen=True, slots=True)
class OpeningBalanceCapitalStatus:
    ob_posted: bool
    ob_date: datetime.date | None
    ob_amount: float | None


@dataclass(frozen=True, slots=True)
class OpeningBalanceLoanRow:
    journal_entry_id: int
    entry_date: datetime.date
    description: str
    amount: float


@dataclass(frozen=True, slots=True)
class OpeningBalancesStatusPage:
    currency: str
    obe_balance: float
    obe_status: str
    obe_account_exists: bool
    bank_rows: tuple[OpeningBalanceBankRow, ...]
    customer_rows: tuple[OpeningBalanceCustomerRow, ...]
    vendor_rows: tuple[OpeningBalanceVendorRow, ...]
    product_rows: tuple[OpeningBalanceProductRow, ...]
    capital: OpeningBalanceCapitalStatus
    loan_rows: tuple[OpeningBalanceLoanRow, ...]
    company_id: int


def _obe_status(balance: float) -> str:
    if abs(balance) < 0.01:
        return "balanced"
    if balance > 0:
        return "assets_exceed"
    return "liabilities_exceed"


def _opening_journal_entry(
    session: Session,
    *,
    company_id: int,
    reference_type: str,
    reference_id: int,
) -> JournalEntry | None:
    return (
        session.query(JournalEntry)
        .filter(
            JournalEntry.company_id == company_id,
            JournalEntry.reference_type == reference_type,
            JournalEntry.reference_id == reference_id,
        )
        .first()
    )


def _opening_amount(journal_entry: JournalEntry | None, obe_account_id: int | None) -> float | None:
    if journal_entry is None or obe_account_id is None:
        return None
    for line in journal_entry.lines:
        if line.account_id != obe_account_id:
            debit = money_to_float(line.debit)
            credit = money_to_float(line.credit)
            return debit if debit > 0 else credit
    return None


def compute_opening_balances_status(
    session: Session,
    *,
    company_id: int,
) -> OpeningBalancesStatusPage:
    currency = get_setting(
        session, "accounting.base_currency", company_id=company_id
    ) or "TRY"
    obe_acct = posting_svc.get_account_by_name(
        session, "Opening Balance Equity", company_id=company_id
    )
    obe_account_id = obe_acct.id if obe_acct else None
    obe_balance = (
        round(
            money_to_float(
                calculate_account_balance(session, obe_acct, company_id=company_id)
            ),
            2,
        )
        if obe_acct
        else 0.0
    )

    bank_rows: list[OpeningBalanceBankRow] = []
    for bank_account in (
        session.query(BankAccount)
        .filter(BankAccount.company_id == company_id)
        .order_by(BankAccount.name)
        .all()
    ):
        journal_entry = _opening_journal_entry(
            session,
            company_id=company_id,
            reference_type="OBBank",
            reference_id=bank_account.id,
        )
        bank_rows.append(
            OpeningBalanceBankRow(
                id=bank_account.id,
                name=bank_account.name,
                kind="credit_card" if is_credit_card_account(bank_account) else "bank",
                currency=bank_account.currency,
                stored_balance=round(money_to_float(bank_account.balance), 2),
                is_active=bool(bank_account.is_active),
                ob_posted=journal_entry is not None,
                ob_date=journal_entry.entry_date if journal_entry else None,
                ob_amount=_opening_amount(journal_entry, obe_account_id),
            )
        )

    customer_rows: list[OpeningBalanceCustomerRow] = []
    for customer in (
        session.query(Customer)
        .filter(Customer.company_id == company_id)
        .order_by(Customer.name)
        .all()
    ):
        journal_entry = _opening_journal_entry(
            session,
            company_id=company_id,
            reference_type="OBAR",
            reference_id=customer.id,
        )
        customer_rows.append(
            OpeningBalanceCustomerRow(
                id=customer.id,
                name=customer.name,
                ob_posted=journal_entry is not None,
                ob_date=journal_entry.entry_date if journal_entry else None,
                ob_amount=_opening_amount(journal_entry, obe_account_id),
            )
        )

    vendor_rows: list[OpeningBalanceVendorRow] = []
    for vendor in (
        session.query(Vendor)
        .filter(Vendor.company_id == company_id, Vendor.is_active == True)  # noqa: E712
        .order_by(Vendor.name)
        .all()
    ):
        journal_entry = _opening_journal_entry(
            session,
            company_id=company_id,
            reference_type="OBAP",
            reference_id=vendor.id,
        )
        vendor_rows.append(
            OpeningBalanceVendorRow(
                id=vendor.id,
                name=vendor.name,
                ob_posted=journal_entry is not None,
                ob_date=journal_entry.entry_date if journal_entry else None,
                ob_amount=_opening_amount(journal_entry, obe_account_id),
            )
        )

    product_rows: list[OpeningBalanceProductRow] = []
    for product in (
        session.query(Product)
        .filter(Product.company_id == company_id, Product.is_active == True)  # noqa: E712
        .order_by(Product.name)
        .all()
    ):
        journal_entry = _opening_journal_entry(
            session,
            company_id=company_id,
            reference_type="OBInventory",
            reference_id=product.id,
        )
        product_rows.append(
            OpeningBalanceProductRow(
                id=product.id,
                name=product.name,
                sku=product.sku,
                quantity=money_to_float(product.quantity),
                ob_posted=journal_entry is not None,
                ob_date=journal_entry.entry_date if journal_entry else None,
                ob_cost=_opening_amount(journal_entry, obe_account_id),
            )
        )

    capital_journal = _opening_journal_entry(
        session,
        company_id=company_id,
        reference_type="OBCapital",
        reference_id=0,
    )
    capital = OpeningBalanceCapitalStatus(
        ob_posted=capital_journal is not None,
        ob_date=capital_journal.entry_date if capital_journal else None,
        ob_amount=_opening_amount(capital_journal, obe_account_id),
    )

    loan_rows: list[OpeningBalanceLoanRow] = []
    for journal_entry in (
        session.query(JournalEntry)
        .filter(
            JournalEntry.company_id == company_id,
            JournalEntry.reference_type == "OBLoan",
        )
        .order_by(JournalEntry.entry_date, JournalEntry.id)
        .all()
    ):
        amount = _opening_amount(journal_entry, obe_account_id)
        loan_rows.append(
            OpeningBalanceLoanRow(
                journal_entry_id=journal_entry.id,
                entry_date=journal_entry.entry_date,
                description=journal_entry.description or "",
                amount=amount or 0.0,
            )
        )

    return OpeningBalancesStatusPage(
        currency=str(currency),
        obe_balance=obe_balance,
        obe_status="equity_missing" if obe_acct is None else _obe_status(obe_balance),
        obe_account_exists=obe_acct is not None,
        bank_rows=tuple(bank_rows),
        customer_rows=tuple(customer_rows),
        vendor_rows=tuple(vendor_rows),
        product_rows=tuple(product_rows),
        capital=capital,
        loan_rows=tuple(loan_rows),
        company_id=company_id,
    )
