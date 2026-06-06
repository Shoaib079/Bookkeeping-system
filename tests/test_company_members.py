"""Tests for registry.company_members — Phase 14D-E."""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from registry.company_members import (
    add_existing_user_to_company,
    count_active_owners,
    create_user_for_company,
    remove_membership,
    update_membership,
    would_violate_last_owner_guard,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as session:
        yield session


def _company(db, slug="co1"):
    c = models.Company(
        name="Acme",
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(c)
    db.flush()
    return c


def _user(db, username="alice"):
    u = models.User(
        username=username,
        password_hash="x",
        role="viewer",
        is_active=True,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(u)
    db.flush()
    return u


def _member(db, company, user, role="owner", is_active=True):
    m = models.CompanyUser(
        company_id=company.id,
        user_id=user.id,
        role=role,
        is_active=is_active,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(m)
    db.flush()
    return m


def test_count_active_owners_per_company(db):
    co1, co2 = _company(db, "a"), _company(db, "b")
    u1, u2 = _user(db, "o1"), _user(db, "o2")
    _member(db, co1, u1, "owner")
    _member(db, co2, u2, "owner")
    assert count_active_owners(db, co1.id) == 1
    assert count_active_owners(db, co2.id) == 1


def test_last_owner_guard_blocks_demote(db):
    co = _company(db)
    u = _user(db)
    m = _member(db, co, u, "owner")
    assert would_violate_last_owner_guard(db, co.id, m, new_role="manager")


def test_last_owner_guard_allows_with_two_owners(db):
    co = _company(db)
    m1 = _member(db, co, _user(db, "o1"), "owner")
    _member(db, co, _user(db, "o2"), "owner")
    assert not would_violate_last_owner_guard(db, co.id, m1, new_role="manager")
    assert count_active_owners(db, co.id) == 2


def test_create_user_for_company_adds_membership(db):
    co = _company(db)
    inviter = _user(db, "boss")
    _member(db, co, inviter, "owner")
    user, membership = create_user_for_company(
        db,
        company_id=co.id,
        username="newhire",
        display_name="New Hire",
        password_hash="hash",
        role="cashier",
        invited_by_id=inviter.id,
    )
    db.commit()
    assert user.role == "viewer"
    assert membership.role == "cashier"
    assert membership.company_id == co.id


def test_add_existing_user_rejects_active_duplicate(db):
    co = _company(db)
    u = _user(db)
    _member(db, co, u, "viewer")
    with pytest.raises(ValueError, match="already a member"):
        add_existing_user_to_company(
            db, company_id=co.id, user=u, role="cashier", invited_by_id=1
        )


def test_add_existing_user_reactivates_inactive_membership(db):
    co = _company(db)
    u = _user(db)
    m = _member(db, co, u, "viewer", is_active=False)
    revived = add_existing_user_to_company(
        db, company_id=co.id, user=u, role="cashier", invited_by_id=99
    )
    db.commit()
    assert revived.id == m.id
    assert revived.is_active is True
    assert revived.role == "cashier"
    assert revived.invited_by_id == 99


def test_remove_membership_blocked_for_last_owner(db):
    co = _company(db)
    u = _user(db)
    m = _member(db, co, u, "owner")
    with pytest.raises(ValueError, match="last active owner"):
        remove_membership(db, co.id, m)


def test_remove_membership_allowed_with_two_owners(db):
    co = _company(db)
    m1 = _member(db, co, _user(db, "o1"), "owner")
    _member(db, co, _user(db, "o2"), "owner")
    remove_membership(db, co.id, m1)
    db.commit()
    assert db.query(models.CompanyUser).filter_by(company_id=co.id).count() == 1


def test_update_membership_deactivate_non_owner(db):
    co = _company(db)
    _member(db, co, _user(db, "boss"), "owner")
    u = _user(db, "bob")
    m = _member(db, co, u, "cashier")
    update_membership(db, co.id, m, role="viewer", is_active=False)
    db.commit()
    assert m.is_active is False
    assert m.role == "viewer"
