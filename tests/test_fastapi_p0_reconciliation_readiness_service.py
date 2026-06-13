"""FASTAPI-P0.2-D — reconciliation readiness read service contract tests."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app as erp_app
from db import Base
import models
from services import read_reconciliation as rr
from ui.banking import (
    banking_company_statement_readiness,
    compute_banking_statement_readiness,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s


def _company(db, slug: str):
    co = models.Company(
        name=slug.title(),
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    return co


def _bank(db, co):
    ba = models.BankAccount(
        name="Main",
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=5000.0,
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
    file_hash="p0d",
    starting_balance=None,
    ending_balance=None,
    rows_spec: list[dict] | None = None,
):
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
                date=datetime.date(2025, 6, min(idx, 28)),
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


def _dto_dict(dto: rr.StatementReadiness) -> dict:
    return dto.to_dict()


class TestComplete:
    def test_true_when_all_rows_terminal(self, db):
        co = _company(db, "complete")
        ba = _bank(db, co)
        imp = _import_stmt(
            db, co, ba,
            rows_spec=[
                {"status": "posted", "credit": 100.0},
                {"status": "skipped", "debit": 50.0},
                {"status": "voided", "credit": 25.0},
            ],
        )
        dto = rr.compute_statement_readiness(db, imp, company_id=co.id)
        assert dto is not None
        assert dto.complete is True
        assert dto.counts.remaining_rows == 0
        assert dto.complete_tri == "ok"

    @pytest.mark.parametrize("status", ["staging", "duplicate_flagged", "parse_error"])
    def test_false_for_non_terminal(self, db, status):
        co = _company(db, status)
        ba = _bank(db, co)
        imp = _import_stmt(
            db, co, ba,
            file_hash=status,
            rows_spec=[
                {"status": "posted", "credit": 100.0},
                {"status": status, "credit": 10.0},
            ],
        )
        dto = rr.compute_statement_readiness(db, imp, company_id=co.id)
        assert dto is not None
        assert dto.complete is False
        assert dto.complete_tri == "attention"


class TestReconciled:
    def test_true_when_complete_balances_and_tie_out_ok(self, db):
        co = _company(db, "recon_ok")
        ba = _bank(db, co)
        imp = _import_stmt(
            db, co, ba,
            starting_balance=1000.0,
            ending_balance=1200.0,
            rows_spec=[
                {"status": "posted", "credit": 300.0},
                {"status": "posted", "debit": 100.0},
            ],
        )
        dto = rr.compute_statement_readiness(db, imp, company_id=co.id)
        assert dto is not None
        assert dto.complete is True
        assert dto.tie_out.state == "ok"
        assert dto.reconciled is True
        assert dto.reconciled_tri == "ok"

    def test_false_when_tie_out_mismatch(self, db):
        co = _company(db, "mismatch")
        ba = _bank(db, co)
        imp = _import_stmt(
            db, co, ba,
            starting_balance=1000.0,
            ending_balance=1300.0,
            rows_spec=[{"status": "posted", "credit": 200.0}],
        )
        dto = rr.compute_statement_readiness(db, imp, company_id=co.id)
        assert dto is not None
        assert dto.tie_out.state == "mismatch"
        assert dto.reconciled is False
        assert dto.reconciled_tri == "attention"

    def test_unavailable_when_balances_missing(self, db):
        co = _company(db, "no_bal")
        ba = _bank(db, co)
        imp = _import_stmt(
            db, co, ba,
            starting_balance=None,
            ending_balance=None,
            rows_spec=[{"status": "posted", "credit": 100.0}],
        )
        dto = rr.compute_statement_readiness(db, imp, company_id=co.id)
        assert dto is not None
        assert dto.tie_out.state == "unavailable"
        assert dto.tie_out.available is False
        assert dto.reconciled is False
        assert dto.reconciled_tri == "unavailable"


class TestTieOutTolerance:
    def test_within_tolerance_is_ok(self, db):
        co = _company(db, "tol_ok")
        ba = _bank(db, co)
        imp = _import_stmt(
            db, co, ba,
            starting_balance=1000.0,
            ending_balance=1000.009,
            rows_spec=[{"status": "posted", "credit": 0.009}],
        )
        dto = rr.compute_statement_readiness(db, imp, company_id=co.id)
        assert dto is not None
        assert dto.tie_out.state == "ok"

    def test_outside_tolerance_is_mismatch(self, db):
        co = _company(db, "tol_bad")
        ba = _bank(db, co)
        imp = _import_stmt(
            db, co, ba,
            starting_balance=1000.0,
            ending_balance=1000.02,
            rows_spec=[{"status": "posted", "credit": 0.01}],
        )
        dto = rr.compute_statement_readiness(db, imp, company_id=co.id)
        assert dto is not None
        assert dto.tie_out.state == "mismatch"


class TestCounts:
    def test_remaining_review_failed(self, db):
        co = _company(db, "counts")
        ba = _bank(db, co)
        imp = _import_stmt(
            db, co, ba,
            rows_spec=[
                {"status": "staging", "credit": 10.0},
                {"status": "duplicate_flagged", "credit": 20.0},
                {"status": "parse_error", "credit": 5.0},
                {"status": "posted", "credit": 30.0},
            ],
        )
        dto = rr.compute_statement_readiness(db, imp, company_id=co.id)
        assert dto is not None
        assert dto.counts.remaining_rows == 2
        assert dto.counts.review_pending == 1
        assert dto.counts.failed_blocked == 1


class TestBankingShimParity:
    def test_shim_matches_service_dict(self, db):
        co = _company(db, "shim")
        ba = _bank(db, co)
        imp = _import_stmt(
            db, co, ba,
            starting_balance=0.0,
            ending_balance=100.0,
            rows_spec=[{"status": "posted", "credit": 100.0}],
        )
        svc = _dto_dict(rr.compute_statement_readiness(db, imp, company_id=co.id))
        shim = compute_banking_statement_readiness(db, imp)
        assert shim == svc

    def test_company_list_shim_matches_service(self, db):
        co = _company(db, "list")
        ba = _bank(db, co)
        _import_stmt(
            db, co, ba,
            starting_balance=0.0,
            ending_balance=50.0,
            rows_spec=[{"status": "posted", "credit": 50.0}],
        )
        svc = [
            _dto_dict(d)
            for d in rr.compute_company_statement_readiness(db, co.id, limit=5)
        ]
        shim = banking_company_statement_readiness(db, co.id, limit=5)
        assert shim == svc


class TestCompanyIsolation:
    def test_wrong_company_returns_none(self, db):
        co_a = _company(db, "co_a")
        co_b = _company(db, "co_b")
        ba = _bank(db, co_a)
        imp = _import_stmt(
            db, co_a, ba,
            rows_spec=[{"status": "posted", "credit": 10.0}],
        )
        assert rr.compute_statement_readiness(db, imp, company_id=co_b.id) is None

    def test_company_lists_are_isolated(self, db):
        co_a = _company(db, "iso_a")
        co_b = _company(db, "iso_b")
        ba_a = _bank(db, co_a)
        ba_b = _bank(db, co_b)
        _import_stmt(
            db, co_a, ba_a,
            file_hash="a",
            starting_balance=0.0,
            ending_balance=100.0,
            rows_spec=[{"status": "posted", "credit": 100.0}],
        )
        _import_stmt(
            db, co_b, ba_b,
            file_hash="b",
            rows_spec=[{"status": "staging", "credit": 50.0}],
        )
        list_a = rr.compute_company_statement_readiness(db, co_a.id)
        list_b = rr.compute_company_statement_readiness(db, co_b.id)
        assert len(list_a) == 1
        assert len(list_b) == 1
        assert list_a[0].reconciled is True
        assert list_b[0].complete is False


class TestReadOnly:
    def test_no_jes_or_bank_txns_created(self, db):
        co = _company(db, "ro")
        ba = _bank(db, co)
        imp = _import_stmt(
            db, co, ba,
            starting_balance=0.0,
            ending_balance=100.0,
            rows_spec=[{"status": "staging", "credit": 100.0}],
        )
        je_before = db.query(models.JournalEntry).count()
        bt_before = db.query(models.BankTransaction).count()
        rr.compute_statement_readiness(db, imp, company_id=co.id)
        rr.compute_company_statement_readiness(db, co.id)
        assert db.query(models.JournalEntry).count() == je_before
        assert db.query(models.BankTransaction).count() == bt_before
