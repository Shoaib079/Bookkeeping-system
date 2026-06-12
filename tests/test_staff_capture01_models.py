"""SC-P1 model tests — ExpenseDraft and DraftAttachment."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        co = models.Company(
            name="Co",
            slug="co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        user = models.User(
            username="u1",
            display_name="U1",
            password_hash="x",
            role="cashier",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.add(user)
        s.commit()
        s.add(
            models.CompanyUser(
                company_id=co.id,
                user_id=user.id,
                role="cashier",
                is_active=True,
                created_at=datetime.datetime.now(),
            )
        )
        s.commit()
        yield s, co.id, user.id


def test_expense_draft_spine_columns(session):
    db, company_id, user_id = session
    now = datetime.datetime.now()
    row = models.ExpenseDraft(
        company_id=company_id,
        created_by_id=user_id,
        status="draft",
        created_at=now,
        submitted_note="note at submit",
        date=datetime.date.today(),
        amount=10.0,
        currency="USD",
        payment_method="Cash",
        description="test",
    )
    db.add(row)
    db.commit()
    loaded = db.get(models.ExpenseDraft, row.id)
    assert loaded.submitted_note == "note at submit"
    assert loaded.expense_record_id is None


def test_draft_attachment_links_expense_draft(session):
    db, company_id, user_id = session
    draft = models.ExpenseDraft(
        company_id=company_id,
        created_by_id=user_id,
        status="draft",
        created_at=datetime.datetime.now(),
        date=datetime.date.today(),
        amount=5.0,
        currency="USD",
        payment_method="Cash",
    )
    db.add(draft)
    db.commit()
    att = models.DraftAttachment(
        company_id=company_id,
        uploaded_by_id=user_id,
        created_at=datetime.datetime.now(),
        draft_type="expense",
        draft_id=draft.id,
        file_path="uploads/1/drafts/2026-06/x.jpg",
        original_name="receipt.jpg",
        mime="image/jpeg",
        size_bytes=100,
        sha256="a" * 64,
    )
    db.add(att)
    db.commit()
    assert db.query(models.DraftAttachment).count() == 1
