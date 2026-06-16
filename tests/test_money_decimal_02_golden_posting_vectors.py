"""MONEY-DECIMAL-02 — golden posting vectors (Float baseline).

Pins current Float posting behavior before Decimal/Numeric migration.
Tests only — no production code, schema, or Decimal changes.

Cross-ref: docs/MONEY_DECIMAL_02_GOLDEN_VECTORS.md
"""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from db import Base

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

import app  # noqa: F401 — bootstrap import graph before direct services.posting use

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

from registry.coa_seed import seed_chart_of_accounts_for_company
from services import posting
from services.money import fx_to_float, line_money, money_to_float
from services.read_balances import calculate_account_balance
from services.read_ledger import compute_ledger_page
from services.read_reports import compute_balance_sheet, compute_profit_loss

AMOUNT = 100.01
COMPANY_ID = 1
POST_DATE = datetime.date(2025, 6, 15)
PERIOD_START = datetime.date(2025, 6, 1)
PERIOD_END = datetime.date(2025, 6, 30)
VOID_REASON = "MD-02 golden void"


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        s.add(
            models.Company(
                name="MD-02 Golden Co",
                slug="md02_golden",
                is_active=True,
                created_at=datetime.datetime.now(),
            )
        )
        s.flush()
        seed_chart_of_accounts_for_company(s, COMPANY_ID)
        s.commit()
        yield s


def _acct_id(session, name: str, *, currency: str | None = None) -> int:
    acct = posting.get_account_by_name(
        session, name, currency=currency, company_id=COMPANY_ID
    )
    assert acct is not None, f"account not found: {name!r} currency={currency!r}"
    return acct.id


def _je_lines(session, journal_entry_id: int) -> list[tuple[int, float, float]]:
    lines = (
        session.query(models.JournalEntryLine)
        .filter_by(journal_entry_id=journal_entry_id)
        .order_by(models.JournalEntryLine.id)
        .all()
    )
    return [(ln.account_id, line_money(ln.debit), line_money(ln.credit)) for ln in lines]


def _entries_for(session, ref_type: str, ref_id: int) -> list[models.JournalEntry]:
    return (
        session.query(models.JournalEntry)
        .filter_by(reference_type=ref_type, reference_id=ref_id)
        .order_by(models.JournalEntry.id)
        .all()
    )


def _open_period(
    session,
    *,
    revenue: float = 0.0,
    expense: float = 0.0,
) -> models.FiscalPeriod:
    period = models.FiscalPeriod(
        name="Jun 2025",
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        is_closed=False,
        company_id=COMPANY_ID,
    )
    session.add(period)
    session.flush()
    cash_id = _acct_id(session, "Cash")
    inc_id = _acct_id(session, "Sales Revenue")
    exp_id = _acct_id(session, "Rent Expense")
    if revenue:
        posting.create_journal_entry(
            session,
            POST_DATE,
            "MD-02 revenue pin",
            "Sale",
            None,
            [(cash_id, revenue, 0.0), (inc_id, 0.0, revenue)],
            company_id=COMPANY_ID,
        )
    if expense:
        posting.create_journal_entry(
            session,
            POST_DATE,
            "MD-02 expense pin",
            "Expense",
            None,
            [(exp_id, expense, 0.0), (cash_id, 0.0, expense)],
            company_id=COMPANY_ID,
        )
    session.commit()
    return period


def _seed_partners(session, pcts: tuple[float, ...]) -> list[models.Partner]:
    partners = []
    for i, pct in enumerate(pcts, start=1):
        cap = models.ChartOfAccounts(
            account_code=f"350{i}",
            account_name=f"P{i} Capital",
            account_type="Equity",
            balance=0.0,
            is_active=True,
            company_id=COMPANY_ID,
        )
        cur = models.ChartOfAccounts(
            account_code=f"360{i}",
            account_name=f"P{i} Current",
            account_type="Equity",
            balance=0.0,
            is_active=True,
            company_id=COMPANY_ID,
        )
        adv = models.ChartOfAccounts(
            account_code=f"150{i}",
            account_name=f"P{i} Advances",
            account_type="Asset",
            balance=0.0,
            is_active=True,
            company_id=COMPANY_ID,
        )
        session.add_all([cap, cur, adv])
        session.flush()
        p = models.Partner(
            name=f"Partner {i}",
            profit_share_pct=pct,
            capital_account_id=cap.id,
            current_account_id=cur.id,
            advance_account_id=adv.id,
            is_active=True,
            company_id=COMPANY_ID,
            created_at=datetime.datetime.now(),
        )
        session.add(p)
        session.flush()
        partners.append(p)
    session.commit()
    return partners


