"""UA-P1 model tests — UserPermissionOverride."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from services.user_access import set_override


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
            role="manager",
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
                role="manager",
                is_active=True,
                created_at=datetime.datetime.now(),
            )
        )
        s.commit()
        yield s, co.id, user.id


def test_override_unique_per_user_company_key(session):
    db, company_id, user_id = session
    first = set_override(db, company_id, user_id, "manage_budget", "grant", user_id)
    assert first.ok
    second = set_override(db, company_id, user_id, "manage_budget", "deny", user_id)
    assert second.ok
    rows = (
        db.query(models.UserPermissionOverride)
        .filter(models.UserPermissionOverride.user_id == user_id)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].mode == "deny"
