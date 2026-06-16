"""FASTAPI-P0.5d-S5 — boundary commit for partner/worker/equity movements."""

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
from db import Base
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import commit_modes, posting
from services.commit_modes import (
    CommitMode,
    POST_EQUITY_MOVEMENT_FAMILY,
    POST_PARTNER_MOVEMENT_FAMILY,
    POST_WORKER_MOVEMENT_FAMILY,
)
from services.unit_of_work import boundary_commit_scope
from tests.helpers.commit_parity import (
    MOVEMENT_TABLES,
    assert_persisted_state_equal,
    audit_row_tuples,
    bank_txn_row_tuples,
    dual_run_parity,
    journal_line_tuples,
    partner_movement_row_tuples,
    persisted_state_snapshot,
    worker_movement_row_tuples,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

POST_DATE = datetime.date(2026, 11, 8)
AMOUNT = 500.0
CURRENCY = "TRY"
PERFORMED_BY = "admin"
CREATED_BY = 7


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
        name="P05d Movement Co",
        slug="p05d_movement_co",
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
            balance=10000.0,
            kind="bank",
        )
    )
    sess.commit()
    return sess, co.id


def _partner_env(sess, cid):
    partner_id, err = app.create_partner(sess, "Alice", 100.0)
    assert err == ""
    partner = sess.get(models.Partner, partner_id)
    bank = sess.query(models.BankAccount).filter_by(company_id=cid).one()
    return {
        "partner_id": partner_id,
        "partner": partner,
        "bank_id": bank.id,
        "bank": bank,
        "cap_id": partner.capital_account_id,
        "cur_id": partner.current_account_id,
        "adv_id": partner.advance_account_id,
    }


def _worker_env(sess, cid):
    worker_id, err = app.create_worker(sess, "Bob")
    assert err == ""
    bank = sess.query(models.BankAccount).filter_by(company_id=cid).one()
    return {"worker_id": worker_id, "bank_id": bank.id, "bank": bank}


def _partner_capital_internal(sess, env):
    mid, err = app.post_partner_movement(
        sess,
        env["partner_id"],
        "CapitalContribution",
        AMOUNT,
        POST_DATE,
        bank_account_id=env["bank_id"],
        created_by_id=CREATED_BY,
    )
    assert err == ""


def _partner_capital_boundary(sess, env):
    commit_modes.set_commit_mode_for_tests(
        POST_PARTNER_MOVEMENT_FAMILY, CommitMode.BOUNDARY
    )
    mid, err = app.post_partner_movement(
        sess,
        env["partner_id"],
        "CapitalContribution",
        AMOUNT,
        POST_DATE,
        bank_account_id=env["bank_id"],
        created_by_id=CREATED_BY,
    )
    assert err == ""


def _worker_advance_internal(sess, env):
    mid, err = app.post_worker_movement(
        sess,
        env["worker_id"],
        "Advance",
        POST_DATE,
        bank_account_id=env["bank_id"],
        amount=AMOUNT,
        created_by_id=CREATED_BY,
    )
    assert err == ""


def _worker_advance_boundary(sess, env):
    commit_modes.set_commit_mode_for_tests(
        POST_WORKER_MOVEMENT_FAMILY, CommitMode.BOUNDARY
    )
    mid, err = app.post_worker_movement(
        sess,
        env["worker_id"],
        "Advance",
        POST_DATE,
        bank_account_id=env["bank_id"],
        amount=AMOUNT,
        created_by_id=CREATED_BY,
    )
    assert err == ""


