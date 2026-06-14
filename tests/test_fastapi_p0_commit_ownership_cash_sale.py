"""FASTAPI-P0.5d-S1 — boundary commit for post_cash_sale only."""

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
from services import audit as audit_svc
from services import commit_modes, posting
from services.commit_modes import CommitMode, POST_CASH_SALE_FAMILY
from services.unit_of_work import boundary_commit_scope
from tests.helpers.commit_parity import (
    assert_persisted_state_equal,
    audit_row_tuples,
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

POST_DATE = datetime.date(2026, 7, 15)
AMOUNT = 250.0
INV_NUM = "INV-P05D-S1"
AUDIT_DESC = f"Sale {INV_NUM} · {AMOUNT:,.2f} TRY"
PERFORMED_BY = "parity_tester"


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
        name="P05d Cash Sale Co",
        slug="p05d_cash_sale_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    sess.add(co)
    sess.flush()
    sys.modules["streamlit"].session_state["active_company_id"] = co.id
    seed_chart_of_accounts_for_company(sess, co.id)
    sess.commit()
    return sess, co.id


def _make_sale(sess, cid):
    sale = models.Sale(
        date=POST_DATE,
        invoice_number=INV_NUM,
        customer_name="Walk-in Customer",
        description="P05d boundary pin",
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
    return sale


def _cash_sale_post_and_audit(sess, cid):
    sale = _make_sale(sess, cid)
    posting.post_cash_sale(sess, sale.id, AMOUNT, POST_DATE, company_id=cid)
    audit_svc.record_audit(
        sess,
        action=audit_svc.ACTION_CREATE,
        entity_type=audit_svc.ENTITY_SALE,
        entity_id=sale.id,
        description=AUDIT_DESC,
        performed_by=PERFORMED_BY,
        company_id=cid,
    )
    return sale


def _cash_sale_boundary_flow(sess, cid):
    sale = _make_sale(sess, cid)
    with boundary_commit_scope(sess, POST_CASH_SALE_FAMILY):
        posting.post_cash_sale(sess, sale.id, AMOUNT, POST_DATE, company_id=cid)
        audit_svc.record_audit(
            sess,
            action=audit_svc.ACTION_CREATE,
            entity_type=audit_svc.ENTITY_SALE,
            entity_id=sale.id,
            description=AUDIT_DESC,
            performed_by=PERFORMED_BY,
            company_id=cid,
        )
    return sale


class TestPostCashSaleDefaultInternal:
    def test_post_cash_sale_still_one_internal_commit(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _make_sale(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            posting.post_cash_sale(sess, sale.id, AMOUNT, POST_DATE, company_id=cid)
            assert mock_commit.call_count == 1

    def test_app_shim_unchanged_in_internal_mode(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _make_sale(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            app.post_cash_sale(sess, sale.id, AMOUNT, POST_DATE)
            assert mock_commit.call_count == 1


class TestPostCashSaleBoundaryMode:
    def test_boundary_flow_has_one_boundary_commit(self):
        commit_modes.set_commit_mode_for_tests(POST_CASH_SALE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _cash_sale_boundary_flow(sess, cid)
            # sale seed commit + single boundary commit (JE + audit atomic)
            assert mock_commit.call_count == 2

    def test_kernel_and_audit_flush_inside_boundary_scope(self):
        commit_modes.set_commit_mode_for_tests(POST_CASH_SALE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _make_sale(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            with patch.object(sess, "flush", wraps=sess.flush) as mock_flush:
                with boundary_commit_scope(sess, POST_CASH_SALE_FAMILY):
                    posting.post_cash_sale(sess, sale.id, AMOUNT, POST_DATE, company_id=cid)
                    audit_svc.record_audit(
                        sess,
                        action=audit_svc.ACTION_CREATE,
                        entity_type=audit_svc.ENTITY_SALE,
                        entity_id=sale.id,
                        description=AUDIT_DESC,
                        performed_by=PERFORMED_BY,
                        company_id=cid,
                    )
                assert mock_commit.call_count == 1
                assert mock_flush.call_count >= 2


class TestPostCashSaleDualRunParity:
    def test_internal_vs_boundary_persisted_state_identical(self):
        def factory():
            _, Session = _make_engine_session()
            sess, _cid = _seed_company_session(Session)
            return sess

        def internal_runner(sess):
            commit_modes.reset_commit_modes_for_tests()
            cid = sess.query(models.Company).one().id
            _cash_sale_post_and_audit(sess, cid)

        def boundary_runner(sess):
            commit_modes.set_commit_mode_for_tests(POST_CASH_SALE_FAMILY, CommitMode.BOUNDARY)
            cid = sess.query(models.Company).one().id
            _cash_sale_boundary_flow(sess, cid)

        left, right = dual_run_parity(
            session_factory=factory,
            internal_runner=internal_runner,
            boundary_runner=boundary_runner,
        )
        assert_persisted_state_equal(left, right)
        assert left["counts"]["journal_entries"] == 1
        assert left["counts"]["audit_log"] == 1
        assert len(left["journal_lines"]) == 2
        assert len(left["sales"]) == 1
        assert len(left["audit_rows"]) == 1

    def test_gl_line_tuples_match_account_pairs(self):
        commit_modes.set_commit_mode_for_tests(POST_CASH_SALE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        _cash_sale_boundary_flow(sess, cid)
        cash = posting.get_account_by_name(sess, "Cash", company_id=cid)
        revenue = posting.get_account_by_name(sess, "Sales Revenue", company_id=cid)
        je = (
            sess.query(models.JournalEntry)
            .filter_by(reference_type="CashSale")
            .one()
        )
        lines = [
            (ln.account_id, ln.debit or 0.0, ln.credit or 0.0)
            for ln in sess.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .order_by(models.JournalEntryLine.id)
            .all()
        ]
        assert lines == [(cash.id, AMOUNT, 0.0), (revenue.id, 0.0, AMOUNT)]
        assert je.description == f"Cash Sale (ID: {je.reference_id})"
        assert je.entry_date == POST_DATE


class TestPostCashSaleBoundaryRollback:
    def test_guard_failure_rolls_back_je_and_audit_together(self):
        commit_modes.set_commit_mode_for_tests(POST_CASH_SALE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _make_sale(sess, cid)
        period = models.FiscalPeriod(
            name="Closed Jul 2026",
            start_date=POST_DATE,
            end_date=POST_DATE,
            is_closed=True,
            closed_at=POST_DATE,
            company_id=cid,
        )
        sess.add(period)
        sess.commit()

        with pytest.raises(ValueError):
            with boundary_commit_scope(sess, POST_CASH_SALE_FAMILY):
                posting.post_cash_sale(sess, sale.id, AMOUNT, POST_DATE, company_id=cid)
                audit_svc.record_audit(
                    sess,
                    action=audit_svc.ACTION_CREATE,
                    entity_type=audit_svc.ENTITY_SALE,
                    entity_id=sale.id,
                    description=AUDIT_DESC,
                    performed_by=PERFORMED_BY,
                    company_id=cid,
                )

        assert sess.query(func.count()).select_from(models.JournalEntry).scalar() == 0
        assert sess.query(func.count()).select_from(models.AuditLog).scalar() == 0
        assert sale_row_tuples(sess) == [
            (
                sale.id,
                INV_NUM,
                "Walk-in Customer",
                AMOUNT,
                "Cash",
                AMOUNT,
                0.0,
                "Paid",
                str(POST_DATE),
                cid,
            )
        ]

    def test_mode_flag_reverts_to_internal(self):
        commit_modes.set_commit_mode_for_tests(POST_CASH_SALE_FAMILY, CommitMode.BOUNDARY)
        assert commit_modes.is_boundary_mode(POST_CASH_SALE_FAMILY)
        commit_modes.reset_commit_modes_for_tests()
        assert not commit_modes.is_boundary_mode(POST_CASH_SALE_FAMILY)


class TestPostCashSaleAuditAtomic:
    def test_audit_row_content_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(POST_CASH_SALE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = _cash_sale_boundary_flow(sess, cid)
        assert audit_row_tuples(sess) == [
            (
                audit_svc.ACTION_CREATE,
                audit_svc.ENTITY_SALE,
                sale.id,
                AUDIT_DESC,
                PERFORMED_BY,
                cid,
            )
        ]

    def test_app_create_cash_sale_path_atomic_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(POST_CASH_SALE_FAMILY, CommitMode.BOUNDARY)
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        sale = models.Sale(
            date=POST_DATE,
            invoice_number=INV_NUM,
            customer_name="Walk-in Customer",
            description="app path",
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
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            with boundary_commit_scope(sess, POST_CASH_SALE_FAMILY):
                app.post_cash_sale(sess, sale.id, AMOUNT, POST_DATE)
                app.log_audit(sess, "Create", "Sale", sale.id, AUDIT_DESC)
            assert mock_commit.call_count == 1
        assert journal_line_tuples(sess)
        assert audit_row_tuples(sess)
