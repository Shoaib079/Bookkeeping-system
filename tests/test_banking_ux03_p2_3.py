"""BANKING-UX-03 P2.3-A — banking configuration MVP (registry settings + presentation)."""
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
from reconciliation.match_post import get_postable_rows
from registry.banking_config import (
    BANKING_BATCH_SAFE_KINDS,
    banking_batch_eligible_kinds,
    banking_batch_posting_enabled,
    banking_batch_review_reason_for_row,
    banking_batch_safe_kinds,
    banking_confidence_meets_batch_threshold,
    banking_default_import_tab,
    banking_normalize_batch_kinds,
    banking_resolve_landing,
    banking_review_required_kinds,
    banking_show_confidence_chips,
    banking_sort_queue_rows,
)
from registry.loader import get_setting_def
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from registry.service import get_setting, set_setting
from ui.banking import banking_apply_session_landing

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True

_P23_LOCALE_KEYS = (
    "settings.banking.default_landing",
    "settings.banking.batch_posting_enabled",
    "settings.banking.batch_eligible_kinds",
    "settings.banking.review_required_kinds",
    "settings.banking.batch_confidence_threshold",
    "settings.banking.show_confidence_chips",
    "settings.banking.show_accounting_previews",
    "settings.banking.queue_density",
    "settings.banking.queue_sort",
    "settings.banking.default_import_tab",
    "settings.banking.landing_preference",
    "settings.banking.workspace_preferences",
    "settings.banking.workspace_policy",
    "banking.batch.bank_fee.reason.review_required_transfer",
    "banking.import.match.accounting_preview",
)


def _seed_dev_auth_user(user_id: int = 1):
    sys.modules["streamlit"].session_state["auth_user"] = {
        **dict(erp_app._DEV_USER),
        "id": user_id,
    }
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
        yield s


