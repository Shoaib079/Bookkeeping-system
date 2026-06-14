"""FASTAPI-P0.5d-S3 — boundary commit for purchases and payable payments."""

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
    CommitMode,
    POST_PAYABLE_PAYMENT_FAMILY,
    POST_PURCHASE_FAMILY,
)
from services.unit_of_work import boundary_commit_scope
from tests.helpers.commit_parity import (
    PURCHASE_PAYABLE_TABLES,
    assert_persisted_state_equal,
    audit_row_tuples,
    bank_txn_row_tuples,
    dual_run_parity,
    journal_line_tuples,
    payable_row_tuples,
    persisted_state_snapshot,
    purchase_row_tuples,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 9, 5)
DUE_DATE = POST_DATE + datetime.timedelta(days=30)
AMOUNT = 200.0
CURRENCY = "TRY"
GL_DEBIT = "Inventory"
VENDOR_NAME = "Acme Supplies"
NOTES = "P05d purchase payable boundary pin"
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
        name="P05d Purchase Payable Co",
        slug="p05d_purchase_payable_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    sess.add(co)
    sess.flush()
    sys.modules["streamlit"].session_state["active_company_id"] = co.id
    seed_chart_of_accounts_for_company(sess, co.id)
    vendor = models.Vendor(name=VENDOR_NAME, is_active=True, company_id=co.id)
    sess.add(vendor)
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
    return sess, co.id, vendor


def _purchase_draft(vendor_id: int, *, purchase_type: str = "Cash") -> models.Purchase:
    return models.Purchase(
        date=POST_DATE,
        vendor_id=vendor_id,
        amount=AMOUNT,
        description=NOTES,
        purchase_type=purchase_type,
        gl_debit=GL_DEBIT,
        currency=CURRENCY,
        fx_rate=1.0,
        native_amount=AMOUNT,
        company_id=None,
    )


def _purchase_audit_desc(record_id: int = 1, *, payable_created: bool = False) -> str:
    if payable_created:
        return f"PUR#{record_id} · {AMOUNT:,.2f} {CURRENCY} — payable created"
    return f"PUR#{record_id} · {AMOUNT:,.2f} {CURRENCY}"


def _cash_purchase_internal(sess, cid, vendor):
    record = _purchase_draft(vendor.id, purchase_type="Cash")
    sess.add(record)
    sess.commit()
    app.post_purchase(
        sess, record.id, AMOUNT, POST_DATE, "Cash", GL_DEBIT, currency=CURRENCY
    )
    app.log_audit(
        sess, "Create", "Purchase", record.id, _purchase_audit_desc(record.id)
    )
    return record


def _cash_purchase_boundary(sess, cid, vendor):
    record = _purchase_draft(vendor.id, purchase_type="Cash")
    with boundary_commit_scope(sess, POST_PURCHASE_FAMILY):
        sess.add(record)
        sess.flush()
        app.post_purchase(
            sess, record.id, AMOUNT, POST_DATE, "Cash", GL_DEBIT, currency=CURRENCY
        )
        app.log_audit(
            sess, "Create", "Purchase", record.id, _purchase_audit_desc(record.id)
        )
    return record


def _bank_purchase_internal(sess, cid, vendor):
    record = _purchase_draft(vendor.id, purchase_type="Bank")
    sess.add(record)
    sess.commit()
    app.post_purchase(
        sess, record.id, AMOUNT, POST_DATE, "Bank", GL_DEBIT, currency=CURRENCY
    )
    bank_accounts = sess.query(models.BankAccount).filter_by(company_id=cid).all()
    app._record_named_bank_movement(
        sess,
        bank_accounts,
        "Main Bank",
        amount=AMOUNT,
        date=POST_DATE,
        description=f"Purchase PUR#{record.id}",
        txn_type="withdrawal",
    )
    sess.commit()
    app.log_audit(
        sess, "Create", "Purchase", record.id, _purchase_audit_desc(record.id)
    )
    return record


