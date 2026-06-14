"""FASTAPI-P0.5d-S0 — commit ownership scaffolding (no behavior change)."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

import models
from db import Base
from services import audit as audit_svc
from services import commit_modes
from services import posting
from services.commit_modes import CommitMode
from services.unit_of_work import unit_of_work
from tests.helpers.commit_parity import (
    assert_persisted_state_equal,
    dual_run_parity,
    persisted_state_snapshot,
)

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
    sys.modules["streamlit"].session_state = {}


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        yield s


def _accounts(session):
    cash = models.ChartOfAccounts(
        account_code="1000",
        account_name="Cash",
        account_type="Asset",
        balance=0.0,
        is_active=True,
        company_id=1,
    )
    income = models.ChartOfAccounts(
        account_code="4000",
        account_name="Sales Revenue",
        account_type="Income",
        balance=0.0,
        is_active=True,
        company_id=1,
    )
    session.add_all([cash, income])
    session.commit()
    return cash, income


class TestCommitModes:
    def test_all_posting_families_default_internal(self):
        for family in commit_modes.POSTING_FAMILIES:
            assert commit_modes.get_commit_mode(family) is CommitMode.INTERNAL
        assert commit_modes.get_commit_mode(commit_modes.AUDIT_FAMILY) is CommitMode.INTERNAL
        assert commit_modes.get_commit_mode(commit_modes.POST_CASH_SALE_FAMILY) is CommitMode.INTERNAL

    def test_unknown_family_defaults_internal(self):
        assert commit_modes.get_commit_mode("future_family") is CommitMode.INTERNAL

    def test_test_override_does_not_change_default(self):
        commit_modes.set_commit_mode_for_tests("sale", CommitMode.BOUNDARY)
        try:
            assert commit_modes.get_commit_mode("sale") is CommitMode.BOUNDARY
            assert commit_modes.get_commit_mode("expense") is CommitMode.INTERNAL
        finally:
            commit_modes.reset_commit_modes_for_tests()
        assert commit_modes.get_commit_mode("sale") is CommitMode.INTERNAL


class TestUnitOfWork:
    def test_commits_once_on_success(self, session):
        session.add(
            models.ChartOfAccounts(
                account_code="1100",
                account_name="Bank",
                account_type="Asset",
                balance=0.0,
                is_active=True,
                company_id=1,
            )
        )
        with unit_of_work(session):
            session.flush()
        assert session.query(func.count()).select_from(models.ChartOfAccounts).scalar() == 1

    def test_rolls_back_on_exception(self, session):
        with pytest.raises(RuntimeError):
            with unit_of_work(session):
                session.add(
                    models.ChartOfAccounts(
                        account_code="1200",
                        account_name="AR",
                        account_type="Asset",
                        balance=0.0,
                        is_active=True,
                        company_id=1,
                    )
                )
                session.flush()
                raise RuntimeError("boom")
        assert session.query(func.count()).select_from(models.ChartOfAccounts).scalar() == 0


class TestLegacyCommitOwnershipUnchanged:
    def test_create_journal_entry_still_commits_internally(self, session):
        cash, income = _accounts(session)
        with patch.object(session, "commit", wraps=session.commit) as mock_commit:
            posting.create_journal_entry(
                session,
                datetime.date(2026, 6, 1),
                "Scaffold pin",
                "CashSale",
                1,
                [(cash.id, 10.0, 0), (income.id, 0, 10.0)],
                company_id=1,
            )
            assert mock_commit.call_count == 1
        session.rollback()
        assert session.query(func.count()).select_from(models.JournalEntry).scalar() == 1

    def test_post_cash_sale_commit_count_unchanged(self, session):
        """Sale family still delegates to create_journal_entry (one internal commit)."""
        cash, income = _accounts(session)
        sale = models.Sale(
            date=datetime.date(2026, 6, 1),
            invoice_number="INV-SCAFFOLD",
            customer_name="Customer",
            amount=40.0,
            sale_type="Cash",
            paid_amount=40.0,
            balance=0.0,
            due_date=datetime.date(2026, 6, 1),
            status="Paid",
            company_id=1,
        )
        session.add(sale)
        session.commit()
        with patch.object(session, "commit", wraps=session.commit) as mock_commit:
            posting.post_cash_sale(
                session, sale.id, 40.0, datetime.date(2026, 6, 1), company_id=1
            )
            assert mock_commit.call_count == 1

    def test_record_audit_still_commits_internally(self, session):
        with patch.object(session, "commit", wraps=session.commit) as mock_commit:
            audit_svc.record_audit(
                session,
                action=audit_svc.ACTION_POST,
                entity_type=audit_svc.ENTITY_SALE,
                entity_id=1,
                description="scaffold pin",
                performed_by="tester",
                company_id=1,
            )
            assert mock_commit.call_count == 1
        session.rollback()
        assert session.query(func.count()).select_from(models.AuditLog).scalar() == 1


class TestDualRunParityHarness:
    def test_harness_detects_identical_snapshots(self):
        def _seed_session():
            engine = create_engine(
                "sqlite:///:memory:", connect_args={"check_same_thread": False}
            )
            Base.metadata.create_all(bind=engine)
            Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            sess = Session()
            _accounts(sess)
            return sess

        def _post(sess):
            cash, income = (
                sess.query(models.ChartOfAccounts)
                .filter_by(account_name="Cash")
                .one(),
                sess.query(models.ChartOfAccounts)
                .filter_by(account_name="Sales Revenue")
                .one(),
            )
            posting.create_journal_entry(
                sess,
                datetime.date(2026, 6, 2),
                "Parity",
                "CashSale",
                2,
                [(cash.id, 25.0, 0), (income.id, 0, 25.0)],
                company_id=1,
            )

        def factory():
            return _seed_session()

        left, right = dual_run_parity(
            session_factory=factory,
            internal_runner=_post,
            boundary_runner=_post,
        )
        assert_persisted_state_equal(left, right)
        assert left["counts"]["journal_entries"] == 1
        assert len(left["journal_lines"]) == 2

    def test_snapshot_helper_stable_shape(self, session):
        snap = persisted_state_snapshot(session)
        assert "counts" in snap
        assert "journal_lines" in snap
        assert snap["counts"]["journal_entries"] == 0
