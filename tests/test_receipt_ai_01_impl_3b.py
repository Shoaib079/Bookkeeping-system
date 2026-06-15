"""RECEIPT-AI-01-IMPL-3b — block Card/Unknown draft approval until payment resolved."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from services import staff_capture as sc


@pytest.fixture()
def ctx():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as db:
        co = models.Company(
            name="Co",
            slug="co",
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
        db.add_all([co, cashier, manager])
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
                    company_id=co.id,
                    user_id=manager.id,
                    role="manager",
                    is_active=True,
                    created_at=datetime.datetime.now(),
                ),
            ]
        )
        cat = models.TransactionCategory(
            company_id=co.id,
            transaction_type="Expense",
            name="Meals",
            is_active=True,
        )
        db.add(cat)
        db.commit()
        yield {
            "db": db,
            "company_id": co.id,
            "cashier_id": cashier.id,
            "manager_id": manager.id,
            "category_id": cat.id,
        }


def _payload(category_id: int, payment_method: str = "Cash") -> sc.ExpenseDraftInput:
    return sc.ExpenseDraftInput(
        date=datetime.date.today(),
        amount=42.0,
        currency="USD",
        payment_method=payment_method,
        tx_category_id=category_id,
        tx_subcategory_id=None,
        description="Team lunch",
    )


def _submitted_draft_id(ctx, payment_method: str = "Cash") -> int:
    created = sc.create_expense_draft(
        ctx["db"],
        ctx["company_id"],
        ctx["cashier_id"],
        _payload(ctx["category_id"], payment_method=payment_method),
    )
    assert created.ok
    draft_id = created.record_id
    if payment_method == "Cash":
        submitted = sc.submit_expense_draft(
            ctx["db"], ctx["company_id"], draft_id, ctx["cashier_id"]
        )
        assert submitted.ok
        return draft_id
    row = ctx["db"].get(models.ExpenseDraft, draft_id)
    row.status = "submitted"
    row.submitted_at = datetime.datetime.now()
    ctx["db"].commit()
    return draft_id


def _counts(db) -> tuple[int, int, int]:
    return (
        db.query(models.ExpenseRecord).count(),
        db.query(models.JournalEntry).count(),
        db.query(models.BankTransaction).count(),
    )


class TestValidateApprovalPayment:
    def test_cash_allowed(self):
        assert sc.validate_approval_payment_method("Cash") is None

    @pytest.mark.parametrize("method", ("Card", "Unknown"))
    def test_non_cash_blocked(self, method):
        assert sc.validate_approval_payment_method(method) == sc.APPROVAL_PAYMENT_RESOLVE_MSG


class TestApprovalPaymentGuard:
    def test_cash_draft_approves_as_before(self, ctx):
        draft_id = _submitted_draft_id(ctx, "Cash")
        before = _counts(ctx["db"])

        def post_fn(session, view: sc.ExpenseDraftView) -> sc.ExpensePostResult:
            record = models.ExpenseRecord(
                date=view.date,
                expense_type="Meals",
                amount=view.amount,
                payment_method=view.payment_method,
                company_id=view.company_id,
            )
            session.add(record)
            session.flush()
            return sc.ExpensePostResult(expense_record_id=record.id)

        result = sc.approve_expense_draft(
            ctx["db"],
            ctx["company_id"],
            draft_id,
            ctx["manager_id"],
            post_fn=post_fn,
        )
        assert result.ok
        view = sc.get_expense_draft(ctx["db"], ctx["company_id"], draft_id)
        assert view.status == "approved"
        assert view.expense_record_id is not None
        after = _counts(ctx["db"])
        assert after[0] == before[0] + 1

    @pytest.mark.parametrize("method", ("Card", "Unknown"))
    def test_non_cash_draft_cannot_approve(self, ctx, method):
        draft_id = _submitted_draft_id(ctx, method)
        post_fn = MagicMock(return_value=sc.ExpensePostResult(expense_record_id=99))
        before_exp, before_je, before_bt = _counts(ctx["db"])

        result = sc.approve_expense_draft(
            ctx["db"],
            ctx["company_id"],
            draft_id,
            ctx["manager_id"],
            post_fn=post_fn,
        )
        assert not result.ok
        assert result.error == sc.APPROVAL_PAYMENT_RESOLVE_MSG
        post_fn.assert_not_called()

        view = sc.get_expense_draft(ctx["db"], ctx["company_id"], draft_id)
        assert view.status == "submitted"
        assert view.expense_record_id is None
        assert view.reviewed_by_id is None

        after_exp, after_je, after_bt = _counts(ctx["db"])
        assert after_exp == before_exp == 0
        assert after_je == before_je == 0
        assert after_bt == before_bt == 0

    def test_posting_seam_blocks_non_cash(self, ctx):
        import app as erp_app

        view = sc.ExpenseDraftView(
            id=1,
            company_id=ctx["company_id"],
            created_by_id=ctx["cashier_id"],
            status="submitted",
            created_at=datetime.datetime.now(),
            submitted_at=datetime.datetime.now(),
            submitted_note=None,
            reviewed_by_id=None,
            reviewed_at=None,
            review_note=None,
            expense_record_id=None,
            date=datetime.date.today(),
            amount=42.0,
            currency="USD",
            payment_method="Card",
            tx_category_id=ctx["category_id"],
            tx_subcategory_id=None,
            description="test",
        )
        before = _counts(ctx["db"])
        result = erp_app._staff_capture_post_expense_draft(ctx["db"], view)
        assert not result.ok
        assert result.error == sc.APPROVAL_PAYMENT_RESOLVE_MSG
        after = _counts(ctx["db"])
        assert after == before
