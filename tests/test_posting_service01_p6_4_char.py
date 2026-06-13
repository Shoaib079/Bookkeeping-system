"""POSTING-SERVICE-01 PS-P6-4-CHAR — period close / year-end close characterization.

Pins close_fiscal_period and perform_year_end_close before PS-P6-4 extraction.
No production changes.
"""
from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event as sa_event, func
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

PAST_YEAR = datetime.date.today().year - 1
FISCAL_YEAR = str(PAST_YEAR)
Y_START = datetime.date(PAST_YEAR, 1, 1)
Y_END = datetime.date(PAST_YEAR, 12, 31)
CLOSER_ID = 9


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )


def _set_company(company_id: int):
    sys.modules["streamlit"].session_state["active_company_id"] = company_id


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    _seed_dev_auth_user()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        co = models.Company(
            name="P6-4 Char Co",
            slug="p6_4_char_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        _set_company(co.id)
        yield s, co.id


def _count(db, model):
    return db.query(func.count()).select_from(model).scalar()


def _make_coa(db, code, name, acct_type):
    acct = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        balance=0.0,
        is_active=True,
    )
    db.add(acct)
    db.flush()
    return acct


def _make_period(db, name, start, end, *, closed=False):
    period = models.FiscalPeriod(
        name=name,
        start_date=start,
        end_date=end,
        is_closed=closed,
        closed_at=datetime.date.today() if closed else None,
    )
    db.add(period)
    db.flush()
    return period


