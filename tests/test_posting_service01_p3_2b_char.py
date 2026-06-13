"""POSTING-SERVICE-01 PS-P3-2b-CHAR — void_sale pre-extraction characterization.

Pins commit counts, GL reversals, audit boundary, and early-return guards
before PS-P3-2b extraction. No production changes.
"""
from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app
from registry.coa_seed import seed_chart_of_accounts_for_company

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 6, 10)
VOID_REASON = "PS-P3-2b-CHAR void_sale pin"


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
            name="P3-2b Char Co",
            slug="p3_2b_char_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        seed_chart_of_accounts_for_company(s, co.id)
        s.commit()
        yield s, co.id


def _make_sale(db, cid, *, sale_type="Cash", amount=100.0):
    sale = models.Sale(
        date=POST_DATE,
        invoice_number=f"INV-{sale_type}-P3-2b",
        customer_name="Test Customer",
        description="PS-P3-2b-CHAR sale",
        amount=amount,
        sale_type=sale_type,
        paid_amount=amount if sale_type != "Credit" else 0.0,
        balance=0.0 if sale_type != "Credit" else amount,
        due_date=POST_DATE + datetime.timedelta(days=30),
        status="Paid" if sale_type != "Credit" else "Outstanding",
        company_id=cid,
    )
    db.add(sale)
    db.commit()
    return sale


def _entries_for(db, ref_type, ref_id):
    return (
        db.query(models.JournalEntry)
        .filter_by(reference_type=ref_type, reference_id=ref_id)
        .order_by(models.JournalEntry.id)
        .all()
    )


def _reversals_for(db, original_entry_id):
    return (
        db.query(models.JournalEntry)
        .filter_by(reference_type="Reversal", reference_id=original_entry_id)
        .order_by(models.JournalEntry.id)
        .all()
    )


def _audit_count(db, sale_id):
    return (
        db.query(models.AuditLog)
        .filter_by(action="Void", entity_type="Sale", entity_id=sale_id)
        .count()
    )


class TestVoidSaleCash:
    def test_void_cash_sale_posts_three_commits_audit_and_void_flags(self, session):
        db, cid = session
        sale = _make_sale(db, cid, sale_type="Cash", amount=110.0)
        app.post_cash_sale(db, sale.id, 110.0, POST_DATE)

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_sale(db, sale.id, VOID_REASON) is True
            # CashSale reversal JE commit + void session.commit + log_audit commit
            assert mock_commit.call_count == 3

        db.refresh(sale)
        assert sale.is_void is True
        assert sale.status == "Void"
        assert sale.void_reason == VOID_REASON

        audit = (
            db.query(models.AuditLog)
            .filter_by(action="Void", entity_type="Sale", entity_id=sale.id)
            .one()
        )
        assert f"Voided Sale #{sale.id}" in audit.description
        assert VOID_REASON in audit.description
        assert audit.performed_by == app._DEV_USER["username"]

        cash_je = _entries_for(db, "CashSale", sale.id)[0]
        assert len(_reversals_for(db, cash_je.id)) == 1


class TestVoidSaleCreditPaid:
    def test_void_paid_credit_sale_posts_four_commits_and_reverses_both_jes(self, session):
        db, cid = session
        sale = _make_sale(db, cid, sale_type="Credit", amount=90.0)
        app.post_credit_sale(db, sale.id, 90.0, POST_DATE)
        assert app.post_receivable_payment(
            db, sale.id, 90.0, POST_DATE, payment_method="Cash"
        ) is None

        credit_je = _entries_for(db, "CreditSale", sale.id)[0]
        payment_je = _entries_for(db, "ReceivablePayment", sale.id)[0]
        assert len(_entries_for(db, "CreditSale", sale.id)) == 1
        assert len(_entries_for(db, "ReceivablePayment", sale.id)) == 1

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_sale(db, sale.id, VOID_REASON) is True
            # CreditSale + ReceivablePayment reversal JE commits + void + log_audit
            assert mock_commit.call_count == 4

        db.refresh(sale)
        assert sale.is_void is True
        assert sale.status == "Void"

        assert len(_reversals_for(db, credit_je.id)) == 1
        assert len(_reversals_for(db, payment_je.id)) == 1


class TestVoidSaleEarlyReturnGuards:
    def test_void_missing_sale_returns_false_no_commit_no_audit(self, session):
        db, _cid = session

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_sale(db, 99999, VOID_REASON) is False
            assert mock_commit.call_count == 0

        assert _audit_count(db, 99999) == 0

    def test_void_already_void_sale_returns_false_no_commit_no_audit(self, session):
        db, cid = session
        sale = _make_sale(db, cid, sale_type="Cash", amount=50.0)
        app.post_cash_sale(db, sale.id, 50.0, POST_DATE)
        sale.is_void = True
        db.commit()

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_sale(db, sale.id, VOID_REASON) is False
            assert mock_commit.call_count == 0

        assert _audit_count(db, sale.id) == 0
