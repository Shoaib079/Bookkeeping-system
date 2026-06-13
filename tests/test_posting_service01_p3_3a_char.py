"""POSTING-SERVICE-01 PS-P3-3a-CHAR — purchase cascade pre-extraction characterization.

Closes PS-P3-3 audit gaps (§7.1–§7.2) before PS-P3-3a helper extraction.
No production changes.
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
VOID_REASON = "PS-P3-3a-CHAR void_purchase commit pin"
COMPANY_REQUIRED_MSG = (
    "current_company_required(): no active_company_id in session. "
    "This call reached a company-scoped query before Gate 2 was satisfied."
)


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
            name="P3-3a Char Co",
            slug="p3_3a_char_co",
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


def _vendor(session, name="Vendor P3-3a"):
    v = models.Vendor(name=name, is_active=True)
    session.add(v)
    session.flush()
    return v


def _second_company(session, slug="p3_3a_other_co"):
    other = models.Company(
        name="P3-3a Other Co",
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    session.add(other)
    session.flush()
    seed_chart_of_accounts_for_company(session, other.id)
    set_setting(session, "banking.company_card_enabled", True, company_id=other.id)
    return other


def _credit_purchase_with_payable(db, cid, vendor):
    pur = models.Purchase(
        date=POST_DATE,
        vendor_id=vendor.id,
        amount=80.0,
        purchase_type="Credit",
        gl_debit="Inventory",
        company_id=cid,
    )
    db.add(pur)
    db.commit()
    _set_active(cid)
    app.post_purchase(
        db, pur.id, 80.0, POST_DATE, purchase_type="Credit", gl_debit="Inventory"
    )
    payable = app._create_purchase_payable(db, pur)
    db.commit()
    return pur, payable


class TestVoidPurchasePaidCommitBoundary:
    def test_void_paid_credit_purchase_posts_four_commits(self, session):
        """Paid linked payable: Purchase + PayablePayment reversals + void + audit."""
        db, cid = session
        pur, payable = _credit_purchase_with_payable(db, cid, _vendor(db))
        app._apply_payable_payment_state(payable, 80.0)
        app.post_payable_payment(
            db, payable.id, 80.0, POST_DATE, payment_method="Cash"
        )
        db.commit()

        with patch.object(db, "commit", wraps=db.commit) as mock_commit:
            assert app.void_purchase(db, pur.id, VOID_REASON) is True
            # Purchase reversal JE + PayablePayment reversal JE + void commit + log_audit
            assert mock_commit.call_count == 4

        audit = (
            db.query(models.AuditLog)
            .filter_by(action="Void", entity_type="Purchase", entity_id=pur.id)
            .one()
        )
        assert f"Voided Purchase #{pur.id}" in audit.description


class TestLinkedPurchasePayableCompanyScoping:
    def test_returns_only_active_company_linked_payable(self, session):
        db, cid_a = session
        cid_b = _second_company(db).id
        vendor = _vendor(db)

        pur_a, pay_a = _credit_purchase_with_payable(db, cid_a, vendor)
        pur_b, pay_b = _credit_purchase_with_payable(db, cid_b, vendor)

        _set_active(cid_a)
        assert app._linked_purchase_payable(db, pur_a.id) is pay_a
        assert app._linked_purchase_payable(db, pur_b.id) is None

        _set_active(cid_b)
        assert app._linked_purchase_payable(db, pur_b.id) is pay_b
        assert app._linked_purchase_payable(db, pur_a.id) is None

    def test_missing_active_company_raises_same_error_as_cq_path(self, session):
        db, cid = session
        pur, _pay = _credit_purchase_with_payable(db, cid, _vendor(db))
        _set_active(None)

        with pytest.raises(RuntimeError) as exc:
            app._linked_purchase_payable(db, pur.id)
        assert str(exc.value) == COMPANY_REQUIRED_MSG

        with pytest.raises(RuntimeError) as exc_cq:
            app.current_company_required()
        assert str(exc_cq.value) == COMPANY_REQUIRED_MSG
