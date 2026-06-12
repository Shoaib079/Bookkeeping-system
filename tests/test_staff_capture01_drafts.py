"""SC-P1 draft lifecycle and attachment tests."""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from services import staff_capture as sc

_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
_PDF = b"%PDF-1.4\n" + b"\x00" * 100


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
        manager = models.User(
            username="mgr",
            display_name="Mgr",
            password_hash="x",
            role="manager",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        db.add_all([co, co_b, cashier, manager])
        db.commit()
        for user, role in ((cashier, "cashier"), (manager, "manager")):
            db.add(
                models.CompanyUser(
                    company_id=co.id,
                    user_id=user.id,
                    role=role,
                    is_active=True,
                    created_at=datetime.datetime.now(),
                )
            )
        db.add(
            models.CompanyUser(
                company_id=co_b.id,
                user_id=cashier.id,
                role="cashier",
                is_active=True,
                created_at=datetime.datetime.now(),
            )
        )
        cat = models.TransactionCategory(
            company_id=co.id,
            transaction_type="Expense",
            name="Office",
            is_active=True,
        )
        db.add(cat)
        db.commit()
        yield {
            "db": db,
            "company_id": co.id,
            "company_b": co_b.id,
            "cashier_id": cashier.id,
            "manager_id": manager.id,
            "category_id": cat.id,
            "uploads": uploads,
        }


def _payload(category_id: int, amount: float = 25.0) -> sc.ExpenseDraftInput:
    return sc.ExpenseDraftInput(
        date=datetime.date.today(),
        amount=amount,
        currency="USD",
        payment_method="Cash",
        tx_category_id=category_id,
        tx_subcategory_id=None,
        description="Lunch",
    )


class TestPureTransitions:
    def test_legal_transitions(self):
        assert sc.can_transition("draft", "submitted")
        assert sc.can_transition("returned", "submitted")
        assert sc.can_transition("submitted", "approved")
        assert sc.can_transition("submitted", "rejected")
        assert sc.can_transition("submitted", "returned")

    def test_illegal_transitions(self):
        assert not sc.can_transition("draft", "approved")
        assert not sc.can_transition("approved", "submitted")
        assert not sc.can_transition("rejected", "draft")


class TestExpenseDraftLifecycle:
    def test_create_update_submit_without_attachment_warning(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        created = sc.create_expense_draft(
            db, company_id, cashier_id, _payload(category_id)
        )
        assert created.ok
        updated = sc.update_expense_draft(
            db,
            company_id,
            created.record_id,
            cashier_id,
            _payload(category_id, amount=30.0),
        )
        assert updated.ok
        submitted = sc.submit_expense_draft(
            db, company_id, created.record_id, cashier_id, submitted_note="Please review"
        )
        assert submitted.ok
        assert "attachment_recommended" in submitted.warnings
        view = sc.get_expense_draft(db, company_id, created.record_id)
        assert view.status == "submitted"
        assert view.submitted_note == "Please review"

    def test_cannot_edit_after_submitted(self, ctx):
        db, company_id, cashier_id, category_id = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["category_id"],
        )
        created = sc.create_expense_draft(
            db, company_id, cashier_id, _payload(category_id)
        )
        sc.submit_expense_draft(db, company_id, created.record_id, cashier_id)
        result = sc.update_expense_draft(
            db,
            company_id,
            created.record_id,
            cashier_id,
            _payload(category_id, amount=99.0),
        )
        assert not result.ok

    def test_return_resubmit_flow(self, ctx):
        db, company_id, cashier_id, manager_id, category_id = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["manager_id"],
            ctx["category_id"],
        )
        created = sc.create_expense_draft(
            db, company_id, cashier_id, _payload(category_id)
        )
        sc.submit_expense_draft(db, company_id, created.record_id, cashier_id)
        returned = sc.return_expense_draft(
            db, company_id, created.record_id, manager_id, "Need receipt"
        )
        assert returned.ok
        view = sc.get_expense_draft(db, company_id, created.record_id)
        assert view.status == "returned"
        resubmitted = sc.submit_expense_draft(db, company_id, created.record_id, cashier_id)
        assert resubmitted.ok
        assert sc.get_expense_draft(db, company_id, created.record_id).status == "submitted"

    def test_reject_is_terminal(self, ctx):
        db, company_id, cashier_id, manager_id, category_id = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["manager_id"],
            ctx["category_id"],
        )
        created = sc.create_expense_draft(
            db, company_id, cashier_id, _payload(category_id)
        )
        sc.submit_expense_draft(db, company_id, created.record_id, cashier_id)
        rejected = sc.reject_expense_draft(
            db, company_id, created.record_id, manager_id, review_note="Invalid"
        )
        assert rejected.ok
        again = sc.submit_expense_draft(db, company_id, created.record_id, cashier_id)
        assert not again.ok

    def test_staff_sees_own_only(self, ctx):
        db, company_id, cashier_id, manager_id, category_id = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["manager_id"],
            ctx["category_id"],
        )
        d1 = sc.create_expense_draft(db, company_id, cashier_id, _payload(category_id))
        d2 = sc.create_expense_draft(db, company_id, manager_id, _payload(category_id))
        cashier_list = sc.list_expense_drafts(db, company_id, cashier_id)
        assert {v.id for v in cashier_list} == {d1.record_id}

    def test_company_isolation(self, ctx):
        db, company_id, company_b, cashier_id, category_id = (
            ctx["db"],
            ctx["company_id"],
            ctx["company_b"],
            ctx["cashier_id"],
            ctx["category_id"],
        )
        created = sc.create_expense_draft(
            db, company_id, cashier_id, _payload(category_id)
        )
        assert sc.get_expense_draft(db, company_b, created.record_id) is None