def _company(db, *, slug="p23"):
    co = models.Company(
        name=slug.title(),
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    return co


def _user(db, *, username="u1"):
    u = models.User(
        username=username,
        password_hash="x",
        role="admin",
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(u)
    db.commit()
    return u


def _activate(db, co):
    sys.modules["streamlit"].session_state["active_company_id"] = co.id
    set_setting(db, "banking.reconciliation_enabled", True, company_id=co.id)
    set_setting(db, "banking.bank_charges_enabled", True, company_id=co.id)


class TestSettingDefaults:
    def test_company_setting_defaults(self):
        for key in (
            "banking.default_landing",
            "banking.batch_posting_enabled",
            "banking.batch_eligible_kinds",
            "banking.review_required_kinds",
            "banking.batch_confidence_threshold",
        ):
            defn = get_setting_def(key)
            assert defn is not None
            assert defn.scope == "company"
        assert get_setting_def("banking.default_landing").default == "cockpit"
        assert get_setting_def("banking.batch_posting_enabled").default is False
        assert get_setting_def("banking.batch_eligible_kinds").default == "bank_fee"
        assert "transfer_charges" in get_setting_def(
            "banking.review_required_kinds"
        ).default
        assert get_setting_def("banking.batch_confidence_threshold").default == "high"

    def test_user_preference_defaults(self):
        for key in (
            "banking.show_confidence_chips",
            "banking.show_accounting_previews",
            "banking.queue_density",
            "banking.queue_sort",
            "banking.default_import_tab",
            "banking.landing_preference",
        ):
            defn = get_setting_def(key)
            assert defn is not None
            assert defn.scope == "user"
        assert get_setting_def("banking.show_confidence_chips").default is True
        assert get_setting_def("banking.default_import_tab").default == "match"
        assert get_setting_def("banking.landing_preference").default == "inherit"


class TestCompanyIsolation:
    def test_company_settings_isolated(self, session):
        co_a = _company(session, slug="coa")
        co_b = _company(session, slug="cob")
        set_setting(session, "banking.default_landing", "accounts", company_id=co_a.id)
        set_setting(session, "banking.default_landing", "cockpit", company_id=co_b.id)
        session.commit()
        assert (
            get_setting(session, "banking.default_landing", company_id=co_a.id)
            == "accounts"
        )
        assert (
            get_setting(session, "banking.default_landing", company_id=co_b.id)
            == "cockpit"
        )


class TestUserIsolation:
    def test_user_preferences_isolated(self, session):
        co = _company(session)
        u1 = _user(session, username="alice")
        u2 = _user(session, username="bob")
        set_setting(
            session,
            "banking.queue_sort",
            "amount",
            company_id=co.id,
            user_id=u1.id,
        )
        set_setting(
            session,
            "banking.queue_sort",
            "confidence",
            company_id=co.id,
            user_id=u2.id,
        )
        session.commit()
        assert (
            get_setting(
                session, "banking.queue_sort", company_id=co.id, user_id=u1.id
            )
            == "amount"
        )
        assert (
            get_setting(
                session, "banking.queue_sort", company_id=co.id, user_id=u2.id
            )
            == "confidence"
        )


class TestBatchSafeSetInvariant:
    def test_safe_set_is_bank_fee_only(self):
        assert banking_batch_safe_kinds() == frozenset({"bank_fee"})

    def test_normalize_never_widens(self):
        assert banking_normalize_batch_kinds("bank_fee,vendor,payroll") == frozenset(
            {"bank_fee"}
        )
        assert banking_normalize_batch_kinds("vendor,worker_payroll") == frozenset()
        assert banking_normalize_batch_kinds("") == frozenset()

    def test_company_cannot_widen_via_setting(self, session):
        co = _company(session, slug="wide")
        set_setting(
            session,
            "banking.batch_eligible_kinds",
            "vendor,bank_fee,card_clearing",
            company_id=co.id,
        )
        session.commit()
        assert banking_batch_eligible_kinds(session, co.id) == frozenset({"bank_fee"})

    def test_empty_eligible_kinds_disables_batch_kind(self, session):
        co = _company(session, slug="empty")
        set_setting(session, "banking.batch_eligible_kinds", "vendor", company_id=co.id)
        session.commit()
        assert banking_batch_eligible_kinds(session, co.id) == frozenset()


class TestConfidenceThreshold:
    def test_low_never_meets_threshold(self):
        assert not banking_confidence_meets_batch_threshold("high", "low")
        assert not banking_confidence_meets_batch_threshold("high_and_medium", "low")

    def test_high_and_medium_allows_medium(self):
        assert banking_confidence_meets_batch_threshold("high_and_medium", "medium")
        assert not banking_confidence_meets_batch_threshold("high", "medium")


class TestReviewPolicy:
    def test_transfer_fee_review_when_policy_on(self, session):
        co = _company(session, slug="xfer")
        set_setting(
            session,
            "banking.review_required_kinds",
            "transfer_charges",
            company_id=co.id,
        )
        session.commit()
        reason = banking_batch_review_reason_for_row(
            session,
            co.id,
            detected_kind="bank_fee",
            confidence="high",
            description="HAVALE MASRAF",
            subtype="transfer_fee",
        )
        assert reason == "review_required_transfer"

    def test_transfer_fee_batch_ok_when_policy_off(self, session):
        co = _company(session, slug="xferoff")
        set_setting(
            session,
            "banking.review_required_kinds",
            "low_confidence",
            company_id=co.id,
        )
        session.commit()
        assert (
            banking_batch_review_reason_for_row(
                session,
                co.id,
                detected_kind="bank_fee",
                confidence="high",
                description="HAVALE MASRAF",
                subtype="transfer_fee",
            )
            is None
        )


class TestLandingResolution:
    def test_company_default_cockpit(self, session):
        co = _company(session)
        assert banking_resolve_landing(session, co.id) == "cockpit"

    def test_user_override_queue(self, session):
        co = _company(session)
        u = _user(session)
        set_setting(
            session,
            "banking.landing_preference",
            "queue",
            company_id=co.id,
            user_id=u.id,
        )
        session.commit()
        assert banking_resolve_landing(session, co.id, user_id=u.id) == "queue"

    def test_apply_session_landing_queue(self, session):
        co = _company(session)
        u = _user(session)
        set_setting(
            session,
            "banking.landing_preference",
            "queue",
            company_id=co.id,
            user_id=u.id,
        )
        session.commit()
        banking_apply_session_landing(session, co.id, user_id=u.id)
        assert sys.modules["streamlit"].session_state["banking_section"] == "import"
        assert sys.modules["streamlit"].session_state["bsi_section"] == "match"


class TestBatchIntegration:
    def _seed_fee_row(self, session, co):
        _activate(session, co)
        for code, name, atype in (
            ("1010", "Bank", "Asset"),
            ("5800", "Bank Charges", "Expense"),
        ):
            session.add(
                models.ChartOfAccounts(
                    account_code=code,
                    account_name=name,
                    account_type=atype,
                    currency="TRY" if name == "Bank" else None,
                    company_id=co.id,
                )
            )
        ba = models.BankAccount(
            name="Main",
            currency="TRY",
            company_id=co.id,
            is_active=True,
            balance=10000.0,
            kind="bank",
        )
        session.add(ba)
        session.commit()
        imp = models.BankStatementImport(
            company_id=co.id,
            bank_account_id=ba.id,
            file_name="f.csv",
            file_hash="f",
            file_size=10,
            file_path="/tmp/f.csv",
            status="staging",
            import_date=datetime.date(2025, 6, 1),
            row_count=1,
            valid_count=1,
            flagged_count=0,
            error_count=0,
            currency="TRY",
            created_at=datetime.datetime.now(),
        )
        session.add(imp)
        session.flush()
        row = models.BankStatementRow(
            bank_statement_import_id=imp.id,
            import_row_index=1,
            date=datetime.date(2025, 6, 1),
            description="POS KOMISYON",
            credit_amount=None,
            debit_amount=50.0,
            amount=50.0,
            currency="TRY",
            original_amount=50.0,
            parsed_successfully=True,
            status="staging",
            created_at=datetime.datetime.now(),
        )
        session.add(row)
        session.commit()
        return row

    def test_batch_disabled_by_default(self, session):
        co = _company(session, slug="boff")
        assert not banking_batch_posting_enabled(session, co.id)

    def test_principal_not_in_candidates(self, session):
        from ui.banking import banking_bank_fee_batch_candidates

        co = _company(session, slug="principal")
        _activate(session, co)
        set_setting(session, "banking.batch_posting_enabled", True, company_id=co.id)
        for code, name, atype in (
            ("1010", "Bank", "Asset"),
            ("5800", "Bank Charges", "Expense"),
        ):
            session.add(
                models.ChartOfAccounts(
                    account_code=code,
                    account_name=name,
                    account_type=atype,
                    currency="TRY" if name == "Bank" else None,
                    company_id=co.id,
                )
            )
        ba = models.BankAccount(
            name="Main",
            currency="TRY",
            company_id=co.id,
            is_active=True,
            balance=10000.0,
            kind="bank",
        )
        session.add(ba)
        session.commit()
        imp = models.BankStatementImport(
            company_id=co.id,
            bank_account_id=ba.id,
            file_name="p.csv",
            file_hash="p",
            file_size=10,
            file_path="/tmp/p.csv",
            status="staging",
            import_date=datetime.date(2025, 6, 1),
            row_count=2,
            valid_count=2,
            flagged_count=0,
            error_count=0,
            currency="TRY",
            created_at=datetime.datetime.now(),
        )
        session.add(imp)
        session.flush()
        for idx, desc in enumerate(("EFT GIDEN ACME LTD", "POS KOMISYON"), start=1):
            session.add(
                models.BankStatementRow(
                    bank_statement_import_id=imp.id,
                    import_row_index=idx,
                    date=datetime.date(2025, 6, 1),
                    description=desc,
                    credit_amount=None,
                    debit_amount=50.0,
                    amount=50.0,
                    currency="TRY",
                    original_amount=50.0,
                    parsed_successfully=True,
                    status="staging",
                    created_at=datetime.datetime.now(),
                )
            )
        session.commit()
        postable = get_postable_rows(session, co.id)
        candidates = banking_bank_fee_batch_candidates(session, co.id, postable)
        assert len(candidates) == 1
        assert "POS" in candidates[0]["description"]

    def test_transfer_fee_excluded_when_review_policy(self, session):
        co = _company(session, slug="xferbatch")
        _activate(session, co)
        set_setting(session, "banking.batch_posting_enabled", True, company_id=co.id)
        set_setting(
            session,
            "banking.review_required_kinds",
            "transfer_charges",
            company_id=co.id,
        )
        for code, name, atype in (
            ("1010", "Bank", "Asset"),
            ("5800", "Bank Charges", "Expense"),
        ):
            session.add(
                models.ChartOfAccounts(
                    account_code=code,
                    account_name=name,
                    account_type=atype,
                    currency="TRY" if name == "Bank" else None,
                    company_id=co.id,
                )
            )
        ba = models.BankAccount(
            name="Main",
            currency="TRY",
            company_id=co.id,
            is_active=True,
            balance=10000.0,
            kind="bank",
        )
        session.add(ba)
        session.commit()
        imp = models.BankStatementImport(
            company_id=co.id,
            bank_account_id=ba.id,
            file_name="t.csv",
            file_hash="t",
            file_size=10,
            file_path="/tmp/t.csv",
            status="staging",
            import_date=datetime.date(2025, 6, 1),
            row_count=1,
            valid_count=1,
            flagged_count=0,
            error_count=0,
            currency="TRY",
            created_at=datetime.datetime.now(),
        )
        session.add(imp)
        session.flush()
        session.add(
            models.BankStatementRow(
                bank_statement_import_id=imp.id,
                import_row_index=1,
                date=datetime.date(2025, 6, 1),
                description="HAVALE MASRAF",
                credit_amount=None,
                debit_amount=12.0,
                amount=12.0,
                currency="TRY",
                original_amount=12.0,
                parsed_successfully=True,
                status="staging",
                created_at=datetime.datetime.now(),
            )
        )
        session.commit()
        postable = get_postable_rows(session, co.id)
        from ui.banking import banking_bank_fee_batch_partition

        part = banking_bank_fee_batch_partition(session, co.id, postable)
        assert part["eligible"] == []
        assert part["needs_review"][0]["review_reason"] == "review_required_transfer"


class TestUiContract:
    def test_render_banking_applies_landing(self):
        src = inspect.getsource(erp_app.render_banking)
        assert "banking_apply_session_landing" in src

    def test_batch_gated_by_company_setting(self):
        src = inspect.getsource(erp_app.render_bank_statement_import)
        match = src.split('elif section == "match":', 1)[1].split(
            'elif section == "history":', 1
        )[0]
        assert "banking_batch_posting_enabled" in match

    def test_match_post_untouched(self):
        src = (
            erp_app.__file__.replace("app.py", "")
            + "../reconciliation/match_post.py"
        )
        from pathlib import Path

        text = Path(__file__).resolve().parents[1].joinpath(
            "reconciliation", "match_post.py"
        ).read_text(encoding="utf-8")
        assert "banking.batch_posting_enabled" not in text


class TestLocales:
    @pytest.mark.parametrize("key", _P23_LOCALE_KEYS)
    def test_en_and_tr_keys_exist(self, key):
        assert key in TRANSACTIONAL_EN
        assert key in TRANSACTIONAL_TR
