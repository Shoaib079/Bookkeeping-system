"""PARTNER-STATEMENT-01 P1 — read-only partner settlement statement."""
from __future__ import annotations

import datetime
import inspect
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app
from registry.partner_statement import (
    advance_offset_position_delta,
    build_partner_statement,
    check_partner_statement_reconciliation,
    partner_position_from_balances,
    partner_position_status,
    partner_statement_net_change,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )


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
            name="Test Co",
            slug="test_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        yield s


def _make_coa(session, code, name, acct_type):
    acct = models.ChartOfAccounts(
        account_code=code,
        account_name=name,
        account_type=acct_type,
        balance=0.0,
        is_active=True,
    )
    session.add(acct)
    session.flush()
    return acct


def _make_partner(session, name, pct, cap_id, cur_id, adv_id, *, active=True):
    p = models.Partner(
        name=name,
        profit_share_pct=pct,
        capital_account_id=cap_id,
        current_account_id=cur_id,
        advance_account_id=adv_id,
        is_active=active,
        created_at=datetime.datetime.now(),
    )
    session.add(p)
    session.flush()
    return p


def _make_bank(session):
    _make_coa(session, "1100", "Cash", "Asset")
    ba = models.BankAccount(
        name="Cash",
        currency="TRY",
        balance=10000.0,
        is_active=True,
        kind="bank",
    )
    session.add(ba)
    session.flush()
    return ba


def _make_period(session, name, start, end, *, closed=False):
    fp = models.FiscalPeriod(
        name=name,
        start_date=start,
        end_date=end,
        is_closed=closed,
        closed_at=datetime.date.today() if closed else None,
    )
    session.add(fp)
    session.flush()
    return fp


def _make_allocation_line(
    session,
    period_id,
    partner_id,
    amount,
    *,
    re_acct,
    cur_acct,
    je_date=None,
    share_pct=100.0,
):
    alloc = models.PartnerProfitAllocation(
        fiscal_period_id=period_id,
        allocated_at=datetime.datetime.now(),
        allocated_by_id=None,
        total_net_income=amount,
        is_void=False,
        created_at=datetime.datetime.now(),
    )
    session.add(alloc)
    session.flush()
    je_date = je_date or datetime.date.today()
    if amount >= 0:
        lines = [(re_acct.id, amount, 0), (cur_acct.id, 0, amount)]
    else:
        lines = [(re_acct.id, 0, abs(amount)), (cur_acct.id, abs(amount), 0)]
    je = app.create_journal_entry(
        session,
        je_date,
        f"Profit Allocation for period {period_id}",
        "ProfitAllocation",
        alloc.id,
        lines,
    )
    alloc.journal_entry_id = je.id
    line = models.PartnerProfitAllocationLine(
        allocation_id=alloc.id,
        partner_id=partner_id,
        share_pct=share_pct,
        amount=amount,
    )
    session.add(line)
    session.commit()
    return alloc


@pytest.fixture()
def partner_env(session):
    re_acct = _make_coa(session, "3100", "Retained Earnings", "Equity")
    cap_acct = _make_coa(session, "3501", "Bob Capital", "Equity")
    cur_acct = _make_coa(session, "3601", "Bob Current", "Equity")
    adv_acct = _make_coa(session, "1501", "Bob Advances", "Asset")
    bank = _make_bank(session)
    partner = _make_partner(
        session, "Bob", 100.0, cap_acct.id, cur_acct.id, adv_acct.id
    )
    session.commit()
    return {
        "partner": partner,
        "bank_id": bank.id,
        "re_id": re_acct.id,
        "cap_id": cap_acct.id,
        "cur_id": cur_acct.id,
        "adv_id": adv_acct.id,
    }


def _stmt(session, partner_id, d_from, d_to):
    return build_partner_statement(
        session,
        partner_id,
        d_from,
        d_to,
        app.calculate_account_balance_for_period,
    )


class TestPositionFormula:
    def test_position_is_capital_plus_current_minus_advances(self):
        assert partner_position_from_balances(1000.0, 500.0, 200.0) == 1300.0
        assert partner_position_from_balances(0.0, -300.0, 100.0) == -400.0


