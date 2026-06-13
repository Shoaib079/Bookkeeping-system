"""FASTAPI-P0.2-B — financial reports read service contract tests."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app as erp_app
from db import Base
import models
from services import read_balances as rb
from services import read_reports as rr

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

_BS_EPOCH = datetime.date(2000, 1, 1)
_PERIOD_CLOSE_EXCL = ["PeriodClose"]
_FINANCING_REFS = {"BankDeposit", "BankWithdrawal", "BankTransfer"}


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s


def _company(db, name="Acme", slug="co1"):
    c = models.Company(
        name=name,
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(c)
    db.flush()
    return c


def _account(db, company_id, code, name, acct_type):
    a = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        is_active=True,
        balance=0.0,
        company_id=company_id,
    )
    db.add(a)
    db.flush()
    return a


def _journal_entry(
    db,
    company_id,
    lines,
    *,
    date=datetime.date(2026, 1, 15),
    description="Test JE",
    reference_type="Sale",
    reference_id=1,
):
    je = models.JournalEntry(
        entry_date=date,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        company_id=company_id,
    )
    db.add(je)
    db.flush()
    for account_id, debit, credit in lines:
        db.add(
            models.JournalEntryLine(
                journal_entry_id=je.id,
                account_id=account_id,
                debit=debit,
                credit=credit,
                company_id=company_id,
            )
        )
    db.flush()
    return je


def _set_company(company_id: int):
    sys.modules["streamlit"].session_state["active_company_id"] = company_id


def _counts(db):
    return (
        db.query(models.JournalEntry).count(),
        db.query(models.BankTransaction).count(),
    )


def _legacy_compute_pnl(db, company_id, start_date, end_date):
    """Inline characterization of pre-extraction render_profit_loss compute."""
    accounts = (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=company_id, is_active=True)
        .order_by(models.ChartOfAccounts.account_code)
        .all()
    )
    income_rows = []
    total_income = 0.0
    for acct in [a for a in accounts if a.account_type == "Income"]:
        bal = rb.calculate_account_balance_for_period(
            db, acct, start_date, end_date,
            exclude_refs=_PERIOD_CLOSE_EXCL, company_id=company_id,
        )
        if bal != 0:
            income_rows.append((acct.account_code, acct.account_name, round(bal, 2)))
            total_income += bal
    expense_rows = []
    total_expenses = 0.0
    for acct in [a for a in accounts if a.account_type == "Expense"]:
        bal = rb.calculate_account_balance_for_period(
            db, acct, start_date, end_date,
            exclude_refs=_PERIOD_CLOSE_EXCL, company_id=company_id,
        )
        if bal != 0:
            expense_rows.append((acct.account_code, acct.account_name, round(bal, 2)))
            total_expenses += bal
    net = round(total_income - total_expenses, 2)
    margin_pct = (net / total_income * 100) if total_income else 0.0
    return income_rows, expense_rows, total_income, total_expenses, net, margin_pct


def _legacy_compute_bs(db, company_id, as_of):
    accounts = (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=company_id, is_active=True)
        .order_by(models.ChartOfAccounts.account_code)
        .all()
    )

    def period_bal(acct):
        return rb.calculate_account_balance_for_period(
            db, acct, _BS_EPOCH, as_of, company_id=company_id,
        )

    asset_rows = [
        (a.account_code, a.account_name, round(period_bal(a), 2))
        for a in accounts if a.account_type == "Asset"
    ]
    liability_rows = [
        (a.account_code, a.account_name, round(period_bal(a), 2))
        for a in accounts if a.account_type == "Liability"
    ]
    equity_rows = [
        (a.account_code, a.account_name, round(period_bal(a), 2))
        for a in accounts if a.account_type == "Equity"
    ]
    income_total = sum(
        rb.calculate_account_balance_for_period(
            db, a, _BS_EPOCH, as_of,
            exclude_refs=_PERIOD_CLOSE_EXCL, company_id=company_id,
        )
        for a in accounts if a.account_type == "Income"
    )
    expense_total = sum(
        rb.calculate_account_balance_for_period(
            db, a, _BS_EPOCH, as_of,
            exclude_refs=_PERIOD_CLOSE_EXCL, company_id=company_id,
        )
        for a in accounts if a.account_type == "Expense"
    )
    net_income = income_total - expense_total
    raw_assets = sum(period_bal(a) for a in accounts if a.account_type == "Asset")
    raw_liabilities = sum(period_bal(a) for a in accounts if a.account_type == "Liability")
    raw_equity = sum(period_bal(a) for a in accounts if a.account_type == "Equity")
    total_assets = round(raw_assets, 2)
    total_liabilities = round(raw_liabilities, 2)
    base_equity = round(raw_equity, 2)
    total_equity = round(raw_equity + net_income, 2)
    raw_rhs = raw_liabilities + raw_equity + net_income
    diff = abs(raw_assets - raw_rhs)
    balanced = diff < 0.01
    return {
        "asset_rows": asset_rows,
        "liability_rows": liability_rows,
        "equity_rows": equity_rows,
        "net_income": net_income,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "base_equity": base_equity,
        "total_equity": total_equity,
        "balanced": balanced,
        "imbalance": diff,
    }


def _legacy_compute_cf(db, company_id, start_date, end_date):
    cash_acct = (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=company_id, account_name="Cash", is_active=True)
        .first()
    )
    bank_acct = (
        db.query(models.ChartOfAccounts)
        .filter_by(company_id=company_id, account_name="Bank", is_active=True)
        .first()
    )
    cash_ids = {a.id for a in [cash_acct, bank_acct] if a}
    if not cash_ids:
        return None

    entries = (
        db.query(models.JournalEntry)
        .filter(
            models.JournalEntry.company_id == company_id,
            models.JournalEntry.entry_date >= start_date,
            models.JournalEntry.entry_date <= end_date,
        )
        .order_by(models.JournalEntry.entry_date)
        .all()
    )
    operating_rows = []
    financing_rows = []
    for entry in entries:
        for line in entry.lines:
            if line.account_id not in cash_ids:
                continue
            net = round((line.debit or 0) - (line.credit or 0), 2)
            if net == 0:
                continue
            row = (
                entry.entry_date,
                entry.description,
                entry.reference_type or "Manual",
                net if net > 0 else 0.0,
                round(-net, 2) if net < 0 else 0.0,
            )
            if (entry.reference_type or "") in _FINANCING_REFS:
                financing_rows.append(row)
            else:
                operating_rows.append(row)

    op_in = round(sum(r[3] for r in operating_rows), 2)
    op_out = round(sum(r[4] for r in operating_rows), 2)
    fin_in = round(sum(r[3] for r in financing_rows), 2)
    fin_out = round(sum(r[4] for r in financing_rows), 2)
    net_op = round(op_in - op_out, 2)
    net_fin = round(fin_in - fin_out, 2)
    net_total = round(net_op + net_fin, 2)
    return {
        "operating_rows": operating_rows,
        "financing_rows": financing_rows,
        "op_in": op_in,
        "op_out": op_out,
        "fin_in": fin_in,
        "fin_out": fin_out,
        "net_op": net_op,
        "net_fin": net_fin,
        "net_total": net_total,
    }


@pytest.fixture()
def seeded_reports(db):
    co_a = _company(db, "Alpha", "alpha")
    co_b = _company(db, "Beta", "beta")

    cash_a = _account(db, co_a.id, "1000", "Cash", "Asset")
    bank_a = _account(db, co_a.id, "1010", "Bank", "Asset")
    income_a = _account(db, co_a.id, "4000", "Sales", "Income")
    expense_a = _account(db, co_a.id, "5000", "Rent", "Expense")
    equity_a = _account(db, co_a.id, "3000", "Equity", "Equity")
    liability_a = _account(db, co_a.id, "2000", "Payables", "Liability")
    _account(db, co_a.id, "1020", "Idle Asset", "Asset")

    cash_b = _account(db, co_b.id, "1000", "Cash", "Asset")
    income_b = _account(db, co_b.id, "4000", "Sales B", "Income")

    _journal_entry(
        db, co_a.id,
        [(cash_a.id, 500.0, 0.0), (income_a.id, 0.0, 500.0)],
        date=datetime.date(2026, 1, 10),
        reference_type="Sale",
        description="Cash sale",
    )
    _journal_entry(
        db, co_a.id,
        [(expense_a.id, 120.0, 0.0), (cash_a.id, 0.0, 120.0)],
        date=datetime.date(2026, 1, 20),
        reference_type="Expense",
        description="Rent paid",
    )
    _journal_entry(
        db, co_a.id,
        [(bank_a.id, 200.0, 0.0), (income_a.id, 0.0, 200.0)],
        date=datetime.date(2026, 2, 5),
        reference_type="BankDeposit",
        description="Bank deposit",
    )
    _journal_entry(
        db, co_a.id,
        [(cash_a.id, 0.0, 50.0), (equity_a.id, 50.0, 0.0)],
        date=datetime.date(2025, 12, 31),
        reference_type="PeriodClose",
        description="Year close",
    )
    _journal_entry(
        db, co_b.id,
        [(cash_b.id, 9000.0, 0.0), (income_b.id, 0.0, 9000.0)],
        date=datetime.date(2026, 1, 15),
        reference_type="Sale",
        description="Other co sale",
    )
    db.commit()
    return co_a, co_b, {
        "cash": cash_a,
        "bank": bank_a,
        "income": income_a,
        "expense": expense_a,
    }


def _line_tuples(lines):
    return tuple((ln.code, ln.account_name, ln.amount) for ln in lines)


def _cf_row_tuples(rows):
    return tuple(
        (r.date, r.description, r.type, r.inflow, r.outflow) for r in rows
    )


class TestProfitLoss:
    def test_matches_legacy_compute(self, db, seeded_reports):
        co_a, _co_b, _accts = seeded_reports
        start = datetime.date(2026, 1, 1)
        end = datetime.date(2026, 1, 31)

        legacy = _legacy_compute_pnl(db, co_a.id, start, end)
        stmt = rr.compute_profit_loss(
            db, company_id=co_a.id, start_date=start, end_date=end,
        )

        assert list(_line_tuples(stmt.income_lines)) == legacy[0]
        assert list(_line_tuples(stmt.expense_lines)) == legacy[1]
        assert stmt.total_income == pytest.approx(legacy[2])
        assert stmt.total_expenses == pytest.approx(legacy[3])
        assert stmt.net == pytest.approx(legacy[4])
        assert stmt.margin_pct == pytest.approx(legacy[5])

    def test_matches_app_shim(self, db, seeded_reports):
        co_a, _co_b, _accts = seeded_reports
        _set_company(co_a.id)
        start = datetime.date(2026, 1, 1)
        end = datetime.date(2026, 1, 31)

        app_stmt = erp_app.compute_profit_loss_report(db, start_date=start, end_date=end)
        svc_stmt = rr.compute_profit_loss(
            db, company_id=co_a.id, start_date=start, end_date=end,
        )
        assert app_stmt == svc_stmt

    def test_date_range_excludes_out_of_period(self, db, seeded_reports):
        co_a, _co_b, _accts = seeded_reports
        stmt = rr.compute_profit_loss(
            db,
            company_id=co_a.id,
            start_date=datetime.date(2026, 3, 1),
            end_date=datetime.date(2026, 3, 31),
        )
        assert stmt.total_income == pytest.approx(0.0)
        assert stmt.total_expenses == pytest.approx(0.0)
        assert stmt.income_lines == ()
        assert stmt.expense_lines == ()


class TestBalanceSheet:
    def test_matches_legacy_compute(self, db, seeded_reports):
        co_a, _co_b, _accts = seeded_reports
        as_of = datetime.date(2026, 2, 28)

        legacy = _legacy_compute_bs(db, co_a.id, as_of)
        stmt = rr.compute_balance_sheet(db, company_id=co_a.id, as_of=as_of)

        assert list(_line_tuples(stmt.asset_lines)) == legacy["asset_rows"]
        assert list(_line_tuples(stmt.liability_lines)) == legacy["liability_rows"]
        assert list(_line_tuples(stmt.equity_lines)) == legacy["equity_rows"]
        assert stmt.net_income == pytest.approx(legacy["net_income"])
        assert stmt.total_assets == pytest.approx(legacy["total_assets"])
        assert stmt.total_liabilities == pytest.approx(legacy["total_liabilities"])
        assert stmt.base_equity == pytest.approx(legacy["base_equity"])
        assert stmt.total_equity == pytest.approx(legacy["total_equity"])
        assert stmt.balanced == legacy["balanced"]
        assert stmt.imbalance == pytest.approx(legacy["imbalance"])

    def test_matches_app_shim(self, db, seeded_reports):
        co_a, _co_b, _accts = seeded_reports
        _set_company(co_a.id)
        as_of = datetime.date(2026, 2, 28)

        app_stmt = erp_app.compute_balance_sheet_report(db, end_date=as_of)
        svc_stmt = rr.compute_balance_sheet(db, company_id=co_a.id, as_of=as_of)
        assert app_stmt == svc_stmt

    def test_period_close_excluded_from_net_income(self, db, seeded_reports):
        co_a, _co_b, _accts = seeded_reports
        stmt = rr.compute_balance_sheet(
            db, company_id=co_a.id, as_of=datetime.date(2026, 2, 28),
        )
        assert stmt.net_income == pytest.approx(580.0)


class TestCashFlow:
    def test_matches_legacy_compute(self, db, seeded_reports):
        co_a, _co_b, _accts = seeded_reports
        start = datetime.date(2026, 1, 1)
        end = datetime.date(2026, 2, 28)

        legacy = _legacy_compute_cf(db, co_a.id, start, end)
        stmt = rr.compute_cash_flow(
            db, company_id=co_a.id, start_date=start, end_date=end,
        )

        assert stmt.has_cash_accounts is True
        assert list(_cf_row_tuples(stmt.operating_rows)) == legacy["operating_rows"]
        assert list(_cf_row_tuples(stmt.financing_rows)) == legacy["financing_rows"]
        assert stmt.op_in == pytest.approx(legacy["op_in"])
        assert stmt.op_out == pytest.approx(legacy["op_out"])
        assert stmt.fin_in == pytest.approx(legacy["fin_in"])
        assert stmt.fin_out == pytest.approx(legacy["fin_out"])
        assert stmt.net_op == pytest.approx(legacy["net_op"])
        assert stmt.net_fin == pytest.approx(legacy["net_fin"])
        assert stmt.net_total == pytest.approx(legacy["net_total"])

    def test_matches_app_shim(self, db, seeded_reports):
        co_a, _co_b, _accts = seeded_reports
        _set_company(co_a.id)
        start = datetime.date(2026, 1, 1)
        end = datetime.date(2026, 2, 28)

        app_stmt = erp_app.compute_cash_flow_report(db, start_date=start, end_date=end)
        svc_stmt = rr.compute_cash_flow(
            db, company_id=co_a.id, start_date=start, end_date=end,
        )
        assert app_stmt == svc_stmt

    def test_no_cash_accounts_flag(self, db):
        co = _company(db)
        db.commit()
        stmt = rr.compute_cash_flow(
            db,
            company_id=co.id,
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 1, 31),
        )
        assert stmt.has_cash_accounts is False
        assert stmt.operating_rows == ()
        assert stmt.financing_rows == ()
        assert stmt.net_total == pytest.approx(0.0)

    def test_financing_reference_types(self, db, seeded_reports):
        co_a, _co_b, accts = seeded_reports
        stmt = rr.compute_cash_flow(
            db,
            company_id=co_a.id,
            start_date=datetime.date(2026, 2, 1),
            end_date=datetime.date(2026, 2, 28),
        )
        assert len(stmt.financing_rows) == 1
        assert stmt.financing_rows[0].type == "BankDeposit"
        assert stmt.fin_in == pytest.approx(200.0)


class TestCompanyIsolation:
    def test_pnl_ignores_other_company(self, db, seeded_reports):
        co_a, _co_b, _accts = seeded_reports
        stmt = rr.compute_profit_loss(
            db,
            company_id=co_a.id,
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 1, 31),
        )
        assert stmt.total_income == pytest.approx(500.0)
        assert stmt.total_income != pytest.approx(9500.0)


class TestReadOnly:
    def test_report_reads_create_no_rows(self, db, seeded_reports):
        co_a, _co_b, _accts = seeded_reports
        je_before, bt_before = _counts(db)

        rr.compute_profit_loss(
            db,
            company_id=co_a.id,
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 1, 31),
        )
        rr.compute_balance_sheet(
            db, company_id=co_a.id, as_of=datetime.date(2026, 2, 28),
        )
        rr.compute_cash_flow(
            db,
            company_id=co_a.id,
            start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 2, 28),
        )

        je_after, bt_after = _counts(db)
        assert je_after == je_before
        assert bt_after == bt_before
