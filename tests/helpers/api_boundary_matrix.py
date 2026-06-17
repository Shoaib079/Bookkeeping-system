"""FASTAPI-REACT-07 — API write-path boundary dual-run helpers (test-only)."""

from __future__ import annotations

import datetime
import sys
from typing import Callable
from unittest.mock import MagicMock

import app as erp_app
import models
from db import Base
from registry.categories_seed import seed_default_categories_for_company
from registry.coa_seed import seed_chart_of_accounts_for_company
from services import commit_modes
from services import write_expenses as write_expenses_svc
from services import write_sales as write_sales_svc
from services import write_voids as write_voids_svc
from services.commit_modes import (
    POST_CASH_SALE_FAMILY,
    POST_EXPENSE_FAMILY,
    VOID_CASCADE_FAMILY,
    CommitMode,
)
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import Session, sessionmaker

from tests.helpers.commit_parity import (
    DEFAULT_TABLES,
    EXPENSE_TABLES,
    VOID_CASCADE_TABLES,
    assert_persisted_state_equal,
    dual_run_parity,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

POST_DATE = datetime.date(2026, 9, 15)
AMOUNT = 125.0
CURRENCY = "TRY"
PERFORMED_BY = "api-boundary-matrix"
VOID_REASON = "FR-07 void matrix pin"


def make_isolated_session_factory():
    """Return a factory that yields a fresh in-memory SQLite session + company id."""

    def factory() -> Session:
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        @sa_event.listens_for(SessionLocal, "before_flush")
        def _stamp(sess, ctx, instances):
            erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

        sess = SessionLocal()
        co = models.Company(
            name="API Boundary Co",
            slug="api_boundary_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        sess.add(co)
        sess.flush()
        seed_chart_of_accounts_for_company(sess, co.id)
        seed_default_categories_for_company(sess, co.id)
        sess.add(
            models.BankAccount(
                name="Main Bank",
                currency=CURRENCY,
                company_id=co.id,
                is_active=True,
                balance=10000.0,
                kind="bank",
            )
        )
        sess.commit()
        return sess

    return factory


def _cash_sale_via_write_service(session: Session, *, boundary: bool) -> int:
    commit_modes.reset_commit_modes_for_tests()
    if boundary:
        commit_modes.set_commit_mode_for_tests(POST_CASH_SALE_FAMILY, CommitMode.BOUNDARY)
    cid = session.query(models.Company).one().id
    result = write_sales_svc.create_and_post_sale(
        session,
        company_id=cid,
        user_id=1,
        performed_by=PERFORMED_BY,
        entry_date=POST_DATE,
        amount=AMOUNT,
        currency=CURRENCY,
        payment_method="Cash",
        notes="api matrix cash sale",
    )
    return result.sale_id


def _expense_via_write_service(session: Session, *, boundary: bool) -> int:
    commit_modes.reset_commit_modes_for_tests()
    if boundary:
        commit_modes.set_commit_mode_for_tests(POST_EXPENSE_FAMILY, CommitMode.BOUNDARY)
    cid = session.query(models.Company).one().id
    result = write_expenses_svc.create_and_post_expense(
        session,
        company_id=cid,
        user_id=1,
        performed_by=PERFORMED_BY,
        entry_date=POST_DATE,
        amount=AMOUNT,
        currency=CURRENCY,
        payment_method="Cash",
        notes="api matrix expense",
        category_name="Office",
    )
    return result.expense_id


def _void_sale_via_write_service(session: Session, sale_id: int, *, boundary: bool) -> None:
    commit_modes.reset_commit_modes_for_tests()
    if boundary:
        commit_modes.set_commit_mode_for_tests(VOID_CASCADE_FAMILY, CommitMode.BOUNDARY)
    cid = session.query(models.Company).one().id
    write_voids_svc.void_record(
        session,
        company_id=cid,
        performed_by=PERFORMED_BY,
        target_type="Sale",
        target_id=sale_id,
        reason=VOID_REASON,
    )


def dual_run_write_service_parity(
    *,
    internal_runner: Callable[[Session], None],
    boundary_runner: Callable[[Session], None],
    tables: tuple[type, ...],
    snapshot_kwargs: dict | None = None,
) -> tuple[dict, dict]:
    factory = make_isolated_session_factory()
    return dual_run_parity(
        session_factory=factory,
        internal_runner=internal_runner,
        boundary_runner=boundary_runner,
        tables=tables,
        snapshot_kwargs=snapshot_kwargs or {},
    )


def assert_cash_sale_write_parity() -> None:
    def internal(sess: Session) -> None:
        _cash_sale_via_write_service(sess, boundary=False)

    def boundary(sess: Session) -> None:
        _cash_sale_via_write_service(sess, boundary=True)

    left, right = dual_run_write_service_parity(
        internal_runner=internal,
        boundary_runner=boundary,
        tables=DEFAULT_TABLES,
        snapshot_kwargs={"include_audit_rows": True},
    )
    assert_persisted_state_equal(left, right)


def assert_expense_write_parity() -> None:
    def internal(sess: Session) -> None:
        _expense_via_write_service(sess, boundary=False)

    def boundary(sess: Session) -> None:
        _expense_via_write_service(sess, boundary=True)

    left, right = dual_run_write_service_parity(
        internal_runner=internal,
        boundary_runner=boundary,
        tables=EXPENSE_TABLES,
        snapshot_kwargs={"include_expense_rows": True, "include_audit_rows": True},
    )
    assert_persisted_state_equal(left, right)


def assert_void_sale_write_parity() -> None:
    def internal(sess: Session) -> None:
        sale_id = _cash_sale_via_write_service(sess, boundary=False)
        _void_sale_via_write_service(sess, sale_id, boundary=False)

    def boundary(sess: Session) -> None:
        sale_id = _cash_sale_via_write_service(sess, boundary=False)
        _void_sale_via_write_service(sess, sale_id, boundary=True)

    left, right = dual_run_write_service_parity(
        internal_runner=internal,
        boundary_runner=boundary,
        tables=VOID_CASCADE_TABLES,
        snapshot_kwargs={
            "include_sale_void_rows": True,
            "include_audit_rows": True,
        },
    )
    assert_persisted_state_equal(left, right)


def seed_expense_for_void_rollback(session: Session) -> tuple[int, int]:
    """Return (company_id, expense_id) with a posted expense."""
    cid = session.query(models.Company).one().id
    exp_id = _expense_via_write_service(session, boundary=False)
    return cid, exp_id
