"""Tests for registry.member_roster — Phase 14D-F."""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from registry.member_roster import (
    compute_member_stats,
    filter_roster_entries,
    query_company_roster,
    roster_to_dataframe,
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


def _seed(db):
    co = models.Company(
        name="Acme",
        slug="acme",
        is_active=True,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(co)
    owner = models.User(
        username="owner1",
        display_name="Owner One",
        password_hash="x",
        role="viewer",
        is_active=True,
        last_login=datetime.datetime(2026, 6, 1, 10, 0, 0),
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    bob = models.User(
        username="bob",
        display_name="Bob",
        password_hash="x",
        role="viewer",
        is_active=True,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add_all([owner, bob])
    db.flush()
    db.add(
        models.CompanyUser(
            company_id=co.id,
            user_id=owner.id,
            role="owner",
            is_active=True,
            created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
            invited_by_id=None,
        )
    )
    db.add(
        models.CompanyUser(
            company_id=co.id,
            user_id=bob.id,
            role="cashier",
            is_active=False,
            created_at=datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc),
            invited_by_id=owner.id,
        )
    )
    db.commit()
    return co


def test_query_roster_includes_invited_by_and_last_login(db):
    co = _seed(db)
    entries = query_company_roster(db, co.id)
    assert len(entries) == 2
    by_user = {e.username: e for e in entries}
    assert by_user["owner1"].invited_by_label == "—"
    assert by_user["bob"].invited_by_label == "Owner One"
    assert "2026" in by_user["owner1"].last_login_label
    assert by_user["bob"].status == "Inactive"


def test_filter_roster_search_and_status(db):
    co = _seed(db)
    entries = query_company_roster(db, co.id)
    assert len(filter_roster_entries(entries, status="active_only")) == 1
    assert len(filter_roster_entries(entries, search="bob")) == 1
    assert len(filter_roster_entries(entries, role="owner")) == 1


def test_roster_dataframe_columns(db):
    co = _seed(db)
    entries = query_company_roster(db, co.id)
    df = roster_to_dataframe(entries)
    assert list(df.columns) == [
        "Username",
        "Display Name",
        "Role",
        "Status",
        "Last Login",
        "Added By",
        "Member Since",
    ]
    assert len(df) == 2


def test_member_stats(db):
    co = _seed(db)
    entries = query_company_roster(db, co.id)
    stats = compute_member_stats(entries)
    assert stats.total == 2
    assert stats.active == 1
    assert stats.inactive == 1
    assert stats.by_role["owner"] == 1
    assert stats.by_role["cashier"] == 1
