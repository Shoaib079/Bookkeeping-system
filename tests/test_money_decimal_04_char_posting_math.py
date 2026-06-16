"""MONEY-DECIMAL-04-CHAR — posting kernel money math characterization.

Pre-Decimal audit of ``services/posting.py`` float semantics. Tests only.
Complements MD-02 golden vectors; MD-04 will wire ``services.money`` into posting.

Cross-ref: docs/MONEY_DECIMAL_04_POSTING_MATH_CHAR.md
"""

from __future__ import annotations

import ast
import datetime
import sys
from pathlib import Path
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
from services.read_balances import calculate_account_balance
from services.read_ledger import compute_ledger_page
from services.read_reports import compute_balance_sheet, compute_profit_loss

ROOT = Path(__file__).resolve().parents[1]
POSTING_PATH = ROOT / "services" / "posting.py"

AMOUNT = 100.01
COMPANY_ID = 1
POST_DATE = datetime.date(2025, 6, 15)
PERIOD_START = datetime.date(2025, 6, 1)
PERIOD_END = datetime.date(2025, 6, 30)
VOID_REASON = "MD-04-CHAR void"

# MD-02 golden vector manifest — MD-04-CHAR must stay aligned until deliberately updated.
MD02_GOLDEN_MANIFEST = {
    "balance_guard_reject_100_99_99": (
        "Journal entry is not balanced: Debit $100.00 vs Credit $99.99"
    ),
    "balance_guard_reject_100_99_98": (
        "Journal entry is not balanced: Debit $100.00 vs Credit $99.98"
    ),
    "profit_split_100_01": [50.0, 50.01],
    "loss_split_100_01": [-50.01, -50.0],
    "multi_line_debit_sum": 1.0,
    "pl_net_after_sale": AMOUNT,
    "gl_cash_debit_total": AMOUNT,
}


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
                name="MD-04 CHAR Co",
                slug="md04_char",
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
    assert acct is not None
    return acct.id


def _je_lines(session, journal_entry_id: int) -> list[tuple[int, float, float]]:
    lines = (
        session.query(models.JournalEntryLine)
        .filter_by(journal_entry_id=journal_entry_id)
        .order_by(models.JournalEntryLine.id)
        .all()
    )
    return [(ln.account_id, ln.debit or 0.0, ln.credit or 0.0) for ln in lines]


def _entries_for(session, ref_type: str, ref_id: int) -> list[models.JournalEntry]:
    return (
        session.query(models.JournalEntry)
        .filter_by(reference_type=ref_type, reference_id=ref_id)
        .order_by(models.JournalEntry.id)
        .all()
    )


def _open_period(session, *, revenue: float = 0.0, expense: float = 0.0) -> models.FiscalPeriod:
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
            session, POST_DATE, "char revenue", "Sale", None,
            [(cash_id, revenue, 0.0), (inc_id, 0.0, revenue)], company_id=COMPANY_ID,
        )
    if expense:
        posting.create_journal_entry(
            session, POST_DATE, "char expense", "Expense", None,
            [(exp_id, expense, 0.0), (cash_id, 0.0, expense)], company_id=COMPANY_ID,
        )
    session.commit()
    return period


def _seed_partners(session, pcts: tuple[float, ...]) -> None:
    for i, pct in enumerate(pcts, start=1):
        cap = models.ChartOfAccounts(
            account_code=f"350{i}", account_name=f"P{i} Capital",
            account_type="Equity", balance=0.0, is_active=True, company_id=COMPANY_ID,
        )
        cur = models.ChartOfAccounts(
            account_code=f"360{i}", account_name=f"P{i} Current",
            account_type="Equity", balance=0.0, is_active=True, company_id=COMPANY_ID,
        )
        adv = models.ChartOfAccounts(
            account_code=f"150{i}", account_name=f"P{i} Advances",
            account_type="Asset", balance=0.0, is_active=True, company_id=COMPANY_ID,
        )
        session.add_all([cap, cur, adv])
        session.flush()
        session.add(
            models.Partner(
                name=f"Partner {i}", profit_share_pct=pct,
                capital_account_id=cap.id, current_account_id=cur.id,
                advance_account_id=adv.id, is_active=True, company_id=COMPANY_ID,
                created_at=datetime.datetime.now(),
            )
        )
        session.flush()
    session.commit()


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


# ── Source-level characterization (no DB) ─────────────────────────────────────