def _equity_contrib_internal(sess, cid):
    bank = sess.query(models.BankAccount).filter_by(company_id=cid).one()
    btxn = models.BankTransaction(
        account_id=bank.id,
        date=POST_DATE,
        amount=AMOUNT,
        type="deposit",
        description="Capital Contribution #TBD",
        company_id=cid,
    )
    sess.add(btxn)
    sess.flush()
    btxn.description = f"Capital Contribution #{btxn.id}"
    apply_account_balance_delta(bank, "deposit", AMOUNT)
    app.post_capital_contribution(
        sess, btxn.id, AMOUNT, POST_DATE, "Bank", currency=CURRENCY
    )
    sess.commit()
    app.log_audit(
        sess,
        "Create",
        "EquityMovement",
        btxn.id,
        f"Capital Contribution #{btxn.id} · {AMOUNT:,.2f} {CURRENCY} → {bank.name}",
    )


def _equity_contrib_boundary(sess, cid):
    commit_modes.set_commit_mode_for_tests(
        POST_EQUITY_MOVEMENT_FAMILY, CommitMode.BOUNDARY
    )
    bank = sess.query(models.BankAccount).filter_by(company_id=cid).one()
    with boundary_commit_scope(sess, POST_EQUITY_MOVEMENT_FAMILY):
        btxn = models.BankTransaction(
            account_id=bank.id,
            date=POST_DATE,
            amount=AMOUNT,
            type="deposit",
            description="Capital Contribution #TBD",
            company_id=cid,
        )
        sess.add(btxn)
        sess.flush()
        btxn.description = f"Capital Contribution #{btxn.id}"
        apply_account_balance_delta(bank, "deposit", AMOUNT)
        app.post_capital_contribution(
            sess, btxn.id, AMOUNT, POST_DATE, "Bank", currency=CURRENCY
        )
        app.log_audit(
            sess,
            "Create",
            "EquityMovement",
            btxn.id,
            f"Capital Contribution #{btxn.id} · {AMOUNT:,.2f} {CURRENCY} → {bank.name}",
        )


