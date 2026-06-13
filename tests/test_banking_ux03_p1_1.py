"""BANKING-UX-03 P1.1 — statement post error UX + skip control hardening."""
from __future__ import annotations

import datetime
import inspect
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app as erp_app
from reconciliation.match_post import MatchPostError, post_generic_deposit
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True

_P11_KEYS = (
    "banking.import.review.skip_select_hint",
    "banking.import.review.skip_row_label",
    "banking.import.match.unclear_amount",
    "banking.import.post_error.closed_year",
    "banking.import.post_error.closed_period",
    "banking.import.post_error.blocked",
)

_POST_RENDER_FUNCS = (
    "_render_bsi_deposit_clearing",
    "_render_bsi_other_deposit",
    "_render_bsi_cc_bill",
    "_render_bsi_vendor_payment",
    "_render_bsi_worker_payroll",
    "_render_bsi_bank_fee",
    "_render_bsi_partner_owner_loan_match",
)


def _seed_dev_auth_user():
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    _seed_dev_auth_user()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        erp_app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        co = models.Company(
            name="Test Co",
            slug="test_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.flush()
        sys.modules["streamlit"].session_state["active_company_id"] = co.id
        yield s


def _seed_coa(db, co):
    for code, name, atype in (
        ("1010", "Bank", "Asset"),
        ("4000", "Sales Revenue", "Income"),
        ("5100", "Office Expense", "Expense"),
    ):
        db.add(
            models.ChartOfAccounts(
                account_code=code,
                account_name=name,
                account_type=atype,
                currency="TRY" if name == "Bank" else None,
                company_id=co.id,
            )
        )
    db.commit()


def _company(db):
    co = models.Company(
        name="Acme",
        slug="acme",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    sys.modules["streamlit"].session_state["active_company_id"] = co.id
    _seed_coa(db, co)
    return co


def _bank(db, co):
    ba = models.BankAccount(
        name="Main TRY",
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=10000.0,
    )
    db.add(ba)
    db.commit()
    return ba


def _stmt_row(db, co, ba, *, row_date: datetime.date, credit=True, amount=100.0):
    imp = models.BankStatementImport(
        company_id=co.id,
        bank_account_id=ba.id,
        file_name="t.csv",
        file_hash="ux031",
        file_size=10,
        file_path="/tmp/t.csv",
        status="staging",
        import_date=row_date,
        row_count=1,
        valid_count=1,
        flagged_count=0,
        error_count=0,
        currency="TRY",
        created_at=datetime.datetime.now(),
    )
    db.add(imp)
    db.flush()
    row = models.BankStatementRow(
        bank_statement_import_id=imp.id,
        import_row_index=2,
        date=row_date,
        description="Test deposit",
        credit_amount=amount if credit else None,
        debit_amount=None if credit else amount,
        amount=amount,
        currency="TRY",
        original_amount=amount,
        parsed_successfully=True,
        status="staging",
        created_at=datetime.datetime.now(),
    )
    db.add(row)
    db.commit()
    return row


class TestPostErrorKeyMapping:
    def test_closed_year_maps_to_friendly_key(self):
        exc = ValueError(
            "Year 2024 is closed. Cannot post entries to 2024-12-15."
        )
        key, kwargs = erp_app._bsi_statement_post_error_key(exc)
        assert key == "banking.import.post_error.closed_year"
        assert kwargs == {}

    def test_closed_period_maps_to_friendly_key(self):
        exc = ValueError(
            "Period 'Dec 2024' (2024-12-01 – 2024-12-31) is closed. "
            "Cannot post entries to 2024-12-15."
        )
        key, kwargs = erp_app._bsi_statement_post_error_key(exc)
        assert key == "banking.import.post_error.closed_period"
        assert kwargs == {}

    def test_other_value_error_uses_blocked_key(self):
        exc = ValueError("Journal entry is not balanced: Debit $1.00 vs Credit $2.00")
        key, kwargs = erp_app._bsi_statement_post_error_key(exc)
        assert key == "banking.import.post_error.blocked"
        assert kwargs["detail"] == str(exc)

    def test_match_post_error_uses_raw_message(self):
        exc = MatchPostError("Select at least one card sale to match")
        assert erp_app._bsi_statement_post_error_message(exc) == str(exc)

    def test_friendly_closed_period_message_not_raw_kernel(self):
        exc = ValueError(
            "Period 'Dec 2024' (2024-12-01 – 2024-12-31) is closed. "
            "Cannot post entries to 2024-12-15."
        )
        msg = erp_app._bsi_statement_post_error_message(exc)
        assert msg == TRANSACTIONAL_EN["banking.import.post_error.closed_period"]
        assert "Cannot post entries" not in msg


class TestClosedPeriodPostIntegration:
    def test_generic_deposit_in_closed_period_raises_value_error(self, session):
        co = _company(session)
        ba = _bank(session, co)
        row_date = datetime.date(2025, 3, 15)
        session.add(
            models.FiscalPeriod(
                name="Mar 2025",
                start_date=datetime.date(2025, 3, 1),
                end_date=datetime.date(2025, 3, 31),
                is_closed=True,
                closed_at=datetime.date.today(),
                company_id=co.id,
            )
        )
        session.commit()
        row = _stmt_row(session, co, ba, row_date=row_date, credit=True)
        with pytest.raises(ValueError, match="is closed"):
            post_generic_deposit(
                session,
                row_id=row.id,
                company_id=co.id,
                credit_account_name="Sales Revenue",
                user_id=1,
            )


class TestPostCallSitesCatchValueError:
    @pytest.mark.parametrize("func_name", _POST_RENDER_FUNCS)
    def test_post_renderer_catches_match_post_and_value_error(self, func_name):
        src = inspect.getsource(getattr(erp_app, func_name))
        assert "except (MatchPostError, ValueError)" in src
        assert "_bsi_render_statement_post_error" in src

    def test_review_unpost_catches_match_post_and_value_error(self):
        src = inspect.getsource(erp_app.render_bank_statement_import)
        assert "except (MatchPostError, ValueError)" in src
        assert "_bsi_render_statement_post_error" in src


class TestSkipControlLabels:
    def test_review_skip_no_raw_id_multiselect(self):
        src = inspect.getsource(erp_app.render_bank_statement_import)
        assert "Row IDs to skip" not in src
        assert "banking.import.review.skip_select_hint" in src
        assert "bsi_skip_row_" in src

    def test_skip_row_label_uses_import_row_index_not_db_id(self):
        row = models.BankStatementRow(
            id=9999,
            import_row_index=7,
            date=datetime.date(2025, 4, 10),
            description="Wire transfer fee",
            credit_amount=None,
            debit_amount=25.0,
            amount=25.0,
        )
        label = erp_app._bsi_review_skip_row_label(row)
        assert "#7" in label
        assert "9999" not in label
        assert "25.00" in label


class TestUnclearAmountLiteral:
    def test_match_section_uses_locale_key(self):
        src = inspect.getsource(erp_app.render_bank_statement_import)
        assert "banking.import.match.unclear_amount" in src
        assert "Row has no clear deposit/withdrawal amount." not in src


class TestLocales:
    @pytest.mark.parametrize("key", _P11_KEYS)
    def test_en_and_tr_keys_exist(self, key):
        assert key in TRANSACTIONAL_EN
        assert key in TRANSACTIONAL_TR
        assert TRANSACTIONAL_EN[key].strip()
        assert TRANSACTIONAL_TR[key].strip()