class TestPostingSourceMoneyContract:
    @pytest.fixture(scope="class")
    def posting_source(self) -> str:
        return POSTING_PATH.read_text(encoding="utf-8")

    @pytest.fixture(scope="class")
    def posting_tree(self, posting_source: str) -> ast.Module:
        return ast.parse(posting_source)

    def test_posting_imports_services_money(self, posting_source: str, posting_tree: ast.Module):
        assert "from services.money import" in posting_source
        imported = False
        for node in ast.walk(posting_tree):
            if isinstance(node, ast.ImportFrom) and node.module == "services.money":
                names = {alias.name for alias in node.names}
                assert "money_to_float" in names
                assert "parse_money" in names
                imported = True
        assert imported

    def test_posting_does_not_import_decimal_module(self, posting_source: str, posting_tree: ast.Module):
        assert "from decimal import" not in posting_source
        assert "import decimal" not in posting_source
        for node in ast.walk(posting_tree):
            if isinstance(node, ast.ImportFrom) and node.module == "decimal":
                pytest.fail("posting.py must not import decimal module before MD-04")

    def test_create_journal_entry_balance_guard_is_float_gt_001(self, posting_source: str):
        assert "abs(total_debit - total_credit) > 0.01" in posting_source

    def test_amount_native_uses_round_four_dp(self, posting_source: str):
        assert "amount_native=round(net * fx_rate, 4)" in posting_source

    def test_allocate_profit_uses_money_share_helper(self, posting_source: str):
        assert "_allocation_share_float" in posting_source
        assert "money_to_float" in posting_source
        start = posting_source.index("def allocate_profit_to_partners")
        end = posting_source.index("def void_profit_allocation", start)
        block = posting_source[start:end]
        assert "round(abs_income * p.profit_share_pct / 100.0, 2)" not in block


# ── create_journal_entry amount handling ──────────────────────────────────────


