"""FASTAPI-P0.5b — posting company-scoping unification tests."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event, func
from sqlalchemy.orm import sessionmaker

import app as erp_app
from db import Base
import models
from reconciliation.company_card import cc_subledger_stmt_ref
from registry.coa_seed import seed_chart_of_accounts_for_company
from registry.service import set_setting
from services import posting

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True

POST_DATE = datetime.date(2026, 6, 14)
CC_DISABLED_MSG = erp_app._t("form.err.company_cc_disabled")


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
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
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        co = models.Company(
            name="Scope Co A",
            slug="scope_co_a",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        seed_chart_of_accounts_for_company(s, co.id)
        set_setting(s, "banking.company_card_enabled", True, company_id=co.id)
        s.commit()
        yield s, co.id


def _set_active(company_id: int | None):
    if company_id is None:
        sys.modules["streamlit"].session_state.pop("active_company_id", None)
    else:
        sys.modules["streamlit"].session_state["active_company_id"] = company_id


def _second_company(session, slug="scope_co_b"):
    other = models.Company(
        name="Scope Co B",
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    session.add(other)
    session.flush()
    seed_chart_of_accounts_for_company(session, other.id)
    set_setting(session, "banking.company_card_enabled", True, company_id=other.id)
    return other


def _acct(session, name, *, company_id=None, currency=None):
    return posting.get_account_by_name(
        session, name, currency=currency, company_id=company_id
    )


def _cc_card(session, company_id, *, name="Company Visa"):
    ba = models.BankAccount(
        name=name,
        currency="TRY",
        company_id=company_id,
        is_active=True,
        balance=0.0,
        kind="credit_card",
    )
    session.add(ba)
    session.flush()
    return ba


def _vendor(session):
    v = models.Vendor(name="Scope Vendor", is_active=True)
    session.add(v)
    session.flush()
    return v


class TestResolvePaymentCreditAccount:
    def test_gate_and_gl_same_company_credit_card(self, db):
        session, cid = db
        other = _second_company(session)
        set_setting(session, "banking.company_card_enabled", False, company_id=cid)
        session.commit()
        _set_active(cid)
        acct_a = _acct(session, "Credit Card Payable", company_id=cid)
        acct_b = _acct(session, "Credit Card Payable", company_id=other.id)
        assert acct_a.id != acct_b.id
        resolved = posting.resolve_payment_credit_account(
            session, "Credit Card", company_id=other.id
        )
        assert resolved.id == acct_b.id

    def test_disabled_gate_blocks_even_if_other_company_enabled(self, db):
        session, cid = db
        _second_company(session)
        set_setting(session, "banking.company_card_enabled", False, company_id=cid)
        session.commit()
        with pytest.raises(ValueError) as exc:
            posting.resolve_payment_credit_account(
                session, "Credit Card", company_id=cid
            )
        assert str(exc.value) == CC_DISABLED_MSG

    def test_cash_resolves_under_explicit_company_not_ambient(self, db):
        session, cid = db
        other = _second_company(session)
        session.commit()
        cash_a = _acct(session, "Cash", company_id=cid)
        cash_b = _acct(session, "Cash", company_id=other.id)
        assert cash_a.id != cash_b.id
        _set_active(cid)
        resolved = posting.resolve_payment_credit_account(
            session, "Cash", company_id=other.id
        )
        assert resolved.id == cash_b.id

    def test_shim_single_company_unchanged_when_company_id_omitted(self, db):
        session, cid = db
        _set_active(cid)
        shim_acct = erp_app._resolve_payment_credit_account(session, "Cash")
        direct_acct = posting.resolve_payment_credit_account(
            session, "Cash", company_id=cid
        )
        assert shim_acct.id == direct_acct.id


class TestSyncCompanyCcSubledger:
    def test_subledger_uses_explicit_company_card(self, db):
        session, cid = db
        other = _second_company(session)
        card_a = _cc_card(session, cid, name="Card A")
        card_b = _cc_card(session, other.id, name="Card B")
        session.commit()
        posting.sync_company_cc_subledger(
            session,
            "Credit Card",
            company_id=other.id,
            credit_card_account_id=card_b.id,
            amount=30.0,
            txn_date=POST_DATE,
            description="scoped sync",
            reference_type="Expense",
            reference_id=501,
        )
        session.commit()
        ref = cc_subledger_stmt_ref("Expense", 501)
        btxn = session.query(models.BankTransaction).filter_by(statement_ref=ref).one()
        assert btxn.account_id == card_b.id
        assert btxn.company_id == other.id
        assert btxn.account_id != card_a.id

    def test_no_cross_tenant_card_resolution(self, db):
        session, cid = db
        other = _second_company(session)
        card_a = _cc_card(session, cid, name="Card A only")
        session.commit()
        with pytest.raises(ValueError):
            posting.sync_company_cc_subledger(
                session,
                "Credit Card",
                company_id=other.id,
                credit_card_account_id=card_a.id,
                amount=10.0,
                txn_date=POST_DATE,
                description="wrong tenant card",
                reference_type="Expense",
                reference_id=502,
            )


class TestPostingFlowsCompanyIsolation:
    def test_cc_expense_je_and_subledger_same_company(self, db):
        session, cid = db
        card = _cc_card(session, cid)
        exp = models.ExpenseRecord(
            date=POST_DATE,
            expense_type="General",
            category="Office",
            description="scoped expense",
            amount=55.0,
            payment_method="Credit Card",
            company_id=cid,
        )
        session.add(exp)
        session.commit()
        posting.post_expense(
            session,
            exp.id,
            55.0,
            POST_DATE,
            "Office",
            payment_method="Credit Card",
            company_id=cid,
        )
        session.commit()
        je = (
            session.query(models.JournalEntry)
            .filter_by(reference_type="Expense", reference_id=exp.id)
            .one()
        )
        assert je.company_id == cid
        ref = cc_subledger_stmt_ref("Expense", exp.id)
        btxn = session.query(models.BankTransaction).filter_by(statement_ref=ref).one()
        assert btxn.account_id == card.id
        assert btxn.company_id == cid

    def test_cc_purchase_je_stamped_explicit_company(self, db):
        session, cid = db
        _cc_card(session, cid)
        vendor = _vendor(session)
        pur = models.Purchase(
            date=POST_DATE,
            vendor_id=vendor.id,
            amount=90.0,
            purchase_type="Credit Card",
            gl_debit="Inventory",
            company_id=cid,
        )
        session.add(pur)
        session.commit()
        posting.post_purchase(
            session,
            pur.id,
            90.0,
            POST_DATE,
            "Credit Card",
            company_id=cid,
        )
        session.commit()
        je = (
            session.query(models.JournalEntry)
            .filter_by(reference_type="CardPurchase", reference_id=pur.id)
            .one()
        )
        assert je.company_id == cid

    def test_app_shim_post_expense_single_company_matches_direct_service(self, db):
        session, cid = db
        _cc_card(session, cid)
        exp = models.ExpenseRecord(
            date=POST_DATE,
            expense_type="General",
            category="Office",
            description="shim parity",
            amount=40.0,
            payment_method="Cash",
            company_id=cid,
        )
        session.add(exp)
        session.commit()
        je_before = session.query(func.count()).select_from(models.JournalEntry).scalar()
        erp_app.post_expense(
            session, exp.id, 40.0, POST_DATE, "Office", payment_method="Cash"
        )
        session.commit()
        je_after = session.query(func.count()).select_from(models.JournalEntry).scalar()
        assert je_after == je_before + 1
        je = (
            session.query(models.JournalEntry)
            .filter_by(reference_type="Expense", reference_id=exp.id)
            .one()
        )
        assert je.company_id == cid
