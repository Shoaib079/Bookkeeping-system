"""BANKING-UX-03 P2.4-A — read-only per-statement readiness & tie-out MVP."""
from __future__ import annotations

import datetime
import inspect
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app as erp_app
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from registry.service import set_setting
from ui.banking import (
    banking_company_statement_readiness,
    banking_readiness_drill_to,
    banking_statement_row_signed_total,
    compute_banking_statement_readiness,
    render_banking_recon_cockpit,
    render_banking_statement_readiness_panel,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True

_P24_KEYS = (
    "banking.readiness.title",
    "banking.readiness.desc",
    "banking.readiness.complete",
    "banking.readiness.reconciled",
    "banking.readiness.tie_out",
    "banking.readiness.remaining",
    "banking.readiness.review_pending",
    "banking.readiness.failed_blocked",
    "banking.readiness.tri.ok",
    "banking.readiness.tri.attention",
    "banking.readiness.tri.unavailable",
    "banking.readiness.tie_out.unavailable_msg",
    "banking.readiness.drill_review",
    "banking.readiness.drill_queue",
    "banking.readiness.no_imports",
)


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
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
        erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        yield s


def _company(db, *, slug: str, name: str | None = None):
    co = models.Company(
        name=name or slug.title(),
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    return co


def _activate(db, co):
    sys.modules["streamlit"].session_state["active_company_id"] = co.id
    set_setting(db, "banking.reconciliation_enabled", True, company_id=co.id)


def _bank(db, co, *, name="Main TRY", balance=5000.0):
    ba = models.BankAccount(
        name=name,
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=balance,
        kind="bank",
    )
    db.add(ba)
    db.commit()
    return ba


def _import_stmt(
    db,
    co,
    ba,
    *,
    file_hash="p24",
    starting_balance=None,
    ending_balance=None,
    rows_spec: list[dict] | None = None,
):
    """rows_spec: list of {status, credit, debit} dicts."""
    imp = models.BankStatementImport(
        company_id=co.id,
        bank_account_id=ba.id,
        file_name="stmt.csv",
        file_hash=file_hash,
        file_size=10,
        file_path="/tmp/stmt.csv",
        status="staging",
        import_date=datetime.date(2025, 6, 1),
        start_date=datetime.date(2025, 6, 1),
        end_date=datetime.date(2025, 6, 30),
        starting_balance=starting_balance,
        ending_balance=ending_balance,
        row_count=len(rows_spec or []),
        valid_count=0,
        flagged_count=0,
        error_count=0,
        currency="TRY",
        created_at=datetime.datetime.now(),
    )
    db.add(imp)
    db.flush()
    for idx, spec in enumerate(rows_spec or [], start=1):
        credit = spec.get("credit")
        debit = spec.get("debit")
        amount = credit or debit or 0.0
        db.add(
            models.BankStatementRow(
                bank_statement_import_id=imp.id,
                import_row_index=idx,
                date=datetime.date(2025, 6, idx if idx <= 28 else 28),
                description=spec.get("description", "Line"),
                credit_amount=credit,
                debit_amount=debit,
                amount=amount,
                currency="TRY",
                original_amount=amount,
                parsed_successfully=spec.get("status") != "parse_error",
                status=spec.get("status", "staging"),
                created_at=datetime.datetime.now(),
            )
        )
    db.commit()
    db.refresh(imp)
    return imp


class TestStatementComplete:
    def test_complete_true_when_all_rows_terminal(self, session):
        co = _company(session, slug="complete")
        _activate(session, co)
        ba = _bank(session, co)
        imp = _import_stmt(
            session,
            co,
            ba,
            rows_spec=[
                {"status": "posted", "credit": 100.0},
                {"status": "skipped", "debit": 50.0},
                {"status": "voided", "credit": 25.0},
            ],
        )
        r = compute_banking_statement_readiness(session, imp)
        assert r["complete"] is True
        assert r["remaining_rows"] == 0
        assert r["complete_tri"] == "ok"

    @pytest.mark.parametrize(
        "blocking_status",
        ["staging", "duplicate_flagged", "parse_error"],
    )
    def test_complete_false_when_non_terminal_rows(self, session, blocking_status):
        co = _company(session, slug=f"inc_{blocking_status}")
        _activate(session, co)
        ba = _bank(session, co)
        imp = _import_stmt(
            session,
            co,
            ba,
            file_hash=blocking_status,
            rows_spec=[
                {"status": "posted", "credit": 100.0},
                {"status": blocking_status, "credit": 10.0},
            ],
        )
        r = compute_banking_statement_readiness(session, imp)
        assert r["complete"] is False
        assert r["complete_tri"] == "attention"


class TestStatementReconciled:
    def test_reconciled_true_when_complete_balances_and_tie_out_match(self, session):
        co = _company(session, slug="recon_ok")
        _activate(session, co)
        ba = _bank(session, co)
        imp = _import_stmt(
            session,
            co,
            ba,
            starting_balance=1000.0,
            ending_balance=1200.0,
            rows_spec=[
                {"status": "posted", "credit": 300.0},
                {"status": "posted", "debit": 100.0},
            ],
        )
        assert banking_statement_row_signed_total(imp.rows) == 200.0
        r = compute_banking_statement_readiness(session, imp)
        assert r["complete"] is True
        assert r["tie_out"] == "ok"
        assert r["reconciled"] is True
        assert r["reconciled_tri"] == "ok"

    def test_reconciled_false_when_complete_but_tie_out_mismatch(self, session):
        co = _company(session, slug="recon_bad")
        _activate(session, co)
        ba = _bank(session, co)
        imp = _import_stmt(
            session,
            co,
            ba,
            starting_balance=1000.0,
            ending_balance=1300.0,
            rows_spec=[
                {"status": "posted", "credit": 200.0},
            ],
        )
        r = compute_banking_statement_readiness(session, imp)
        assert r["complete"] is True
        assert r["tie_out"] == "mismatch"
        assert r["reconciled"] is False
        assert r["reconciled_tri"] == "attention"

    def test_reconciled_unavailable_when_balances_missing(self, session):
        co = _company(session, slug="no_bal")
        _activate(session, co)
        ba = _bank(session, co)
        imp = _import_stmt(
            session,
            co,
            ba,
            starting_balance=None,
            ending_balance=None,
            rows_spec=[
                {"status": "posted", "credit": 100.0},
            ],
        )
        r = compute_banking_statement_readiness(session, imp)
        assert r["tie_out"] == "unavailable"
        assert r["reconciled"] is False
        assert r["reconciled_tri"] == "unavailable"
        assert r["tie_out_available"] is False

    def test_no_declared_balance_never_shows_reconciled(self, session):
        co = _company(session, slug="never_recon")
        _activate(session, co)
        ba = _bank(session, co)
        imp = _import_stmt(
            session,
            co,
            ba,
            starting_balance=1000.0,
            ending_balance=None,
            rows_spec=[
                {"status": "posted", "credit": 100.0},
            ],
        )
        r = compute_banking_statement_readiness(session, imp)
        assert r["reconciled"] is False
        assert r["reconciled_tri"] == "unavailable"


class TestReadinessCounts:
    def test_remaining_review_and_failed_counts(self, session):
        co = _company(session, slug="counts")
        _activate(session, co)
        ba = _bank(session, co)
        imp = _import_stmt(
            session,
            co,
            ba,
            rows_spec=[
                {"status": "staging", "credit": 10.0},
                {"status": "duplicate_flagged", "credit": 20.0},
                {"status": "parse_error", "credit": 5.0},
                {"status": "posted", "credit": 30.0},
            ],
        )
        r = compute_banking_statement_readiness(session, imp)
        assert r["remaining_rows"] == 2
        assert r["review_pending"] == 1
        assert r["failed_blocked"] == 1


class TestReadOnly:
    def test_readiness_computation_creates_zero_journal_entries(self, session):
        co = _company(session, slug="ro_je")
        _activate(session, co)
        ba = _bank(session, co)
        imp = _import_stmt(
            session,
            co,
            ba,
            starting_balance=0.0,
            ending_balance=100.0,
            rows_spec=[{"status": "staging", "credit": 100.0}],
        )
        before_je = session.query(models.JournalEntry).count()
        before_bt = session.query(models.BankTransaction).count()
        compute_banking_statement_readiness(session, imp)
        banking_company_statement_readiness(session, co.id)
        assert session.query(models.JournalEntry).count() == before_je
        assert session.query(models.BankTransaction).count() == before_bt

    def test_readiness_panel_has_no_posting_calls(self):
        src = inspect.getsource(render_banking_statement_readiness_panel)
        assert "create_journal_entry" not in src
        assert "post_bank_charge_outflow" not in src
        assert "post_deposit_clearing_match" not in src

    def test_cockpit_includes_readiness_section(self):
        src = inspect.getsource(render_banking_recon_cockpit)
        assert "render_banking_statement_readiness_panel" in src


class TestCompanyIsolation:
    def test_readiness_scoped_to_company(self, session):
        co_a = _company(session, slug="co_a")
        co_b = _company(session, slug="co_b")
        _activate(session, co_a)
        ba_a = _bank(session, co_a)
        ba_b = _bank(session, co_b)
        _import_stmt(
            session,
            co_a,
            ba_a,
            file_hash="a",
            starting_balance=0.0,
            ending_balance=100.0,
            rows_spec=[{"status": "posted", "credit": 100.0}],
        )
        _import_stmt(
            session,
            co_b,
            ba_b,
            file_hash="b",
            rows_spec=[{"status": "staging", "credit": 50.0}],
        )
        list_a = banking_company_statement_readiness(session, co_a.id)
        list_b = banking_company_statement_readiness(session, co_b.id)
        assert len(list_a) == 1
        assert len(list_b) == 1
        assert list_a[0]["reconciled"] is True
        assert list_b[0]["complete"] is False


class TestDrillThrough:
    def test_drill_to_review_sets_import(self):
        banking_readiness_drill_to("review", import_id=42)
        assert sys.modules["streamlit"].session_state["banking_section"] == "import"
        assert sys.modules["streamlit"].session_state["bsi_section"] == "review"
        assert sys.modules["streamlit"].session_state["bsi_review_import"] == 42

    def test_drill_to_match_queue(self):
        banking_readiness_drill_to("match")
        assert sys.modules["streamlit"].session_state["bsi_section"] == "match"


class TestLocales:
    def test_readiness_keys_present_en_tr(self):
        for key in _P24_KEYS:
            assert key in TRANSACTIONAL_EN
            assert key in TRANSACTIONAL_TR
