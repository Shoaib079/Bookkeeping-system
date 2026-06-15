"""RECEIPT-AI-02-IMPL-3 — persistent receipt_learning_map + PersistentLearningStore."""

from __future__ import annotations

import datetime
import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, inspect as sa_inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from services import receipt_learning as learn
from services.receipt_learning_store import PersistentLearningStore, persistent_learning_store

_BASELINE = (
    Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0001_baseline.py"
)


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
    )
    base.update(kw)
    return learn.ApprovalLearningEvent(**base)


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
def store(db_session):
    return persistent_learning_store(db_session)


class TestModelSchema:
    def test_receipt_learning_map_table_exists(self, db_session):
        assert hasattr(models, "ReceiptLearningMap")
        assert db_session.query(models.ReceiptLearningMap).count() == 0
        tables = sa_inspect(db_session.bind).get_table_names()
        assert "receipt_learning_map" in tables

    def test_unique_constraint_blocks_duplicate_row(self, db_session):
        now = datetime.datetime.now()
        row = models.ReceiptLearningMap(
            company_id=1,
            signature_type="vendor_category",
            signature_key="BIM",
            target_kind="category_id",
            target_id=5,
            target_value="",
            approval_count=1,
            correction_count=0,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(row)
        db_session.commit()
        dup = models.ReceiptLearningMap(
            company_id=1,
            signature_type="vendor_category",
            signature_key="BIM",
            target_kind="category_id",
            target_id=5,
            target_value="",
            approval_count=2,
            correction_count=0,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(dup)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_store_increments_instead_of_duplicate_category_row(self, store):
        learn.record_approval(store, _event())
        learn.record_approval(store, _event())
        records = store.list_for_signature(1, "vendor_category", "BIM")
        assert len(records) == 1
        assert records[0].approval_count == 2

    def test_migrate_schema_indexes_declared(self):
        import app as erp_app

        src = inspect.getsource(erp_app.migrate_schema)
        assert "ix_rcptlearn_company_id" in src
        assert "ix_rcptlearn_signature" in src
        assert "receipt_learning_map" in src

    def test_alembic_baseline_contains_learning_map_indexes(self):
        text = _BASELINE.read_text(encoding="utf-8")
        assert "receipt_learning_map" in text
        assert "ix_rcptlearn_company_id" in text
        assert "ix_rcptlearn_signature" in text


class TestPersistentStoreRecordApproval:
    def test_increments_approval_count(self, store):
        learn.record_approval(store, _event())
        row = store.get_map_row(1, "vendor_category", "BIM", "5")
        assert row is not None
        assert row.approval_count == 1
        assert row.target_kind == "category_id"
        assert row.target_id == 5
        assert row.target_value == ""
        assert row.confidence_cached is not None

        learn.record_approval(store, _event())
        row2 = store.get_map_row(1, "vendor_category", "BIM", "5")
        assert row2.approval_count == 2

    def test_blank_vendor_not_written(self, store):
        result = learn.record_approval(store, _event(vendor_signature=""))
        assert not result.learned
        assert store.list_for_signature(1, "vendor_category", "BIM") == ()

    def test_company_isolation(self, store):
        learn.record_approval(store, _event(company_id=1, tx_category_id=5))
        learn.record_approval(store, _event(company_id=2, tx_category_id=9))
        sug_a = learn.suggest_for_vendor(store, 1, "BIM")
        sug_b = learn.suggest_for_vendor(store, 2, "BIM")
        assert sug_a is not None and sug_b is not None
        assert sug_a.category.target_value == "5"
        assert sug_b.category.target_value == "9"
        assert store.get_map_row(2, "vendor_category", "BIM", "5") is None

    def test_conflicting_category_lowers_confidence(self, store):
        for _ in range(3):
            learn.record_approval(store, _event(tx_category_id=5))
        learn.record_approval(store, _event(tx_category_id=9))

        dominant = learn.suggest_for_vendor(store, 1, "BIM")
        assert dominant.category.target_value == "5"
        dominant_conf = dominant.category.confidence

        records = store.list_for_signature(1, "vendor_category", "BIM")
        minority = next(r for r in records if r.target_value == "9")
        minority_conf = learn.calculate_confidence(
            approval_count=minority.approval_count,
            total_approvals_for_signature=sum(r.approval_count for r in records),
            approvals_for_target=minority.approval_count,
        )
        assert dominant_conf > minority_conf

    def test_payment_mapping_advisory_only(self, store):
        learn.record_approval(store, _event(payment_method="Card"))
        suggestion = learn.suggest_for_vendor(store, 1, "BIM")
        assert suggestion.payment_method is not None
        assert suggestion.payment_method.advisory_only is True
        assert suggestion.payment_method.target_value == "Card"
        pay_row = store.get_map_row(1, "vendor_payment", "BIM", "Card")
        assert pay_row is not None
        assert pay_row.target_kind == "payment_method"
        assert pay_row.target_id == -1
        assert pay_row.target_value == "Card"


class TestNoPostingOrApprovalWiring:
    def test_learning_alone_creates_no_expense_or_journal(self, db_session, store):
        learn.record_approval(store, _event())
        assert db_session.query(models.ExpenseRecord).count() == 0
        assert db_session.query(models.JournalEntry).count() == 0
        assert db_session.query(models.ExpenseDraft).count() == 0

    def test_approve_expense_draft_not_wired_to_learning(self):
        from services import staff_capture as sc

        src = inspect.getsource(sc.approve_expense_draft)
        assert "record_approval" not in src
        assert "receipt_learning" not in src

    def test_no_auto_post_helpers_in_learning_store(self):
        import services.receipt_learning_store as rls

        src = inspect.getsource(rls)
        assert "auto_post" not in src.lower()
        assert "create_journal_entry" not in src
        assert "post_expense" not in src


class TestStorePurity:
    def test_no_streamlit_import(self):
        import ast

        mod_tree = ast.parse(
            Path(__file__).resolve().parents[1]
            .joinpath("services", "receipt_learning_store.py")
            .read_text(encoding="utf-8")
        )
        roots = set()
        for node in ast.walk(mod_tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    roots.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        assert "streamlit" not in roots

    def test_implements_learning_store_protocol(self, store):
        assert hasattr(store, "list_for_signature")
        assert hasattr(store, "record_approval_hit")
        learn.record_approval(store, _event())
        records = store.list_for_signature(1, "vendor_category", "BIM")
        assert len(records) == 1
        assert records[0].target_value == "5"
