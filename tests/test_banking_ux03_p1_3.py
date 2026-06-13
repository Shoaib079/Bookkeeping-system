"""BANKING-UX-03 P1.3 — Match queue MVP (list replaces single-row dropdown)."""
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
from reconciliation.match_post import (
    MatchPostError,
    get_postable_rows,
    post_generic_deposit,
)
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from ui.banking import (
    banking_pos_settlement_route_keys,
    render_banking_match_queue_list,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True

_P13_KEYS = (
    "banking.import.match.queue_heading",
    "banking.import.match.queue_review",
    "banking.import.match.queue_detail",
)

_ROW_SCOPED_WIDGET_BASES = (
    "bsi_match_sales",
    "bsi_match_settlement",
    "bsi_confirm_fee",
    "bsi_match_credit_acct",
    "bsi_other_income_use_sales_revenue",
    "bsi_match_vendor",
    "bsi_match_payable",
    "bsi_match_worker",
    "bsi_match_cc_acct",
    "bsi_match_kind",
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


def _stmt_row(
    db,
    co,
    ba,
    *,
    row_date: datetime.date,
    credit=True,
    amount=100.0,
    description="Test line",
    status="staging",
    import_row_index=2,
):
    imp = models.BankStatementImport(
        company_id=co.id,
        bank_account_id=ba.id,
        file_name="t.csv",
        file_hash=f"ux03_{import_row_index}_{status}",
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
        import_row_index=import_row_index,
        date=row_date,
        description=description,
        credit_amount=amount if credit else None,
        debit_amount=None if credit else amount,
        amount=amount,
        currency="TRY",
        original_amount=amount,
        parsed_successfully=True,
        status=status,
        created_at=datetime.datetime.now(),
    )
    db.add(row)
    db.commit()
    return row


class TestGetPostableRowsScope:
    def test_company_wide_staging_and_duplicate_flagged(self, session):
        co = _company(session)
        ba = _bank(session, co)
        row_date = datetime.date(2025, 5, 10)
        r1 = _stmt_row(session, co, ba, row_date=row_date, import_row_index=1)
        r2 = _stmt_row(
            session,
            co,
            ba,
            row_date=row_date,
            credit=False,
            amount=50.0,
            description="Fee",
            import_row_index=3,
        )
        r3 = _stmt_row(
            session,
            co,
            ba,
            row_date=row_date,
            status="duplicate_flagged",
            import_row_index=4,
        )
        _stmt_row(
            session,
            co,
            ba,
            row_date=row_date,
            status="posted",
            import_row_index=5,
        )
        rows = get_postable_rows(session, co.id)
        assert [r.id for r in rows] == [r1.id, r2.id, r3.id]

    def test_ordered_by_date_then_import_row_index(self, session):
        co = _company(session)
        ba = _bank(session, co)
        late = _stmt_row(
            session,
            co,
            ba,
            row_date=datetime.date(2025, 5, 12),
            import_row_index=10,
        )
        early = _stmt_row(
            session,
            co,
            ba,
            row_date=datetime.date(2025, 5, 8),
            import_row_index=20,
        )
        rows = get_postable_rows(session, co.id)
        assert rows[0].id == early.id
        assert rows[1].id == late.id


class TestQueueUiContract:
    def test_match_section_uses_queue_not_selectbox(self):
        src = inspect.getsource(erp_app.render_bank_statement_import)
        match_block = src.split('elif section == "match":', 1)[1].split(
            'elif section == "history":', 1
        )[0]
        assert "render_banking_match_queue_list" in match_block
        assert 'key="bsi_match_row"' not in match_block
        assert "bsi_queue_sel_row" in match_block

    def test_widget_key_helper_exists(self):
        assert hasattr(erp_app, "_bsi_widget_key")
        assert erp_app._bsi_widget_key("bsi_match_sales", 42) == "bsi_match_sales_42"

    def test_row_scoped_keys_in_post_panels(self):
        kind_src = inspect.getsource(erp_app._bsi_match_queue_detail_body)
        assert "_bsi_widget_key" in kind_src
        assert "bsi_match_kind" in kind_src
        for base in _ROW_SCOPED_WIDGET_BASES:
            if base == "bsi_match_kind":
                continue
            found = False
            for func_name in _POST_RENDER_FUNCS:
                src = inspect.getsource(getattr(erp_app, func_name))
                if "_bsi_widget_key" in src and base in src:
                    found = True
                    break
            assert found, f"{base} not row-scoped via _bsi_widget_key"

    def test_no_audit_in_except_blocks(self):
        for func_name in _POST_RENDER_FUNCS:
            src = inspect.getsource(getattr(erp_app, func_name))
            for block in src.split("except (MatchPostError, ValueError)"):
                if "_bsi_render_statement_post_error" not in block:
                    continue
                handler = block.split("_bsi_render_statement_post_error", 1)[1]
                handler = handler.split("\n", 2)[0]
                assert "log_audit" not in handler

    def test_detail_uses_fragment(self):
        app_path = inspect.getsourcefile(erp_app)
        src = open(app_path, encoding="utf-8").read()
        assert "@st.fragment" in src
        assert "_bsi_match_queue_detail_fragment" in src
        assert "_bsi_match_queue_detail_body" in src

    def test_queue_list_helper_uses_locale_keys(self):
        src = inspect.getsource(render_banking_match_queue_list)
        assert "banking.import.match.queue_review" in src


class TestPostingParity:
    def test_post_panels_still_call_same_posters(self):
        clearing_src = inspect.getsource(erp_app._render_bsi_deposit_clearing)
        assert "post_deposit_clearing_match(" in clearing_src
        other_src = inspect.getsource(erp_app._render_bsi_other_deposit)
        assert "post_generic_deposit(" in other_src

    def test_one_log_audit_per_successful_post(self):
        for func_name in _POST_RENDER_FUNCS:
            src = inspect.getsource(getattr(erp_app, func_name))
            assert src.count('log_audit(\n') + src.count("log_audit(") >= 1
            assert '"BankStatementRow"' in src

    def test_queue_post_identical_to_direct_post_generic_deposit(self, session):
        co = _company(session)
        ba = _bank(session, co)
        row = _stmt_row(
            session,
            co,
            ba,
            row_date=datetime.date(2025, 6, 1),
            description="Misc deposit",
        )
        before_audits = session.query(models.AuditLog).count()
        post_generic_deposit(
            session,
            row_id=row.id,
            company_id=co.id,
            credit_account_name="Sales Revenue",
            user_id=1,
        )
        session.commit()
        row_after = session.get(models.BankStatementRow, row.id)
        assert row_after.status == "posted"
        assert session.query(models.AuditLog).count() == before_audits

    def test_failed_post_raises_no_finalize(self, session):
        co = _company(session)
        ba = _bank(session, co)
        row = _stmt_row(session, co, ba, row_date=datetime.date(2025, 6, 1))
        row.status = "posted"
        session.commit()
        with pytest.raises(MatchPostError, match="already posted"):
            post_generic_deposit(
                session,
                row_id=row.id,
                company_id=co.id,
                credit_account_name="Sales Revenue",
                user_id=1,
            )


class TestPosEntryDeepLink:
    def test_pos_entry_route_still_sets_card_clearing_flag(self):
        keys = banking_pos_settlement_route_keys()
        assert keys["bsi_pos_entry"] is True
        assert keys["bsi_section"] == "match"

    def test_match_section_honours_pos_entry(self):
        src = inspect.getsource(erp_app.render_bank_statement_import)
        match_block = src.split('elif section == "match":', 1)[1].split(
            'elif section == "history":', 1
        )[0]
        assert 'pop("bsi_pos_entry"' in match_block
        assert "card_clearing" in match_block
        assert "bsi_queue_sel_row" in match_block


class TestErrorRendering:
    @pytest.mark.parametrize("func_name", _POST_RENDER_FUNCS)
    def test_post_renderer_catches_match_post_and_value_error(self, func_name):
        src = inspect.getsource(getattr(erp_app, func_name))
        assert "except (MatchPostError, ValueError)" in src
        assert "_bsi_render_statement_post_error" in src


class TestLocales:
    @pytest.mark.parametrize("key", _P13_KEYS)
    def test_en_and_tr_keys_exist(self, key):
        assert key in TRANSACTIONAL_EN
        assert key in TRANSACTIONAL_TR
        assert TRANSACTIONAL_EN[key].strip()
        assert TRANSACTIONAL_TR[key].strip()