class TestPositionStatus:
    def test_company_owes_partner(self):
        status, amt = partner_position_status(150.0)
        assert status == "company_owes"
        assert amt == 150.0

    def test_partner_owes_company(self):
        status, amt = partner_position_status(-75.5)
        assert status == "partner_owes"
        assert amt == 75.5

    def test_settled_near_zero(self):
        status, amt = partner_position_status(0.005)
        assert status == "settled"
        assert amt == 0.0


class TestMovementTypes:
    def test_all_six_movement_types_bucketed(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        d = datetime.date(2025, 6, 15)

        for mtype, amt in (
            ("CapitalContribution", 1000.0),
            ("Drawing", 100.0),
            ("Salary", 50.0),
            ("Advance", 200.0),
            ("Repayment", 75.0),
            ("AdvanceOffset", 25.0),
        ):
            if mtype == "AdvanceOffset":
                app.post_partner_movement(
                    session, pid, mtype, amt, d, created_by_id=1
                )
            else:
                app.post_partner_movement(
                    session, pid, mtype, amt, d, bank_account_id=bank_id, created_by_id=1
                )

        stmt = _stmt(session, pid, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30))
        assert stmt.capital_contributions == 1000.0
        assert stmt.drawings == 100.0
        assert stmt.salary == 50.0
        assert stmt.advances_taken == 200.0
        assert stmt.repayments == 75.0
        assert stmt.advance_offsets == 25.0


