"""FASTAPI-P0.5d-S8 — boundary commit for void cascades."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event as sa_event, func
from sqlalchemy.orm import sessionmaker

import app
import models
from reconciliation.company_card import apply_account_balance_delta
from services.money import persist_money
from db import Base
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import commit_modes, posting
from services.commit_modes import VOID_CASCADE_FAMILY, CommitMode
from services.unit_of_work import boundary_commit_scope
from tests.helpers.commit_parity import (
    VOID_CASCADE_TABLES,
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

POST_DATE = datetime.date(2026, 8, 12)
AMOUNT = 100.0
VOID_REASON = "P05d-S8 void pin"
VOIDER_ID = 7
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
        name="P05d Void Co",
        slug="p05d_void_co",
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
            currency="TRY",
            company_id=co.id,
            is_active=True,
            balance=10000.0,
            kind="bank",
        )
    )
    sess.commit()
    return sess, co.id


def _vendor(sess):
    v = models.Vendor(name="Supplier A", is_active=True)
    sess.add(v)
    sess.flush()
    return v


def _expense_posted(sess, cid):
    exp = models.ExpenseRecord(
        date=POST_DATE,
        expense_type="Expense",
        category="Office Expense",
        amount=AMOUNT,
        payment_method="Cash",
        company_id=cid,
    )
    sess.add(exp)
    sess.commit()
    app.post_expense(sess, exp.id, AMOUNT, POST_DATE, "Office Expense", payment_method="Cash")
    return exp


def _cash_sale_posted(sess, cid):
    sale = models.Sale(
        date=POST_DATE,
        invoice_number="INV-VOID",
        customer_name="Walk-in",
        amount=AMOUNT,
        sale_type="Cash",
        paid_amount=AMOUNT,
        balance=0.0,
        due_date=POST_DATE,
        status="Paid",
        company_id=cid,
    )
    sess.add(sale)
    sess.commit()
    app.post_cash_sale(sess, sale.id, AMOUNT, POST_DATE)
    return sale


def _purchase_unpaid(sess, cid):
    vendor = _vendor(sess)
    pur = models.Purchase(
        date=POST_DATE,
        vendor_id=vendor.id,
        amount=AMOUNT,
        purchase_type="Cash",
        gl_debit="Inventory",
        company_id=cid,
    )
    sess.add(pur)
    sess.commit()
    app.post_purchase(sess, pur.id, AMOUNT, POST_DATE, purchase_type="Cash", gl_debit="Inventory")
    return pur


def _purchase_paid_credit(sess, cid):
    vendor = _vendor(sess)
    pur = models.Purchase(
        date=POST_DATE,
        vendor_id=vendor.id,
        amount=AMOUNT,
        purchase_type="Credit",
        gl_debit="Inventory",
        company_id=cid,
    )
    sess.add(pur)
    sess.commit()
    app.post_purchase(sess, pur.id, AMOUNT, POST_DATE, purchase_type="Credit", gl_debit="Inventory")
    payable = app._create_purchase_payable(sess, pur)
    sess.commit()
    app._apply_payable_payment_state(payable, AMOUNT)
    app.post_payable_payment(sess, payable.id, AMOUNT, POST_DATE, payment_method="Cash")
    sess.commit()
    return pur, payable


def _bank_deposit_posted(sess, cid):
    bank = sess.query(models.BankAccount).filter_by(company_id=cid).one()
    txn = models.BankTransaction(
        account_id=bank.id,
        date=POST_DATE,
        amount=persist_money(AMOUNT),
        type="deposit",
        description="Manual deposit",
        company_id=cid,
    )
    sess.add(txn)
    apply_account_balance_delta(bank, "deposit", AMOUNT)
    sess.commit()
    app.post_bank_transaction(sess, txn.id, AMOUNT, POST_DATE, "deposit")
    sess.commit()
    return txn


def _partner_movement_posted(sess, cid):
    partner_id, err = app.create_partner(sess, "Alice", 100.0)
    assert err == ""
    bank = sess.query(models.BankAccount).filter_by(company_id=cid).one()
    mid, err = app.post_partner_movement(
        sess,
        partner_id,
        "CapitalContribution",
        AMOUNT,
        POST_DATE,
        bank_account_id=bank.id,
        created_by_id=VOIDER_ID,
    )
    assert err == ""
    return mid


def _void_expense_internal(sess, exp_id):
    with app._void_boundary_scope(sess):
        assert app.void_expense(sess, exp_id, VOID_REASON) is True


def _void_expense_boundary(sess, exp_id):
    commit_modes.set_commit_mode_for_tests(VOID_CASCADE_FAMILY, CommitMode.BOUNDARY)
    _void_expense_internal(sess, exp_id)


def _void_sale_internal(sess, sale_id):
    with app._void_boundary_scope(sess):
        assert app.void_sale(sess, sale_id, VOID_REASON) is True


def _void_sale_boundary(sess, sale_id):
    commit_modes.set_commit_mode_for_tests(VOID_CASCADE_FAMILY, CommitMode.BOUNDARY)
    _void_sale_internal(sess, sale_id)


class TestDefaultInternalCommitCounts:
    def test_void_expense_kernel_two_commits(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        exp = _expense_posted(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            posting.void_expense(sess, exp.id, VOID_REASON, company_id=cid)
            assert mock_commit.call_count == 2

    def test_void_expense_app_shim_three_commits(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        exp = _expense_posted(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _void_expense_internal(sess, exp.id)
            assert mock_commit.call_count == 3

    def test_void_purchase_unpaid_app_shim_three_commits(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        pur = _purchase_unpaid(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            with app._void_boundary_scope(sess):
                assert app.void_purchase(sess, pur.id, VOID_REASON) is True
            assert mock_commit.call_count == 3


class TestVoidBoundaryMode:
    def test_void_expense_boundary_one_commit(self):
        commit_modes.set_commit_mode_for_tests(VOID_CASCADE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        exp = _expense_posted(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _void_expense_boundary(sess, exp.id)
            assert mock_commit.call_count == 1

    def test_void_sale_boundary_one_commit(self):
        commit_modes.set_commit_mode_for_tests(VOID_CASCADE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _cash_sale_posted(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _void_sale_boundary(sess, sale.id)
            assert mock_commit.call_count == 1


class TestVoidDualRunParity:
    @pytest.mark.parametrize(
        "flow_kind",
        ["expense", "sale", "purchase_unpaid", "purchase_paid", "bank_txn", "partner_movement"],
    )
    def test_internal_vs_boundary_persisted_state_identical(self, flow_kind):
        snap_extra = {
            "include_sale_rows": False,
            "include_bank_txn_rows": flow_kind in ("bank_txn", "partner_movement"),
            "include_sale_void_rows": flow_kind == "sale",
            "include_expense_void_rows": flow_kind == "expense",
            "include_purchase_void_rows": flow_kind.startswith("purchase"),
            "include_payable_void_rows": flow_kind == "purchase_paid",
            "include_partner_movement_rows": flow_kind == "partner_movement",
        }

        def factory():
            _, Session = _make_engine_session()
            sess, cid = _seed_company_session(Session)
            return sess, cid

        def _setup(sess, cid):
            if flow_kind == "expense":
                return _expense_posted(sess, cid).id
            if flow_kind == "sale":
                return _cash_sale_posted(sess, cid).id
            if flow_kind == "purchase_unpaid":
                return _purchase_unpaid(sess, cid).id
            if flow_kind == "purchase_paid":
                pur, _pay = _purchase_paid_credit(sess, cid)
                return pur.id
            if flow_kind == "bank_txn":
                return _bank_deposit_posted(sess, cid).id
            return _partner_movement_posted(sess, cid)

        def run_internal(sess_cid):
            sess, cid = sess_cid
            commit_modes.reset_commit_modes_for_tests()
            entity_id = _setup(sess, cid)
            if flow_kind == "expense":
                _void_expense_internal(sess, entity_id)
            elif flow_kind == "sale":
                _void_sale_internal(sess, entity_id)
            elif flow_kind.startswith("purchase"):
                with app._void_boundary_scope(sess):
                    assert app.void_purchase(sess, entity_id, VOID_REASON) is True
            elif flow_kind == "bank_txn":
                with app._void_boundary_scope(sess):
                    assert app.void_bank_transaction(sess, entity_id, VOID_REASON) is True
            else:
                with app._void_boundary_scope(sess):
                    assert app.void_partner_movement(sess, entity_id, VOIDER_ID, VOID_REASON) == ""

        def run_boundary(sess_cid):
            commit_modes.set_commit_mode_for_tests(VOID_CASCADE_FAMILY, CommitMode.BOUNDARY)
            sess, cid = sess_cid
            entity_id = _setup(sess, cid)
            if flow_kind == "expense":
                _void_expense_boundary(sess, entity_id)
            elif flow_kind == "sale":
                _void_sale_boundary(sess, entity_id)
            elif flow_kind.startswith("purchase"):
                with app._void_boundary_scope(sess):
                    assert app.void_purchase(sess, entity_id, VOID_REASON) is True
            elif flow_kind == "bank_txn":
                with app._void_boundary_scope(sess):
                    assert app.void_bank_transaction(sess, entity_id, VOID_REASON) is True
            else:
                with app._void_boundary_scope(sess):
                    assert app.void_partner_movement(sess, entity_id, VOIDER_ID, VOID_REASON) == ""

        left, right = dual_run_parity(
            session_factory=lambda: factory()[0],
            internal_runner=lambda s: run_internal((s, s.query(models.Company).one().id)),
            boundary_runner=lambda s: run_boundary((s, s.query(models.Company).one().id)),
            tables=VOID_CASCADE_TABLES,
            snapshot_kwargs=snap_extra,
        )
        assert_persisted_state_equal(left, right)


class TestVoidBoundaryRollback:
    def test_expense_void_failure_leaves_record_unvoided(self):
        commit_modes.set_commit_mode_for_tests(VOID_CASCADE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        exp = _expense_posted(sess, cid)
        today = datetime.date.today()
        blocker = models.FiscalPeriod(
            name="Closed today",
            start_date=today,
            end_date=today,
            is_closed=True,
            closed_at=today,
            company_id=cid,
        )
        sess.add(blocker)
        sess.commit()

        with pytest.raises(ValueError):
            with boundary_commit_scope(sess, VOID_CASCADE_FAMILY):
                posting.void_expense(sess, exp.id, VOID_REASON, company_id=cid)
                app.log_audit(
                    sess,
                    "Void",
                    "ExpenseRecord",
                    exp.id,
                    f"Voided Expense #{exp.id}: {VOID_REASON}",
                )

        refreshed = sess.get(models.ExpenseRecord, exp.id)
        assert refreshed.is_void is False
        assert (
            sess.query(func.count())
            .select_from(models.JournalEntry)
            .filter_by(reference_type="Reversal")
            .scalar()
            == 0
        )
        assert (
            sess.query(func.count())
            .select_from(models.AuditLog)
            .filter_by(entity_type="ExpenseRecord", entity_id=exp.id)
            .scalar()
            == 0
        )


class TestVoidReturnContracts:
    def test_void_expense_false_when_already_voided(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        exp = _expense_posted(sess, cid)
        assert app.void_expense(sess, exp.id, VOID_REASON) is True
        assert app.void_expense(sess, exp.id, "Again") is False

    def test_void_partner_movement_requires_reason(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        mid = _partner_movement_posted(sess, cid)
        err = app.void_partner_movement(sess, mid, VOIDER_ID, "   ")
        assert err == "Void reason is required."


class TestVoidAuditAtomic:
    def test_expense_void_audit_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(VOID_CASCADE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        exp = _expense_posted(sess, cid)
        _void_expense_boundary(sess, exp.id)
        audits = [r for r in audit_row_tuples(sess) if r[1] == "ExpenseRecord"]
        assert audits == [
            (
                "Void",
                "ExpenseRecord",
                exp.id,
                f"Voided Expense #{exp.id}: {VOID_REASON}",
                PERFORMED_BY,
                cid,
            )
        ]

    def test_sale_reversal_je_lines_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(VOID_CASCADE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _cash_sale_posted(sess, cid)
        orig_je = (
            sess.query(models.JournalEntry)
            .filter_by(reference_type="CashSale", reference_id=sale.id)
            .one()
        )
        orig_lines = journal_line_tuples(sess)
        _void_sale_boundary(sess, sale.id)
        reversal = (
            sess.query(models.JournalEntry)
            .filter_by(reference_type="Reversal", reference_id=orig_je.id)
            .one()
        )
        rev_lines = [
            t for t in journal_line_tuples(sess) if t[0] == reversal.id
        ]
        orig_only = [t for t in orig_lines if t[0] == orig_je.id]
        assert len(rev_lines) == len(orig_only)
        for (__, acct, debit, credit), (_, acct2, debit2, credit2) in zip(
            sorted(orig_only), sorted(rev_lines)
        ):
            assert acct == acct2
            assert abs(debit - credit2) < 0.01
            assert abs(credit - debit2) < 0.01
