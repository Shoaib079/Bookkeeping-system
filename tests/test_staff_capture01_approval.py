"""SC-P1 approval tests — injected post_fn, separation of duties, idempotency."""

from __future__ import annotations

import datetime

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


def _payload(category_id: int) -> sc.ExpenseDraftInput:
    return sc.ExpenseDraftInput(
        date=datetime.date.today(),
        amount=42.0,
        currency="USD",
        payment_method="Cash",
        tx_category_id=category_id,
        tx_subcategory_id=None,
        description="Team lunch",
    )


def _submit_draft(ctx) -> int:
    created = sc.create_expense_draft(
        ctx["db"],
        ctx["company_id"],
        ctx["cashier_id"],
        _payload(ctx["category_id"]),
    )
    sc.submit_expense_draft(
        ctx["db"], ctx["company_id"], created.record_id, ctx["cashier_id"]
    )
    return created.record_id


class TestApproval:
    def test_self_approval_rejected(self, ctx):
        created = sc.create_expense_draft(
            ctx["db"],
            ctx["company_id"],
            ctx["manager_id"],
            _payload(ctx["category_id"]),
        )
        sc.submit_expense_draft(
            ctx["db"], ctx["company_id"], created.record_id, ctx["manager_id"]
        )
        result = sc.approve_expense_draft(
            ctx["db"],
            ctx["company_id"],
            created.record_id,
            ctx["manager_id"],
            post_fn=lambda _s, _v: sc.ExpensePostResult(expense_record_id=1),
        )
        assert not result.ok
        assert "own draft" in result.error.lower()

    def test_approve_with_injected_post_fn(self, ctx):
        draft_id = _submit_draft(ctx)
        posted_ids: list[int] = []

        def post_fn(session, view: sc.ExpenseDraftView) -> sc.ExpensePostResult:
            record = models.ExpenseRecord(
                date=view.date,
                expense_type="Meals",
                category="Office Expense",
                description=view.description,
                amount=view.amount,
                payment_method=view.payment_method,
                company_id=view.company_id,
                created_by_id=view.created_by_id,
                currency=view.currency,
            )
            session.add(record)
            session.flush()
            posted_ids.append(record.id)
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
        assert view.expense_record_id == posted_ids[0]
        assert ctx["db"].get(models.ExpenseRecord, posted_ids[0]) is not None

    def test_idempotent_approve(self, ctx):
        draft_id = _submit_draft(ctx)
        calls = 0

        def post_fn(session, view: sc.ExpenseDraftView) -> sc.ExpensePostResult:
            nonlocal calls
            calls += 1
            record = models.ExpenseRecord(
                date=view.date,
                expense_type="Meals",
                amount=view.amount,
                payment_method="Cash",
                company_id=view.company_id,
            )
            session.add(record)
            session.flush()
            return sc.ExpensePostResult(expense_record_id=record.id)

        first = sc.approve_expense_draft(
            ctx["db"],
            ctx["company_id"],
            draft_id,
            ctx["manager_id"],
            post_fn=post_fn,
        )
        second = sc.approve_expense_draft(
            ctx["db"],
            ctx["company_id"],
            draft_id,
            ctx["manager_id"],
            post_fn=post_fn,
        )
        assert first.ok and second.ok
        assert calls == 1
        assert ctx["db"].query(models.ExpenseRecord).count() == 1

    def test_post_fn_error_surfaces(self, ctx):
        draft_id = _submit_draft(ctx)

        def post_fn(_session, _view):
            return sc.ExpensePostResult(expense_record_id=None, error="Closed period.")

        result = sc.approve_expense_draft(
            ctx["db"],
            ctx["company_id"],
            draft_id,
            ctx["manager_id"],
            post_fn=post_fn,
        )
        assert not result.ok
        assert "Closed period" in result.error
        view = sc.get_expense_draft(ctx["db"], ctx["company_id"], draft_id)
        assert view.status == "submitted"
        assert view.expense_record_id is None

    def test_post_fn_value_error_surfaces(self, ctx):
        draft_id = _submit_draft(ctx)

        def post_fn(_session, _view):
            raise ValueError("Fiscal period is closed.")

        result = sc.approve_expense_draft(
            ctx["db"],
            ctx["company_id"],
            draft_id,
            ctx["manager_id"],
            post_fn=post_fn,
        )
        assert not result.ok
        assert "closed" in result.error.lower()

    def test_list_submitted_for_manager(self, ctx):
        draft_id = _submit_draft(ctx)
        rows = sc.list_submitted_expense_drafts(
            ctx["db"], ctx["company_id"], ctx["manager_id"]
        )
        assert any(r.id == draft_id for r in rows)

    def test_audit_log_on_approve(self, ctx):
        draft_id = _submit_draft(ctx)

        def post_fn(session, view):
            record = models.ExpenseRecord(
                date=view.date,
                expense_type="Meals",
                amount=view.amount,
                payment_method="Cash",
                company_id=view.company_id,
            )
            session.add(record)
            session.flush()
            return sc.ExpensePostResult(expense_record_id=record.id)

        sc.approve_expense_draft(
            ctx["db"],
            ctx["company_id"],
            draft_id,
            ctx["manager_id"],
            post_fn=post_fn,
        )
        row = (
            ctx["db"]
            .query(models.AuditLog)
            .filter(
                models.AuditLog.entity_type == "ExpenseDraft",
                models.AuditLog.action == "approve_expense_draft",
            )
            .first()
        )
        assert row is not None