def _bank_purchase_boundary(sess, cid, vendor):
    record = _purchase_draft(vendor.id, purchase_type="Bank")
    bank_accounts = sess.query(models.BankAccount).filter_by(company_id=cid).all()
    with boundary_commit_scope(sess, POST_PURCHASE_FAMILY):
        sess.add(record)
        sess.flush()
        app.post_purchase(
            sess, record.id, AMOUNT, POST_DATE, "Bank", GL_DEBIT, currency=CURRENCY
        )
        app._record_named_bank_movement(
            sess,
            bank_accounts,
            "Main Bank",
            amount=AMOUNT,
            date=POST_DATE,
            description=f"Purchase PUR#{record.id}",
            txn_type="withdrawal",
        )
        app.log_audit(
            sess, "Create", "Purchase", record.id, _purchase_audit_desc(record.id)
        )
    return record


def _credit_purchase_internal(sess, cid, vendor):
    record = _purchase_draft(vendor.id, purchase_type="Credit")
    sess.add(record)
    sess.commit()
    app.post_purchase(
        sess, record.id, AMOUNT, POST_DATE, "Credit", GL_DEBIT, currency=CURRENCY
    )
    payable = models.Payable(
        date=POST_DATE,
        vendor_id=vendor.id,
        amount=AMOUNT,
        due_date=DUE_DATE,
        paid=False,
        description=f"From Purchase #{record.id}: {NOTES}",
        expense_category=GL_DEBIT,
        purchase_id=record.id,
        company_id=cid,
    )
    sess.add(payable)
    sess.commit()
    app.log_audit(
        sess,
        "Create",
        "Purchase",
        record.id,
        _purchase_audit_desc(record.id, payable_created=True),
    )
    return record, payable


def _credit_purchase_boundary(sess, cid, vendor):
    record = _purchase_draft(vendor.id, purchase_type="Credit")
    with boundary_commit_scope(sess, POST_PURCHASE_FAMILY):
        sess.add(record)
        sess.flush()
        app.post_purchase(
            sess, record.id, AMOUNT, POST_DATE, "Credit", GL_DEBIT, currency=CURRENCY
        )
        payable = models.Payable(
            date=POST_DATE,
            vendor_id=vendor.id,
            amount=AMOUNT,
            due_date=DUE_DATE,
            paid=False,
            description=f"From Purchase #{record.id}: {NOTES}",
            expense_category=GL_DEBIT,
            purchase_id=record.id,
            company_id=cid,
        )
        sess.add(payable)
        sess.flush()
        app.log_audit(
            sess,
            "Create",
            "Purchase",
            record.id,
            _purchase_audit_desc(record.id, payable_created=True),
        )
    return record, payable


def _seed_open_payable(sess, cid, vendor):
    """Identical credit-purchase seed for payable-payment parity runs."""
    record = _purchase_draft(vendor.id, purchase_type="Credit")
    sess.add(record)
    sess.commit()
    app.post_purchase(
        sess, record.id, AMOUNT, POST_DATE, "Credit", GL_DEBIT, currency=CURRENCY
    )
    payable = models.Payable(
        date=POST_DATE,
        vendor_id=vendor.id,
        amount=AMOUNT,
        due_date=DUE_DATE,
        paid=False,
        description=f"From Purchase #{record.id}: {NOTES}",
        expense_category=GL_DEBIT,
        purchase_id=record.id,
        company_id=cid,
    )
    sess.add(payable)
    sess.commit()
    return payable


def _payable_payment_audit_desc(payable_id: int) -> str:
    return f"Payable #{payable_id} paid · {AMOUNT:,.2f} {CURRENCY}"


def _payable_payment_cash_internal(sess, payable):
    payable.payment_method = "Cash"
    app._apply_payable_payment_state(payable, AMOUNT)
    sess.commit()
    app.post_payable_payment(
        sess, payable.id, AMOUNT, POST_DATE, "Cash", currency=CURRENCY
    )
    app.log_audit(
        sess,
        "Payment",
        "Payable",
        payable.id,
        _payable_payment_audit_desc(payable.id),
    )


def _payable_payment_cash_boundary(sess, payable):
    with boundary_commit_scope(sess, POST_PAYABLE_PAYMENT_FAMILY):
        payable.payment_method = "Cash"
        app._apply_payable_payment_state(payable, AMOUNT)
        sess.flush()
        app.post_payable_payment(
            sess, payable.id, AMOUNT, POST_DATE, "Cash", currency=CURRENCY
        )
        app.log_audit(
            sess,
            "Payment",
            "Payable",
            payable.id,
            _payable_payment_audit_desc(payable.id),
        )