class TestPostPartnerMovementDefaultInternal:
    def test_kernel_still_two_internal_commits(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _partner_env(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            posting.post_partner_movement(
                sess,
                env["partner_id"],
                "CapitalContribution",
                AMOUNT,
                POST_DATE,
                bank_account_id=env["bank_id"],
                created_by_id=CREATED_BY,
                company_id=cid,
            )
            assert mock_commit.call_count == 2

    def test_app_shim_still_three_commits_with_audit(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _partner_env(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            app.post_partner_movement(
                sess,
                env["partner_id"],
                "CapitalContribution",
                AMOUNT,
                POST_DATE,
                bank_account_id=env["bank_id"],
                created_by_id=CREATED_BY,
            )
            assert mock_commit.call_count == 3


class TestPostWorkerMovementDefaultInternal:
    def test_kernel_still_two_internal_commits(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _worker_env(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            posting.post_worker_movement(
                sess,
                env["worker_id"],
                "Advance",
                POST_DATE,
                bank_account_id=env["bank_id"],
                amount=AMOUNT,
                created_by_id=CREATED_BY,
                company_id=cid,
            )
            assert mock_commit.call_count == 2


class TestPostEquityMovementDefaultInternal:
    def test_post_capital_contribution_still_one_internal_commit(self):
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            posting.post_capital_contribution(
                sess, 42, AMOUNT, POST_DATE, "Bank", company_id=cid
            )
            assert mock_commit.call_count == 1


class TestMovementBoundaryMode:
    def test_partner_boundary_one_commit(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PARTNER_MOVEMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _partner_env(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _partner_capital_boundary(sess, env)
            assert mock_commit.call_count == 1

    def test_worker_boundary_one_commit(self):
        commit_modes.set_commit_mode_for_tests(
            POST_WORKER_MOVEMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _worker_env(sess, cid)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _worker_advance_boundary(sess, env)
            assert mock_commit.call_count == 1

    def test_equity_boundary_one_commit(self):
        commit_modes.set_commit_mode_for_tests(
            POST_EQUITY_MOVEMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        with patch.object(sess, "commit", wraps=sess.commit) as mock_commit:
            _equity_contrib_boundary(sess, cid)
            assert mock_commit.call_count == 1


class TestMovementDualRunParity:
    @pytest.mark.parametrize(
        "internal_runner,boundary_runner,movement_key",
        [
            (_partner_capital_internal, _partner_capital_boundary, "partner_movements"),
            (_worker_advance_internal, _worker_advance_boundary, "worker_movements"),
            (_equity_contrib_internal, _equity_contrib_boundary, None),
        ],
        ids=["partner_capital", "worker_advance", "equity_contribution"],
    )
    def test_internal_vs_boundary_persisted_state_identical(
        self, internal_runner, boundary_runner, movement_key
    ):
        def factory():
            _, Session = _make_engine_session()
            sess, cid = _seed_company_session(Session)
            return sess, cid

        def run_internal(sess_cid):
            sess, cid = sess_cid
            commit_modes.reset_commit_modes_for_tests()
            env = (
                _partner_env(sess, cid)
                if movement_key == "partner_movements"
                else _worker_env(sess, cid)
                if movement_key == "worker_movements"
                else None
            )
            if env is not None:
                internal_runner(sess, env)
            else:
                internal_runner(sess, cid)

        def run_boundary(sess_cid):
            sess, cid = sess_cid
            env = (
                _partner_env(sess, cid)
                if movement_key == "partner_movements"
                else _worker_env(sess, cid)
                if movement_key == "worker_movements"
                else None
            )
            if env is not None:
                boundary_runner(sess, env)
            else:
                boundary_runner(sess, cid)

        snap_kw = {
            "include_sale_rows": False,
            "include_bank_txn_rows": True,
            "include_partner_movement_rows": movement_key == "partner_movements",
            "include_worker_movement_rows": movement_key == "worker_movements",
        }

        def factory_session_only():
            sess, _cid = factory()
            return sess

        left, right = dual_run_parity(
            session_factory=factory_session_only,
            internal_runner=lambda s: run_internal(
                (s, s.query(models.Company).one().id)
            ),
            boundary_runner=lambda s: run_boundary(
                (s, s.query(models.Company).one().id)
            ),
            tables=MOVEMENT_TABLES,
            snapshot_kwargs=snap_kw,
        )
        assert_persisted_state_equal(left, right)
        assert left["counts"]["journal_entries"] >= 1
        expected_audits = 2 if movement_key in ("partner_movements", "worker_movements") else 1
        assert left["counts"]["audit_log"] == expected_audits
        assert left["counts"]["bank_transactions"] == 1
        if movement_key == "partner_movements":
            assert left["counts"]["partner_movements"] == 1
            assert left["partner_movements"][0][2] == "CapitalContribution"
        if movement_key == "worker_movements":
            assert left["counts"]["worker_movements"] == 1
            assert left["worker_movements"][0][2] == "Advance"

    def test_partner_gl_lines_match(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PARTNER_MOVEMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _partner_env(sess, cid)
        _partner_capital_boundary(sess, env)
        movement = sess.query(models.PartnerMovement).one()
        je = sess.get(models.JournalEntry, movement.journal_entry_id)
        lines = [
            (ln.account_id, ln.debit or 0.0, ln.credit or 0.0)
            for ln in sess.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=je.id)
            .order_by(models.JournalEntryLine.id)
            .all()
        ]
        bank_gl = posting.get_account_by_name(sess, "Bank", company_id=cid)
        assert lines == [(bank_gl.id, AMOUNT, 0.0), (env["cap_id"], 0.0, AMOUNT)]


class TestMovementBoundaryRollback:
    def test_partner_failure_rolls_back_movement_btxn_je_and_audit(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PARTNER_MOVEMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _partner_env(sess, cid)
        period = models.FiscalPeriod(
            name="Closed Nov 2026",
            start_date=POST_DATE,
            end_date=POST_DATE,
            is_closed=True,
            closed_at=POST_DATE,
            company_id=cid,
        )
        sess.add(period)
        sess.commit()

        with pytest.raises(ValueError):
            with boundary_commit_scope(sess, POST_PARTNER_MOVEMENT_FAMILY):
                mid, err = app.post_partner_movement(
                    sess,
                    env["partner_id"],
                    "CapitalContribution",
                    AMOUNT,
                    POST_DATE,
                    bank_account_id=env["bank_id"],
                    created_by_id=CREATED_BY,
                )
                assert err == ""

        assert sess.query(func.count()).select_from(models.PartnerMovement).scalar() == 0
        assert sess.query(func.count()).select_from(models.BankTransaction).scalar() == 0
        assert (
            sess.query(func.count())
            .select_from(models.JournalEntry)
            .filter_by(reference_type="PartnerCapital")
            .scalar()
            == 0
        )
        assert sess.query(func.count()).select_from(models.AuditLog).filter_by(
            entity_type="PartnerMovement"
        ).scalar() == 0

    def test_worker_validation_leaves_no_movement_rows(self):
        commit_modes.set_commit_mode_for_tests(
            POST_WORKER_MOVEMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _worker_env(sess, cid)
        mid, err = app.post_worker_movement(
            sess,
            env["worker_id"],
            "Advance",
            POST_DATE,
            bank_account_id=env["bank_id"],
            amount=0.0,
            created_by_id=CREATED_BY,
        )
        assert err == "Amount must be greater than zero."
        assert sess.query(func.count()).select_from(models.WorkerMovement).scalar() == 0
        assert (
            sess.query(func.count())
            .select_from(models.JournalEntry)
            .filter_by(reference_type="WorkerAdvance")
            .scalar()
            == 0
        )

    def test_mode_flags_revert_to_internal(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PARTNER_MOVEMENT_FAMILY, CommitMode.BOUNDARY
        )
        commit_modes.set_commit_mode_for_tests(
            POST_WORKER_MOVEMENT_FAMILY, CommitMode.BOUNDARY
        )
        commit_modes.set_commit_mode_for_tests(
            POST_EQUITY_MOVEMENT_FAMILY, CommitMode.BOUNDARY
        )
        commit_modes.reset_commit_modes_for_tests()
        assert not commit_modes.is_boundary_mode(POST_PARTNER_MOVEMENT_FAMILY)
        assert not commit_modes.is_boundary_mode(POST_WORKER_MOVEMENT_FAMILY)
        assert not commit_modes.is_boundary_mode(POST_EQUITY_MOVEMENT_FAMILY)


class TestMovementAuditAtomic:
    def test_partner_audit_row_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(
            POST_PARTNER_MOVEMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        env = _partner_env(sess, cid)
        _partner_capital_boundary(sess, env)
        movement = sess.query(models.PartnerMovement).one()
        partner = sess.get(models.Partner, env["partner_id"])
        movement_audits = [
            r for r in audit_row_tuples(sess) if r[1] == "PartnerMovement"
        ]
        assert movement_audits == [
            (
                "Create",
                "PartnerMovement",
                movement.id,
                f"CapitalContribution: {partner.name} — {AMOUNT:,.2f}",
                PERFORMED_BY,
                cid,
            )
        ]

    def test_equity_audit_row_preserved_in_boundary_mode(self):
        commit_modes.set_commit_mode_for_tests(
            POST_EQUITY_MOVEMENT_FAMILY, CommitMode.BOUNDARY
        )
        _, Session = _make_engine_session()
        sess, cid = _seed_company_session(Session)
        _equity_contrib_boundary(sess, cid)
        btxn = sess.query(models.BankTransaction).one()
        bank = sess.query(models.BankAccount).filter_by(company_id=cid).one()
        assert audit_row_tuples(sess) == [
            (
                "Create",
                "EquityMovement",
                btxn.id,
                f"Capital Contribution #{btxn.id} · {AMOUNT:,.2f} {CURRENCY} → {bank.name}",
                PERFORMED_BY,
                cid,
            )
        ]