def _make_partner(db, name, pct, cap_id, cur_id, adv_id):
    p = models.Partner(
        name=name,
        profit_share_pct=pct,
        capital_account_id=cap_id,
        current_account_id=cur_id,
        advance_account_id=adv_id,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(p)
    db.flush()
    return p


def _line_tuples(db, journal_entry_id):
    lines = (
        db.query(models.JournalEntryLine)
        .filter_by(journal_entry_id=journal_entry_id)
        .order_by(models.JournalEntryLine.id)
        .all()
    )
    return [(ln.account_id, ln.debit or 0.0, ln.credit or 0.0) for ln in lines]


def _post_sale(db, cash_id, inc_id, amount, entry_date):
    app.create_journal_entry(
        db,
        entry_date,
        "Sale pin",
        "Sale",
        None,
        [(cash_id, amount, 0.0), (inc_id, 0.0, amount)],
    )


def _post_expense(db, cash_id, exp_id, amount, entry_date):
    app.create_journal_entry(
        db,
        entry_date,
        "Expense pin",
        "Expense",
        None,
        [(exp_id, amount, 0.0), (cash_id, 0.0, amount)],
    )


def _period_close_env(db, *, revenue=1000.0, expense=0.0):
    re_acct = _make_coa(db, "3100", "Retained Earnings", "Equity")
    inc_acct = _make_coa(db, "4000", "Revenue", "Income")
    exp_acct = _make_coa(db, "5000", "Expenses", "Expense")
    cash_acct = _make_coa(db, "1000", "Cash", "Asset")
    db.commit()
    period = _make_period(
        db,
        f"Jan {PAST_YEAR}",
        datetime.date(PAST_YEAR, 1, 1),
        datetime.date(PAST_YEAR, 1, 31),
    )
    mid = datetime.date(PAST_YEAR, 1, 15)
    if revenue:
        _post_sale(db, cash_acct.id, inc_acct.id, revenue, mid)
    if expense:
        _post_expense(db, cash_acct.id, exp_acct.id, expense, mid)
    db.commit()
    return {
        "period": period,
        "re_id": re_acct.id,
        "inc_id": inc_acct.id,
        "exp_id": exp_acct.id,
        "cash_id": cash_acct.id,
    }


def _make_allocation(db, period_id, re_id, cur_id, amount, partner_id):
    alloc = models.PartnerProfitAllocation(
        fiscal_period_id=period_id,
        allocated_at=datetime.datetime.now(),
        allocated_by_id=CLOSER_ID,
        total_net_income=amount,
        is_void=False,
        created_at=datetime.datetime.now(),
    )
    db.add(alloc)
    db.flush()
    je = app.create_journal_entry(
        db,
        datetime.date.today(),
        f"Profit Allocation {period_id}",
        "ProfitAllocation",
        alloc.id,
        [(re_id, amount, 0.0), (cur_id, 0.0, amount)],
    )
    alloc.journal_entry_id = je.id
    db.add(
        models.PartnerProfitAllocationLine(
            allocation_id=alloc.id,
            partner_id=partner_id,
            share_pct=100.0,
            amount=amount,
        )
    )
    db.commit()
    return alloc


def _closed_allocated_period(db, net_income=1000.0, *, alloc_amount=None):
    """Single full-year period closed + allocated for YEC tests."""
    alloc_amount = net_income if alloc_amount is None else alloc_amount
    re_acct = _make_coa(db, "3100", "Retained Earnings", "Equity")
    inc_acct = _make_coa(db, "4000", "Revenue", "Income")
    exp_acct = _make_coa(db, "5000", "Expenses", "Expense")
    cash_acct = _make_coa(db, "1000", "Cash", "Asset")
    cap_acct = _make_coa(db, "3501", "Alice Capital", "Equity")
    cur_acct = _make_coa(db, "3601", "Alice Current", "Equity")
    adv_acct = _make_coa(db, "1501", "Alice Advances", "Asset")
    db.commit()
    partner = _make_partner(db, "Alice", 100.0, cap_acct.id, cur_acct.id, adv_acct.id)
    period = _make_period(db, f"FY {FISCAL_YEAR}", Y_START, Y_END)
    _post_sale(db, cash_acct.id, inc_acct.id, net_income, Y_START)
    je = app.close_fiscal_period(db, period.id)
    _make_allocation(db, period.id, re_acct.id, cur_acct.id, alloc_amount, partner.id)
    db.commit()
    return {
        "period": period,
        "closing_je": je,
        "partner_id": partner.id,
        "re_id": re_acct.id,
        "cur_id": cur_acct.id,
        "adv_id": adv_acct.id,
        "cash_id": cash_acct.id,
        "net_income": net_income,
    }


class TestCloseFiscalPeriodSuccessProfit:
    def test_returns_period_close_je_and_sets_period_fields(self, session):
        db, _ = session
        env = _period_close_env(db, revenue=1000.0, expense=600.0)
        period = env["period"]

        je = app.close_fiscal_period(db, period.id)

        assert isinstance(je, models.JournalEntry)
        assert je.reference_type == "PeriodClose"
        assert je.reference_id == period.id
        assert je.entry_date == period.end_date
        db.refresh(period)
        assert period.is_closed is True
        assert period.closed_at is not None
        assert period.closing_je_id == je.id
        assert _line_tuples(db, je.id) == [
            (env["inc_id"], 1000.0, 0.0),
            (env["exp_id"], 0.0, 600.0),
            (env["re_id"], 0.0, 400.0),
        ]


class TestCloseFiscalPeriodSuccessLoss:
    def test_debits_retained_earnings_on_net_loss(self, session):
        db, _ = session
        env = _period_close_env(db, revenue=0.0, expense=750.0)
        period = env["period"]

        je = app.close_fiscal_period(db, period.id)

        assert _line_tuples(db, je.id) == [
            (env["exp_id"], 0.0, 750.0),
            (env["re_id"], 750.0, 0.0),
        ]


class TestCloseFiscalPeriodZeroNetIncome:
    def test_no_retained_earnings_line_when_net_is_zero(self, session):
        db, _ = session
        env = _period_close_env(db, revenue=1000.0, expense=1000.0)
        period = env["period"]

        je = app.close_fiscal_period(db, period.id)
        line_accounts = {acct_id for acct_id, _, _ in _line_tuples(db, je.id)}

        assert env["inc_id"] in line_accounts
        assert env["exp_id"] in line_accounts
        assert env["re_id"] not in line_accounts


class TestCloseFiscalPeriodGuards:
    def test_period_not_found_or_already_closed(self, session):
        db, _ = session
        env = _period_close_env(db)
        period = env["period"]
        je = app.close_fiscal_period(db, period.id)

        with pytest.raises(ValueError, match="Period not found or already closed."):
            app.close_fiscal_period(db, period.id)
        assert je.id is not None

    def test_missing_retained_earnings_account(self, session):
        db, _ = session
        env = _period_close_env(db)
        db.query(models.ChartOfAccounts).filter_by(account_name="Retained Earnings").delete()
        db.commit()

        with pytest.raises(
            ValueError,
            match="Retained Earnings account not found in Chart of Accounts.",
        ):
            app.close_fiscal_period(db, env["period"].id)

    def test_no_income_or_expense_activity(self, session):
        db, _ = session
        re_acct = _make_coa(db, "3100", "Retained Earnings", "Equity")
        period = _make_period(
            db,
            "Empty",
            datetime.date(PAST_YEAR, 2, 1),
            datetime.date(PAST_YEAR, 2, 28),
        )
        db.commit()

        with pytest.raises(
            ValueError,
            match="No income or expense activity in this period. Nothing to close.",
        ):
            app.close_fiscal_period(db, period.id)
        assert re_acct.id is not None

    def test_guard_failure_posts_zero_commits(self, session):
        db, _ = session
        env = _period_close_env(db)
        period = env["period"]
        app.close_fiscal_period(db, period.id)

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            with pytest.raises(ValueError, match="Period not found or already closed."):
                app.close_fiscal_period(db, period.id)
        assert mock_commit.call_count == 0


class TestCloseFiscalPeriodCommitAudit:
    def test_success_posts_three_commits_and_audit(self, session):
        db, _ = session
        env = _period_close_env(db, revenue=500.0)
        period = env["period"]

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            je = app.close_fiscal_period(db, period.id)
            assert mock_commit.call_count == 3

        audit = (
            db.query(models.AuditLog)
            .filter_by(action="PeriodClose", entity_type="FiscalPeriod", entity_id=period.id)
            .one()
        )
        assert f"Closing JE #{je.id}" in audit.description
        assert audit.performed_by == app._DEV_USER["username"]


class TestCloseFiscalPeriodExcludeRefs:
    def test_ignores_prior_period_close_jes_in_balance_calc(self, session):
        db, _ = session
        env = _period_close_env(db, revenue=1000.0)
        period = env["period"]
        # Stale PeriodClose in the same period — excluded from balance scan.
        app.create_journal_entry(
            db,
            period.end_date,
            "Stale Period Close",
            "PeriodClose",
            period.id,
            [(env["inc_id"], 1000.0, 0.0), (env["re_id"], 0.0, 1000.0)],
        )
        db.commit()

        je = app.close_fiscal_period(db, period.id)

        assert (env["re_id"], 0.0, 1000.0) in _line_tuples(db, je.id)


class TestCloseFiscalPeriodCompanyScoping:
    def test_closes_only_active_company_activity(self, session):
        db, cid1 = session
        env1 = _period_close_env(db, revenue=500.0)

        co2 = models.Company(
            name="Other Co",
            slug="other_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        db.add(co2)
        db.flush()
        _set_company(co2.id)
        cash2 = _make_coa(db, "1000", "Cash", "Asset")
        inc2 = _make_coa(db, "4000", "Revenue", "Income")
        _make_coa(db, "3100", "Retained Earnings", "Equity")
        period2 = _make_period(
            db,
            f"Jan {PAST_YEAR} B",
            datetime.date(PAST_YEAR, 1, 1),
            datetime.date(PAST_YEAR, 1, 31),
        )
        _post_sale(db, cash2.id, inc2.id, 9000.0, datetime.date(PAST_YEAR, 1, 10))
        db.commit()

        _set_company(cid1)
        je = app.close_fiscal_period(db, env1["period"].id)

        assert _line_tuples(db, je.id) == [
            (env1["inc_id"], 500.0, 0.0),
            (env1["re_id"], 0.0, 500.0),
        ]


class TestPerformYearEndCloseSuccess:
    def test_success_returns_tuple_and_creates_yec_without_je(self, session):
        db, cid = session
        ctx = _closed_allocated_period(db, net_income=1200.0)
        n_je = _count(db, models.JournalEntry)

        _, warnings, err = app.perform_year_end_close(db, FISCAL_YEAR)
        assert err == ""
        assert isinstance(warnings, list)
        ack = [w[0] for w in warnings]
        yec_id, warnings2, err2 = app.perform_year_end_close(
            db, FISCAL_YEAR, closed_by_id=CLOSER_ID, acknowledged_warnings=ack
        )

        assert err2 == ""
        assert yec_id is not None
        assert _count(db, models.JournalEntry) == n_je
        yec = db.get(models.YearEndClose, yec_id)
        assert yec.fiscal_year == FISCAL_YEAR
        assert yec.status == "closed"
        assert yec.period_count == 1
        assert yec.allocation_count == 1
        assert yec.net_income_snapshot == 1200.0
        assert yec.company_id == cid
        assert warnings2  # soft warnings still returned on success path


class TestPerformYearEndCloseWarnings:
    def test_unacked_warnings_return_none_id_empty_error(self, session):
        db, _ = session
        re_acct = _make_coa(db, "3100", "Retained Earnings", "Equity")
        inc_acct = _make_coa(db, "4000", "Revenue", "Income")
        cash_acct = _make_coa(db, "1000", "Cash", "Asset")
        cap_acct = _make_coa(db, "3501", "Alice Capital", "Equity")
        cur_acct = _make_coa(db, "3601", "Alice Current", "Equity")
        adv_acct = _make_coa(db, "1501", "Alice Advances", "Asset")
        obe = _make_coa(db, "3900", "Opening Balance Equity", "Equity")
        legacy_cap = _make_coa(db, "3000", "Owner Capital", "Equity")
        legacy_draw = _make_coa(db, "3200", "Owner Drawings", "Equity")
        user = models.User(
            username="yec_char",
            display_name="YEC Char",
            password_hash="x",
            role="owner",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        db.add(user)
        db.flush()
        partner = _make_partner(db, "Alice", 100.0, cap_acct.id, cur_acct.id, adv_acct.id)
        period = _make_period(db, f"FY {FISCAL_YEAR}", Y_START, Y_END)
        mid = datetime.date(PAST_YEAR, 6, 15)
        _post_sale(db, cash_acct.id, inc_acct.id, 1000.0, mid)
        _post_sale(db, cash_acct.id, obe.id, 50.0, mid)
        _post_sale(db, cash_acct.id, legacy_cap.id, 40.0, mid)
        app.create_journal_entry(
            db,
            mid,
            "Legacy drawings pin",
            "Manual",
            None,
            [(legacy_draw.id, 30.0, 0.0), (cash_acct.id, 0.0, 30.0)],
        )
        app.create_journal_entry(
            db,
            mid,
            "Partner advance pin",
            "PartnerAdvance",
            partner.id,
            [(adv_acct.id, 25.0, 0.0), (cash_acct.id, 0.0, 25.0)],
        )
        db.commit()
        app.close_fiscal_period(db, period.id)
        _make_allocation(db, period.id, re_acct.id, cur_acct.id, 900.0, partner.id)
        db.add(
            models.DailyCashReconciliation(
                date=mid,
                cash_account_id=cash_acct.id,
                expected_cash=0.0,
                actual_cash=0.0,
                difference=0.0,
                variance_type="balanced",
                status="pending_approval",
                created_by_id=user.id,
                created_at=datetime.datetime.now(),
                is_void=False,
            )
        )
        db.commit()

        yec_id, warnings, err = app.perform_year_end_close(db, FISCAL_YEAR)

        assert yec_id is None
        assert err == ""
        assert warnings
        keys = {k for k, _ in warnings}
        assert "re_residual" in keys
        assert "obe_balance" in keys
        assert f"advance_{partner.id}" in keys
        assert "legacy_capital" in keys
        assert "legacy_drawings" in keys
        assert "unresolved_recons" in keys
        assert "stale_eod" in keys

    def test_acknowledged_warnings_allow_close(self, session):
        db, _ = session
        _closed_allocated_period(db)
        _, warnings, _ = app.perform_year_end_close(db, FISCAL_YEAR)
        ack = [w[0] for w in warnings]
        yec_id, _, err = app.perform_year_end_close(
            db, FISCAL_YEAR, acknowledged_warnings=ack
        )
        assert err == ""
        assert yec_id is not None


class TestPerformYearEndCloseHardBlocks:
    def test_duplicate_close_exact_error(self, session):
        db, _ = session
        _closed_allocated_period(db)
        _, warnings, _ = app.perform_year_end_close(db, FISCAL_YEAR)
        yec_id, _, err = app.perform_year_end_close(
            db, FISCAL_YEAR, acknowledged_warnings=[w[0] for w in warnings]
        )
        assert yec_id is not None

        yec_id2, _, err2 = app.perform_year_end_close(db, FISCAL_YEAR)
        assert yec_id2 is None
        assert err2 == f"Year {FISCAL_YEAR} is already closed (Year-End Close #{yec_id})."

    def test_open_period_exact_error(self, session):
        db, _ = session
        re_acct = _make_coa(db, "3100", "Retained Earnings", "Equity")
        inc_acct = _make_coa(db, "4000", "Revenue", "Income")
        cap_acct = _make_coa(db, "3501", "Alice Capital", "Equity")
        cur_acct = _make_coa(db, "3601", "Alice Current", "Equity")
        adv_acct = _make_coa(db, "1501", "Alice Advances", "Asset")
        cash_acct = _make_coa(db, "1000", "Cash", "Asset")
        db.commit()
        _make_partner(db, "Alice", 100.0, cap_acct.id, cur_acct.id, adv_acct.id)
        period = _make_period(db, f"FY {FISCAL_YEAR}", Y_START, Y_END, closed=False)
        _post_sale(db, cash_acct.id, inc_acct.id, 100.0, Y_START)
        db.commit()

        _, _, err = app.perform_year_end_close(db, FISCAL_YEAR)
        assert err == f"Not all periods are closed. Open: {period.name}."

    def test_missing_allocation_exact_error(self, session):
        db, _ = session
        re_acct = _make_coa(db, "3100", "Retained Earnings", "Equity")
        inc_acct = _make_coa(db, "4000", "Revenue", "Income")
        cap_acct = _make_coa(db, "3501", "Alice Capital", "Equity")
        cur_acct = _make_coa(db, "3601", "Alice Current", "Equity")
        adv_acct = _make_coa(db, "1501", "Alice Advances", "Asset")
        cash_acct = _make_coa(db, "1000", "Cash", "Asset")
        db.commit()
        _make_partner(db, "Alice", 100.0, cap_acct.id, cur_acct.id, adv_acct.id)
        period = _make_period(db, f"FY {FISCAL_YEAR}", Y_START, Y_END)
        _post_sale(db, cash_acct.id, inc_acct.id, 100.0, Y_START)
        app.close_fiscal_period(db, period.id)

        _, _, err = app.perform_year_end_close(db, FISCAL_YEAR)
        assert err == f"Periods missing profit allocation: {period.name}."

    def test_invalid_partner_shares_exact_error(self, session):
        db, _ = session
        re_acct = _make_coa(db, "3100", "Retained Earnings", "Equity")
        inc_acct = _make_coa(db, "4000", "Revenue", "Income")
        cap_acct = _make_coa(db, "3501", "Alice Capital", "Equity")
        cur_acct = _make_coa(db, "3601", "Alice Current", "Equity")
        adv_acct = _make_coa(db, "1501", "Alice Advances", "Asset")
        cap2 = _make_coa(db, "3502", "Bob Capital", "Equity")
        cur2 = _make_coa(db, "3602", "Bob Current", "Equity")
        adv2 = _make_coa(db, "1502", "Bob Advances", "Asset")
        cash_acct = _make_coa(db, "1000", "Cash", "Asset")
        db.commit()
        _make_partner(db, "Alice", 60.0, cap_acct.id, cur_acct.id, adv_acct.id)
        _make_partner(db, "Bob", 30.0, cap2.id, cur2.id, adv2.id)
        period = _make_period(db, f"FY {FISCAL_YEAR}", Y_START, Y_END)
        _post_sale(db, cash_acct.id, inc_acct.id, 100.0, Y_START)
        app.close_fiscal_period(db, period.id)
        _make_allocation(db, period.id, re_acct.id, cur_acct.id, 100.0, 1)

        _, _, err = app.perform_year_end_close(db, FISCAL_YEAR)
        assert err == "Partner shares invalid: Partner shares sum to 90.00% — must equal 100%."

    def test_unbalanced_trial_balance_exact_error(self, session):
        db, cid = session
        ctx = _closed_allocated_period(db, net_income=100.0)
        je = models.JournalEntry(
            entry_date=Y_END,
            description="Unbalanced pin",
            reference_type="Manual",
            reference_id=None,
            company_id=cid,
        )
        db.add(je)
        db.flush()
        db.add(
            models.JournalEntryLine(
                journal_entry_id=je.id,
                account_id=ctx["re_id"],
                debit=50.0,
                credit=0.0,
            )
        )
        db.commit()

        _, _, err = app.perform_year_end_close(db, FISCAL_YEAR)
        assert err.startswith(
            f"Trial Balance is not balanced for year {FISCAL_YEAR}: Debit "
        )

    def test_no_periods_continuity_error(self, session):
        db, _ = session
        _, _, err = app.perform_year_end_close(db, FISCAL_YEAR)
        assert err == f"No fiscal periods exist for this year ({Y_START} – {Y_END})."

    def test_hard_block_posts_zero_commits(self, session):
        db, _ = session
        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            _, _, err = app.perform_year_end_close(db, FISCAL_YEAR)
        assert err == f"No fiscal periods exist for this year ({Y_START} – {Y_END})."
        assert mock_commit.call_count == 0


class TestPerformYearEndCloseCommitAudit:
    def test_success_posts_two_commits_and_audit(self, session):
        db, _ = session
        _closed_allocated_period(db)
        _, warnings, _ = app.perform_year_end_close(db, FISCAL_YEAR)
        ack = [w[0] for w in warnings]

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            yec_id, _, err = app.perform_year_end_close(
                db, FISCAL_YEAR, acknowledged_warnings=ack
            )
            assert err == ""
            assert yec_id is not None
            assert mock_commit.call_count == 2

        audit = (
            db.query(models.AuditLog)
            .filter_by(action="YearEndClose", entity_type="YearEndClose", entity_id=yec_id)
            .one()
        )
        assert f"Year {FISCAL_YEAR} closed." in audit.description
        assert audit.performed_by == app._DEV_USER["username"]


class TestPerformYearEndCloseCompanyScoping:
    def test_other_company_open_period_does_not_block_close(self, session):
        db, cid1 = session
        _closed_allocated_period(db)

        co2 = models.Company(
            name="Leak Co",
            slug="leak_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        db.add(co2)
        db.flush()
        _set_company(co2.id)
        _make_period(db, f"Open {FISCAL_YEAR}", Y_START, Y_END, closed=False)
        db.commit()

        _set_company(cid1)
        _, warnings, err = app.perform_year_end_close(db, FISCAL_YEAR)
        assert err == ""
        yec_id, _, err2 = app.perform_year_end_close(
            db, FISCAL_YEAR, acknowledged_warnings=[w[0] for w in warnings]
        )
        assert err2 == ""
        assert yec_id is not None

    def test_net_income_snapshot_uses_only_active_company_periods(self, session):
        db, cid1 = session
        ctx1 = _closed_allocated_period(db, net_income=800.0)

        co2 = models.Company(
            name="Other FY Co",
            slug="other_fy_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        db.add(co2)
        db.flush()
        _set_company(co2.id)
        re2 = _make_coa(db, "3100", "Retained Earnings", "Equity")
        inc2 = _make_coa(db, "4000", "Revenue", "Income")
        cash2 = _make_coa(db, "1000", "Cash", "Asset")
        cap2 = _make_coa(db, "3501", "Bob Capital", "Equity")
        cur2 = _make_coa(db, "3602", "Bob Current", "Equity")
        adv2 = _make_coa(db, "1502", "Bob Advances", "Asset")
        db.commit()
        p2 = _make_partner(db, "Bob", 100.0, cap2.id, cur2.id, adv2.id)
        period2 = _make_period(db, f"FY {FISCAL_YEAR} B", Y_START, Y_END)
        _post_sale(db, cash2.id, inc2.id, 5000.0, Y_START)
        je2 = app.close_fiscal_period(db, period2.id)
        _make_allocation(db, period2.id, re2.id, cur2.id, 5000.0, p2.id)
        db.commit()

        _set_company(cid1)
        _, warnings, _ = app.perform_year_end_close(db, FISCAL_YEAR)
        yec_id, _, err = app.perform_year_end_close(
            db, FISCAL_YEAR, acknowledged_warnings=[w[0] for w in warnings]
        )
        assert err == ""
        yec = db.get(models.YearEndClose, yec_id)
        assert yec.net_income_snapshot == ctx1["net_income"]
        assert je2.id is not None
