"""RECEIPT-AI-01-IMPL-3a — Staff Expenses receipt capture UI + service tests."""

from __future__ import annotations

import datetime
import inspect
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from registry.service import get_setting, set_setting
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


@pytest.fixture()
def ui_src() -> str:
    return UI_PATH.read_text(encoding="utf-8")


class TestFeatureFlag:
    def test_registry_default_off(self, ctx):
        db, company_id = ctx["db"], ctx["company_id"]
        assert get_setting(db, adapter.RECEIPT_CAPTURE_SETTING, company_id=company_id) is False
        assert adapter.is_receipt_capture_enabled(db, company_id) is False

    def test_flag_on_enables_capture(self, ctx):
        db, company_id = ctx["db"], ctx["company_id"]
        _enable_capture(db, company_id)
        assert adapter.is_receipt_capture_enabled(db, company_id) is True


class TestReceiptCaptureService:
    def test_flag_off_rejects_create(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        result = adapter.create_receipt_capture_draft(
            db,
            company_id,
            cashier_id,
            vendor_text="BIM",
            receipt_date=datetime.date(2026, 6, 14),
            total_amount=40.0,
            currency="TRY",
            payment_method="Cash",
            tx_category_id=category_id,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
        )
        assert not result.ok
        assert "not enabled" in result.error.lower()

    def test_manual_fields_create_draft_with_attachment(self, ctx):
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
            vendor_text="New Vendor",
            receipt_date=datetime.date(2026, 6, 14),
            total_amount=40.0,
            currency="TRY",
            payment_method="Cash",
            tx_category_id=category_id,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_name="receipt.jpg",
            attachment_mime="image/jpeg",
        )
        assert result.ok
        view = sc.get_expense_draft(db, company_id, result.draft_id)
        assert view.status == "draft"
        assert view.expense_record_id is None
        assert view.amount == 40.0
        assert db.query(models.ExpenseRecord).count() == 0
        assert db.query(models.JournalEntry).count() == 0
        atts = sc.list_draft_attachments(
            db, company_id, sc.EXPENSE_DRAFT_TYPE, result.draft_id
        )
        assert len(atts) == 1

    def test_missing_vendor_gives_create_suggestion_only(self, ctx):
        db, company_id, cashier_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["uploads"],
        )
        _enable_capture(db, company_id)
        result = adapter.create_receipt_capture_draft(
            db,
            company_id,
            cashier_id,
            vendor_text="Unknown Shop",
            receipt_date=datetime.date.today(),
            total_amount=12.0,
            currency="TRY",
            payment_method="Cash",
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
        )
        assert result.ok
        kinds = {c.kind for c in result.create_suggestions}
        assert "vendor" in kinds
        assert db.query(models.Vendor).count() == 0

    def test_card_draft_created_not_posted(self, ctx):
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
            vendor_text="BIM",
            receipt_date=datetime.date.today(),
            total_amount=20.0,
            currency="TRY",
            payment_method="Card",
            tx_category_id=category_id,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
        )
        assert result.ok
        view = sc.get_expense_draft(db, company_id, result.draft_id)
        assert view.payment_method == "Card"
        post_fn = MagicMock()
        approved = sc.approve_expense_draft(
            db, company_id, result.draft_id, ctx["cashier_id"], post_fn=post_fn
        )
        assert not approved.ok
        post_fn.assert_not_called()

    def test_unknown_payment_draft_created(self, ctx):
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
            vendor_text="BIM",
            receipt_date=datetime.date.today(),
            total_amount=20.0,
            currency="TRY",
            payment_method="Unknown",
            tx_category_id=category_id,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
        )
        assert result.ok
        view = sc.get_expense_draft(db, company_id, result.draft_id)
        assert view.payment_method == "Unknown"


class TestUiStructural:
    def test_feature_flag_gates_receipt_capture(self, ui_src: str):
        assert "is_receipt_capture_enabled" in ui_src
        assert "receipt_ai_adapter" in ui_src or "rcpt_adapt" in ui_src
        assert "sc.rcpt.section" in ui_src

    def test_receipt_capture_delegates_to_adapter(self, ui_src: str):
        assert "create_receipt_capture_draft" in ui_src
        assert "_render_receipt_capture" in ui_src

    def test_receipt_capture_has_no_posting(self, ui_src: str):
        start = ui_src.index("def _render_receipt_capture")
        end = ui_src.index("def _load_draft_into_session", start)
        block = ui_src[start:end]
        for forbidden in (
            "approve_expense_draft",
            "submit_expense_draft",
            "post_fn",
            "create_journal_entry",
            "post_expense",
        ):
            assert forbidden not in block, f"Receipt capture must not call {forbidden!r}"

    def test_submit_tab_still_requires_submit_permission(self, ui_src: str):
        assert '_can("submit_expense_drafts")' in ui_src
        assert "upload_receipts" in ui_src

    def test_renderer_signature_unchanged(self):
        from ui.staff_capture import render_staff_expense_capture

        params = list(inspect.signature(render_staff_expense_capture).parameters)
        assert params == ["session"]
