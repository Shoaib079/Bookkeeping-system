"""FASTAPI-P0.5d-S7 — boundary commit for reconciliation match/post."""

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
from registry.coa_seed import ensure_accounts_for_company, seed_chart_of_accounts_for_company
from registry.service import set_setting
from reconciliation.match_post import post_bank_charge_outflow, post_generic_deposit
from services import commit_modes
from services.commit_modes import RECONCILIATION_FAMILY, CommitMode
from services.unit_of_work import boundary_commit_scope
from tests.helpers.commit_parity import (
    RECONCILIATION_TABLES,
    assert_persisted_state_equal,
    audit_row_tuples,
    bank_account_row_tuples,
    bank_statement_row_tuples,
    bank_txn_row_tuples,
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

DEPOSIT_AMT = 300.0
FEE_AMT = 15.0
CREDIT_ACCT = "Sales Revenue"
AUDIT_DEPOSIT_DESC = f"Deposit · {DEPOSIT_AMT:,.2f} · CR {CREDIT_ACCT}"
AUDIT_FEE_DESC = f"Bank charge · {FEE_AMT:,.2f}"
PERFORMED_BY = "admin"
USER_ID = 7


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
        name="P05d Recon Co",
        slug="p05d_recon_co",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    sess.add(co)
    sess.flush()
    sys.modules["streamlit"].session_state["active_company_id"] = co.id
    seed_chart_of_accounts_for_company(sess, co.id)
    ensure_accounts_for_company(sess, co.id)
    set_setting(sess, "banking.bank_charges_enabled", True, company_id=co.id)
    ba = models.BankAccount(
        name="Main TRY",
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=0.0,
    )
    sess.add(ba)
    sess.commit()
    return sess, co.id, ba.id


def _stmt_row(sess, cid, bank_account_id, *, credit=True, amount=DEPOSIT_AMT):
    imp = models.BankStatementImport(
        company_id=cid,
        bank_account_id=bank_account_id,
        file_name="stmt.csv",
        file_hash="p05d-recon-hash",
        file_size=10,
        file_path="/tmp/stmt.csv",
        status="staging",
        import_date=datetime.date.today(),
        row_count=1,
        valid_count=1,
        flagged_count=0,
        error_count=0,
        currency="TRY",
        created_at=datetime.datetime.now(),
    )
    sess.add(imp)
    sess.flush()
    row = models.BankStatementRow(
        bank_statement_import_id=imp.id,
        status="staging",
        import_row_index=1,
        date=datetime.date.today(),
        description="Deposit test" if credit else "Bank commission fee",
        debit_amount=None if credit else amount,
        credit_amount=amount if credit else None,
        amount=amount,
        currency="TRY",
        original_amount=amount,
        parsed_successfully=True,
        created_at=datetime.datetime.now(),
    )
    sess.add(row)
    sess.flush()
    return row, imp


def _deposit_internal(sess, row_id, cid):
    with app._recon_boundary_scope(sess):
        post_generic_deposit(
            sess,
            row_id=row_id,
            company_id=cid,
            credit_account_name=CREDIT_ACCT,
            user_id=USER_ID,
        )
        app.log_audit(
            sess,
            "Post",
            "BankStatementRow",
            row_id,
            AUDIT_DEPOSIT_DESC,
        )


def _deposit_boundary(sess, row_id, cid):
    commit_modes.set_commit_mode_for_tests(RECONCILIATION_FAMILY, CommitMode.BOUNDARY)
    _deposit_internal(sess, row_id, cid)


def _fee_internal(sess, row_id, cid):
    with app._recon_boundary_scope(sess):
        post_bank_charge_outflow(
            sess,
            row_id=row_id,
            company_id=cid,
            user_id=USER_ID,
        )
        app.log_audit(
            sess,
            "Post",
            "BankStatementRow",
            row_id,
            AUDIT_FEE_DESC,
        )


def _fee_boundary(sess, row_id, cid):
    commit_modes.set_commit_mode_for_tests(RECONCILIATION_FAMILY, CommitMode.BOUNDARY)
    _fee_internal(sess, row_id, cid)


class TestDefaultInternalCommitCounts:
    def test_generic_deposit_kernel_two_commits(self):
        _, Session = _make_engine_session()
        sess, cid, ba_id = _seed_company_session(Session)
        row, _imp = _stmt_row(sess, cid, ba_id, credit=True)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            post_generic_deposit(
                sess,
                row_id=row.id,
                company_id=cid,
                credit_account_name=CREDIT_ACCT,
                user_id=USER_ID,
            )
            assert mock_commit.call_count == 2

    def test_generic_deposit_app_shim_three_commits(self):
        _, Session = _make_engine_session()
        sess, cid, ba_id = _seed_company_session(Session)
        row, _imp = _stmt_row(sess, cid, ba_id, credit=True)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _deposit_internal(sess, row.id, cid)
            assert mock_commit.call_count == 3

    def test_bank_charge_kernel_two_commits(self):
        _, Session = _make_engine_session()
        sess, cid, ba_id = _seed_company_session(Session)
        row, _imp = _stmt_row(sess, cid, ba_id, credit=False, amount=FEE_AMT)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            post_bank_charge_outflow(
                sess,
                row_id=row.id,
                company_id=cid,
                user_id=USER_ID,
            )
            assert mock_commit.call_count == 2


class TestReconciliationBoundaryMode:
    def test_generic_deposit_boundary_one_commit(self):
        commit_modes.set_commit_mode_for_tests(
            RECONCILIATION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, ba_id = _seed_company_session(Session)
        row, _imp = _stmt_row(sess, cid, ba_id, credit=True)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _deposit_boundary(sess, row.id, cid)
            assert mock_commit.call_count == 1

    def test_bank_charge_boundary_one_commit(self):
        commit_modes.set_commit_mode_for_tests(
            RECONCILIATION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, ba_id = _seed_company_session(Session)
        row, _imp = _stmt_row(sess, cid, ba_id, credit=False, amount=FEE_AMT)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _fee_boundary(sess, row.id, cid)
            assert mock_commit.call_count == 1


class TestReconciliationDualRunParity:
    @pytest.mark.parametrize(
        "flow_kind",
        ["generic_deposit", "bank_charge"],
    )
    def test_internal_vs_boundary_persisted_state_identical(self, flow_kind):
        snap_extra = {
            "include_sale_rows": False,
            "include_bank_txn_rows": True,
            "include_bank_statement_rows": True,
            "include_bank_account_rows": True,
        }

        def factory():
            _, Session = _make_engine_session()
            sess, cid, ba_id = _seed_company_session(Session)
            return sess, cid, ba_id

        def run_internal(sess_cid_ba):
            sess, cid, ba_id = sess_cid_ba
            commit_modes.reset_commit_modes_for_tests()
            if flow_kind == "generic_deposit":
                row, _imp = _stmt_row(sess, cid, ba_id, credit=True)
                _deposit_internal(sess, row.id, cid)
            else:
                row, _imp = _stmt_row(
                    sess, cid, ba_id, credit=False, amount=FEE_AMT
                )
                _fee_internal(sess, row.id, cid)

        def run_boundary(sess_cid_ba):
            sess, cid, ba_id = sess_cid_ba
            if flow_kind == "generic_deposit":
                row, _imp = _stmt_row(sess, cid, ba_id, credit=True)
                _deposit_boundary(sess, row.id, cid)
            else:
                row, _imp = _stmt_row(
                    sess, cid, ba_id, credit=False, amount=FEE_AMT
                )
                _fee_boundary(sess, row.id, cid)

        def factory_session_only():
            sess, _cid, _ba_id = factory()
            return sess

        def run_internal_session(sess):
            cid = sys.modules["streamlit"].session_state["active_company_id"]
            ba_id = sess.query(models.BankAccount).filter_by(company_id=cid).one().id
            run_internal((sess, cid, ba_id))

        def run_boundary_session(sess):
            cid = sys.modules["streamlit"].session_state["active_company_id"]
            ba_id = sess.query(models.BankAccount).filter_by(company_id=cid).one().id
            run_boundary((sess, cid, ba_id))

        left, right = dual_run_parity(
            session_factory=factory_session_only,
            internal_runner=run_internal_session,
            boundary_runner=run_boundary_session,
            tables=RECONCILIATION_TABLES,
            snapshot_kwargs=snap_extra,
        )
        assert_persisted_state_equal(left, right)


class TestReconciliationBoundaryRollback:
    def test_posting_failure_rolls_back_row_btxn_je_and_audit(self):
        commit_modes.set_commit_mode_for_tests(
            RECONCILIATION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, ba_id = _seed_company_session(Session)
        row, _imp = _stmt_row(sess, cid, ba_id, credit=True)
        today = datetime.date.today()
        blocker = models.FiscalPeriod(
            name="Closed today blocker",
            start_date=today,
            end_date=today,
            is_closed=True,
            closed_at=today,
            company_id=cid,
        )
        sess.add(blocker)
        sess.commit()

        with pytest.raises(ValueError):
            with boundary_commit_scope(sess, RECONCILIATION_FAMILY):
                post_generic_deposit(
                    sess,
                    row_id=row.id,
                    company_id=cid,
                    credit_account_name=CREDIT_ACCT,
                    user_id=USER_ID,
                )
                app.log_audit(
                    sess,
                    "Post",
                    "BankStatementRow",
                    row.id,
                    AUDIT_DEPOSIT_DESC,
                )

        refreshed = sess.get(models.BankStatementRow, row.id)
        assert refreshed.status == "staging"
        assert refreshed.posted_journal_entry_id is None
        assert refreshed.bank_transaction_id is None
        assert (
            sess.query(func.count())
            .select_from(models.JournalEntry)
            .filter_by(reference_type="BankStmtDeposit")
            .scalar()
            == 0
        )
        assert (
            sess.query(func.count()).select_from(models.BankTransaction).scalar() == 0
        )
        assert (
            sess.query(func.count())
            .select_from(models.AuditLog)
            .filter_by(entity_type="BankStatementRow")
            .scalar()
            == 0
        )

    def test_mode_flag_reverts_to_internal(self):
        commit_modes.set_commit_mode_for_tests(
            RECONCILIATION_FAMILY, CommitMode.BOUNDARY
        )
        commit_modes.reset_commit_modes_for_tests()
        assert not commit_modes.is_boundary_mode(RECONCILIATION_FAMILY)


class TestReconciliationAuditAtomic:
    def test_deposit_audit_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(
            RECONCILIATION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid, ba_id = _seed_company_session(Session)
        row, _imp = _stmt_row(sess, cid, ba_id, credit=True)
        _deposit_boundary(sess, row.id, cid)
        audits = [r for r in audit_row_tuples(sess) if r[1] == "BankStatementRow"]
        assert audits == [
            ("Post", "BankStatementRow", row.id, AUDIT_DEPOSIT_DESC, PERFORMED_BY, cid)
        ]


class TestReconciliationCompanyIsolation:
    def test_explicit_company_stamping_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(
            RECONCILIATION_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess = Session()
        co_a = models.Company(
            name="Recon A",
            slug="recon_a",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        co_b = models.Company(
            name="Recon B",
            slug="recon_b",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        sess.add_all([co_a, co_b])
        sess.flush()
        for co in (co_a, co_b):
            seed_chart_of_accounts_for_company(sess, co.id)
            ensure_accounts_for_company(sess, co.id)
            set_setting(sess, "banking.bank_charges_enabled", True, company_id=co.id)
            sess.add(
                models.BankAccount(
                    name=f"Bank {co.slug}",
                    currency="TRY",
                    company_id=co.id,
                    is_active=True,
                    balance=0.0,
                )
            )
        sess.commit()

        sys.modules["streamlit"].session_state["active_company_id"] = co_a.id
        ba_b = sess.query(models.BankAccount).filter_by(company_id=co_b.id).one()
        row, imp = _stmt_row(sess, co_b.id, ba_b.id, credit=True)
        imp_id = imp.id
        sess.commit()

        with app._recon_boundary_scope(sess):
            result = post_generic_deposit(
                sess,
                row_id=row.id,
                company_id=co_b.id,
                credit_account_name=CREDIT_ACCT,
                user_id=USER_ID,
            )
            app.log_audit(
                sess,
                "Post",
                "BankStatementRow",
                row.id,
                AUDIT_DEPOSIT_DESC,
            )

        je = sess.get(models.JournalEntry, result["journal_entry_id"])
        btxn = sess.get(models.BankTransaction, result["bank_transaction_id"])
        sess.refresh(imp)

        assert je.company_id == co_b.id
        assert je.company_id != co_a.id
        assert btxn.company_id == co_b.id
        assert imp.company_id == co_b.id
        assert imp.id == imp_id
        assert bank_statement_row_tuples(sess) == [
            (
                row.id,
                imp.id,
                "posted",
                "other_deposit",
                je.id,
                btxn.id,
                DEPOSIT_AMT,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            )
        ]