class TestAdvanceOffsetZeroNet:
    def test_advance_offset_has_zero_position_delta(self):
        assert advance_offset_position_delta(500.0) == 0.0

    def test_advance_offset_does_not_change_net_activity(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        d = datetime.date(2025, 7, 10)
        app.post_partner_movement(
            session, pid, "Advance", 300.0, d, bank_account_id=bank_id, created_by_id=1
        )
        before = _stmt(session, pid, d, d)
        app.post_partner_movement(session, pid, "AdvanceOffset", 100.0, d, created_by_id=1)
        after = _stmt(session, pid, d, d)
        assert after.advance_offsets == 100.0
        assert after.net_position_change == before.net_position_change - 100.0 + 100.0
        assert after.closing_position == before.closing_position - 100.0 + 100.0


class TestProfitAllocationByPeriodEnd:
    def test_allocation_included_by_fiscal_period_end_not_posting_date(
        self, session, partner_env
    ):
        pid = partner_env["partner"].id
        re_acct = session.get(models.ChartOfAccounts, partner_env["re_id"])
        cur_acct = session.get(models.ChartOfAccounts, partner_env["cur_id"])
        may = _make_period(
            session,
            "May 2025",
            datetime.date(2025, 5, 1),
            datetime.date(2025, 5, 31),
            closed=True,
        )
        _make_allocation_line(
            session,
            may.id,
            pid,
            800.0,
            re_acct=re_acct,
            cur_acct=cur_acct,
            je_date=datetime.date(2025, 6, 15),
        )

        may_stmt = _stmt(
            session, pid, datetime.date(2025, 5, 1), datetime.date(2025, 5, 31)
        )
        june_stmt = _stmt(
            session, pid, datetime.date(2025, 6, 1), datetime.date(2025, 6, 30)
        )
        assert may_stmt.profit_allocated == 800.0
        assert june_stmt.profit_allocated == 0.0


class TestStoredAllocationAmount:
    def test_uses_stored_line_amount_not_percentage(self, session, partner_env):
        pid = partner_env["partner"].id
        re_acct = session.get(models.ChartOfAccounts, partner_env["re_id"])
        cur_acct = session.get(models.ChartOfAccounts, partner_env["cur_id"])
        period = _make_period(
            session,
            "Q1 2025",
            datetime.date(2025, 1, 1),
            datetime.date(2025, 3, 31),
            closed=True,
        )
        _make_allocation_line(
            session,
            period.id,
            pid,
            499.0,
            re_acct=re_acct,
            cur_acct=cur_acct,
            share_pct=50.0,
        )
        stmt = _stmt(
            session, pid, datetime.date(2025, 1, 1), datetime.date(2025, 3, 31)
        )
        assert stmt.profit_allocated == 499.0


class TestVoidedMovementsExcluded:
    def test_voided_movement_not_in_statement(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        d = datetime.date(2025, 8, 5)
        mid, err = app.post_partner_movement(
            session, pid, "Drawing", 400.0, d, bank_account_id=bank_id, created_by_id=1
        )
        assert err == ""
        assert app.void_partner_movement(session, mid, 1, "test void") == ""
        stmt = _stmt(session, pid, d, d)
        assert stmt.drawings == 0.0


class TestWarnings:
    def test_outstanding_advance_warning(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        d = datetime.date(2025, 9, 1)
        app.post_partner_movement(
            session, pid, "Advance", 250.0, d, bank_account_id=bank_id, created_by_id=1
        )
        stmt = _stmt(session, pid, d, d)
        keys = [w.key for w in stmt.warnings]
        assert "partner.stmt.warn_outstanding_advance" in keys

    def test_closed_period_without_allocation_warning(self, session, partner_env):
        pid = partner_env["partner"].id
        _make_period(
            session,
            "April 2025",
            datetime.date(2025, 4, 1),
            datetime.date(2025, 4, 30),
            closed=True,
        )
        stmt = _stmt(
            session, pid, datetime.date(2025, 4, 1), datetime.date(2025, 4, 30)
        )
        keys = [w.key for w in stmt.warnings]
        assert "partner.stmt.warn_closed_period_no_alloc" in keys

    def test_reconciliation_mismatch_warning(self):
        assert not check_partner_statement_reconciliation(100.0, 50.0, 200.0)
        assert check_partner_statement_reconciliation(100.0, 50.0, 150.0)

    def test_build_statement_emits_reconciliation_warning(self, session, partner_env):
        """Orphan movement (no JE) breaks identity and surfaces warning."""
        pid = partner_env["partner"].id
        d = datetime.date(2025, 12, 1)
        session.add(
            models.PartnerMovement(
                partner_id=pid,
                movement_type="Drawing",
                amount=500.0,
                date=d,
                is_void=False,
                created_at=datetime.datetime.now(),
            )
        )
        session.commit()
        stmt = _stmt(session, pid, d, d)
        assert not stmt.reconciliation_ok
        assert any(
            w.key == "partner.stmt.warn_reconciliation" for w in stmt.warnings
        )


class TestInactivePartner:
    def test_inactive_partner_with_balance_renders(self, session, partner_env):
        partner = partner_env["partner"]
        bank_id = partner_env["bank_id"]
        app.post_partner_movement(
            session,
            partner.id,
            "CapitalContribution",
            500.0,
            datetime.date(2025, 10, 1),
            bank_account_id=bank_id,
            created_by_id=1,
        )
        partner.is_active = False
        session.commit()
        stmt = _stmt(
            session,
            partner.id,
            datetime.date(2025, 10, 1),
            datetime.date(2025, 10, 31),
        )
        assert stmt is not None
        assert stmt.partner_name == "Bob"
        assert not stmt.partner_is_active
        assert stmt.capital_contributions == 500.0


class TestReconciliationIdentity:
    def test_opening_plus_activity_equals_closing(self, session, partner_env):
        pid = partner_env["partner"].id
        bank_id = partner_env["bank_id"]
        d_from = datetime.date(2025, 11, 1)
        d_to = datetime.date(2025, 11, 30)
        app.post_partner_movement(
            session,
            pid,
            "CapitalContribution",
            2000.0,
            datetime.date(2025, 11, 5),
            bank_account_id=bank_id,
            created_by_id=1,
        )
        app.post_partner_movement(
            session,
            pid,
            "Drawing",
            300.0,
            datetime.date(2025, 11, 10),
            bank_account_id=bank_id,
            created_by_id=1,
        )
        stmt = _stmt(session, pid, d_from, d_to)
        assert stmt.reconciliation_ok
        assert check_partner_statement_reconciliation(
            stmt.opening_position, stmt.net_position_change, stmt.closing_position
        )


class TestPostingLogicUnchanged:
    def test_post_partner_movement_unchanged(self):
        src = inspect.getsource(app.post_partner_movement)
        assert "def post_partner_movement" in src
        assert "posting_service.post_partner_movement(" in src

    def test_allocate_profit_to_partners_unchanged(self):
        src = inspect.getsource(app.allocate_profit_to_partners)
        assert "def allocate_profit_to_partners" in src
        assert "posting_service.allocate_profit_to_partners(" in src


class TestPartnerStatementUI:
    def test_statement_tab_on_partner_accounts(self):
        src = inspect.getsource(app.render_partner_accounts)
        assert "partner.tab_statement" in src
        assert "_render_partner_statement" in src

    def test_year_end_close_tests_still_importable(self):
        import tests.test_year_end_close as yec  # noqa: F401
