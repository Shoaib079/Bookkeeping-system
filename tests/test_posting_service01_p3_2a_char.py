"""POSTING-SERVICE-01 PS-P3-2a-CHAR — void_payable commit-count characterization.

Closes the PS-P3-2 audit gap (§4.1): pins exact session.commit() counts for
void_payable before PS-P3-2a extraction. No production changes.
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
from registry.service import set_setting

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 6, 10)
VOID_REASON = "PS-P3-2a-CHAR void_payable commit pin"


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
            name="P3-2a Char Co",
            slug="p3_2a_char_co",
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


def _vendor(session):
    v = models.Vendor(name="Vendor P3-2a", is_active=True)
    session.add(v)
    session.flush()
    return v


def _unpaid_payable(db, cid, vendor):
    payable = models.Payable(
        date=POST_DATE,
        vendor_id=vendor.id,
        amount=100.0,
        paid_amount=0.0,
        balance=100.0,
        due_date=POST_DATE,
        paid=False,
        expense_category="Rent",
        company_id=cid,
    )
    db.add(payable)
    db.commit()
    return payable


class TestVoidPayableCommitBoundary:
    def test_void_unpaid_payable_without_gl_posts_two_commits(self, session):
        """Unpaid payable with no PayableCreation/PayablePayment GL."""
        db, cid = session
        payable = _unpaid_payable(db, cid, _vendor(db))

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_payable(db, payable.id, VOID_REASON) is True
            # No reversal JE commits + void session.commit + log_audit commit
            assert mock_commit.call_count == 2

        audit = (
            db.query(models.AuditLog)
            .filter_by(action="Void", entity_type="Payable", entity_id=payable.id)
            .one()
        )
        assert f"Voided Payable #{payable.id}" in audit.description

    def test_void_payable_with_payable_creation_only_posts_three_commits(self, session):
        """Unpaid payable with PayableCreation GL only."""
        db, cid = session
        payable = _unpaid_payable(db, cid, _vendor(db))
        app.post_payable_creation(
            db, payable.id, 100.0, POST_DATE, expense_category="Rent"
        )

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_payable(db, payable.id, VOID_REASON) is True
            # PayableCreation reversal JE commit + void session.commit + log_audit
            assert mock_commit.call_count == 3

    def test_void_paid_payable_with_creation_and_payment_posts_four_commits(self, session):
        """Paid payable with both PayableCreation and PayablePayment GL."""
        db, cid = session
        payable = _unpaid_payable(db, cid, _vendor(db))
        app.post_payable_creation(
            db, payable.id, 100.0, POST_DATE, expense_category="Rent"
        )
        app.post_payable_payment(
            db, payable.id, 100.0, POST_DATE, payment_method="Cash"
        )
        db.commit()

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_payable(db, payable.id, VOID_REASON) is True
            # PayableCreation + PayablePayment reversal JE commits + void + log_audit
            assert mock_commit.call_count == 4
