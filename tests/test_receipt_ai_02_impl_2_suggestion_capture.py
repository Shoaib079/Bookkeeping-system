"""RECEIPT-AI-02-IMPL-2 — original suggestion capture tests."""

from __future__ import annotations

import datetime
import json
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from registry.service import set_setting
from services import receipt_ai as rcpt
from services import receipt_ai_adapter as adapter
from services import receipt_learning as learn
from services import receipt_suggestion_capture as rsc
from services import staff_capture as sc

_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100


@pytest.fixture()
def ctx(tmp_path):
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    with Session() as db:
        co_a = models.Company(
            name="Co A",
            slug="co_a",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        co_b = models.Company(
            name="Co B",
            slug="co_b",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        cashier = models.User(
            username="cash",
            display_name="Cash",
            password_hash="x",
            role="cashier",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        db.add_all([co_a, co_b, cashier])
        db.commit()
        for company in (co_a, co_b):
            db.add(
                models.CompanyUser(
                    company_id=company.id,
                    user_id=cashier.id,
                    role="cashier",
                    is_active=True,
                    created_at=datetime.datetime.now(),
                )
            )
        cat = models.TransactionCategory(
            company_id=co_a.id,
            transaction_type="Expense",
            name="Supplies",
            is_active=True,
        )
        db.add(cat)
        db.commit()
        yield {
            "db": db,
            "company_a": co_a.id,
            "company_b": co_b.id,
            "cashier_id": cashier.id,
            "category_id": cat.id,
            "uploads": uploads,
        }


def _enable_capture(db, company_id: int) -> None:
    set_setting(db, adapter.RECEIPT_CAPTURE_SETTING, True, company_id=company_id)
    db.commit()


def _suggestion(**kw) -> rcpt.DraftSuggestion:
    ext = rcpt.ReceiptExtraction(
        vendor_text=kw.pop("vendor_text", "BIM"),
        receipt_date=kw.pop("receipt_date", datetime.date(2026, 6, 14)),
        total_amount=kw.pop("total_amount", 55.0),
        currency=kw.pop("currency", "TRY"),
        confidence=0.9,
        payment_method="Cash",
        payment_confidence=0.9,
        payment_evidence=["NAKIT"],
    )
    return rcpt.map_extraction_to_draft_suggestion(
        ext,
        existing_tx_category_id=kw.pop("existing_tx_category_id", None),
        vendor_exists=kw.pop("vendor_exists", False),
    )


class TestModelSchema:
    def test_receipt_draft_suggestion_table_exists(self, ctx):
        db = ctx["db"]
        assert db.query(models.ReceiptDraftSuggestion).count() == 0
        assert hasattr(models, "ReceiptDraftSuggestion")


class TestCaptureService:
    def test_capture_matches_draft_suggestion(self, ctx):
        db, company_id, cashier_id = ctx["db"], ctx["company_a"], ctx["cashier_id"]
        suggestion = _suggestion(existing_tx_category_id=ctx["category_id"])
        result = rsc.capture_draft_suggestion(
            db,
            company_id,
            draft_id=42,
            suggestion=suggestion,
            created_by_id=cashier_id,
            source="manual",
            attachment_sha256="a" * 64,
            vendor_text="BIM Market",
        )
        assert result.ok
        view = rsc.get_captured_suggestion(db, company_id, 42)
        assert view is not None
        assert view.vendor_signature == "BIM"
        assert view.suggested_category_id == suggestion.tx_category_id
        assert view.suggested_payment_method == "Cash"
        assert view.suggested_payment_confidence == pytest.approx(0.9)
        assert view.snapshot["suggestion"] == suggestion.to_dict()
        json.dumps(view.to_dict())

    def test_second_capture_does_not_overwrite(self, ctx):
        db, company_id, cashier_id = ctx["db"], ctx["company_a"], ctx["cashier_id"]
        s1 = _suggestion(existing_tx_category_id=5)
        s2 = _suggestion(existing_tx_category_id=9)
        rsc.capture_draft_suggestion(
            db, company_id, 7, s1, created_by_id=cashier_id, source="manual"
        )
        again = rsc.capture_draft_suggestion(
            db, company_id, 7, s2, created_by_id=cashier_id, source="manual"
        )
        assert not again.captured
        view = rsc.get_captured_suggestion(db, company_id, 7)
        assert view.suggested_category_id == 5

    def test_company_isolation(self, ctx):
        db = ctx["db"]
        suggestion = _suggestion()
        rsc.capture_draft_suggestion(
            db,
            ctx["company_a"],
            1,
            suggestion,
            created_by_id=ctx["cashier_id"],
            source="manual",
        )
        assert rsc.get_captured_suggestion(db, ctx["company_b"], 1) is None


class TestReceiptCaptureWiring:
    def test_suggestion_captured_on_receipt_draft_create(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_a"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        _enable_capture(db, company_id)
        result = adapter.create_receipt_capture_draft(
            db,
            company_id,
            cashier_id,
            vendor_text="BIM",
            receipt_date=datetime.date(2026, 6, 14),
            total_amount=55.0,
            currency="TRY",
            payment_method="Cash",
            tx_category_id=category_id,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
            attachment_name="BIM_55_cash.jpg",
        )
        assert result.ok
        captured = rsc.get_captured_suggestion(db, company_id, result.draft_id)
        assert captured is not None
        assert captured.draft_id == result.draft_id
        assert captured.attachment_sha256 is not None
        assert len(captured.attachment_sha256) == 64
        assert captured.source == "manual"

        view = sc.get_expense_draft(db, company_id, result.draft_id)
        assert view.status == "draft"
        assert db.query(models.ExpenseRecord).count() == 0
        assert db.query(models.JournalEntry).count() == 0

    def test_draft_edit_does_not_overwrite_capture(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_a"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        _enable_capture(db, company_id)
        created = adapter.create_receipt_capture_draft(
            db,
            company_id,
            cashier_id,
            vendor_text="BIM",
            receipt_date=datetime.date.today(),
            total_amount=40.0,
            currency="TRY",
            payment_method="Cash",
            tx_category_id=category_id,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
        )
        captured_before = rsc.get_captured_suggestion(db, company_id, created.draft_id)
        sc.update_expense_draft(
            db,
            company_id,
            created.draft_id,
            cashier_id,
            sc.ExpenseDraftInput(
                date=datetime.date.today(),
                amount=99.0,
                currency="TRY",
                payment_method="Cash",
                tx_category_id=category_id,
                tx_subcategory_id=None,
                description="Edited vendor",
            ),
        )
        captured_after = rsc.get_captured_suggestion(db, company_id, created.draft_id)
        assert captured_after.suggested_category_id == captured_before.suggested_category_id
        assert captured_after.snapshot == captured_before.snapshot

    def test_no_learning_in_this_slice(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_a"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        _enable_capture(db, company_id)
        store = learn.InMemoryLearningStore()
        learn_fn = MagicMock(wraps=learn.record_approval)
        adapter.create_receipt_capture_draft(
            db,
            company_id,
            cashier_id,
            vendor_text="BIM",
            receipt_date=datetime.date.today(),
            total_amount=40.0,
            currency="TRY",
            payment_method="Cash",
            tx_category_id=category_id,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
        )
        learn_fn.assert_not_called()
        assert store.all_records() == ()

    def test_sample_extractor_source(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_a"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        _enable_capture(db, company_id)
        result = adapter.create_receipt_capture_draft(
            db,
            company_id,
            cashier_id,
            currency="TRY",
            tx_category_id=category_id,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
            attachment_name="BIM_450_cash.jpg",
            use_sample_extraction=True,
        )
        assert result.ok
        captured = rsc.get_captured_suggestion(db, company_id, result.draft_id)
        assert captured.source == "sample_extractor"
        assert captured.vendor_signature == "BIM"
        view = sc.get_expense_draft(db, company_id, result.draft_id)
        assert view.amount == 450.0
