"""RECEIPT-AI-02-IMPL-5 — learned receipt prefill for Receipt Capture."""

from __future__ import annotations

import datetime
import inspect
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from registry.service import set_setting
from services import receipt_ai_adapter as adapter
from services import receipt_learning as learn
from services import receipt_learning_prefill as rlp
from services import staff_capture as sc
from services.receipt_learning_store import persistent_learning_store

ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "ui" / "staff_capture.py"
_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100


def _event(**kw) -> learn.ApprovalLearningEvent:
    base = dict(
        company_id=1,
        vendor_signature="BIM",
        expense_record_id=100,
        tx_category_id=5,
        tx_subcategory_id=None,
        payment_method="Cash",
        category_name="Groceries",
        amount=50.0,
        approved_at=datetime.datetime(2026, 6, 15, 10, 0, 0),
    )
    base.update(kw)
    return learn.ApprovalLearningEvent(**base)


def _seed_vendor_learning(
    store: learn.LearningStore,
    *,
    company_id: int,
    category_id: int,
    count: int = 5,
    payment: str = "Cash",
) -> None:
    for _ in range(count):
        learn.record_approval(
            store,
            _event(
                company_id=company_id,
                tx_category_id=category_id,
                payment_method=payment,
            ),
        )


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
        cat_a = models.TransactionCategory(
            company_id=co_a.id,
            transaction_type="Expense",
            name="Supplies",
            is_active=True,
        )
        cat_b = models.TransactionCategory(
            company_id=co_b.id,
            transaction_type="Expense",
            name="Other",
            is_active=True,
        )
        db.add_all([cat_a, cat_b])
        db.commit()
        yield {
            "db": db,
            "company_a": co_a.id,
            "company_b": co_b.id,
            "cashier_id": cashier.id,
            "category_a": cat_a.id,
            "category_b": cat_b.id,
            "uploads": uploads,
        }


def _enable_capture(db, company_id: int) -> None:
    set_setting(db, adapter.RECEIPT_CAPTURE_SETTING, True, company_id=company_id)
    db.commit()


class TestPrefillService:
    def test_high_confidence_prefills_category(self, ctx):
        db, company_id, category_id = ctx["db"], ctx["company_a"], ctx["category_a"]
        store = persistent_learning_store(db)
        _seed_vendor_learning(store, company_id=company_id, category_id=category_id, count=5)

        learned = rlp.get_learned_receipt_suggestion(db, company_id, "BIM")
        assert learned is not None
        assert learned.prefill_category is True
        assert learned.suggested_category_id == category_id
        assert learned.category_tier in rlp.PREFILL_ELIGIBLE_TIERS
        assert learned.category_confidence is not None
        assert learned.category_confidence >= 80.0

    def test_low_confidence_does_not_prefill(self, ctx):
        db, company_id, category_id = ctx["db"], ctx["company_a"], ctx["category_a"]
        store = persistent_learning_store(db)
        _seed_vendor_learning(store, company_id=company_id, category_id=category_id, count=1)

        learned = rlp.get_learned_receipt_suggestion(db, company_id, "BIM")
        assert learned is not None
        assert learned.prefill_category is False
        assert learned.suggested_category_id is None
        assert learned.category_tier == learn.TIER_MANUAL

    def test_company_isolation(self, ctx):
        db = ctx["db"]
        store = persistent_learning_store(db)
        _seed_vendor_learning(
            store, company_id=ctx["company_a"], category_id=ctx["category_a"], count=5
        )
        _seed_vendor_learning(
            store, company_id=ctx["company_b"], category_id=ctx["category_b"], count=5
        )

        learned_a = rlp.get_learned_receipt_suggestion(db, ctx["company_a"], "BIM")
        learned_b = rlp.get_learned_receipt_suggestion(db, ctx["company_b"], "BIM")
        assert learned_a.suggested_category_id == ctx["category_a"]
        assert learned_b.suggested_category_id == ctx["category_b"]

    def test_payment_suggestion_is_advisory_only(self, ctx):
        db, company_id, category_id = ctx["db"], ctx["company_a"], ctx["category_a"]
        store = persistent_learning_store(db)
        _seed_vendor_learning(
            store,
            company_id=company_id,
            category_id=category_id,
            count=5,
            payment="Card",
        )

        learned = rlp.get_learned_receipt_suggestion(db, company_id, "BIM")
        assert learned.suggested_payment_method == "Card"
        assert learned.payment_advisory_only is True
        assert "payment:Card" in " ".join(learned.evidence)
        assert "advisory" in " ".join(learned.evidence)

    def test_apply_prefill_respects_user_category(self, ctx):
        learned = rlp.LearnedReceiptSuggestion(
            vendor_signature="BIM",
            suggested_category_id=ctx["category_a"],
            prefill_category=True,
        )
        cat, sub = rlp.apply_learned_category_prefill(
            learned, tx_category_id=99, tx_subcategory_id=None
        )
        assert cat == 99
        assert sub is None


