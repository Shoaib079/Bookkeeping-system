"""FASTAPI-REACT-07 — API write-path boundary matrix tests."""

from __future__ import annotations

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import func

import app as erp_app  # noqa: F401 — initialise module graph
import models
from services import commit_modes
from services import write_voids as write_voids_svc
from services.commit_modes import VOID_CASCADE_FAMILY, CommitMode
from tests.helpers.api_boundary_matrix import (
    VOID_REASON,
    assert_cash_sale_write_parity,
    assert_expense_write_parity,
    assert_void_sale_write_parity,
    make_isolated_session_factory,
    seed_expense_for_void_rollback,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock


@pytest.fixture(autouse=True)
def _reset_commit_modes():
    commit_modes.reset_commit_modes_for_tests()
    yield
    commit_modes.reset_commit_modes_for_tests()


class TestApiPostingBoundaryParity:
    def test_cash_sale_write_service_internal_vs_boundary_parity(self):
        assert_cash_sale_write_parity()

    def test_expense_write_service_internal_vs_boundary_parity(self):
        assert_expense_write_parity()


class TestApiVoidBoundaryParity:
    def test_void_sale_write_service_internal_vs_boundary_parity(self):
        assert_void_sale_write_parity()


class TestApiVoidBoundaryRollback:
    def test_void_expense_write_service_boundary_rollback_on_closed_period(self):
        factory = make_isolated_session_factory()
        session = factory()
        try:
            cid, exp_id = seed_expense_for_void_rollback(session)
            today = datetime.date.today()
            session.add(
                models.FiscalPeriod(
                    name="Closed today",
                    start_date=today,
                    end_date=today,
                    is_closed=True,
                    closed_at=today,
                    company_id=cid,
                )
            )
            session.commit()

            commit_modes.set_commit_mode_for_tests(VOID_CASCADE_FAMILY, CommitMode.BOUNDARY)
            with pytest.raises(ValueError):
                write_voids_svc.void_record(
                    session,
                    company_id=cid,
                    performed_by="matrix",
                    target_type="ExpenseRecord",
                    target_id=exp_id,
                    reason=VOID_REASON,
                )

            refreshed = session.get(models.ExpenseRecord, exp_id)
            assert refreshed is not None
            assert refreshed.is_void is False
            assert (
                session.query(func.count())
                .select_from(models.JournalEntry)
                .filter_by(reference_type="Reversal")
                .scalar()
                == 0
            )
        finally:
            session.close()

    def test_void_write_service_rejects_missing_reason_before_boundary(self):
        factory = make_isolated_session_factory()
        session = factory()
        try:
            cid, exp_id = seed_expense_for_void_rollback(session)
            commit_modes.set_commit_mode_for_tests(VOID_CASCADE_FAMILY, CommitMode.BOUNDARY)
            with pytest.raises(ValueError, match="Void reason is required"):
                write_voids_svc.void_record(
                    session,
                    company_id=cid,
                    performed_by="matrix",
                    target_type="ExpenseRecord",
                    target_id=exp_id,
                    reason="   ",
                )
            refreshed = session.get(models.ExpenseRecord, exp_id)
            assert refreshed.is_void is False
        finally:
            session.close()
