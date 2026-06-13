"""POSTING-SERVICE-01 PS-P2b-CHAR — pre-extraction characterization.

Pins current app.py behavior for `_resolve_payment_credit_account` and
`post_payable_creation` before PS-P2b extraction. No code moves in this phase.
"""
from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app
from registry.coa_seed import seed_chart_of_accounts_for_company
from registry.service import set_setting

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 4, 10)
CC_DISABLED_MSG = app._t("form.err.company_cc_disabled")
CC_GL_MISSING_MSG = app._t("form.err.company_cc_gl_missing")


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
            name="P2b Char Co",
            slug="p2b_char_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        seed_chart_of_accounts_for_company(s, co.id)
        yield s, co.id


def _set_active(company_id: int | None):
    if company_id is None:
        sys.modules["streamlit"].session_state.pop("active_company_id", None)
    else:
        sys.modules["streamlit"].session_state["active_company_id"] = company_id


def _acct(session, name, currency=None):
    return app.get_account_by_name(session, name, currency=currency)


def _entries_for(session, ref_type, ref_id):
    return (
        session.query(models.JournalEntry)
        .filter_by(reference_type=ref_type, reference_id=ref_id)
        .order_by(models.JournalEntry.id)
        .all()
    )


def _line_tuples(session, journal_entry_id):
    lines = (
        session.query(models.JournalEntryLine)
        .filter_by(journal_entry_id=journal_entry_id)
        .order_by(models.JournalEntryLine.id)
        .all()
    )
    return [(ln.account_id, ln.debit or 0.0, ln.credit or 0.0) for ln in lines]


def _make_vendor(session):
    vendor = models.Vendor(name="Vendor P2b", is_active=True)
    session.add(vendor)
    session.flush()
    return vendor


def _make_payable(session, vendor, *, payable_id_hint=None, amount=120.0):
    payable = models.Payable(
        date=POST_DATE,
        vendor_id=vendor.id,
        amount=amount,
        paid_amount=0.0,
        balance=amount,
        due_date=POST_DATE + datetime.timedelta(days=30),
        paid=False,
        description="P2b char payable",
        expense_category="Rent",
    )
    session.add(payable)
    session.flush()
    return payable


