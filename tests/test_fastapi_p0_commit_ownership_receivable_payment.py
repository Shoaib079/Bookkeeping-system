"""FASTAPI-P0.5d-S4 — boundary commit for receivable/customer payments."""

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
from services.commit_modes import CommitMode, POST_RECEIVABLE_PAYMENT_FAMILY
from services.unit_of_work import boundary_commit_scope
from tests.helpers.commit_parity import (
    RECEIVABLE_PAYMENT_TABLES,
    assert_persisted_state_equal,
    audit_row_tuples,
    bank_txn_row_tuples,
    dual_run_parity,
    journal_line_tuples,
    persisted_state_snapshot,
    sale_row_tuples,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 10, 12)
DUE_DATE = POST_DATE + datetime.timedelta(days=30)
SALE_AMOUNT = 200.0
PARTIAL = 80.0
FULL = 200.0
CURRENCY = "TRY"
INV_NUM = "INV-P05D-S4"
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
        name="P05d Receivable Payment Co",
        slug="p05d_receivable_payment_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    sess.add(co)
    sess.flush()
    sys.modules["streamlit"].session_state["active_company_id"] = co.id
    seed_chart_of_accounts_for_company(sess, co.id)
    sess.add(
        models.BankAccount(
            name="Main Bank",
            currency=CURRENCY,
            company_id=co.id,
            is_active=True,
            balance=5000.0,
            kind="bank",
        )
    )
    sess.commit()
    return sess, co.id


def _seed_credit_sale(sess, cid, *, amount: float = SALE_AMOUNT) -> models.Sale:
    sale = models.Sale(
        date=POST_DATE,
        invoice_number=INV_NUM,
        customer_name="Credit Customer",
        description="P05d receivable payment boundary pin",
        amount=amount,
        sale_type="Credit",
        paid_amount=0.0,
        balance=amount,
        due_date=DUE_DATE,
        status="Open",
        currency=CURRENCY,
        fx_rate=1.0,
        company_id=cid,
    )
    sess.add(sale)
    sess.commit()
    app.post_credit_sale(sess, sale.id, amount, POST_DATE)
    return sale


def _payment_audit_desc(amount: float, invoice: str = INV_NUM) -> str:
    return f"Payment {amount:,.2f} {CURRENCY} on {invoice}"


def _partial_cash_internal(sess, cid, sale):
    err = app.post_receivable_payment(
        sess, sale.id, PARTIAL, POST_DATE, "Cash", currency=CURRENCY
    )
    assert err is None
    app.log_audit(
        sess,
        "Payment",
        "Sale",
        sale.id,
        _payment_audit_desc(PARTIAL, sale.invoice_number),
    )


def _partial_cash_boundary(sess, cid, sale):
    with boundary_commit_scope(sess, POST_RECEIVABLE_PAYMENT_FAMILY):
        err = app.post_receivable_payment(
            sess, sale.id, PARTIAL, POST_DATE, "Cash", currency=CURRENCY
        )
        assert err is None
        app.log_audit(
            sess,
            "Payment",
            "Sale",
            sale.id,
            _payment_audit_desc(PARTIAL, sale.invoice_number),
        )


def _full_cash_internal(sess, cid, sale):
    err = app.post_receivable_payment(
        sess, sale.id, FULL, POST_DATE, "Cash", currency=CURRENCY
    )
    assert err is None
    app.log_audit(
        sess,
        "Payment",
        "Sale",
        sale.id,
        _payment_audit_desc(FULL, sale.invoice_number),
    )


def _full_cash_boundary(sess, cid, sale):
    with boundary_commit_scope(sess, POST_RECEIVABLE_PAYMENT_FAMILY):
        err = app.post_receivable_payment(
            sess, sale.id, FULL, POST_DATE, "Cash", currency=CURRENCY
        )
        assert err is None
        app.log_audit(
            sess,
            "Payment",
            "Sale",
            sale.id,
            _payment_audit_desc(FULL, sale.invoice_number),
        )


def _partial_bank_internal(sess, cid, sale):
    err = app.post_receivable_payment(
        sess, sale.id, PARTIAL, POST_DATE, "Bank", currency=CURRENCY
    )
    assert err is None
    bank_accounts = sess.query(models.BankAccount).filter_by(company_id=cid).all()
    app._record_named_bank_movement(
        sess,
        bank_accounts,
        "Main Bank",
        amount=PARTIAL,
        date=POST_DATE,
        description=f"Customer payment {sale.invoice_number}",
        txn_type="deposit",
    )
    sess.commit()
    app.log_audit(
        sess,
        "Payment",
        "Sale",
        sale.id,
        _payment_audit_desc(PARTIAL, sale.invoice_number),
    )


def _partial_bank_boundary(sess, cid, sale):
    bank_accounts = sess.query(models.BankAccount).filter_by(company_id=cid).all()
    with boundary_commit_scope(sess, POST_RECEIVABLE_PAYMENT_FAMILY):
        err = app.post_receivable_payment(
            sess, sale.id, PARTIAL, POST_DATE, "Bank", currency=CURRENCY
        )
        assert err is None
        app._record_named_bank_movement(
            sess,
            bank_accounts,
            "Main Bank",
            amount=PARTIAL,
            date=POST_DATE,
            description=f"Customer payment {sale.invoice_number}",
            txn_type="deposit",
        )
        app.log_audit(
            sess,
            "Payment",
            "Sale",
            sale.id,
            _payment_audit_desc(PARTIAL, sale.invoice_number),
        )