def _closed_period_with_partners(
    session,
    *,
    revenue: float = 0.0,
    expense: float = 0.0,
    pcts: tuple[float, ...] = (50.0, 50.0),
) -> models.FiscalPeriod:
    _seed_partners(session, pcts)
    period = _open_period(session, revenue=revenue, expense=expense)
    posting.close_fiscal_period(session, period.id, company_id=COMPANY_ID)
    session.commit()
    return period


# ── 1. Journal Entry balance guard ───────────────────────────────────────────


class TestGoldenJournalEntryBalanceGuard:
    def test_balanced_entry_accepted(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        entry = posting.create_journal_entry(
            session,
            POST_DATE,
            "balanced",
            "Manual",
            None,
            [(cash_id, AMOUNT, 0.0), (inc_id, 0.0, AMOUNT)],
            company_id=COMPANY_ID,
        )
        assert entry.id is not None
        lines = _je_lines(session, entry.id)
        assert lines == [(cash_id, AMOUNT, 0.0), (inc_id, 0.0, AMOUNT)]

    def test_one_cent_imbalance_rejected_at_100_vs_99_99(self, session):
        """100.00 vs 99.99 looks like 1-cent diff but float accumulation overshoots > 0.01."""
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        with pytest.raises(ValueError) as exc:
            posting.create_journal_entry(
                session,
                POST_DATE,
                "float overshoot",
                "Manual",
                None,
                [(cash_id, 100.0, 0.0), (inc_id, 0.0, 99.99)],
                company_id=COMPANY_ID,
            )
        assert str(exc.value) == (
            "Journal entry is not balanced: Debit $100.00 vs Credit $99.99"
        )

    def test_one_cent_imbalance_accepted_when_float_stays_within_guard(self, session):
        """128.03 vs 128.02 — nominal 1-cent gap that survives float accumulation."""
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        entry = posting.create_journal_entry(
            session,
            POST_DATE,
            "float-safe one cent",
            "Manual",
            None,
            [(cash_id, 128.03, 0.0), (inc_id, 0.0, 128.02)],
            company_id=COMPANY_ID,
        )
        assert entry.id is not None

    def test_two_cent_imbalance_rejected_exact_message(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        with pytest.raises(ValueError) as exc:
            posting.create_journal_entry(
                session,
                POST_DATE,
                "two-cent imbalance",
                "Manual",
                None,
                [(cash_id, 100.0, 0.0), (inc_id, 0.0, 99.98)],
                company_id=COMPANY_ID,
            )
        assert str(exc.value) == (
            "Journal entry is not balanced: Debit $100.00 vs Credit $99.98"
        )
        assert session.query(models.JournalEntry).count() == 0


# ── 2. Basic posting amounts ─────────────────────────────────────────────────


class TestGoldenBasicPostingAmounts:
    def test_cash_sale_100_01(self, session):
        sale = models.Sale(
            date=POST_DATE,
            invoice_number="MD02-SALE",
            customer_name="Customer",
            description="golden sale",
            amount=AMOUNT,
            sale_type="Cash",
            paid_amount=AMOUNT,
            balance=0.0,
            status="Paid",
            company_id=COMPANY_ID,
        )
        session.add(sale)
        session.flush()
        posting.post_cash_sale(
            session, sale.id, AMOUNT, POST_DATE, company_id=COMPANY_ID
        )
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        entry = _entries_for(session, "CashSale", sale.id)[0]
        assert _je_lines(session, entry.id) == [
            (cash_id, AMOUNT, 0.0),
            (inc_id, 0.0, AMOUNT),
        ]

    def test_expense_100_01(self, session):
        expense = models.ExpenseRecord(
            date=POST_DATE,
            expense_type="General",
            category="Office",
            description="golden expense",
            amount=AMOUNT,
            payment_method="Cash",
            company_id=COMPANY_ID,
        )
        session.add(expense)
        session.flush()
        posting.post_expense(
            session,
            expense.id,
            AMOUNT,
            POST_DATE,
            "Office",
            payment_method="Cash",
            company_id=COMPANY_ID,
        )
        cash_id = _acct_id(session, "Cash")
        exp_id = _acct_id(session, "Office Expense")
        entry = _entries_for(session, "Expense", expense.id)[0]
        assert _je_lines(session, entry.id) == [
            (exp_id, AMOUNT, 0.0),
            (cash_id, 0.0, AMOUNT),
        ]

    def test_purchase_100_01(self, session):
        vendor = models.Vendor(name="Vendor MD02", is_active=True, company_id=COMPANY_ID)
        session.add(vendor)
        session.flush()
        purchase = models.Purchase(
            date=POST_DATE,
            vendor_id=vendor.id,
            purchase_number="PO-MD02",
            amount=AMOUNT,
            description="golden purchase",
            purchase_type="Cash",
            gl_debit="Inventory",
            company_id=COMPANY_ID,
        )
        session.add(purchase)
        session.flush()
        posting.post_purchase(
            session,
            purchase.id,
            AMOUNT,
            POST_DATE,
            purchase_type="Cash",
            company_id=COMPANY_ID,
        )
        cash_id = _acct_id(session, "Cash")
        inv_id = _acct_id(session, "Inventory")
        entry = _entries_for(session, "CashPurchase", purchase.id)[0]
        assert _je_lines(session, entry.id) == [
            (inv_id, AMOUNT, 0.0),
            (cash_id, 0.0, AMOUNT),
        ]

    def test_bank_deposit_100_01(self, session):
        txn = models.BankTransaction(
            account_id=1,
            date=POST_DATE,
            amount=AMOUNT,
            type="deposit",
            description="golden deposit",
            company_id=COMPANY_ID,
        )
        session.add(txn)
        session.flush()
        posting.post_bank_transaction(
            session,
            txn.id,
            AMOUNT,
            POST_DATE,
            "deposit",
            company_id=COMPANY_ID,
        )
        cash_id = _acct_id(session, "Cash")
        bank_id = _acct_id(session, "Bank")
        entry = _entries_for(session, "BankDeposit", txn.id)[0]
        assert _je_lines(session, entry.id) == [
            (bank_id, AMOUNT, 0.0),
            (cash_id, 0.0, AMOUNT),
        ]


# ── 3. Profit allocation penny absorption ────────────────────────────────────


class TestGoldenProfitAllocationPennyAbsorption:
    def test_profit_100_01_split_50_50(self, session):
        period = _closed_period_with_partners(
            session, revenue=AMOUNT, expense=0.0, pcts=(50.0, 50.0)
        )
        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, allocated_by_id=1, company_id=COMPANY_ID
        )
        assert err == ""
        assert alloc_id is not None
        lines = (
            session.query(models.PartnerProfitAllocationLine)
            .filter_by(allocation_id=alloc_id)
            .order_by(models.PartnerProfitAllocationLine.id)
            .all()
        )
        amounts = sorted(money_to_float(l.amount) for l in lines)
        assert amounts == [50.0, 50.01]
        assert round(sum(amounts), 2) == AMOUNT

    def test_loss_100_01_split_50_50(self, session):
        period = _closed_period_with_partners(
            session, revenue=0.0, expense=AMOUNT, pcts=(50.0, 50.0)
        )
        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, allocated_by_id=1, company_id=COMPANY_ID
        )
        assert err == ""
        lines = (
            session.query(models.PartnerProfitAllocationLine)
            .filter_by(allocation_id=alloc_id)
            .all()
        )
        amounts = sorted(money_to_float(l.amount) for l in lines)
        assert amounts == [-50.01, -50.0]
        assert round(sum(amounts), 2) == -AMOUNT