def _payable_payment_bank_internal(sess, cid, payable):
    payable.payment_method = "Bank"
    app._apply_payable_payment_state(payable, AMOUNT)
    sess.commit()
    app.post_payable_payment(
        sess, payable.id, AMOUNT, POST_DATE, "Bank", currency=CURRENCY
    )
    bank_accounts = sess.query(models.BankAccount).filter_by(company_id=cid).all()
    app._record_named_bank_movement(
        sess,
        bank_accounts,
        "Main Bank",
        amount=AMOUNT,
        date=POST_DATE,
        description=f"Supplier payment PAY#{payable.id}",
        txn_type="withdrawal",
    )
    sess.commit()
    app.log_audit(
        sess,
        "Payment",
        "Payable",
        payable.id,
        _payable_payment_audit_desc(payable.id),
    )


def _payable_payment_bank_boundary(sess, cid, payable):
    bank_accounts = sess.query(models.BankAccount).filter_by(company_id=cid).all()
    with boundary_commit_scope(sess, POST_PAYABLE_PAYMENT_FAMILY):
        payable.payment_method = "Bank"
        app._apply_payable_payment_state(payable, AMOUNT)
        sess.flush()
        app.post_payable_payment(
            sess, payable.id, AMOUNT, POST_DATE, "Bank", currency=CURRENCY
        )
        app._record_named_bank_movement(
            sess,
            bank_accounts,
            "Main Bank",
            amount=AMOUNT,
            date=POST_DATE,
            description=f"Supplier payment PAY#{payable.id}",
            txn_type="withdrawal",
        )
        app.log_audit(
            sess,
            "Payment",
            "Payable",
            payable.id,
            _payable_payment_audit_desc(payable.id),
        )


def _purchase_snapshot(sess, *, include_payables: bool = False):
    return persisted_state_snapshot(
        sess,
        tables=PURCHASE_PAYABLE_TABLES,
        include_sale_rows=False,
        include_purchase_rows=True,
        include_payable_rows=include_payables,
        include_bank_txn_rows=True,
    )


class TestPostPurchaseDefaultInternal:
    def test_post_purchase_still_one_internal_commit(self):
        _, Session = _make_engine_session()
        sess, cid, vendor = _seed_company_session(Session)
        record = _purchase_draft(vendor.id, purchase_type="Cash")
        sess.add(record)
        sess.commit()
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            posting.post_purchase(
                sess,
                record.id,
                AMOUNT,
                POST_DATE,
                "Cash",
                GL_DEBIT,
                company_id=cid,
            )
            assert mock_commit.call_count == 1

    def test_app_post_purchase_shim_unchanged_in_internal_mode(self):
        _, Session = _make_engine_session()
        sess, _cid, vendor = _seed_company_session(Session)
        record = _purchase_draft(vendor.id, purchase_type="Cash")
        sess.add(record)
        sess.commit()
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            app.post_purchase(sess, record.id, AMOUNT, POST_DATE, "Cash", GL_DEBIT)
            assert mock_commit.call_count == 1


class TestPostPayablePaymentDefaultInternal:
    def test_post_payable_payment_still_one_internal_commit(self):
        _, Session = _make_engine_session()
        sess, cid, vendor = _seed_company_session(Session)
        payable = _seed_open_payable(sess, cid, vendor)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            posting.post_payable_payment(
                sess,
                payable.id,
                AMOUNT,
                POST_DATE,
                "Cash",
                company_id=cid,
            )
            assert mock_commit.call_count == 1

    def test_app_post_payable_payment_shim_unchanged_in_internal_mode(self):
        _, Session = _make_engine_session()
        sess, cid, vendor = _seed_company_session(Session)
        payable = _seed_open_payable(sess, cid, vendor)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            app.post_payable_payment(sess, payable.id, AMOUNT, POST_DATE, "Cash")
            assert mock_commit.call_count == 1


