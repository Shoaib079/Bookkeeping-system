"""DSC-P1 model tests for ExternalSalesVerification."""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from services.daily_sales_close import (
    ExternalSalesSource,
    ExternalSalesTotals,
    get_active_verification,
    save_draft,
    verify_external_sales,
)


TEST_DATE = datetime.date(2026, 6, 5)


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        co = models.Company(
            name="Test Co",
            slug="test_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        user = models.User(
            username="mgr",
            display_name="Manager",
            password_hash="x",
            role="manager",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.add(user)
        s.commit()
        yield s, co.id, user.id


def test_model_create_draft_leaves_erp_and_variance_null(session):
    db, company_id, user_id = session
    row = models.ExternalSalesVerification(
        company_id=company_id,
        business_date=TEST_DATE,
        source_name="Terminal A",
        status="draft",
        created_by_id=user_id,
        created_at=datetime.datetime.now(),
        is_void=False,
        variance_acknowledged=False,
        attachment_count=0,
    )
    db.add(row)
    db.commit()

    saved = db.get(models.ExternalSalesVerification, row.id)
    assert saved.company_id == company_id
    assert saved.erp_total is None
    assert saved.variance_total is None
    assert saved.within_tolerance is None
    assert saved.sale_count_snapshot is None


def test_save_draft_persists_null_erp_snapshot(session):
    db, company_id, user_id = session
    result = save_draft(
        db,
        company_id,
        TEST_DATE,
        ExternalSalesSource(source_name="POS Export"),
        ExternalSalesTotals(external_total=100.0),
        user_id,
    )
    assert result.ok
    row = db.get(models.ExternalSalesVerification, result.record_id)
    assert row.erp_total is None
    assert row.variance_type is None


def test_verify_populates_erp_snapshot(session):
    db, company_id, user_id = session
    result = save_draft(
        db,
        company_id,
        TEST_DATE,
        ExternalSalesSource(source_name="Manual"),
        ExternalSalesTotals(external_total=0.0),
        user_id,
    )
    verify = verify_external_sales(db, company_id, result.record_id, user_id)
    assert verify.ok
    row = db.get(models.ExternalSalesVerification, verify.record_id)
    assert row.status == "verified"
    assert row.erp_total == 0.0
    assert row.variance_type == "balanced"
    assert row.within_tolerance is True
    assert row.sale_count_snapshot == 0


def test_default_branch_uniqueness_via_service(session):
    db, company_id, user_id = session
    first = save_draft(
        db,
        company_id,
        TEST_DATE,
        ExternalSalesSource(source_name="Source A", branch_location=""),
        ExternalSalesTotals(),
        user_id,
    )
    second = save_draft(
        db,
        company_id,
        TEST_DATE,
        ExternalSalesSource(source_name="Source B", branch_location="   "),
        ExternalSalesTotals(external_total=50.0),
        user_id,
    )
    assert first.ok
    assert second.ok
    assert second.record_id == first.record_id
    active = get_active_verification(db, company_id, TEST_DATE, branch=None)
    assert active is not None
    assert active.source_name == "Source B"
    assert active.external_total == 50.0


def test_different_branches_allow_two_active_rows(session):
    db, company_id, user_id = session
    default = save_draft(
        db,
        company_id,
        TEST_DATE,
        ExternalSalesSource(source_name="Main"),
        ExternalSalesTotals(external_total=10.0),
        user_id,
    )
    branch = save_draft(
        db,
        company_id,
        TEST_DATE,
        ExternalSalesSource(source_name="Branch POS", branch_location="Branch A"),
        ExternalSalesTotals(external_total=20.0),
        user_id,
    )
    assert default.ok
    assert branch.ok
    assert branch.record_id != default.record_id