class TestCreateJournalEntryBalanceGuard:
    def test_balanced_100_01_accepted(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        entry = posting.create_journal_entry(
            session, POST_DATE, "char balanced", "Manual", None,
            [(cash_id, AMOUNT, 0.0), (inc_id, 0.0, AMOUNT)], company_id=COMPANY_ID,
        )
        assert _je_lines(session, entry.id) == [
            (cash_id, AMOUNT, 0.0), (inc_id, 0.0, AMOUNT),
        ]

    def test_amounts_persisted_via_je_line_parse_without_two_dp_quantize(self, session):
        """Kernel uses parse_money path — extra precision preserved (no money_to_float on lines)."""
        raw = 100.012345
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        entry = posting.create_journal_entry(
            session, POST_DATE, "no quantize", "Manual", None,
            [(cash_id, raw, 0.0), (inc_id, 0.0, raw)], company_id=COMPANY_ID,
        )
        lines = (
            session.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=entry.id)
            .order_by(models.JournalEntryLine.id)
            .all()
        )
        assert lines[0].debit == raw
        assert lines[1].credit == raw

    def test_float_tolerance_rejects_100_vs_99_99(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        with pytest.raises(ValueError) as exc:
            posting.create_journal_entry(
                session, POST_DATE, "char reject", "Manual", None,
                [(cash_id, 100.0, 0.0), (inc_id, 0.0, 99.99)], company_id=COMPANY_ID,
            )
        assert str(exc.value) == MD02_GOLDEN_MANIFEST["balance_guard_reject_100_99_99"]

    def test_float_tolerance_accepts_128_03_vs_128_02(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        entry = posting.create_journal_entry(
            session, POST_DATE, "char accept", "Manual", None,
            [(cash_id, 128.03, 0.0), (inc_id, 0.0, 128.02)], company_id=COMPANY_ID,
        )
        assert entry.id is not None

    def test_two_cent_imbalance_rejected_exact_message(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        with pytest.raises(ValueError) as exc:
            posting.create_journal_entry(
                session, POST_DATE, "char two cent", "Manual", None,
                [(cash_id, 100.0, 0.0), (inc_id, 0.0, 99.98)], company_id=COMPANY_ID,
            )
        assert str(exc.value) == MD02_GOLDEN_MANIFEST["balance_guard_reject_100_99_98"]


# ── post_* family amount passthrough ──────────────────────────────────────────


class TestPostFamilyAmountHandling:
    def test_post_cash_sale_100_01(self, session):
        sale = models.Sale(
            date=POST_DATE, invoice_number="CHAR-SALE", customer_name="C",
            description="char", amount=AMOUNT, sale_type="Cash",
            paid_amount=AMOUNT, balance=0.0, status="Paid", company_id=COMPANY_ID,
        )
        session.add(sale)
        session.flush()
        posting.post_cash_sale(session, sale.id, AMOUNT, POST_DATE, company_id=COMPANY_ID)
        entry = _entries_for(session, "CashSale", sale.id)[0]
        debits = [l.debit for l in entry.lines if l.debit]
        credits = [l.credit for l in entry.lines if l.credit]
        assert debits == [AMOUNT]
        assert credits == [AMOUNT]

    def test_post_credit_sale_100_01(self, session):
        sale = models.Sale(
            date=POST_DATE, invoice_number="CHAR-CR", customer_name="C",
            description="char credit", amount=AMOUNT, sale_type="Credit",
            paid_amount=0.0, balance=AMOUNT, status="Outstanding", company_id=COMPANY_ID,
        )
        session.add(sale)
        session.flush()
        posting.post_credit_sale(session, sale.id, AMOUNT, POST_DATE, company_id=COMPANY_ID)
        ar_id = _acct_id(session, "Accounts Receivable")
        inc_id = _acct_id(session, "Sales Revenue")
        entry = _entries_for(session, "CreditSale", sale.id)[0]
        assert _je_lines(session, entry.id) == [(ar_id, AMOUNT, 0.0), (inc_id, 0.0, AMOUNT)]

    def test_post_expense_100_01(self, session):
        expense = models.ExpenseRecord(
            date=POST_DATE, expense_type="General", category="Office",
            description="char expense", amount=AMOUNT, payment_method="Cash",
            company_id=COMPANY_ID,
        )
        session.add(expense)
        session.flush()
        posting.post_expense(
            session, expense.id, AMOUNT, POST_DATE, "Office",
            payment_method="Cash", company_id=COMPANY_ID,
        )
        entry = _entries_for(session, "Expense", expense.id)[0]
        assert sum(l.debit or 0 for l in entry.lines) == AMOUNT
        assert sum(l.credit or 0 for l in entry.lines) == AMOUNT

    def test_post_purchase_100_01(self, session):
        vendor = models.Vendor(name="V", is_active=True, company_id=COMPANY_ID)
        session.add(vendor)
        session.flush()
        purchase = models.Purchase(
            date=POST_DATE, vendor_id=vendor.id, purchase_number="PO-CHAR",
            amount=AMOUNT, description="char purchase", purchase_type="Cash",
            gl_debit="Inventory", company_id=COMPANY_ID,
        )
        session.add(purchase)
        session.flush()
        posting.post_purchase(
            session, purchase.id, AMOUNT, POST_DATE,
            purchase_type="Cash", company_id=COMPANY_ID,
        )
        entry = _entries_for(session, "CashPurchase", purchase.id)[0]
        assert sum(l.debit or 0 for l in entry.lines) == AMOUNT

    @pytest.mark.parametrize("txn_type", ["deposit", "withdrawal"])
    def test_post_bank_transaction_100_01(self, session, txn_type: str):
        txn = models.BankTransaction(
            account_id=1, date=POST_DATE, amount=AMOUNT, type=txn_type,
            description=f"char {txn_type}", company_id=COMPANY_ID,
        )
        session.add(txn)
        session.flush()
        posting.post_bank_transaction(
            session, txn.id, AMOUNT, POST_DATE, txn_type, company_id=COMPANY_ID,
        )
        ref = "BankDeposit" if txn_type == "deposit" else "BankWithdrawal"
        entry = _entries_for(session, ref, txn.id)[0]
        assert sum(l.debit or 0 for l in entry.lines) == AMOUNT
        assert sum(l.credit or 0 for l in entry.lines) == AMOUNT


# ── Profit allocation rounding ────────────────────────────────────────────────


class TestProfitAllocationRounding:
    def test_profit_100_01_penny_absorption(self, session):
        period = _closed_period_with_partners(session, revenue=AMOUNT, expense=0.0)
        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, allocated_by_id=1, company_id=COMPANY_ID,
        )
        assert err == ""
        lines = (
            session.query(models.PartnerProfitAllocationLine)
            .filter_by(allocation_id=alloc_id)
            .all()
        )
        amounts = sorted(round(l.amount, 2) for l in lines)
        assert amounts == MD02_GOLDEN_MANIFEST["profit_split_100_01"]

    def test_loss_100_01_penny_absorption(self, session):
        period = _closed_period_with_partners(session, revenue=0.0, expense=AMOUNT)
        alloc_id, err = posting.allocate_profit_to_partners(
            session, period.id, allocated_by_id=1, company_id=COMPANY_ID,
        )
        assert err == ""
        lines = (
            session.query(models.PartnerProfitAllocationLine)
            .filter_by(allocation_id=alloc_id)
            .all()
        )
        amounts = sorted(round(l.amount, 2) for l in lines)
        assert amounts == MD02_GOLDEN_MANIFEST["loss_split_100_01"]

    def test_allocation_je_partner_credits_sum_to_net_income(self, session):
        period = _closed_period_with_partners(session, revenue=AMOUNT, expense=0.0)
        alloc_id, _ = posting.allocate_profit_to_partners(
            session, period.id, allocated_by_id=1, company_id=COMPANY_ID,
        )
        alloc = session.get(models.PartnerProfitAllocation, alloc_id)
        je = session.get(models.JournalEntry, alloc.journal_entry_id)
        re_id = _acct_id(session, "Retained Earnings")
        partner_credit = sum(
            l.credit or 0 for l in je.lines if l.account_id != re_id
        )
        assert round(partner_credit, 2) == AMOUNT


# ── Void / reversal symmetry ──────────────────────────────────────────────────


class TestVoidReversalAmountSymmetry:
    def test_void_cash_sale_net_zero(self, session):
        sale = models.Sale(
            date=POST_DATE, invoice_number="V-SALE", customer_name="C",
            description="void char", amount=AMOUNT, sale_type="Cash",
            paid_amount=AMOUNT, balance=0.0, status="Paid", company_id=COMPANY_ID,
        )
        session.add(sale)
        session.flush()
        posting.post_cash_sale(session, sale.id, AMOUNT, POST_DATE, company_id=COMPANY_ID)
        cash = posting.get_account_by_name(session, "Cash", company_id=COMPANY_ID)
        assert calculate_account_balance(session, cash, company_id=COMPANY_ID) == AMOUNT
        assert posting.void_sale(session, sale.id, VOID_REASON, company_id=COMPANY_ID)
        assert calculate_account_balance(session, cash, company_id=COMPANY_ID) == 0.0

    def test_void_expense_net_zero(self, session):
        expense = models.ExpenseRecord(
            date=POST_DATE, expense_type="General", category="Office",
            description="void char", amount=AMOUNT, payment_method="Cash",
            company_id=COMPANY_ID,
        )
        session.add(expense)
        session.flush()
        posting.post_expense(
            session, expense.id, AMOUNT, POST_DATE, "Office",
            payment_method="Cash", company_id=COMPANY_ID,
        )
        cash = posting.get_account_by_name(session, "Cash", company_id=COMPANY_ID)
        office = posting.get_account_by_name(session, "Office Expense", company_id=COMPANY_ID)
        assert calculate_account_balance(session, cash, company_id=COMPANY_ID) == -AMOUNT
        assert calculate_account_balance(session, office, company_id=COMPANY_ID) == AMOUNT
        assert posting.void_expense(session, expense.id, VOID_REASON, company_id=COMPANY_ID)
        assert calculate_account_balance(session, cash, company_id=COMPANY_ID) == 0.0
        assert calculate_account_balance(session, office, company_id=COMPANY_ID) == 0.0

    def test_void_purchase_net_zero(self, session):
        vendor = models.Vendor(name="V2", is_active=True, company_id=COMPANY_ID)
        session.add(vendor)
        session.flush()
        purchase = models.Purchase(
            date=POST_DATE, vendor_id=vendor.id, purchase_number="PO-V",
            amount=AMOUNT, description="void purchase", purchase_type="Cash",
            gl_debit="Inventory", company_id=COMPANY_ID,
        )
        session.add(purchase)
        session.flush()
        posting.post_purchase(
            session, purchase.id, AMOUNT, POST_DATE,
            purchase_type="Cash", company_id=COMPANY_ID,
        )
        cash = posting.get_account_by_name(session, "Cash", company_id=COMPANY_ID)
        inv = posting.get_account_by_name(session, "Inventory", company_id=COMPANY_ID)
        assert calculate_account_balance(session, cash, company_id=COMPANY_ID) == -AMOUNT
        assert calculate_account_balance(session, inv, company_id=COMPANY_ID) == AMOUNT
        assert posting.void_purchase(session, purchase.id, VOID_REASON, company_id=COMPANY_ID)
        assert calculate_account_balance(session, cash, company_id=COMPANY_ID) == 0.0
        assert calculate_account_balance(session, inv, company_id=COMPANY_ID) == 0.0

    def test_reversal_swaps_exact_float_amounts(self, session):
        sale = models.Sale(
            date=POST_DATE, invoice_number="V-REV", customer_name="C",
            description="reversal char", amount=AMOUNT, sale_type="Cash",
            paid_amount=AMOUNT, balance=0.0, status="Paid", company_id=COMPANY_ID,
        )
        session.add(sale)
        session.flush()
        posting.post_cash_sale(session, sale.id, AMOUNT, POST_DATE, company_id=COMPANY_ID)
        original = _entries_for(session, "CashSale", sale.id)[0]
        orig_lines = _je_lines(session, original.id)
        posting.void_sale(session, sale.id, VOID_REASON, company_id=COMPANY_ID)
        rev_lines = _je_lines(session, _entries_for(session, "Reversal", original.id)[0].id)
        assert rev_lines == [(a, c, d) for a, d, c in orig_lines]


# ── Multi-line accumulation ───────────────────────────────────────────────────


class TestMultiLineJeAccumulation:
    def test_hundred_one_cent_lines_match_md02(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        lines = [(cash_id, 0.01, 0.0)] * 100 + [(inc_id, 0.0, 1.0)]
        entry = posting.create_journal_entry(
            session, POST_DATE, "char 100x0.01", "Manual", None,
            lines, company_id=COMPANY_ID,
        )
        debits = sum(l.debit or 0 for l in entry.lines)
        assert debits == MD02_GOLDEN_MANIFEST["multi_line_debit_sum"]
        assert sum(l.credit or 0 for l in entry.lines) == MD02_GOLDEN_MANIFEST["multi_line_debit_sum"]


# ── Reports depending on posting outputs ────────────────────────────────────


class TestReportsDependOnPostingOutputs:
    def test_profit_loss_reads_posted_sale_amount(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        posting.create_journal_entry(
            session, POST_DATE, "char pl", "CashSale", 1,
            [(cash_id, AMOUNT, 0.0), (inc_id, 0.0, AMOUNT)], company_id=COMPANY_ID,
        )
        pl = compute_profit_loss(
            session, company_id=COMPANY_ID,
            start_date=PERIOD_START, end_date=PERIOD_END,
        )
        assert pl.net == MD02_GOLDEN_MANIFEST["pl_net_after_sale"]

    def test_balance_sheet_balanced_after_posting(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        posting.create_journal_entry(
            session, POST_DATE, "char bs", "CashSale", 2,
            [(cash_id, AMOUNT, 0.0), (inc_id, 0.0, AMOUNT)], company_id=COMPANY_ID,
        )
        bs = compute_balance_sheet(session, company_id=COMPANY_ID, as_of=PERIOD_END)
        assert bs.balanced is True
        assert bs.total_assets == AMOUNT

    def test_ledger_page_debit_total_from_posting(self, session):
        cash = posting.get_account_by_name(session, "Cash", company_id=COMPANY_ID)
        inc_id = _acct_id(session, "Sales Revenue")
        posting.create_journal_entry(
            session, POST_DATE, "char gl", "CashSale", 3,
            [(cash.id, AMOUNT, 0.0), (inc_id, 0.0, AMOUNT)], company_id=COMPANY_ID,
        )
        page = compute_ledger_page(
            session, company_id=COMPANY_ID, account_id=cash.id,
            start_date=PERIOD_START, end_date=PERIOD_END,
        )
        assert page.total_debit == MD02_GOLDEN_MANIFEST["gl_cash_debit_total"]


# ── MD-02 alignment contract ──────────────────────────────────────────────────


class TestMatchesMd02GoldenVectors:
    def test_md02_manifest_documented(self):
        assert "balance_guard_reject_100_99_99" in MD02_GOLDEN_MANIFEST
        assert MD02_GOLDEN_MANIFEST["profit_split_100_01"] == [50.0, 50.01]

    def test_services_money_wired_in_posting_module(self):
        posting_source = POSTING_PATH.read_text(encoding="utf-8")
        assert "_normalize_money_amount" in posting_source
        assert "_je_line_money" in posting_source
        assert "money_to_float" in posting_source
        assert "parse_money" in posting_source