def _second_company(session, slug="other_co"):
    other = models.Company(
        name="Other Co",
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    session.add(other)
    session.flush()
    seed_chart_of_accounts_for_company(session, other.id)
    return other


# ─── _resolve_payment_credit_account ─────────────────────────────────────────


class TestResolvePaymentCreditAccount:
    def test_cash_returns_cash_account(self, session):
        db, _cid = session
        acct = app._resolve_payment_credit_account(db, "Cash")
        assert acct is not None
        assert acct.account_name == "Cash"

    def test_bank_returns_bank_account(self, session):
        db, _cid = session
        acct = app._resolve_payment_credit_account(db, "Bank")
        assert acct is not None
        assert acct.account_name == "Bank"

    def test_unknown_method_falls_back_to_cash_when_both_exist(self, session):
        db, _cid = session
        acct = app._resolve_payment_credit_account(db, "Mobile Money")
        cash = _acct(db, "Cash")
        bank = _acct(db, "Bank")
        assert acct is not None
        assert acct.id == cash.id

    def test_unknown_method_falls_back_to_bank_when_cash_missing(self, session):
        db, cid = session
        cash = _acct(db, "Cash")
        db.delete(cash)
        db.commit()
        acct = app._resolve_payment_credit_account(db, "Other")
        bank = _acct(db, "Bank")
        assert acct is not None
        assert acct.id == bank.id

    def test_credit_card_enabled_returns_cc_payable(self, session):
        db, cid = session
        set_setting(db, "banking.company_card_enabled", True, company_id=cid)
        db.commit()
        acct = app._resolve_payment_credit_account(db, "Credit Card", company_id=cid)
        cc = _acct(db, "Credit Card Payable")
        assert acct is not None
        assert acct.id == cc.id

    def test_credit_card_disabled_raises_exact_message(self, session):
        db, cid = session
        set_setting(db, "banking.company_card_enabled", False, company_id=cid)
        db.commit()
        with pytest.raises(ValueError) as exc:
            app._resolve_payment_credit_account(db, "Credit Card", company_id=cid)
        assert str(exc.value) == CC_DISABLED_MSG

    def test_credit_card_gl_missing_raises_exact_message(self, session):
        db, cid = session
        set_setting(db, "banking.company_card_enabled", True, company_id=cid)
        cc = _acct(db, "Credit Card Payable")
        db.delete(cc)
        db.commit()
        with pytest.raises(ValueError) as exc:
            app._resolve_payment_credit_account(db, "Credit Card", company_id=cid)
        assert str(exc.value) == CC_GL_MISSING_MSG

    def test_explicit_company_id_honored_for_credit_card_enablement_only(self, session):
        """company_id gates company_card_enabled; GL lookup still uses ambient company."""
        db, cid = session
        other = _second_company(db, "cc_other")
        set_setting(db, "banking.company_card_enabled", False, company_id=cid)
        set_setting(db, "banking.company_card_enabled", True, company_id=other.id)
        db.commit()
        _set_active(cid)
        ambient_cc = _acct(db, "Credit Card Payable")
        _set_active(other.id)
        other_cc = _acct(db, "Credit Card Payable")
        _set_active(cid)
        assert ambient_cc.id != other_cc.id
        acct = app._resolve_payment_credit_account(
            db, "Credit Card", company_id=other.id
        )
        assert acct.id == ambient_cc.id

    def test_ambient_company_used_when_company_id_omitted_for_credit_card(self, session):
        db, cid = session
        set_setting(db, "banking.company_card_enabled", True, company_id=cid)
        db.commit()
        _set_active(cid)
        acct = app._resolve_payment_credit_account(db, "Credit Card")
        cc = _acct(db, "Credit Card Payable")
        assert acct.id == cc.id

    def test_explicit_company_id_ignored_for_cash_uses_ambient_company(self, session):
        db, cid = session
        other = _second_company(db, "cash_other")
        db.commit()
        _set_active(cid)
        ambient_cash = _acct(db, "Cash")
        acct = app._resolve_payment_credit_account(
            db, "Cash", company_id=other.id
        )
        assert acct.id == ambient_cash.id

    def test_currency_propagates_to_suffixed_cash(self, session):
        db, _cid = session
        acct = app._resolve_payment_credit_account(db, "Cash", currency="USD")
        assert acct is not None
        assert acct.account_name == "Cash USD"

    def test_currency_propagates_to_suffixed_bank(self, session):
        db, _cid = session
        acct = app._resolve_payment_credit_account(db, "Bank", currency="USD")
        assert acct is not None
        assert acct.account_name == "Bank USD"


# ─── post_payable_creation ────────────────────────────────────────────────────


class TestPostPayableCreation:
    @pytest.mark.parametrize(
        "category,expense_name",
        [
            ("Rent", "Rent Expense"),
            ("Salary", "Salary Expense"),
            ("Utility", "Utility Expense"),
            ("Electricity", "Utility Expense"),
            ("Advertising", "Advertising Expense"),
            ("Fuel", "Fuel Expense"),
            ("Supplies", "Office Expense"),
        ],
    )
    def test_expense_account_selection_by_category(
        self, session, category, expense_name
    ):
        db, _cid = session
        vendor = _make_vendor(db)
        payable = _make_payable(db, vendor, amount=88.0)
        db.commit()

        app.post_payable_creation(
            db, payable.id, 88.0, POST_DATE, expense_category=category
        )

        entries = _entries_for(db, "PayableCreation", payable.id)
        assert len(entries) == 1
        je = entries[0]
        assert je.description == f"Payable Created (ID: {payable.id}) — {category}"
        assert je.reference_type == "PayableCreation"
        assert je.reference_id == payable.id
        expense_acct = _acct(db, expense_name)
        ap_acct = _acct(db, "Accounts Payable")
        assert _line_tuples(db, je.id) == [
            (expense_acct.id, 88.0, 0.0),
            (ap_acct.id, 0.0, 88.0),
        ]

    def test_ap_account_is_accounts_payable(self, session):
        db, _cid = session
        vendor = _make_vendor(db)
        payable = _make_payable(db, vendor)
        db.commit()
        app.post_payable_creation(db, payable.id, 50.0, POST_DATE, expense_category="Rent")
        je = _entries_for(db, "PayableCreation", payable.id)[0]
        ap = _acct(db, "Accounts Payable")
        lines = _line_tuples(db, je.id)
        assert lines[1] == (ap.id, 0.0, 50.0)

    def test_company_isolation_uses_active_company_accounts(self, session):
        db, cid = session
        other = _second_company(db, "iso_other")
        vendor = _make_vendor(db)
        payable = _make_payable(db, vendor, amount=77.0)
        db.commit()

        _set_active(cid)
        app.post_payable_creation(db, payable.id, 77.0, POST_DATE, expense_category="Rent")
        je = _entries_for(db, "PayableCreation", payable.id)[0]
        rent_a = _acct(db, "Rent Expense")
        ap_a = _acct(db, "Accounts Payable")

        _set_active(other.id)
        rent_b = _acct(db, "Rent Expense")
        ap_b = _acct(db, "Accounts Payable")

        assert rent_a.id != rent_b.id
        assert ap_a.id != ap_b.id
        assert _line_tuples(db, je.id) == [
            (rent_a.id, 77.0, 0.0),
            (ap_a.id, 0.0, 77.0),
        ]
        assert je.company_id == cid

    def test_no_journal_when_accounts_missing(self, session):
        db, _cid = session
        vendor = _make_vendor(db)
        payable = _make_payable(db, vendor)
        ap = _acct(db, "Accounts Payable")
        db.delete(ap)
        db.commit()
        before = db.query(models.JournalEntry).count()
        app.post_payable_creation(db, payable.id, 40.0, POST_DATE, expense_category="Rent")
        assert db.query(models.JournalEntry).count() == before