class TestCaptureDraftPrefill:
    def test_learned_category_applied_when_not_provided(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_a"],
            ctx["cashier_id"],
            ctx["category_a"],
            ctx["uploads"],
        )
        _enable_capture(db, company_id)
        store = persistent_learning_store(db)
        _seed_vendor_learning(store, company_id=company_id, category_id=category_id, count=5)

        result = adapter.create_receipt_capture_draft(
            db,
            company_id,
            cashier_id,
            vendor_text="BIM",
            receipt_date=datetime.date(2026, 6, 14),
            total_amount=40.0,
            currency="TRY",
            payment_method="Cash",
            tx_category_id=None,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
        )
        assert result.ok
        assert result.learned_prefill_applied is True
        view = sc.get_expense_draft(db, company_id, result.draft_id)
        assert view.tx_category_id == category_id

    def test_user_override_category_not_replaced(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_a"],
            ctx["cashier_id"],
            ctx["category_a"],
            ctx["uploads"],
        )
        _enable_capture(db, company_id)
        store = persistent_learning_store(db)
        _seed_vendor_learning(store, company_id=company_id, category_id=category_id, count=5)

        other_cat = models.TransactionCategory(
            company_id=company_id,
            transaction_type="Expense",
            name="Travel",
            is_active=True,
        )
        db.add(other_cat)
        db.commit()

        result = adapter.create_receipt_capture_draft(
            db,
            company_id,
            cashier_id,
            vendor_text="BIM",
            receipt_date=datetime.date.today(),
            total_amount=25.0,
            currency="TRY",
            payment_method="Cash",
            tx_category_id=other_cat.id,
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
        )
        assert result.ok
        view = sc.get_expense_draft(db, company_id, result.draft_id)
        assert view.tx_category_id == other_cat.id

    def test_no_auto_post_side_effects(self, ctx):
        db, company_id, cashier_id, category_id, uploads = (
            ctx["db"],
            ctx["company_a"],
            ctx["cashier_id"],
            ctx["category_a"],
            ctx["uploads"],
        )
        _enable_capture(db, company_id)
        store = persistent_learning_store(db)
        _seed_vendor_learning(store, company_id=company_id, category_id=category_id, count=5)

        result = adapter.create_receipt_capture_draft(
            db,
            company_id,
            cashier_id,
            vendor_text="BIM",
            receipt_date=datetime.date.today(),
            total_amount=30.0,
            currency="TRY",
            payment_method="Cash",
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
        )
        assert result.ok
        assert db.query(models.ExpenseRecord).count() == 0
        assert db.query(models.JournalEntry).count() == 0
        view = sc.get_expense_draft(db, company_id, result.draft_id)
        assert view.status == "draft"


class TestUiAndFlag:
    def test_feature_flag_still_gates_capture(self, ctx):
        db, company_id, cashier_id, uploads = (
            ctx["db"],
            ctx["company_a"],
            ctx["cashier_id"],
            ctx["uploads"],
        )
        store = persistent_learning_store(db)
        _seed_vendor_learning(
            store, company_id=company_id, category_id=ctx["category_a"], count=5
        )
        result = adapter.create_receipt_capture_draft(
            db,
            company_id,
            cashier_id,
            vendor_text="BIM",
            receipt_date=datetime.date.today(),
            total_amount=10.0,
            currency="TRY",
            payment_method="Cash",
            uploads_root=uploads,
            file_bytes=_JPEG,
            attachment_mime="image/jpeg",
        )
        assert not result.ok

    def test_ui_delegates_to_services(self):
        ui_src = UI_PATH.read_text(encoding="utf-8")
        start = ui_src.index("def _render_receipt_capture")
        end = ui_src.index("def _load_draft_into_session", start)
        block = ui_src[start:end]
        assert "get_learned_receipt_suggestion" in block
        assert "receipt_learning_prefill" not in block
        assert "record_approval" not in block
        for forbidden in (
            "approve_expense_draft",
            "submit_expense_draft",
            "create_journal_entry",
            "post_expense",
        ):
            assert forbidden not in block

    def test_prefill_service_no_streamlit(self):
        import ast

        src = (ROOT / "services" / "receipt_learning_prefill.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    roots.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        assert "streamlit" not in roots

    def test_tier_allows_prefill_helper(self):
        assert rlp.tier_allows_prefill(learn.TIER_PREFILL)
        assert not rlp.tier_allows_prefill(learn.TIER_MANUAL)
