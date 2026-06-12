"""DSC-P1 service tests for External Sales Verification."""

from __future__ import annotations

import datetime
import inspect
import pathlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from services import daily_sales_close as svc


TEST_DATE = datetime.date(2026, 6, 5)
SERVICE_PATH = pathlib.Path(svc.__file__)


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
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
        user = models.User(
            username="mgr",
            display_name="Manager",
            password_hash="x",
            role="manager",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add_all([co_a, co_b, user])
        s.commit()
        yield s, co_a.id, co_b.id, user.id


def _add_sale(session, company_id, *, amount, sale_type="Cash", voided=False):
    sale = models.Sale(
        company_id=company_id,
        date=TEST_DATE,
        invoice_number=f"INV-{amount}",
        customer_name="Walk-in",
        amount=amount,
        sale_type=sale_type,
        status="Paid",
        is_void=voided,
    )
    session.add(sale)
    session.commit()


def _source(name="Terminal", branch=None, source_type=None):
    return svc.ExternalSalesSource(
        source_name=name,
        branch_location=branch,
        source_type=source_type,
    )


def _external(**kwargs):
    return svc.ExternalSalesTotals(**kwargs)


# ── Pure helpers ──────────────────────────────────────────────────────────────


class TestNormalizeBranch:
    def test_none_and_blank_become_none(self):
        assert svc.normalize_branch(None) is None
        assert svc.normalize_branch("") is None
        assert svc.normalize_branch("   ") is None

    def test_trimmed_text_preserved(self):
        assert svc.normalize_branch("  Branch A  ") == "Branch A"


class TestValidateExternalSource:
    def test_empty_source_name_rejected(self):
        assert svc.validate_external_source(_source(name="  ")) is not None

    def test_arbitrary_source_name_accepted(self):
        assert svc.validate_external_source(_source(name="Custom POS Export")) is None

    def test_invalid_source_type_rejected(self):
        err = svc.validate_external_source(_source(source_type="UNKNOWN"))
        assert err is not None

    def test_allowed_source_type_accepted(self):
        assert svc.validate_external_source(_source(source_type="POS")) is None


class TestValidateExternalTotals:
    def test_draft_allows_missing_totals(self):
        assert svc.validate_external_totals(_external(), for_verify=False) is None

    def test_verify_requires_at_least_one_total(self):
        err = svc.validate_external_totals(_external(), for_verify=True)
        assert err is not None

    def test_verify_allows_z_only(self):
        assert (
            svc.validate_external_totals(
                _external(z_report_total=100.0), for_verify=True
            )
            is None
        )

    def test_negative_total_rejected(self):
        err = svc.validate_external_totals(_external(external_total=-1.0))
        assert err is not None


class TestComputeVariance:
    def _erp(self, total=100.0, cash=40.0, card=30.0, credit=30.0):
        return svc.ErpSalesTotals(
            business_date=TEST_DATE,
            total=total,
            cash=cash,
            card=card,
            credit=credit,
            sale_count=3,
        )

    def test_balanced_within_tolerance(self):
        result = svc.compute_variance(
            _external(external_total=100.0), self._erp(), tolerance=0.01
        )
        assert result.within_tolerance is True
        assert result.variance_type == "balanced"

    def test_total_variance(self):
        result = svc.compute_variance(
            _external(external_total=110.0), self._erp(), tolerance=0.01
        )
        assert result.within_tolerance is False
        assert result.variance_type == "total_variance"
        assert result.variance_total == 10.0

    def test_cash_breakdown_variance(self):
        result = svc.compute_variance(
            _external(external_total=100.0, cash=50.0),
            self._erp(),
            tolerance=0.01,
        )
        assert result.variance_type == "cash_variance"
        assert result.variance_cash == 10.0

    def test_z_report_variance_only(self):
        result = svc.compute_variance(
            _external(z_report_total=90.0),
            self._erp(total=100.0),
            tolerance=0.01,
        )
        assert result.variance_total is None
        assert result.variance_type == "z_report_variance"
        assert result.z_report_variance == -10.0

    def test_multi_variance(self):
        result = svc.compute_variance(
            _external(external_total=110.0, cash=50.0),
            self._erp(),
            tolerance=0.01,
        )
        assert result.variance_type == "multi_variance"

    def test_breakdown_sum_warning_only(self):
        result = svc.compute_variance(
            _external(external_total=100.0, cash=60.0, card=50.0),
            self._erp(),
            tolerance=0.01,
        )
        assert result.breakdown_warnings

    def test_dto_serializable(self):
        result = svc.compute_variance(_external(external_total=100.0), self._erp())
        payload = result.to_dict()
        assert "within_tolerance" in payload
        assert isinstance(payload["breakdown_warnings"], list)


# ── ERP reads ─────────────────────────────────────────────────────────────────


class TestComputeErpSalesTotals:
    def test_empty_day(self, session):
        db, company_id, _, _ = session
        totals = svc.compute_erp_sales_totals(db, company_id, TEST_DATE)
        assert totals.total == 0.0
        assert totals.sale_count == 0

    def test_mixed_sale_types(self, session):
        db, company_id, _, _ = session
        _add_sale(db, company_id, amount=10.0, sale_type="Cash")
        _add_sale(db, company_id, amount=20.0, sale_type="Card")
        _add_sale(db, company_id, amount=30.0, sale_type="Credit")
        totals = svc.compute_erp_sales_totals(db, company_id, TEST_DATE)
        assert totals.total == 60.0
        assert totals.cash == 10.0
        assert totals.card == 20.0
        assert totals.credit == 30.0
        assert totals.sale_count == 3

    def test_voided_sales_excluded(self, session):
        db, company_id, _, _ = session
        _add_sale(db, company_id, amount=10.0)
        _add_sale(db, company_id, amount=99.0, voided=True)
        totals = svc.compute_erp_sales_totals(db, company_id, TEST_DATE)
        assert totals.total == 10.0
        assert totals.sale_count == 1

    def test_company_isolation(self, session):
        db, company_a, company_b, _ = session
        _add_sale(db, company_a, amount=10.0)
        _add_sale(db, company_b, amount=99.0)
        totals_a = svc.compute_erp_sales_totals(db, company_a, TEST_DATE)
        totals_b = svc.compute_erp_sales_totals(db, company_b, TEST_DATE)
        assert totals_a.total == 10.0
        assert totals_b.total == 99.0


# ── Lifecycle ─────────────────────────────────────────────────────────────────


class TestSaveDraftVerifyVoid:
    def test_save_draft_creates_record(self, session):
        db, company_id, _, user_id = session
        result = svc.save_draft(
            db,
            company_id,
            TEST_DATE,
            _source("POS Export"),
            _external(external_total=50.0),
            user_id,
            performed_by="mgr",
        )
        assert result.ok
        record = svc.get_active_verification(db, company_id, TEST_DATE)
        assert record is not None
        assert record.status == "draft"
        assert record.erp_total is None

    def test_save_draft_upserts_active_draft(self, session):
        db, company_id, _, user_id = session
        first = svc.save_draft(
            db, company_id, TEST_DATE, _source("A"), _external(), user_id
        )
        second = svc.save_draft(
            db,
            company_id,
            TEST_DATE,
            _source("B"),
            _external(external_total=25.0),
            user_id,
        )
        assert first.ok and second.ok
        assert second.record_id == first.record_id

    def test_cannot_save_draft_when_active_verified_exists(self, session):
        db, company_id, _, user_id = session
        draft = svc.save_draft(
            db,
            company_id,
            TEST_DATE,
            _source("POS"),
            _external(external_total=0.0),
            user_id,
        )
        assert svc.verify_external_sales(
            db, company_id, draft.record_id, user_id
        ).ok
        blocked = svc.save_draft(
            db, company_id, TEST_DATE, _source("New"), _external(), user_id
        )
        assert not blocked.ok

    def test_verify_balanced(self, session):
        db, company_id, _, user_id = session
        _add_sale(db, company_id, amount=100.0)
        draft = svc.save_draft(
            db,
            company_id,
            TEST_DATE,
            _source("POS"),
            _external(external_total=100.0),
            user_id,
        )
        result = svc.verify_external_sales(
            db, company_id, draft.record_id, user_id, performed_by="mgr"
        )
        assert result.ok
        record = svc.get_active_verification(db, company_id, TEST_DATE)
        assert record.status == "verified"
        assert record.within_tolerance is True
        assert record.erp_total == 100.0

    def test_verify_material_variance_requires_ack(self, session):
        db, company_id, _, user_id = session
        _add_sale(db, company_id, amount=100.0)
        draft = svc.save_draft(
            db,
            company_id,
            TEST_DATE,
            _source("POS"),
            _external(external_total=200.0),
            user_id,
        )
        blocked = svc.verify_external_sales(
            db, company_id, draft.record_id, user_id
        )
        assert not blocked.ok
        allowed = svc.verify_external_sales(
            db,
            company_id,
            draft.record_id,
            user_id,
            ack_note="Counted twice",
        )
        assert allowed.ok
        record = svc.get_active_verification(db, company_id, TEST_DATE)
        assert record.variance_acknowledged is True

    def test_verify_z_only(self, session):
        db, company_id, _, user_id = session
        _add_sale(db, company_id, amount=50.0)
        draft = svc.save_draft(
            db,
            company_id,
            TEST_DATE,
            _source("Z Slip", source_type="Z_REPORT"),
            _external(z_report_total=50.0),
            user_id,
        )
        result = svc.verify_external_sales(
            db, company_id, draft.record_id, user_id
        )
        assert result.ok
        record = svc.get_active_verification(db, company_id, TEST_DATE)
        assert record.variance_total is None
        assert record.z_report_variance == 0.0

    def test_void_allows_new_active_row(self, session):
        db, company_id, _, user_id = session
        draft = svc.save_draft(
            db,
            company_id,
            TEST_DATE,
            _source("POS"),
            _external(external_total=0.0),
            user_id,
        )
        svc.verify_external_sales(db, company_id, draft.record_id, user_id)
        err = svc.void_verification(
            db, company_id, draft.record_id, user_id, "Wrong date"
        )
        assert err == ""
        replacement = svc.save_draft(
            db,
            company_id,
            TEST_DATE,
            _source("POS 2"),
            _external(external_total=0.0),
            user_id,
        )
        assert replacement.ok
        assert replacement.record_id != draft.record_id

    def test_void_requires_reason(self, session):
        db, company_id, _, user_id = session
        draft = svc.save_draft(
            db,
            company_id,
            TEST_DATE,
            _source("POS"),
            _external(external_total=0.0),
            user_id,
        )
        err = svc.void_verification(db, company_id, draft.record_id, user_id, "  ")
        assert err != ""


class TestListAndStale:
    def test_list_verifications_in_range(self, session):
        db, company_id, _, user_id = session
        svc.save_draft(
            db,
            company_id,
            TEST_DATE,
            _source("POS"),
            _external(external_total=1.0),
            user_id,
        )
        rows = svc.list_verifications(
            db, company_id, TEST_DATE, TEST_DATE
        )
        assert len(rows) == 1
        assert rows[0].to_dict()["source_name"] == "POS"

    def test_is_verification_stale_after_new_sale(self, session):
        db, company_id, _, user_id = session
        draft = svc.save_draft(
            db,
            company_id,
            TEST_DATE,
            _source("POS"),
            _external(external_total=0.0),
            user_id,
        )
        svc.verify_external_sales(db, company_id, draft.record_id, user_id)
        record = svc.get_active_verification(db, company_id, TEST_DATE)
        assert svc.is_verification_stale(db, company_id, record) is False
        _add_sale(db, company_id, amount=5.0)
        assert svc.is_verification_stale(db, company_id, record) is True


# ── Architecture contracts ────────────────────────────────────────────────────


class TestArchitectureContracts:
    FORBIDDEN_IMPORTS = (
        "create_journal_entry",
        "post_cash_sale",
        "post_card_sale",
        "post_credit_sale",
        "submit_reconciliation",
        "streamlit",
    )
    FORBIDDEN_VENDOR_TOKENS = ("wolvox", "suitable_pos", "suitable")

    def test_no_streamlit_or_posting_imports(self):
        source = SERVICE_PATH.read_text(encoding="utf-8")
        for token in self.FORBIDDEN_IMPORTS:
            assert token not in source

    def test_no_vendor_specific_identifiers(self):
        source = SERVICE_PATH.read_text(encoding="utf-8").lower()
        for token in self.FORBIDDEN_VENDOR_TOKENS:
            assert token not in source

    def test_public_api_uses_explicit_company_id(self):
        db_funcs = (
            svc.compute_erp_sales_totals,
            svc.get_active_verification,
            svc.list_verifications,
            svc.save_draft,
            svc.verify_external_sales,
            svc.void_verification,
            svc.is_verification_stale,
        )
        for fn in db_funcs:
            params = list(inspect.signature(fn).parameters)
            assert params[1] == "company_id", f"{fn.__name__} must take company_id explicitly"

    def test_returns_are_serializable_dtos(self):
        result = svc.MutationResult(record_id=1, error="")
        assert result.to_dict()["ok"] is True
        record = svc.VerificationRecord(
            id=1,
            company_id=1,
            business_date=TEST_DATE,
            source_name="POS",
            source_type=None,
            branch_location=None,
            status="draft",
            external_total=None,
            z_report_total=None,
            external_cash=None,
            external_card=None,
            external_online=None,
            erp_total=None,
            erp_cash=None,
            erp_card=None,
            erp_credit=None,
            variance_total=None,
            variance_cash=None,
            variance_card=None,
            variance_online=None,
            z_report_variance=None,
            variance_type=None,
            within_tolerance=None,
            variance_acknowledged=False,
            variance_ack_note=None,
            notes=None,
            verified_by_id=None,
            verified_at=None,
            created_by_id=1,
            created_at=datetime.datetime.now(),
            updated_at=None,
            is_void=False,
            voided_by_id=None,
            voided_at=None,
            void_reason=None,
            sale_count_snapshot=None,
            attachment_count=0,
        )
        payload = record.to_dict()
        assert payload["business_date"] == TEST_DATE.isoformat()
        assert isinstance(payload, dict)

    def test_audit_written_without_streamlit(self, session):
        db, company_id, _, user_id = session
        result = svc.save_draft(
            db,
            company_id,
            TEST_DATE,
            _source("POS"),
            _external(external_total=1.0),
            user_id,
            performed_by="mgr",
        )
        audit = (
            db.query(models.AuditLog)
            .filter(
                models.AuditLog.entity_type == "ExternalSalesVerification",
                models.AuditLog.entity_id == result.record_id,
            )
            .one()
        )
        assert audit.performed_by == "mgr"
        assert audit.company_id == company_id