class TestAttachments:
    def test_add_jpeg_attachment(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        draft_id = sc.create_expense_draft(
            db, company_id, cashier_id, _payload(category_id)
        ).record_id
        result = sc.add_draft_attachment(
            db,
            company_id,
            sc.EXPENSE_DRAFT_TYPE,
            draft_id,
            cashier_id,
            file_bytes=_JPEG,
            original_name="receipt.jpg",
            mime_type="image/jpeg",
            uploads_root=uploads,
        )
        assert result.ok
        atts = sc.list_draft_attachments(db, company_id, sc.EXPENSE_DRAFT_TYPE, draft_id)
        assert len(atts) == 1
        assert atts[0].mime == "image/jpeg"
        assert "uploads/" in atts[0].file_path

    def test_reject_spoofed_mime(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        draft_id = sc.create_expense_draft(
            db, company_id, cashier_id, _payload(category_id)
        ).record_id
        result = sc.add_draft_attachment(
            db,
            company_id,
            sc.EXPENSE_DRAFT_TYPE,
            draft_id,
            cashier_id,
            file_bytes=_PDF,
            original_name="fake.jpg",
            mime_type="image/jpeg",
            uploads_root=uploads,
        )
        assert not result.ok

    def test_reject_oversize(self, ctx):
        err = sc.validate_attachment_bytes(b"x" * (sc.MAX_ATTACHMENT_BYTES + 1), declared_mime="image/png")
        assert err is not None

    def test_traversal_original_name_sanitized(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        draft_id = sc.create_expense_draft(
            db, company_id, cashier_id, _payload(category_id)
        ).record_id
        result = sc.add_draft_attachment(
            db,
            company_id,
            sc.EXPENSE_DRAFT_TYPE,
            draft_id,
            cashier_id,
            file_bytes=_PNG,
            original_name="../../etc/passwd",
            mime_type="image/png",
            uploads_root=uploads,
        )
        assert result.ok
        att = sc.list_draft_attachments(db, company_id, sc.EXPENSE_DRAFT_TYPE, draft_id)[0]
        assert ".." not in att.original_name

    def test_cannot_attach_after_submit(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_id"],
            ctx["cashier_id"],
            ctx["category_id"],
            ctx["uploads"],
        )
        draft_id = sc.create_expense_draft(
            db, company_id, cashier_id, _payload(category_id)
        ).record_id
        sc.submit_expense_draft(db, company_id, draft_id, cashier_id)
        result = sc.add_draft_attachment(
            db,
            company_id,
            sc.EXPENSE_DRAFT_TYPE,
            draft_id,
            cashier_id,
            file_bytes=_JPEG,
            original_name="late.jpg",
            mime_type="image/jpeg",
            uploads_root=uploads,
        )
        assert not result.ok


class TestMigrationReadiness:
    SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "staff_capture.py"

    def test_service_imports_no_streamlit_or_app(self):
        source = self.SERVICE_PATH.read_text(encoding="utf-8")
        assert "import streamlit" not in source
        assert "from streamlit" not in source
        assert "import app" not in source
        assert "from app" not in source

    def test_sniff_mime_helpers(self):
        assert sc.sniff_mime(_JPEG) == "image/jpeg"
        assert sc.sniff_mime(_PDF) == "application/pdf"