def _receivable_snapshot(sess):
    return persisted_state_snapshot(
        sess,
        tables=RECEIVABLE_PAYMENT_TABLES,
        include_sale_rows=True,
        include_bank_txn_rows=True,
    )


class TestPostReceivablePaymentDefaultInternal:
    def test_post_receivable_payment_still_two_internal_commits(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _seed_credit_sale(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            posting.post_receivable_payment(
                sess,
                sale.id,
                PARTIAL,
                POST_DATE,
                "Cash",
                company_id=cid,
            )
            assert mock_commit.call_count == 2

    def test_app_post_receivable_payment_shim_unchanged_in_internal_mode(self):
        _, Session = _make_engine_session()
        sess, _cid = _seed_company_session(Session)
        sale = _seed_credit_sale(sess, _cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            app.post_receivable_payment(sess, sale.id, PARTIAL, POST_DATE, "Cash")
            assert mock_commit.call_count == 2


class TestPostReceivablePaymentBoundaryMode:
    def test_boundary_flow_has_one_boundary_commit_cash(self):
        commit_modes.set_commit_mode_for_tests(
            POST_RECEIVABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _seed_credit_sale(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _partial_cash_boundary(sess, cid, sale)
            assert mock_commit.call_count == 1

    def test_kernel_and_audit_flush_inside_boundary_scope(self):
        commit_modes.set_commit_mode_for_tests(
            POST_RECEIVABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _seed_credit_sale(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            with patch.object(sess, "flush", wraps=sess.flush) as mock_flush:
                with boundary_commit_scope(sess, POST_RECEIVABLE_PAYMENT_FAMILY):
                    err = app.post_receivable_payment(
                        sess, sale.id, PARTIAL, POST_DATE, "Cash", currency=CURRENCY
                    )
                    assert err is None
                    app.log_audit(
                        sess,
                        "Payment",
                        "Sale",
                        sale.id,
                        _payment_audit_desc(PARTIAL, sale.invoice_number),
                    )
                assert mock_commit.call_count == 1
                assert mock_flush.call_count >= 2


class TestReceivablePaymentDualRunParity:
    @pytest.mark.parametrize(
        "internal_runner,boundary_runner,expect_bank_txn,expected_je_count",
        [
            (_partial_cash_internal, _partial_cash_boundary, False, 2),
            (_full_cash_internal, _full_cash_boundary, False, 2),
            (_partial_bank_internal, _partial_bank_boundary, True, 2),
        ],
        ids=["partial_cash", "full_cash", "partial_bank"],
    )
    def test_internal_vs_boundary_persisted_state_identical(
        self,
        internal_runner,
        boundary_runner,
        expect_bank_txn,
        expected_je_count,
    ):
        def factory():
            _, Session = _make_engine_session()
            sess, cid = _seed_company_session(Session)
            return sess, cid

        def run_internal(sess_cid):
            sess, cid = sess_cid
            commit_modes.reset_commit_modes_for_tests()
            sale = _seed_credit_sale(sess, cid)
            internal_runner(sess, cid, sale)

        def run_boundary(sess_cid):
            sess, cid = sess_cid
            commit_modes.set_commit_mode_for_tests(
                POST_RECEIVABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
            )
            sale = _seed_credit_sale(sess, cid)
            boundary_runner(sess, cid, sale)

        def factory_session_only():
            sess, cid = factory()
            return sess

        left, right = dual_run_parity(
            session_factory=factory_session_only,
            internal_runner=lambda s: run_internal(
                (s, s.query(models.Company).one().id)
            ),
            boundary_runner=lambda s: run_boundary(
                (s, s.query(models.Company).one().id)
            ),
            tables=RECEIVABLE_PAYMENT_TABLES,
            snapshot_kwargs={
                "include_sale_rows": True,
                "include_bank_txn_rows": True,
            },
        )
        assert_persisted_state_equal(left, right)
        assert left["counts"]["journal_entries"] == expected_je_count
        assert left["counts"]["audit_log"] == 1
        assert left["counts"]["sales"] == 1
        assert len(left["audit_rows"]) == 1
        if expect_bank_txn:
            assert left["counts"]["bank_transactions"] == 1
            assert left["bank_txns"][0][3] == "deposit"

    def test_gl_line_tuples_partial_cash_payment(self):
        commit_modes.set_commit_mode_for_tests(
            POST_RECEIVABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _seed_credit_sale(sess, cid)
        _partial_cash_boundary(sess, cid, sale)
        cash = posting.get_account_by_name(sess, "Cash", company_id=cid)
        ar = posting.get_account_by_name(sess, "Accounts Receivable", company_id=cid)
        je = (
            sess.query(models.JournalEntry)
            .filter_by(reference_type="ReceivablePayment", reference_id=sale.id)
            .one()
        )
        lines = [
            (ln.account_id, ln.debit or 0.0, ln.credit or 0.0)
            for ln in sess.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .order_by(models.JournalEntryLine.id)
            .all()
        ]
        assert lines == [(cash.id, PARTIAL, 0.0), (ar.id, 0.0, PARTIAL)]
        assert je.entry_date == POST_DATE

    def test_sale_state_partial_payment(self):
        commit_modes.set_commit_mode_for_tests(
            POST_RECEIVABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _seed_credit_sale(sess, cid)
        _partial_cash_boundary(sess, cid, sale)
        rows = sale_row_tuples(sess)
        assert rows[0][5] == pytest.approx(PARTIAL)
        assert rows[0][6] == pytest.approx(SALE_AMOUNT - PARTIAL)
        assert rows[0][7] == "Partial"

    def test_sale_state_full_payment(self):
        commit_modes.set_commit_mode_for_tests(
            POST_RECEIVABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _seed_credit_sale(sess, cid)
        _full_cash_boundary(sess, cid, sale)
        rows = sale_row_tuples(sess)
        assert rows[0][5] == pytest.approx(FULL)
        assert rows[0][6] == pytest.approx(0.0)
        assert rows[0][7] == "Paid"


class TestReceivablePaymentBoundaryRollback:
    def test_guard_failure_rolls_back_sale_je_and_audit(self):
        commit_modes.set_commit_mode_for_tests(
            POST_RECEIVABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _seed_credit_sale(sess, cid)
        period = models.FiscalPeriod(
            name="Closed Oct 2026",
            start_date=POST_DATE,
            end_date=POST_DATE,
            is_closed=True,
            closed_at=POST_DATE,
            company_id=cid,
        )
        sess.add(period)
        sess.commit()

        with pytest.raises(ValueError):
            with boundary_commit_scope(sess, POST_RECEIVABLE_PAYMENT_FAMILY):
                err = app.post_receivable_payment(
                    sess, sale.id, PARTIAL, POST_DATE, "Cash", currency=CURRENCY
                )
                assert err is None
                app.log_audit(
                    sess,
                    "Payment",
                    "Sale",
                    sale.id,
                    _payment_audit_desc(PARTIAL, sale.invoice_number),
                )

        assert sess.query(func.count()).select_from(models.JournalEntry).scalar() == 1
        assert sess.query(func.count()).select_from(models.AuditLog).scalar() == 0
        refreshed = sess.query(models.Sale).filter_by(id=sale.id).one()
        assert refreshed.paid_amount == 0.0
        assert refreshed.balance == pytest.approx(SALE_AMOUNT)
        assert refreshed.status == "Open"

    def test_validation_error_leaves_sale_unpaid(self):
        commit_modes.set_commit_mode_for_tests(
            POST_RECEIVABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _seed_credit_sale(sess, cid)
        err = app.post_receivable_payment(
            sess, sale.id, SALE_AMOUNT + 50.0, POST_DATE, "Cash", currency=CURRENCY
        )
        assert err == "Payment amount exceeds the remaining balance."
        refreshed = sess.query(models.Sale).filter_by(id=sale.id).one()
        assert refreshed.paid_amount == 0.0
        assert refreshed.balance == pytest.approx(SALE_AMOUNT)
        assert refreshed.status == "Open"
        assert (
            sess.query(func.count())
            .select_from(models.JournalEntry)
            .filter_by(reference_type="ReceivablePayment")
            .scalar()
            == 0
        )

    def test_mode_flag_reverts_to_internal(self):
        commit_modes.set_commit_mode_for_tests(
            POST_RECEIVABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        assert commit_modes.is_boundary_mode(POST_RECEIVABLE_PAYMENT_FAMILY)
        commit_modes.reset_commit_modes_for_tests()
        assert not commit_modes.is_boundary_mode(POST_RECEIVABLE_PAYMENT_FAMILY)


class TestReceivablePaymentAuditAtomic:
    def test_audit_row_content_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(
            POST_RECEIVABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _seed_credit_sale(sess, cid)
        _partial_cash_boundary(sess, cid, sale)
        assert audit_row_tuples(sess) == [
            (
                "Payment",
                "Sale",
                sale.id,
                _payment_audit_desc(PARTIAL, sale.invoice_number),
                PERFORMED_BY,
                cid,
            )
        ]

    def test_app_post_receivable_payment_shim_atomic_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(
            POST_RECEIVABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _seed_credit_sale(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            app.post_receivable_payment(sess, sale.id, PARTIAL, POST_DATE, "Cash")
            assert mock_commit.call_count == 1
        assert journal_line_tuples(sess)

    def test_bank_subledger_rows_match_internal(self):
        commit_modes.set_commit_mode_for_tests(
            POST_RECEIVABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _seed_credit_sale(sess, cid)
        _partial_bank_boundary(sess, cid, sale)
        snap = _receivable_snapshot(sess)
        assert snap["counts"]["bank_transactions"] == 1
        assert snap["bank_txns"][0][3] == "deposit"
        assert sale.invoice_number in snap["bank_txns"][0][4]