class TestPostPurchaseBoundaryMode:
    def test_boundary_flow_has_one_boundary_commit_cash(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PURCHASE_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, vendor = _seed_company_session(Session)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _cash_purchase_boundary(sess, cid, vendor)
            assert mock_commit.call_count == 1

    def test_kernel_and_audit_flush_inside_purchase_boundary_scope(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PURCHASE_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, vendor = _seed_company_session(Session)
        record = _purchase_draft(vendor.id, purchase_type="Cash")
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            with patch.object(sess, "flush", wraps=sess.flush) as mock_flush:
                with boundary_commit_scope(sess, POST_PURCHASE_FAMILY):
                    sess.add(record)
                    sess.flush()
                    app.post_purchase(
                        sess,
                        record.id,
                        AMOUNT,
                        POST_DATE,
                        "Cash",
                        GL_DEBIT,
                        currency=CURRENCY,
                    )
                    app.log_audit(
                        sess, "Create", "Purchase", record.id, _purchase_audit_desc(record.id)
                    )
                assert mock_commit.call_count == 1
                assert mock_flush.call_count >= 2


class TestPostPayablePaymentBoundaryMode:
    def test_boundary_flow_has_one_boundary_commit_cash(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PAYABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, vendor = _seed_company_session(Session)
        payable = _seed_open_payable(sess, cid, vendor)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _payable_payment_cash_boundary(sess, payable)
            assert mock_commit.call_count == 1

    def test_kernel_and_audit_flush_inside_payable_payment_boundary_scope(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PAYABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, vendor = _seed_company_session(Session)
        payable = _seed_open_payable(sess, cid, vendor)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            with patch.object(sess, "flush", wraps=sess.flush) as mock_flush:
                with boundary_commit_scope(sess, POST_PAYABLE_PAYMENT_FAMILY):
                    payable.payment_method = "Cash"
                    app._apply_payable_payment_state(payable, AMOUNT)
                    sess.flush()
                    app.post_payable_payment(
                        sess,
                        payable.id,
                        AMOUNT,
                        POST_DATE,
                        "Cash",
                        currency=CURRENCY,
                    )
                    app.log_audit(
                        sess,
                        "Payment",
                        "Payable",
                        payable.id,
                        _payable_payment_audit_desc(payable.id),
                    )
                assert mock_commit.call_count == 1
                assert mock_flush.call_count >= 2


class TestPurchaseDualRunParity:
    @pytest.mark.parametrize(
        "internal_runner,boundary_runner,include_payables",
        [
            (_cash_purchase_internal, _cash_purchase_boundary, False),
            (_bank_purchase_internal, _bank_purchase_boundary, False),
            (_credit_purchase_internal, _credit_purchase_boundary, True),
        ],
        ids=["cash", "bank", "credit"],
    )
    def test_internal_vs_boundary_persisted_state_identical(
        self, internal_runner, boundary_runner, include_payables
    ):
        def factory():
            _, Session = _make_engine_session()
            sess, _cid, vendor = _seed_company_session(Session)
            return sess, vendor

        def run_internal(sess_vendor):
            sess, vendor = sess_vendor
            commit_modes.reset_commit_modes_for_tests()
            cid = sess.query(models.Company).one().id
            internal_runner(sess, cid, vendor)

        def run_boundary(sess_vendor):
            sess, vendor = sess_vendor
            commit_modes.set_commit_mode_for_tests(
                POST_PURCHASE_FAMILY, CommitMode.BOUNDARY
            )
            cid = sess.query(models.Company).one().id
            boundary_runner(sess, cid, vendor)

        def factory_session_only():
            sess, vendor = factory()
            return sess

        left, right = dual_run_parity(
            session_factory=factory_session_only,
            internal_runner=lambda s: run_internal((s, s.query(models.Vendor).one())),
            boundary_runner=lambda s: run_boundary((s, s.query(models.Vendor).one())),
            tables=PURCHASE_PAYABLE_TABLES,
            snapshot_kwargs={
                "include_sale_rows": False,
                "include_purchase_rows": True,
                "include_payable_rows": include_payables,
                "include_bank_txn_rows": True,
            },
        )
        assert_persisted_state_equal(left, right)
        assert left["counts"]["journal_entries"] == 1
        assert left["counts"]["audit_log"] == 1
        assert left["counts"]["purchases"] == 1
        assert len(left["journal_lines"]) == 2
        assert len(left["audit_rows"]) == 1
        if include_payables:
            assert left["counts"]["payables"] == 1

    def test_gl_line_tuples_cash_purchase(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PURCHASE_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, vendor = _seed_company_session(Session)
        _cash_purchase_boundary(sess, cid, vendor)
        inventory = posting.get_account_by_name(sess, "Inventory", company_id=cid)
        cash = posting.get_account_by_name(sess, "Cash", company_id=cid)
        je = sess.query(models.JournalEntry).filter_by(reference_type="CashPurchase").one()
        lines = [
            (ln.account_id, ln.debit or 0.0, ln.credit or 0.0)
            for ln in sess.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .order_by(models.JournalEntryLine.id)
            .all()
        ]
        assert lines == [(inventory.id, AMOUNT, 0.0), (cash.id, 0.0, AMOUNT)]
        assert je.description == f"Cash Purchase (ID: {je.reference_id})"
        assert je.entry_date == POST_DATE

    def test_bank_subledger_rows_match_internal(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PURCHASE_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, vendor = _seed_company_session(Session)
        record = _bank_purchase_boundary(sess, cid, vendor)
        snap = _purchase_snapshot(sess)
        assert snap["counts"]["bank_transactions"] == 1
        assert snap["bank_txns"][0][3] == "withdrawal"
        assert f"PUR#{record.id}" in snap["bank_txns"][0][4]


class TestPayablePaymentDualRunParity:
    @pytest.mark.parametrize(
        "internal_runner,boundary_runner,expect_bank_txn",
        [
            (_payable_payment_cash_internal, _payable_payment_cash_boundary, False),
            (_payable_payment_bank_internal, _payable_payment_bank_boundary, True),
        ],
        ids=["cash", "bank"],
    )
    def test_internal_vs_boundary_persisted_state_identical(
        self, internal_runner, boundary_runner, expect_bank_txn
    ):
        def factory():
            _, Session = _make_engine_session()
            sess, cid, vendor = _seed_company_session(Session)
            return sess, cid, vendor

        def run_internal(sess_cid_vendor):
            sess, cid, vendor = sess_cid_vendor
            commit_modes.reset_commit_modes_for_tests()
            payable = _seed_open_payable(sess, cid, vendor)
            if expect_bank_txn:
                internal_runner(sess, cid, payable)
            else:
                internal_runner(sess, payable)

        def run_boundary(sess_cid_vendor):
            sess, cid, vendor = sess_cid_vendor
            commit_modes.set_commit_mode_for_tests(
                POST_PAYABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
            )
            payable = _seed_open_payable(sess, cid, vendor)
            if expect_bank_txn:
                boundary_runner(sess, cid, payable)
            else:
                boundary_runner(sess, payable)

        def factory_session_only():
            sess, cid, vendor = factory()
            return sess

        left, right = dual_run_parity(
            session_factory=factory_session_only,
            internal_runner=lambda s: run_internal(
                (s, s.query(models.Company).one().id, s.query(models.Vendor).one())
            ),
            boundary_runner=lambda s: run_boundary(
                (s, s.query(models.Company).one().id, s.query(models.Vendor).one())
            ),
            tables=PURCHASE_PAYABLE_TABLES,
            snapshot_kwargs={
                "include_sale_rows": False,
                "include_purchase_rows": True,
                "include_payable_rows": True,
                "include_bank_txn_rows": True,
            },
        )
        assert_persisted_state_equal(left, right)
        assert left["counts"]["journal_entries"] == 2
        assert left["counts"]["audit_log"] == 1
        assert left["counts"]["payables"] == 1
        assert len(left["journal_lines"]) == 4
        payable_rows = left["payables"]
        assert payable_rows[0][3] == AMOUNT
        assert payable_rows[0][4] == 0.0
        assert payable_rows[0][5] is True
        if expect_bank_txn:
            assert left["counts"]["bank_transactions"] == 1


class TestPurchasePayableBoundaryRollback:
    def test_guard_failure_rolls_back_purchase_payable_je_and_audit(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PURCHASE_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, vendor = _seed_company_session(Session)
        period = models.FiscalPeriod(
            name="Closed Sep 2026",
            start_date=POST_DATE,
            end_date=POST_DATE,
            is_closed=True,
            closed_at=POST_DATE,
            company_id=cid,
        )
        sess.add(period)
        sess.commit()

        record = _purchase_draft(vendor.id, purchase_type="Credit")
        with pytest.raises(ValueError):
            with boundary_commit_scope(sess, POST_PURCHASE_FAMILY):
                sess.add(record)
                sess.flush()
                app.post_purchase(
                    sess,
                    record.id,
                    AMOUNT,
                    POST_DATE,
                    "Credit",
                    GL_DEBIT,
                    currency=CURRENCY,
                )
                payable = models.Payable(
                    date=POST_DATE,
                    vendor_id=vendor.id,
                    amount=AMOUNT,
                    due_date=DUE_DATE,
                    paid=False,
                    description=f"From Purchase #{record.id}: {NOTES}",
                    expense_category=GL_DEBIT,
                    purchase_id=record.id,
                    company_id=cid,
                )
                sess.add(payable)
                sess.flush()
                app.log_audit(
                    sess,
                    "Create",
                    "Purchase",
                    record.id,
                    _purchase_audit_desc(record.id, payable_created=True),
                )

        assert sess.query(func.count()).select_from(models.JournalEntry).scalar() == 0
        assert sess.query(func.count()).select_from(models.AuditLog).scalar() == 0
        assert sess.query(func.count()).select_from(models.Purchase).scalar() == 0
        assert sess.query(func.count()).select_from(models.Payable).scalar() == 0

    def test_payable_payment_failure_rolls_back_state_je_and_audit(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PAYABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, vendor = _seed_company_session(Session)
        payable = _seed_open_payable(sess, cid, vendor)
        period = models.FiscalPeriod(
            name="Closed Sep 2026 payment",
            start_date=POST_DATE,
            end_date=POST_DATE,
            is_closed=True,
            closed_at=POST_DATE,
            company_id=cid,
        )
        sess.add(period)
        sess.commit()

        with pytest.raises(ValueError):
            with boundary_commit_scope(sess, POST_PAYABLE_PAYMENT_FAMILY):
                payable.payment_method = "Cash"
                app._apply_payable_payment_state(payable, AMOUNT)
                sess.flush()
                app.post_payable_payment(
                    sess,
                    payable.id,
                    AMOUNT,
                    POST_DATE,
                    "Cash",
                    currency=CURRENCY,
                )
                app.log_audit(
                    sess,
                    "Payment",
                    "Payable",
                    payable.id,
                    _payable_payment_audit_desc(payable.id),
                )

        assert sess.query(func.count()).select_from(models.JournalEntry).scalar() == 1
        assert sess.query(func.count()).select_from(models.AuditLog).scalar() == 0
        refreshed = sess.query(models.Payable).filter_by(id=payable.id).one()
        assert refreshed.paid_amount == 0.0
        assert refreshed.balance in (None, AMOUNT)
        assert refreshed.paid is False
        assert refreshed.payment_method is None

    def test_mode_flags_revert_to_internal(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PURCHASE_FAMILY, CommitMode.BOUNDARY
        )
        commit_modes.set_commit_mode_for_tests(
            POST_PAYABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        assert commit_modes.is_boundary_mode(POST_PURCHASE_FAMILY)
        assert commit_modes.is_boundary_mode(POST_PAYABLE_PAYMENT_FAMILY)
        commit_modes.reset_commit_modes_for_tests()
        assert not commit_modes.is_boundary_mode(POST_PURCHASE_FAMILY)
        assert not commit_modes.is_boundary_mode(POST_PAYABLE_PAYMENT_FAMILY)


class TestPurchasePayableAuditAtomic:
    def test_purchase_audit_row_content_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PURCHASE_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, vendor = _seed_company_session(Session)
        record = _cash_purchase_boundary(sess, cid, vendor)
        assert audit_row_tuples(sess) == [
            (
                "Create",
                "Purchase",
                record.id,
                _purchase_audit_desc(record.id),
                PERFORMED_BY,
                cid,
            )
        ]

    def test_payable_payment_audit_row_content_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PAYABLE_PAYMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, vendor = _seed_company_session(Session)
        payable = _seed_open_payable(sess, cid, vendor)
        _payable_payment_cash_boundary(sess, payable)
        assert audit_row_tuples(sess) == [
            (
                "Payment",
                "Payable",
                payable.id,
                _payable_payment_audit_desc(payable.id),
                PERFORMED_BY,
                cid,
            )
        ]

    def test_app_post_purchase_shim_atomic_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PURCHASE_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, _cid, vendor = _seed_company_session(Session)
        record = _purchase_draft(vendor.id, purchase_type="Cash")
        sess.add(record)
        sess.commit()
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            app.post_purchase(sess, record.id, AMOUNT, POST_DATE, "Cash", GL_DEBIT)
            assert mock_commit.call_count == 1
        assert journal_line_tuples(sess)
