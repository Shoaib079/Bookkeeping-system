"""RECEIPT-AI-01-IMPL-3c — deterministic fake extractor + Receipt Capture wiring."""

from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from registry.service import set_setting
from services import receipt_ai as rcpt
from services import receipt_ai_adapter as adapter
from services import staff_capture as sc

ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "ui" / "staff_capture.py"

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
        co = models.Company(
            name="Co A",
            slug="co_a",
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
        db.add_all([co, cashier])
        db.commit()
        db.add(
            models.CompanyUser(
                company_id=co.id,
                user_id=cashier.id,
                role="cashier",
                is_active=True,
                created_at=datetime.datetime.now(),
            )
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
            "cashier_id": cashier.id,
            "category_id": cat.id,
            "uploads": uploads,
        }


def _enable_capture(db, company_id: int) -> None:
    set_setting(db, adapter.RECEIPT_CAPTURE_SETTING, True, company_id=company_id)
    db.commit()


class TestFakeExtractor:
    def test_bim_450_cash_filename(self):
        ext = rcpt.fake_receipt_extractor(filename="BIM_450_cash.jpg", default_currency="TRY")
        assert ext.vendor_text == "BIM"
        assert ext.total_amount == 450.0
        assert ext.payment_method == "Cash"
        assert ext.payment_confidence == 1.0

    def test_deterministic_same_input_same_output(self):
        kwargs = dict(filename="BIM_450_cash.jpg", text="extra", default_currency="TRY")
        a = rcpt.fake_receipt_extractor(**kwargs)
        b = rcpt.fake_receipt_extractor(**kwargs)
        assert a.to_dict() == b.to_dict()

    def test_extract_receipt_with_seam(self):
        ext = rcpt.extract_receipt_with(
            rcpt.fake_receipt_extractor,
            filename="BIM_450_card.png",
            default_currency="TRY",
        )
        assert isinstance(ext, rcpt.ReceiptExtraction)
        assert ext.vendor_text == "BIM"
        assert ext.total_amount == 450.0
        assert ext.payment_method == "Card"

    def test_optional_text_supplements_payment(self):
        ext = rcpt.fake_receipt_extractor(
            filename="SHOP_100.jpg",
            text="ÖDEME: NAKİT",
            default_currency="TRY",
        )
        assert ext.payment_method == "Cash"
        assert ext.payment_confidence > 0.6

    def test_testing_payload_override(self):
        ext = rcpt.fake_receipt_extractor(
            filename="ignored.jpg",
            payload={
                "vendor_text": "TestCo",
                "total_amount": 99.5,
                "payment_method": "Card",
                "payment_confidence": 0.95,
                "currency": "USD",
            },
        )
        assert ext.vendor_text == "TestCo"
        assert ext.total_amount == 99.5
        assert ext.payment_method == "Card"


class TestSampleExtractionDraft:
    def test_sample_extraction_creates_draft(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
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
            attachment_name="BIM_450_cash.jpg",
            attachment_mime="image/jpeg",
            use_sample_extraction=True,
        )
        assert result.ok
        view = sc.get_expense_draft(db, company_id, result.draft_id)
        assert view.status == "draft"
        assert view.amount == 450.0
        assert view.description == "BIM"
        assert view.payment_method == "Cash"
        assert db.query(models.ExpenseRecord).count() == 0
        assert db.query(models.JournalEntry).count() == 0

    def test_no_posting_side_effects(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
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
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_name="BIM_450_cash.jpg",
            attachment_mime="image/jpeg",
            use_sample_extraction=True,
        )
        assert result.ok
        post_fn = MagicMock()
        approved = sc.approve_expense_draft(
            db, company_id, result.draft_id, cashier_id, post_fn=post_fn
        )
        assert not approved.ok
        post_fn.assert_not_called()


class TestUiWiring:
    def test_sample_extraction_toggle_in_ui(self):
        src = UI_PATH.read_text(encoding="utf-8")
        assert "sc.rcpt.use_sample_extraction" in src
        assert "use_sample_extraction" in src

    def test_fake_extractor_in_service_not_ui(self):
        src = UI_PATH.read_text(encoding="utf-8")
        assert "fake_receipt_extractor" not in src
        assert "extract_receipt_with" not in src
