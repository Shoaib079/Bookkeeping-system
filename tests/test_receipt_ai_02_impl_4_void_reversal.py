"""RECEIPT-AI-02-IMPL-4 — void-aware receipt learning tests."""

from __future__ import annotations

import datetime
import inspect

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from services import receipt_learning as learn
from services.receipt_learning_store import persistent_learning_store


def _event(**kw) -> learn.ApprovalLearningEvent:
    base = dict(
        company_id=1,
        vendor_signature="BIM",
        expense_record_id=100,
        tx_category_id=5,
        tx_subcategory_id=12,
        payment_method="Cash",
        category_name="Groceries",
        amount=50.0,
        approved_at=datetime.datetime(2026, 6, 15, 10, 0, 0),
        is_voided=False,
    )
    base.update(kw)
    return learn.ApprovalLearningEvent(**base)


def _void_event(**kw) -> learn.ApprovalLearningEvent:
    return _event(
        is_voided=True,
        voided_at=datetime.datetime(2026, 6, 16, 9, 0, 0),
        **kw,
    )


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as session:
        yield session


@pytest.fixture()
def mem_store():
    return learn.InMemoryLearningStore()


@pytest.fixture()
def db_store(db_session):
    return persistent_learning_store(db_session)


class TestVoidDoesNotReinforce:
    def test_voided_event_skips_record_approval(self, mem_store):
        result = learn.record_approval(mem_store, _void_event())
        assert not result.learned
        assert "record_void_reversal" in result.skip_reason
        assert mem_store.all_records() == ()

    def test_learning_event_from_posted_draft_void_flag(self):
        ctx = learn.PostedDraftLearningContext(
            company_id=1,
            expense_record_id=55,
            vendor_signature="BIM",
            tx_category_id=5,
            expense_record_is_void=True,
            voided_at=datetime.datetime(2026, 6, 16),
        )
        event = learn.learning_event_from_posted_draft(ctx)
        assert event.is_voided is True
        assert event.expense_record_id == 55


class TestRecordVoidReversalInMemory:
    def test_void_reversal_decrements_after_approval(self, mem_store):
        learn.record_approval(mem_store, _event())
        before = mem_store.list_for_signature(1, "vendor_category", "BIM")[0]
        assert before.approval_count == 1

        result = learn.record_void_reversal(mem_store, _void_event())
        assert result.reconciled
        assert result.records_updated >= 1

        after = mem_store.list_for_signature(1, "vendor_category", "BIM")
        assert after == ()

    def test_confidence_decreases_after_void(self, mem_store):
        for _ in range(3):
            learn.record_approval(mem_store, _event())
        before = learn.suggest_for_vendor(mem_store, 1, "BIM")
        assert before.category.confidence > 0

        learn.record_void_reversal(mem_store, _void_event())
        after = learn.suggest_for_vendor(mem_store, 1, "BIM")
        assert after is None or after.category.confidence < before.category.confidence

    def test_count_never_below_zero(self, mem_store):
        learn.record_approval(mem_store, _event())
        learn.record_void_reversal(mem_store, _void_event())
        learn.record_void_reversal(mem_store, _void_event())

        rows = [
            r
            for r in mem_store.all_records()
            if r.signature_type == "vendor_category"
        ]
        assert len(rows) == 1
        assert rows[0].approval_count == 0
        assert rows[0].correction_count == 1

    def test_missing_row_is_no_op(self, mem_store):
        result = learn.record_void_reversal(mem_store, _void_event())
        assert not result.reconciled
        assert result.records_updated == 0

    def test_company_isolation_on_void(self, mem_store):
        learn.record_approval(mem_store, _event(company_id=1))
        learn.record_approval(
            mem_store,
            _event(
                company_id=2,
                tx_category_id=9,
                tx_subcategory_id=None,
                payment_method="Unknown",
            ),
        )

        learn.record_void_reversal(
            mem_store,
            _void_event(
                company_id=2,
                tx_category_id=9,
                tx_subcategory_id=None,
                payment_method="Unknown",
            ),
        )

        assert learn.suggest_for_vendor(mem_store, 1, "BIM") is not None
        assert learn.suggest_for_vendor(mem_store, 2, "BIM") is None

    def test_correction_count_increments(self, mem_store):
        learn.record_approval(mem_store, _event())
        learn.record_void_reversal(mem_store, _void_event())
        row = next(
            r for r in mem_store.all_records() if r.signature_type == "vendor_category"
        )
        assert row.correction_count == 1


class TestRecordVoidReversalPersistent:
    def test_void_deactivates_row_at_zero(self, db_store):
        learn.record_approval(db_store, _event())
        learn.record_void_reversal(db_store, _void_event())

        row = db_store.get_map_row(1, "vendor_category", "BIM", "5")
        assert row is not None
        assert row.approval_count == 0
        assert row.is_active is False
        assert row.correction_count == 1
        assert db_store.list_for_signature(1, "vendor_category", "BIM") == ()

    def test_approval_then_void_round_trip(self, db_store):
        learn.record_approval(db_store, _event())
        learn.record_approval(db_store, _event())
        row = db_store.get_map_row(1, "vendor_category", "BIM", "5")
        assert row.approval_count == 2

        learn.record_void_reversal(db_store, _void_event())
        row = db_store.get_map_row(1, "vendor_category", "BIM", "5")
        assert row.approval_count == 1
        assert row.is_active is True

    def test_confidence_cached_drops_after_void(self, db_store):
        for _ in range(3):
            learn.record_approval(db_store, _event())
        before = db_store.get_map_row(1, "vendor_category", "BIM", "5").confidence_cached

        learn.record_void_reversal(db_store, _void_event())
        after = db_store.get_map_row(1, "vendor_category", "BIM", "5").confidence_cached
        assert after < before


class TestNoPostingOrHooks:
    def test_void_reversal_creates_no_expense_records(self, db_session, db_store):
        learn.record_approval(db_store, _event())
        learn.record_void_reversal(db_store, _void_event())
        assert db_session.query(models.ExpenseRecord).count() == 0
        assert db_session.query(models.JournalEntry).count() == 0

    def test_void_expense_not_wired_to_learning(self):
        from services import posting as posting_mod

        src = inspect.getsource(posting_mod.void_expense)
        assert "receipt_learning" not in src
        assert "record_void_reversal" not in src

    def test_reconcile_alias_is_record_void_reversal(self):
        assert learn.reconcile_voided_receipt_learning is learn.record_void_reversal