# ── 4. Multi-line JE accumulation ──────────────────────────────────────────────


class TestGoldenMultiLineJeAccumulation:
    def test_hundred_one_cent_debits_sum_to_one_dollar(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        lines = [(cash_id, 0.01, 0.0)] * 100 + [(inc_id, 0.0, 1.0)]
        entry = posting.create_journal_entry(
            session,
            POST_DATE,
            "100 x 0.01",
            "Manual",
            None,
            lines,
            company_id=COMPANY_ID,
        )
        debits = sum(line_money(l.debit) for l in entry.lines)
        credits = sum(line_money(l.credit) for l in entry.lines)
        assert debits == 1.0
        assert credits == 1.0
        assert len(entry.lines) == 101


# ── 5. Void / reversal symmetry ────────────────────────────────────────────────


class TestGoldenVoidReversalSymmetry:
    def test_void_cash_sale_returns_net_zero(self, session):
        sale = models.Sale(
            date=POST_DATE,
            invoice_number="MD02-VOID",
            customer_name="Customer",
            description="void golden",
            amount=AMOUNT,
            sale_type="Cash",
            paid_amount=AMOUNT,
            balance=0.0,
            status="Paid",
            company_id=COMPANY_ID,
        )
        session.add(sale)
        session.flush()
        posting.post_cash_sale(
            session, sale.id, AMOUNT, POST_DATE, company_id=COMPANY_ID
        )
        cash_acct = posting.get_account_by_name(
            session, "Cash", company_id=COMPANY_ID
        )
        assert calculate_account_balance(
            session, cash_acct, company_id=COMPANY_ID
        ) == AMOUNT

        original = _entries_for(session, "CashSale", sale.id)[0]
        orig_lines = _je_lines(session, original.id)

        assert posting.void_sale(
            session, sale.id, VOID_REASON, company_id=COMPANY_ID
        )
        assert calculate_account_balance(
            session, cash_acct, company_id=COMPANY_ID
        ) == 0.0

        reversals = _entries_for(session, "Reversal", original.id)
        assert len(reversals) == 1
        rev_lines = _je_lines(session, reversals[0].id)
        assert rev_lines == [(a, c, d) for a, d, c in orig_lines]
        assert all(d == AMOUNT or c == AMOUNT for _, d, c in rev_lines)


# ── 6. Reports parity ──────────────────────────────────────────────────────────


class TestGoldenReportsParity:
    def test_pl_and_balance_sheet_after_100_01_sale(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        posting.create_journal_entry(
            session,
            POST_DATE,
            "MD-02 P&L pin",
            "CashSale",
            99,
            [(cash_id, AMOUNT, 0.0), (inc_id, 0.0, AMOUNT)],
            company_id=COMPANY_ID,
        )
        pl = compute_profit_loss(
            session,
            company_id=COMPANY_ID,
            start_date=PERIOD_START,
            end_date=PERIOD_END,
        )
        assert pl.total_income == AMOUNT
        assert pl.total_expenses == 0.0
        assert pl.net == AMOUNT

        bs = compute_balance_sheet(
            session, company_id=COMPANY_ID, as_of=PERIOD_END
        )
        assert bs.balanced is True
        assert bs.total_assets == AMOUNT
        assert bs.net_income == AMOUNT

    def test_gl_ledger_totals_100_01(self, session):
        cash_acct = posting.get_account_by_name(
            session, "Cash", company_id=COMPANY_ID
        )
        inc_id = _acct_id(session, "Sales Revenue")
        posting.create_journal_entry(
            session,
            POST_DATE,
            "MD-02 GL pin",
            "CashSale",
            100,
            [(cash_acct.id, AMOUNT, 0.0), (inc_id, 0.0, AMOUNT)],
            company_id=COMPANY_ID,
        )
        page = compute_ledger_page(
            session,
            company_id=COMPANY_ID,
            account_id=cash_acct.id,
            start_date=PERIOD_START,
            end_date=PERIOD_END,
        )
        assert page.total_debit == AMOUNT
        assert page.total_credit == 0.0
        assert page.closing_balance == AMOUNT


# ── 7. Multi-currency rounding ─────────────────────────────────────────────────


class TestGoldenMultiCurrencyRounding:
    @pytest.mark.parametrize(
        ("currency", "cash_name", "fx_rate"),
        [
            ("TRY", "Cash", 1.0),
            ("USD", "Cash USD", 34.5678),
            ("EUR", "Cash EUR", 37.1234),
        ],
    )
    def test_foreign_cash_sale_amount_native(self, session, currency, cash_name, fx_rate):
        sale = models.Sale(
            date=POST_DATE,
            invoice_number=f"MD02-{currency}",
            customer_name="Customer",
            description=f"golden {currency}",
            amount=AMOUNT,
            sale_type="Cash",
            paid_amount=AMOUNT,
            balance=0.0,
            status="Paid",
            currency=currency,
            fx_rate=fx_rate,
            company_id=COMPANY_ID,
        )
        session.add(sale)
        session.flush()
        posting.post_cash_sale(
            session,
            sale.id,
            AMOUNT,
            POST_DATE,
            currency=currency,
            fx_rate=fx_rate,
            company_id=COMPANY_ID,
        )
        entry = _entries_for(session, "CashSale", sale.id)[0]
        natives = [fx_to_float(ln.amount_native) for ln in entry.lines if ln.amount_native is not None]
        expected = round(AMOUNT * fx_rate, 4)
        assert len(natives) == 2
        assert natives[0] == expected
        assert natives[1] == -expected
