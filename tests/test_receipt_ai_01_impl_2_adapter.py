"""RECEIPT-AI-01-IMPL-2 — adapter tests (DraftSuggestion → ExpenseDraft pipeline)."""

from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from services import receipt_ai as rcpt
from services import receipt_ai_adapter as adapter
from services import staff_capture as sc

_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100
_JPEG_B = b"\xff\xd8\xff\xe1" + b"\x01" * 100


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
        co = models.Company(
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
        db.add_all([co, co_b, cashier])
        db.commit()
        db.add_all(
            [
                models.CompanyUser(
                    company_id=co.id,
                    user_id=cashier.id,
                    role="cashier",
                    is_active=True,
                    created_at=datetime.datetime.now(),
                ),
                models.CompanyUser(
                    company_id=co_b.id,
                    user_id=cashier.id,
                    role="cashier",
                    is_active=True,
                    created_at=datetime.datetime.now(),
                ),
            ]
        )
        cat = models.TransactionCategory(
            company_id=co.id,
            transaction_type="Expense",
            name="Supplies",
            is_active=True,
        )
        db.add(cat)
        db.commit()
        yield {
            "db": db,
            "company_id": co.id,
            "company_b": co_b.id,
            "cashier_id": cashier.id,
            "category_id": cat.id,
            "uploads": uploads,
        }


def _extraction(**kw) -> rcpt.ReceiptExtraction:
    base = dict(
        vendor_text="BİM",
        receipt_date=datetime.date(2026, 6, 14),
        total_amount=55.0,
        currency="TRY",
        line_items=[rcpt.ReceiptLineItem(description="Ekmek", amount=5.0)],
        confidence=0.85,
        raw_text="BİM\nNAKİT",
    )
    base.update(kw)
    return rcpt.ReceiptExtraction(**base)


def _suggestion(**kw) -> rcpt.DraftSuggestion:
    map_keys = {
        "existing_tx_category_id",
        "existing_tx_subcategory_id",
        "vendor_exists",
        "known_item_descriptions",
        "payment_prefill_threshold",
    }
    ext_kw = {k: v for k, v in kw.items() if k not in map_keys}
    map_kw = {k: v for k, v in kw.items() if k in map_keys}
    ext = _extraction(**ext_kw)
    return rcpt.map_extraction_to_draft_suggestion(ext, **map_kw)


def _counts(db) -> tuple[int, int, int]:
    expenses = db.query(models.ExpenseRecord).count()
    journals = db.query(models.JournalEntry).count()
    drafts = db.query(models.ExpenseDraft).count()
    return expenses, journals, drafts


class TestSuggestionToInput:
    def test_confident_card_maps_to_card(self):
        ext = _extraction(
            payment_method="Card",
            payment_confidence=0.9,
            payment_evidence=["VISA"],
        )
        suggestion = rcpt.map_extraction_to_draft_suggestion(
            ext, existing_tx_category_id=3, vendor_exists=True
        )
        payload = adapter.suggestion_to_expense_draft_input(suggestion)
        assert payload.payment_method == "Card"
        assert payload.amount == 55.0
        assert payload.tx_category_id == 3

    def test_low_confidence_maps_to_unknown(self):
        ext = _extraction(payment_method="Unknown", payment_confidence=0.0)
        suggestion = rcpt.map_extraction_to_draft_suggestion(
            ext, existing_tx_category_id=3, vendor_exists=True
        )
        payload = adapter.suggestion_to_expense_draft_input(suggestion)
        assert payload.payment_method == "Unknown"


class TestCreateExpenseDraftFromSuggestion:
    def test_draft_created_with_draft_status(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        before_exp, before_je, before_drafts = _counts(db)
        suggestion = _suggestion(
            existing_tx_category_id=category_id,
            vendor_exists=True,
            payment_method="Cash",
            payment_confidence=0.9,
            payment_evidence=["NAKIT"],
        )
        result = adapter.create_expense_draft_from_suggestion(
            db,
            company_id,
            cashier_id,
            suggestion,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_name="receipt.jpg",
            attachment_mime="image/jpeg",
        )
        assert result.ok
        assert result.attachment_id is not None
        assert result.payment_prefilled is True

        view = sc.get_expense_draft(db, company_id, result.draft_id)
        assert view.status == "draft"
        assert view.expense_record_id is None
        assert view.payment_method == "Cash"
        assert view.amount == 55.0

        after_exp, after_je, after_drafts = _counts(db)
        assert after_exp == before_exp == 0
        assert after_je == before_je == 0
        assert after_drafts == before_drafts + 1

        atts = sc.list_draft_attachments(
            db, company_id, sc.EXPENSE_DRAFT_TYPE, result.draft_id
        )
        assert len(atts) == 1
        assert atts[0].company_id == company_id

    def test_no_posting_or_approval_side_effects(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        post_fn = MagicMock()
        suggestion = _suggestion(existing_tx_category_id=category_id, vendor_exists=True)
        result = adapter.create_expense_draft_from_suggestion(
            db, company_id, cashier_id, suggestion, uploads_root=uploads
        )
        assert result.ok
        post_fn.assert_not_called()
        approve = sc.approve_expense_draft(
            db, company_id, result.draft_id, cashier_id, post_fn=post_fn
        )
        assert not approve.ok
        assert db.query(models.ExpenseRecord).count() == 0
        assert db.query(models.JournalEntry).count() == 0

    def test_missing_vendor_category_item_are_suggestions_only(self, ctx):
        db, company_id, cashier_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["uploads"],
        )
        suggestion = _suggestion(
            existing_tx_category_id=None,
            vendor_exists=False,
            known_item_descriptions=[],
        )
        result = adapter.create_expense_draft_from_suggestion(
            db, company_id, cashier_id, suggestion, uploads_root=uploads
        )
        assert result.ok
        kinds = {c.kind for c in result.create_suggestions}
        assert "vendor" in kinds
        assert "category" in kinds
        assert "item" in kinds
        assert db.query(models.Vendor).count() == 0

        view = sc.get_expense_draft(db, company_id, result.draft_id)
        assert view.tx_category_id is None

    def test_company_isolation(self, ctx):
        db, company_id, company_b, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["company_b"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        suggestion = _suggestion(existing_tx_category_id=category_id, vendor_exists=True)
        result = adapter.create_expense_draft_from_suggestion(
            db, company_id, cashier_id, suggestion, uploads_root=uploads
        )
        assert result.ok
        assert sc.get_expense_draft(db, company_b, result.draft_id) is None

    def test_duplicate_attachment_detection(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        suggestion = _suggestion(existing_tx_category_id=category_id, vendor_exists=True)

        first = adapter.create_expense_draft_from_suggestion(
            db,
            company_id,
            cashier_id,
            suggestion,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
        )
        assert first.ok
        assert first.attachment_id is not None

        second = adapter.create_expense_draft_from_suggestion(
            db,
            company_id,
            cashier_id,
            suggestion,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
        )
        assert second.ok
        assert second.duplicate_attachment is True
        assert second.attachment_id is None
        assert "duplicate_attachment" in second.warnings
        atts = sc.list_draft_attachments(
            db, company_id, sc.EXPENSE_DRAFT_TYPE, second.draft_id
        )
        assert len(atts) == 0

    def test_different_file_not_duplicate(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        suggestion = _suggestion(existing_tx_category_id=category_id, vendor_exists=True)
        r1 = adapter.create_expense_draft_from_suggestion(
            db,
            company_id,
            cashier_id,
            suggestion,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
        )
        r2 = adapter.create_expense_draft_from_suggestion(
            db,
            company_id,
            cashier_id,
            suggestion,
            uploads_root=uploads,
            file_bytes=_JPEG_B,
            attachment_mime="image/jpeg",
        )
        assert r1.ok and r2.ok
        assert r2.duplicate_attachment is False
        assert r2.attachment_id is not None

    def test_payment_confidence_threshold_respected(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        ext = _extraction(
            payment_method="Card",
            payment_confidence=0.5,
            payment_evidence=["VISA"],
        )
        low = rcpt.map_extraction_to_draft_suggestion(
            ext, existing_tx_category_id=category_id, vendor_exists=True
        )
        low_result = adapter.create_expense_draft_from_suggestion(
            db, company_id, cashier_id, low, uploads_root=uploads
        )
        assert low_result.user_must_choose_payment is True
        low_view = sc.get_expense_draft(db, company_id, low_result.draft_id)
        assert low_view.payment_method == "Unknown"

        ext_hi = _extraction(
            payment_method="Card",
            payment_confidence=0.9,
            payment_evidence=["VISA"],
        )
        high = rcpt.map_extraction_to_draft_suggestion(
            ext_hi, existing_tx_category_id=category_id, vendor_exists=True
        )
        high_result = adapter.create_expense_draft_from_suggestion(
            db, company_id, cashier_id, high, uploads_root=uploads
        )
        assert high_result.payment_prefilled is True
        high_view = sc.get_expense_draft(db, company_id, high_result.draft_id)
        assert high_view.payment_method == "Card"

    def test_never_auto_submits(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        suggestion = _suggestion(existing_tx_category_id=category_id, vendor_exists=True)
        result = adapter.create_expense_draft_from_suggestion(
            db, company_id, cashier_id, suggestion, uploads_root=uploads
        )
        view = sc.get_expense_draft(db, company_id, result.draft_id)
        assert view.status == "draft"
        assert view.submitted_at is None

    def test_adapter_does_not_import_streamlit_or_app(self):
        path = Path(__file__).resolve().parents[1] / "services" / "receipt_ai_adapter.py"
        source = path.read_text(encoding="utf-8")
        assert "import streamlit" not in source
        assert "from streamlit" not in source
        assert "import app" not in source
        assert "approve_expense_draft" not in source
        assert "submit_expense_draft" not in source
