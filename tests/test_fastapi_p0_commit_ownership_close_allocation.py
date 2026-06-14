"""FASTAPI-P0.5d-S6 — boundary commit for allocation / period close / year-end close."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event as sa_event, func
from sqlalchemy.orm import sessionmaker

import app
import models
from db import Base
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import commit_modes, posting
from services.commit_modes import (
    PERIOD_CLOSE_FAMILY,
    PROFIT_ALLOCATION_FAMILY,
    CommitMode,
    YEAR_END_CLOSE_FAMILY,
)
from services.unit_of_work import boundary_commit_scope
from tests.helpers.commit_parity import (
    CLOSE_ALLOCATION_TABLES,
    assert_persisted_state_equal,
    audit_row_tuples,
    dual_run_parity,
    journal_line_tuples,
    persisted_state_snapshot,
)

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
ALLOCATOR_ID = 7
CLOSER_ID = 9
PERFORMED_BY = "admin"


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )


@pytest.fixture(autouse=True)
def _reset_commit_modes():
    commit_modes.reset_commit_modes_for_tests()
    yield
    commit_modes.reset_commit_modes_for_tests()


@pytest.fixture(autouse=True)
def _clear_streamlit_state():
    sys.modules["streamlit"].session_state.clear()
    _seed_dev_auth_user()
    yield
    sys.modules["streamlit"].session_state.clear()


def _make_engine_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        app._stamp_company_id_on_new_objects(sess, ctx, instances)

    return engine, Session


def _seed_company_session(Session):
    sess = Session()
    co = models.Company(
        name="P05d Close Allocation Co",
        slug="p05d_close_allocation_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    sess.add(co)
    sess.flush()
    sys.modules["streamlit"].session_state["active_company_id"] = co.id
    seed_chart_of_accounts_for_company(sess, co.id)
    sess.commit()
    return sess, co.id


def _acct(sess, cid, name):
    acct = posting.get_account_by_name(sess, name, company_id=cid)
    assert acct is not None, f"Seeded account {name!r} missing"
    return acct


def _make_coa(sess, code, name, acct_type):
    acct = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        balance=0.0,
        is_active=True,
    )
    sess.add(acct)
    sess.flush()
    return acct


def _make_partner(sess, name, pct, cap_id, cur_id, adv_id):
    p = models.Partner(
        name=name,
        profit_share_pct=pct,
        capital_account_id=cap_id,
        current_account_id=cur_id,
        advance_account_id=adv_id,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    sess.add(p)
    sess.flush()
    return p


def _closed_period(sess, name, start, end, closing_lines):
    period = models.FiscalPeriod(
        name=name,
        start_date=start,
        end_date=end,
        is_closed=True,
        closed_at=datetime.date.today(),
    )
    sess.add(period)
    sess.flush()
    closing_je = app.create_journal_entry(
        sess,
        end,
        f"Period Close: {name}",
        "PeriodClose",
        period.id,
        closing_lines,
    )
    period.closing_je_id = closing_je.id
    sess.commit()
    return period


def _alloc_env(sess, cid):
    re_acct = _acct(sess, cid, "Retained Earnings")
    inc_acct = _acct(sess, cid, "Sales Revenue")
    cap1 = _make_coa(sess, "3501", "Alice Capital", "Equity")
    cur1 = _make_coa(sess, "3601", "Alice Current", "Equity")
    adv1 = _make_coa(sess, "1501", "Alice Advances", "Asset")
    cap2 = _make_coa(sess, "3502", "Bob Capital", "Equity")
    cur2 = _make_coa(sess, "3602", "Bob Current", "Equity")
    adv2 = _make_coa(sess, "1502", "Bob Advances", "Asset")
    sess.commit()
    _make_partner(sess, "Alice", 50.0, cap1.id, cur1.id, adv1.id)
    _make_partner(sess, "Bob", 50.0, cap2.id, cur2.id, adv2.id)
    sess.commit()
    return {
        "re_id": re_acct.id,
        "inc_id": inc_acct.id,
        "p1_cur": cur1.id,
        "p2_cur": cur2.id,
    }


def _period_close_env(sess, cid, *, revenue=1000.0, expense=600.0):
    re_acct = _acct(sess, cid, "Retained Earnings")
    inc_acct = _acct(sess, cid, "Sales Revenue")
    exp_acct = _acct(sess, cid, "Rent Expense")
    cash_acct = _acct(sess, cid, "Cash")
    sess.commit()
    period = models.FiscalPeriod(
        name=f"Jan {PAST_YEAR}",
        start_date=datetime.date(PAST_YEAR, 1, 1),
        end_date=datetime.date(PAST_YEAR, 1, 31),
        is_closed=False,
    )
    sess.add(period)
    sess.flush()
    mid = datetime.date(PAST_YEAR, 1, 15)
    if revenue:
        app.create_journal_entry(
            sess,
            mid,
            "Sale pin",
            "Sale",
            None,
            [(cash_acct.id, revenue, 0.0), (inc_acct.id, 0.0, revenue)],
        )
    if expense:
        app.create_journal_entry(
            sess,
            mid,
            "Expense pin",
            "Expense",
            None,
            [(exp_acct.id, expense, 0.0), (cash_acct.id, 0.0, expense)],
        )
    sess.commit()
    return {
        "period": period,
        "re_id": re_acct.id,
        "inc_id": inc_acct.id,
        "exp_id": exp_acct.id,
    }


def _make_allocation(sess, period_id, re_id, cur_id, amount, partner_id):
    alloc = models.PartnerProfitAllocation(
        fiscal_period_id=period_id,
        allocated_at=datetime.datetime.now(),
        allocated_by_id=ALLOCATOR_ID,
        total_net_income=amount,
        is_void=False,
        created_at=datetime.datetime.now(),
    )
    sess.add(alloc)
    sess.flush()
    je = app.create_journal_entry(
        sess,
        datetime.date.today(),
        f"Profit Allocation {period_id}",
        "ProfitAllocation",
        alloc.id,
        [(re_id, amount, 0.0), (cur_id, 0.0, amount)],
    )
    alloc.journal_entry_id = je.id
    sess.add(
        models.PartnerProfitAllocationLine(
            allocation_id=alloc.id,
            partner_id=partner_id,
            share_pct=100.0,
            amount=amount,
        )
    )
    sess.commit()
    return alloc


def _closed_allocated_year(sess, cid, *, net_income=1000.0):
    re_acct = _acct(sess, cid, "Retained Earnings")
    inc_acct = _acct(sess, cid, "Sales Revenue")
    cash_acct = _acct(sess, cid, "Cash")
    cap_acct = _make_coa(sess, "3501", "Alice Capital", "Equity")
    cur_acct = _make_coa(sess, "3601", "Alice Current", "Equity")
    adv_acct = _make_coa(sess, "1501", "Alice Advances", "Asset")
    sess.commit()
    partner = _make_partner(sess, "Alice", 100.0, cap_acct.id, cur_acct.id, adv_acct.id)
    period = models.FiscalPeriod(
        name=f"FY {FISCAL_YEAR}",
        start_date=Y_START,
        end_date=Y_END,
        is_closed=False,
    )
    sess.add(period)
    sess.flush()
    app.create_journal_entry(
        sess,
        Y_START,
        "Sale pin",
        "Sale",
        None,
        [(cash_acct.id, net_income, 0.0), (inc_acct.id, 0.0, net_income)],
    )
    sess.commit()
    app.close_fiscal_period(sess, period.id)
    _make_allocation(sess, period.id, re_acct.id, cur_acct.id, net_income, partner.id)
    return period


def _profit_period(sess, cid):
    env = _alloc_env(sess, cid)
    return _closed_period(
        sess,
        f"Jan {PAST_YEAR}",
        datetime.date(PAST_YEAR, 1, 1),
        datetime.date(PAST_YEAR, 1, 31),
        [(env["inc_id"], 1000.0, 0), (env["re_id"], 0, 1000.0)],
    )


def _alloc_internal(sess, period_id):
    alloc_id, err = app.allocate_profit_to_partners(sess, period_id, ALLOCATOR_ID)
    assert err == ""
    return alloc_id


def _alloc_boundary(sess, period_id):
    commit_modes.set_commit_mode_for_tests(PROFIT_ALLOCATION_FAMILY, CommitMode.BOUNDARY)
    alloc_id, err = app.allocate_profit_to_partners(sess, period_id, ALLOCATOR_ID)
    assert err == ""
    return alloc_id


def _period_close_internal(sess, period_id):
    return app.close_fiscal_period(sess, period_id)


def _period_close_boundary(sess, period_id):
    commit_modes.set_commit_mode_for_tests(PERIOD_CLOSE_FAMILY, CommitMode.BOUNDARY)
    return app.close_fiscal_period(sess, period_id)


def _yec_complete(sess, year: str):
    _, warnings, err = app.perform_year_end_close(sess, year, closed_by_id=CLOSER_ID)
    assert err == ""
    ack = [w[0] for w in warnings]
    yec_id, _, err2 = app.perform_year_end_close(
        sess, year, closed_by_id=CLOSER_ID, acknowledged_warnings=ack
    )
    assert err2 == ""
    return yec_id


def _yec_internal(sess, cid, year: str):
    _closed_allocated_year(sess, cid)
    return _yec_complete(sess, year)


def _yec_boundary(sess, cid, year: str):
    commit_modes.set_commit_mode_for_tests(YEAR_END_CLOSE_FAMILY, CommitMode.BOUNDARY)
    _closed_allocated_year(sess, cid)
    return _yec_complete(sess, year)


class TestDefaultInternalCommitCounts:
    def test_allocate_profit_kernel_two_commits(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        period = _profit_period(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            posting.allocate_profit_to_partners(
                sess, period.id, ALLOCATOR_ID, company_id=cid
            )
            assert mock_commit.call_count == 2

    def test_allocate_profit_app_shim_three_commits(self):
        _, Session = _make_engine_session()
        sess, _cid = _seed_company_session(Session)
        period = _profit_period(sess, _cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            app.allocate_profit_to_partners(sess, period.id, ALLOCATOR_ID)
            assert mock_commit.call_count == 3

    def test_close_fiscal_period_kernel_two_commits(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _period_close_env(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            posting.close_fiscal_period(sess, env["period"].id, company_id=cid)
            assert mock_commit.call_count == 2

    def test_close_fiscal_period_app_shim_three_commits(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _period_close_env(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            app.close_fiscal_period(sess, env["period"].id)
            assert mock_commit.call_count == 3

    def test_year_end_close_app_shim_two_commits(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        _closed_allocated_year(sess, cid)
        _, warnings, _ = app.perform_year_end_close(sess, FISCAL_YEAR)
        ack = [w[0] for w in warnings]
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            yec_id, _, err = app.perform_year_end_close(
                sess, FISCAL_YEAR, acknowledged_warnings=ack
            )
            assert err == ""
            assert yec_id is not None
            assert mock_commit.call_count == 2


class TestCloseAllocationBoundaryMode:
    def test_allocate_boundary_one_commit(self):
        commit_modes.set_commit_mode_for_tests(
            PROFIT_ALLOCATION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        period = _profit_period(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _alloc_boundary(sess, period.id)
            assert mock_commit.call_count == 1

    def test_period_close_boundary_one_commit(self):
        commit_modes.set_commit_mode_for_tests(PERIOD_CLOSE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _period_close_env(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _period_close_boundary(sess, env["period"].id)
            assert mock_commit.call_count == 1

    def test_year_end_close_boundary_one_commit(self):
        commit_modes.set_commit_mode_for_tests(
            YEAR_END_CLOSE_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        _closed_allocated_year(sess, cid)
        _, warnings, _ = app.perform_year_end_close(sess, FISCAL_YEAR)
        ack = [w[0] for w in warnings]
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            yec_id, _, err = app.perform_year_end_close(
                sess, FISCAL_YEAR, acknowledged_warnings=ack
            )
            assert err == ""
            assert yec_id is not None
            assert mock_commit.call_count == 1


class TestCloseAllocationDualRunParity:
    _SNAP_EXTRA = {
        "profit_allocation": {
            "include_fiscal_period_rows": True,
            "include_profit_allocation_rows": True,
            "include_profit_allocation_lines": True,
        },
        "period_close": {"include_fiscal_period_rows": True},
        "year_end_close": {
            "include_fiscal_period_rows": True,
            "include_profit_allocation_rows": True,
            "include_year_end_close_rows": True,
        },
    }

    @pytest.mark.parametrize(
        "flow_kind",
        ["profit_allocation", "period_close", "year_end_close"],
    )
    def test_internal_vs_boundary_persisted_state_identical(self, flow_kind):
        snap_extra = self._SNAP_EXTRA[flow_kind]

        def factory():
            _, Session = _make_engine_session()
            sess, _cid = _seed_company_session(Session)
            return sess

        def run_internal(sess):
            commit_modes.reset_commit_modes_for_tests()
            cid = sys.modules["streamlit"].session_state["active_company_id"]
            if flow_kind == "year_end_close":
                _yec_internal(sess, cid, FISCAL_YEAR)
            elif flow_kind == "profit_allocation":
                period = _profit_period(sess, cid)
                _alloc_internal(sess, period.id)
            else:
                env = _period_close_env(sess, cid)
                _period_close_internal(sess, env["period"].id)

        def run_boundary(sess):
            cid = sys.modules["streamlit"].session_state["active_company_id"]
            if flow_kind == "year_end_close":
                _yec_boundary(sess, cid, FISCAL_YEAR)
            elif flow_kind == "profit_allocation":
                period = _profit_period(sess, cid)
                _alloc_boundary(sess, period.id)
            else:
                env = _period_close_env(sess, cid)
                _period_close_boundary(sess, env["period"].id)

        left, right = dual_run_parity(
            session_factory=factory,
            internal_runner=run_internal,
            boundary_runner=run_boundary,
            tables=CLOSE_ALLOCATION_TABLES,
            snapshot_kwargs={
                "include_sale_rows": False,
                **snap_extra,
            },
        )
        assert_persisted_state_equal(left, right)


class TestCloseAllocationBoundaryRollback:
    def test_allocation_failure_rolls_back_allocation_je_and_audit(self):
        commit_modes.set_commit_mode_for_tests(
            PROFIT_ALLOCATION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        period = _profit_period(sess, cid)
        today = datetime.date.today()
        blocker = models.FiscalPeriod(
            name="Closed today blocker",
            start_date=today,
            end_date=today,
            is_closed=True,
            closed_at=today,
            company_id=cid,
        )
        sess.add(blocker)
        sess.commit()

        with pytest.raises(ValueError):
            with boundary_commit_scope(sess, PROFIT_ALLOCATION_FAMILY):
                alloc_id, err = app.allocate_profit_to_partners(
                    sess, period.id, ALLOCATOR_ID
                )
                assert err == ""

        assert (
            sess.query(func.count())
            .select_from(models.PartnerProfitAllocation)
            .scalar()
            == 0
        )
        assert (
            sess.query(func.count())
            .select_from(models.JournalEntry)
            .filter_by(reference_type="ProfitAllocation")
            .scalar()
            == 0
        )
        assert (
            sess.query(func.count())
            .select_from(models.AuditLog)
            .filter_by(entity_type="PartnerProfitAllocation")
            .scalar()
            == 0
        )

    def test_period_close_failure_rolls_back_je_and_period_state(self):
        commit_modes.set_commit_mode_for_tests(PERIOD_CLOSE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)

        env = _period_close_env(sess, cid)
        yec = models.YearEndClose(
            fiscal_year=FISCAL_YEAR,
            start_date=Y_START,
            end_date=Y_END,
            status="closed",
            closed_at=datetime.datetime.now(),
            period_count=1,
            allocation_count=1,
            net_income_snapshot=0.0,
            re_balance_at_close=0.0,
            is_void=False,
            created_at=datetime.datetime.now(),
            company_id=cid,
        )
        sess.add(yec)
        sess.commit()

        with pytest.raises(ValueError, match="Year .+ is closed"):
            with boundary_commit_scope(sess, PERIOD_CLOSE_FAMILY):
                app.close_fiscal_period(sess, env["period"].id)

        period = sess.get(models.FiscalPeriod, env["period"].id)
        assert period.is_closed is False
        assert period.closing_je_id is None
        assert (
            sess.query(func.count())
            .select_from(models.JournalEntry)
            .filter_by(reference_type="PeriodClose")
            .scalar()
            == 0
        )
        assert (
            sess.query(func.count())
            .select_from(models.AuditLog)
            .filter_by(entity_type="FiscalPeriod")
            .scalar()
            == 0
        )

    def test_year_end_close_validation_leaves_no_yec_row(self):
        commit_modes.set_commit_mode_for_tests(
            YEAR_END_CLOSE_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, _cid = _seed_company_session(Session)
        period = models.FiscalPeriod(
            name=f"Open {FISCAL_YEAR}",
            start_date=Y_START,
            end_date=Y_END,
            is_closed=False,
        )
        sess.add(period)
        sess.commit()
        _, _, err = app.perform_year_end_close(sess, FISCAL_YEAR)
        assert err.startswith("Not all periods are closed. Open:")
        assert sess.query(func.count()).select_from(models.YearEndClose).scalar() == 0

    def test_mode_flags_revert_to_internal(self):
        commit_modes.set_commit_mode_for_tests(
            PROFIT_ALLOCATION_FAMILY, CommitMode.BOUNDARY
        )
        commit_modes.set_commit_mode_for_tests(PERIOD_CLOSE_FAMILY, CommitMode.BOUNDARY)
        commit_modes.set_commit_mode_for_tests(
            YEAR_END_CLOSE_FAMILY, CommitMode.BOUNDARY
        )
        commit_modes.reset_commit_modes_for_tests()
        assert not commit_modes.is_boundary_mode(PROFIT_ALLOCATION_FAMILY)
        assert not commit_modes.is_boundary_mode(PERIOD_CLOSE_FAMILY)
        assert not commit_modes.is_boundary_mode(YEAR_END_CLOSE_FAMILY)


class TestCloseAllocationAuditAtomic:
    def test_allocation_audit_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(
            PROFIT_ALLOCATION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        period = _profit_period(sess, cid)
        alloc_id = _alloc_boundary(sess, period.id)
        allocation = sess.get(models.PartnerProfitAllocation, alloc_id)
        audits = [
            r for r in audit_row_tuples(sess) if r[1] == "PartnerProfitAllocation"
        ]
        assert audits == [
            (
                "ProfitAllocation",
                "PartnerProfitAllocation",
                alloc_id,
                f"Allocated {period.name}: net {allocation.total_net_income:,.2f} → 2 partners",
                PERFORMED_BY,
                cid,
            )
        ]

    def test_period_close_audit_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(PERIOD_CLOSE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)

        env = _period_close_env(sess, cid)
        je = _period_close_boundary(sess, env["period"].id)
        period = sess.get(models.FiscalPeriod, env["period"].id)
        net_income = app._get_period_net_income_from_je(sess, period)
        audits = [r for r in audit_row_tuples(sess) if r[1] == "FiscalPeriod"]
        assert audits == [
            (
                "PeriodClose",
                "FiscalPeriod",
                period.id,
                f"Closed period '{period.name}' ({period.start_date}–{period.end_date}). "
                f"Net income: ${net_income:,.2f}. Closing JE #{je.id}.",
                PERFORMED_BY,
                cid,
            )
        ]
