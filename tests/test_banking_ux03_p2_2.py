"""BANKING-UX-03 P2.2-A — bank fee batch posting (UI orchestration only)."""
from __future__ import annotations

import datetime
import inspect
import sys
from pathlib import Path
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
    infer_bank_charge_subtype,
    post_bank_charge_outflow,
)
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from registry.service import set_setting
from ui.banking import (
    banking_bank_fee_batch_candidates,
    banking_bank_fee_batch_partition,
    banking_bank_fee_batch_review_reason,
    render_banking_bank_fee_batch_panel,
)

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True

MATCH_POST = Path(__file__).resolve().parents[1] / "reconciliation" / "match_post.py"
POSTING = Path(__file__).resolve().parents[1] / "services" / "posting.py"

_P22_KEYS = (
    "banking.batch.bank_fee.title",
    "banking.batch.bank_fee.confirm",
    "banking.batch.bank_fee.confirm_line",
    "banking.batch.bank_fee.confirm_detail",
    "banking.batch.bank_fee.needs_review_title",
    "banking.batch.bank_fee.needs_review_desc",
    "banking.batch.bank_fee.needs_review_line",
    "banking.batch.bank_fee.results_title",
    "banking.batch.bank_fee.summary",
    "banking.batch.bank_fee.status.posted",
    "banking.batch.bank_fee.status.failed",
    "banking.batch.bank_fee.status.already_posted",
    "banking.batch.bank_fee.dismiss",
    "banking.batch.bank_fee.reason.low_confidence",
    "banking.batch.bank_fee.reason.ambiguous_subtype",
    "banking.batch.bank_fee.reason.mixed_description",
    "banking.batch.bank_fee.reason.not_withdrawal",
    "banking.batch.bank_fee.reason.missing_gl_accounts",
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
        yield s


def _company(db, *, slug="acme"):
    co = models.Company(
        name=slug.title(),
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    return co


def _activate(db, co, *, charges=True, settlement=False, cc=False):
    sys.modules["streamlit"].session_state["active_company_id"] = co.id
    set_setting(db, "banking.reconciliation_enabled", True, company_id=co.id)
    set_setting(db, "banking.bank_charges_enabled", charges, company_id=co.id)
    set_setting(db, "banking.card_settlement_enabled", settlement, company_id=co.id)
    set_setting(db, "banking.company_card_enabled", cc, company_id=co.id)


def _seed_coa(db, co):
    for code, name, atype in (
        ("1010", "Bank", "Asset"),
        ("5800", "Bank Charges", "Expense"),
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


def _bank(db, co):
    ba = models.BankAccount(
        name="Main TRY",
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=10000.0,
        kind="bank",
    )
    db.add(ba)
    db.commit()
    return ba


def _withdrawal_row(
    db,
    co,
    ba,
    *,
    description: str,
    amount: float = 50.0,
    row_date: datetime.date | None = None,
    status: str = "staging",
    import_row_index: int = 1,
    file_hash: str = "p22",
):
    row_date = row_date or datetime.date(2025, 6, 10)
    imp = models.BankStatementImport(
        company_id=co.id,
        bank_account_id=ba.id,
        file_name=f"{file_hash}.csv",
        file_hash=file_hash,
        file_size=10,
        file_path="/tmp/x.csv",
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
        credit_amount=None,
        debit_amount=amount,
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


def _deposit_row(
    db,
    co,
    ba,
    *,
    description: str = "POS YATIRMA",
    amount: float = 100.0,
    import_row_index: int = 99,
    file_hash: str = "dep",
):
    row_date = datetime.date(2025, 6, 11)
    imp = models.BankStatementImport(
        company_id=co.id,
        bank_account_id=ba.id,
        file_name=f"{file_hash}.csv",
        file_hash=file_hash,
        file_size=10,
        file_path="/tmp/x.csv",
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
        credit_amount=amount,
        debit_amount=None,
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


class TestConservativeEligibility:
    def test_low_confidence_not_batch_eligible(self, session, monkeypatch):
        co = _company(session, slug="lowconf")
        _activate(session, co, charges=True)
        _seed_coa(session, co)
        ba = _bank(session, co)
        row = _withdrawal_row(session, co, ba, description="POS KOMISYON", file_hash="lc")
        postable = get_postable_rows(session, co.id)

        monkeypatch.setattr(
            erp_app,
            "_banking_match_kind_confidence",
            lambda kind, desc, is_deposit=False: "low",
        )
        assert banking_bank_fee_batch_review_reason(session, co.id, row) == "low_confidence"
        partition = banking_bank_fee_batch_partition(session, co.id, postable)
        assert row.id not in [c["row_id"] for c in partition["eligible"]]
        assert row.id in [c["row_id"] for c in partition["needs_review"]]

    def test_ambiguous_subtype_not_batch_eligible(self, session, monkeypatch):
        co = _company(session, slug="ambig")
        _activate(session, co, charges=True)
        _seed_coa(session, co)
        ba = _bank(session, co)
        row = _withdrawal_row(session, co, ba, description="POS KOMISYON", file_hash="amb")
        postable = get_postable_rows(session, co.id)

        monkeypatch.setattr(
            erp_app,
            "_bsi_bank_fee_subtype_is_unambiguous",
            lambda desc: False,
        )
        assert (
            banking_bank_fee_batch_review_reason(session, co.id, row)
            == "ambiguous_subtype"
        )
        partition = banking_bank_fee_batch_partition(session, co.id, postable)
        assert partition["eligible"] == []
        assert [c["row_id"] for c in partition["needs_review"]] == [row.id]

    def test_mixed_description_not_batch_eligible(self, session):
        co = _company(session, slug="mixed")
        _activate(session, co, charges=True)
        _seed_coa(session, co)
        ba = _bank(session, co)
        row = _withdrawal_row(
            session, co, ba, description="KOMISYON UCRET", file_hash="mix"
        )
        postable = get_postable_rows(session, co.id)
        assert (
            banking_bank_fee_batch_review_reason(session, co.id, row)
            == "mixed_description"
        )
        partition = banking_bank_fee_batch_partition(session, co.id, postable)
        assert row.id not in [c["row_id"] for c in partition["eligible"]]
        assert row.id in [c["row_id"] for c in partition["needs_review"]]

    def test_non_withdrawal_not_batch_eligible(self, session):
        co = _company(session, slug="deposit")
        _activate(session, co, charges=True)
        _seed_coa(session, co)
        ba = _bank(session, co)
        row = _deposit_row(session, co, ba, description="POS KOMISYON", file_hash="dep")
        postable = get_postable_rows(session, co.id)
        assert (
            banking_bank_fee_batch_review_reason(session, co.id, row)
            == "not_withdrawal"
        )
        partition = banking_bank_fee_batch_partition(session, co.id, postable)
        assert partition["eligible"] == []

    def test_missing_gl_not_batch_eligible(self, session):
        co = _company(session, slug="nogl")
        _activate(session, co, charges=True)
        ba = _bank(session, co)
        row = _withdrawal_row(session, co, ba, description="POS KOMISYON", file_hash="nogl")
        postable = get_postable_rows(session, co.id)
        assert (
            banking_bank_fee_batch_review_reason(session, co.id, row)
            == "missing_gl_accounts"
        )
        partition = banking_bank_fee_batch_partition(session, co.id, postable)
        assert partition["eligible"] == []

    def test_partition_excludes_all_review_required_rows(self, session, monkeypatch):
        co = _company(session, slug="part")
        _activate(session, co, charges=True)
        _seed_coa(session, co)
        ba = _bank(session, co)
        eligible_a = _withdrawal_row(
            session, co, ba, description="POS KOMISYON", import_row_index=1, file_hash="e1"
        )
        eligible_b = _withdrawal_row(
            session,
            co,
            ba,
            description="HAVALE MASRAF",
            import_row_index=2,
            amount=25.0,
            file_hash="e2",
        )
        mixed = _withdrawal_row(
            session,
            co,
            ba,
            description="KOMISYON UCRET",
            import_row_index=3,
            file_hash="mix",
        )
        vendor = _withdrawal_row(
            session,
            co,
            ba,
            description="ACME SUPPLIES",
            import_row_index=4,
            file_hash="ven",
        )
        deposit = _deposit_row(
            session, co, ba, description="POS KOMISYON", import_row_index=5, file_hash="dep"
        )
        postable = get_postable_rows(session, co.id)
        partition = banking_bank_fee_batch_partition(session, co.id, postable)
        eligible_ids = {c["row_id"] for c in partition["eligible"]}
        review_ids = {c["row_id"] for c in partition["needs_review"]}
        assert eligible_ids == {eligible_a.id, eligible_b.id}
        assert mixed.id in review_ids
        assert vendor.id in review_ids
        assert deposit.id in review_ids
        assert eligible_ids.isdisjoint(review_ids)
        assert eligible_ids | review_ids >= {
            eligible_a.id,
            eligible_b.id,
            mixed.id,
            vendor.id,
            deposit.id,
        }


class TestCandidateSelection:
    def test_includes_only_bank_fee_classified_rows(self, session):
        co = _company(session)
        _activate(session, co, charges=True)
        _seed_coa(session, co)
        ba = _bank(session, co)
        fee_row = _withdrawal_row(
            session, co, ba, description="POS KOMISYON", import_row_index=1
        )
        _withdrawal_row(
            session,
            co,
            ba,
            description="ACME SUPPLIES",
            import_row_index=2,
            file_hash="vendor",
        )
        postable = get_postable_rows(session, co.id)
        candidates = banking_bank_fee_batch_candidates(session, co.id, postable)
        assert [c["row_id"] for c in candidates] == [fee_row.id]
        assert candidates[0]["subtype"] == infer_bank_charge_subtype("POS KOMISYON")

    def test_empty_when_bank_charges_disabled(self, session):
        co = _company(session, slug="nochg")
        _activate(session, co, charges=False)
        _seed_coa(session, co)
        ba = _bank(session, co)
        _withdrawal_row(session, co, ba, description="POS KOMISYON", file_hash="nc")
        postable = get_postable_rows(session, co.id)
        assert banking_bank_fee_batch_candidates(session, co.id, postable) == []


class TestBatchPostingParity:
    def test_batch_posts_two_rows(self, session):
        co = _company(session, slug="batch1")
        _activate(session, co, charges=True)
        _seed_coa(session, co)
        ba = _bank(session, co)
        r1 = _withdrawal_row(
            session, co, ba, description="POS KOMISYON", import_row_index=1, file_hash="b1"
        )
        r2 = _withdrawal_row(
            session,
            co,
            ba,
            description="HAVALE MASRAF",
            import_row_index=2,
            amount=25.0,
            file_hash="b2",
        )
        results = erp_app._bsi_execute_bank_fee_batch_post(
            session, co.id, [r1.id, r2.id], user_id=1
        )
        assert len(results) == 2
        assert all(r["status"] == "posted" for r in results)
        assert session.get(models.BankStatementRow, r1.id).match_type == "bank_charge"
        assert session.get(models.BankStatementRow, r2.id).match_type == "bank_charge"
        assert results[1]["error"] is None

    def test_one_audit_per_successful_row(self, session):
        co = _company(session, slug="audit")
        _activate(session, co, charges=True)
        _seed_coa(session, co)
        ba = _bank(session, co)
        r1 = _withdrawal_row(session, co, ba, description="POS KOMISYON", file_hash="a1")
        r2 = _withdrawal_row(
            session,
            co,
            ba,
            description="KOMISYON UCRET",
            import_row_index=2,
            file_hash="a2",
        )
        before = session.query(models.AuditLog).filter_by(
            entity_type="BankStatementRow", action="Post"
        ).count()
        results = erp_app._bsi_execute_bank_fee_batch_post(
            session, co.id, [r1.id, r2.id], user_id=1
        )
        after = session.query(models.AuditLog).filter_by(
            entity_type="BankStatementRow", action="Post"
        ).count()
        assert after - before == 1
        by_id = {r["row_id"]: r for r in results}
        assert by_id[r1.id]["status"] == "posted"
        assert by_id[r2.id]["status"] == "skipped"
        assert by_id[r2.id]["error"] == "mixed_description"

    def test_no_audit_on_failed_row(self, session):
        co = _company(session, slug="fail")
        _activate(session, co, charges=True)
        _seed_coa(session, co)
        ba = _bank(session, co)
        row_date = datetime.date(2025, 7, 1)
        session.add(
            models.FiscalPeriod(
                name="Jul 2025",
                start_date=datetime.date(2025, 7, 1),
                end_date=datetime.date(2025, 7, 31),
                is_closed=True,
                closed_at=datetime.date.today(),
                company_id=co.id,
            )
        )
        session.commit()
        row = _withdrawal_row(
            session,
            co,
            ba,
            description="POS KOMISYON",
            row_date=row_date,
            file_hash="closed",
        )
        before = session.query(models.AuditLog).count()
        results = erp_app._bsi_execute_bank_fee_batch_post(
            session, co.id, [row.id], user_id=1
        )
        assert results[0]["status"] == "failed"
        assert session.query(models.AuditLog).count() == before

    def test_continue_on_error(self, session):
        co = _company(session, slug="partial")
        _activate(session, co, charges=True)
        _seed_coa(session, co)
        ba = _bank(session, co)
        ok_row = _withdrawal_row(
            session,
            co,
            ba,
            description="POS KOMISYON",
            row_date=datetime.date(2025, 8, 1),
            import_row_index=1,
            file_hash="ok",
        )
        bad_row = _withdrawal_row(
            session,
            co,
            ba,
            description="KOMISYON",
            row_date=datetime.date(2025, 9, 1),
            import_row_index=2,
            file_hash="bad",
        )
        session.add(
            models.FiscalPeriod(
                name="Sep 2025",
                start_date=datetime.date(2025, 9, 1),
                end_date=datetime.date(2025, 9, 30),
                is_closed=True,
                closed_at=datetime.date.today(),
                company_id=co.id,
            )
        )
        session.commit()
        results = erp_app._bsi_execute_bank_fee_batch_post(
            session, co.id, [ok_row.id, bad_row.id], user_id=1
        )
        by_id = {r["row_id"]: r for r in results}
        assert by_id[ok_row.id]["status"] == "posted"
        assert by_id[bad_row.id]["status"] == "failed"
        assert session.get(models.BankStatementRow, ok_row.id).status == "posted"

    def test_already_posted_does_not_double_post(self, session):
        co = _company(session, slug="idem")
        _activate(session, co, charges=True)
        _seed_coa(session, co)
        ba = _bank(session, co)
        row = _withdrawal_row(session, co, ba, description="POS KOMISYON", file_hash="idem")
        post_bank_charge_outflow(session, row_id=row.id, company_id=co.id, user_id=1)
        session.commit()
        je_id = session.get(models.BankStatementRow, row.id).posted_journal_entry_id
        results = erp_app._bsi_execute_bank_fee_batch_post(
            session, co.id, [row.id], user_id=1
        )
        assert results[0]["status"] == "already_posted"
        assert session.get(models.BankStatementRow, row.id).posted_journal_entry_id == je_id


class TestUiContract:
    def test_match_section_renders_batch_panel(self):
        src = inspect.getsource(erp_app.render_bank_statement_import)
        match = src.split('elif section == "match":', 1)[1].split(
            'elif section == "history":', 1
        )[0]
        assert "render_banking_bank_fee_batch_panel" in match
        assert "_bsi_bank_fee_batch_partition" in match
        assert "_bank_charges_on" in match

    def test_confirm_panel_shows_detail_and_explicit_button_only(self):
        src = inspect.getsource(render_banking_bank_fee_batch_panel)
        assert "confirm_detail" in src
        assert "bsi_bank_fee_batch_confirm" in src
        assert "on_page_load" not in src.lower()
        assert "post_bank_charge_outflow" not in src

    def test_executor_skips_ineligible_row(self, session):
        co = _company(session, slug="exskip")
        _activate(session, co, charges=True)
        _seed_coa(session, co)
        ba = _bank(session, co)
        ok = _withdrawal_row(session, co, ba, description="POS KOMISYON", file_hash="ok")
        mixed = _withdrawal_row(
            session,
            co,
            ba,
            description="KOMISYON UCRET",
            import_row_index=2,
            file_hash="mix",
        )
        results = erp_app._bsi_execute_bank_fee_batch_post(
            session, co.id, [ok.id, mixed.id], user_id=1
        )
        by_id = {r["row_id"]: r for r in results}
        assert by_id[ok.id]["status"] == "posted"
        assert by_id[mixed.id]["status"] == "skipped"
        assert by_id[mixed.id]["error"] == "mixed_description"

    def test_batch_executor_revalidates_eligibility(self):
        src = inspect.getsource(erp_app._bsi_execute_bank_fee_batch_post)
        assert "_bsi_bank_fee_batch_review_reason" in src
        assert '"skipped"' in src
        src = inspect.getsource(erp_app._bsi_execute_bank_fee_batch_post)
        assert "post_bank_charge_outflow(" in src
        assert "post_vendor_outflow" not in src
        assert "post_deposit_clearing_match" not in src
        assert "log_audit(" in src

    def test_ui_panel_no_direct_posting(self):
        src = inspect.getsource(render_banking_bank_fee_batch_panel)
        assert "post_bank_charge_outflow" not in src
        assert "_bsi_execute_bank_fee_batch_post" in src

    def test_batch_single_matches_individual_post(self, session):
        co = _company(session, slug="parity")
        _activate(session, co, charges=True)
        _seed_coa(session, co)
        ba = _bank(session, co)
        row = _withdrawal_row(session, co, ba, description="POS KOMISYON", file_hash="p")
        single = post_bank_charge_outflow(
            session, row_id=row.id, company_id=co.id, user_id=1
        )
        session.commit()
        single_row = session.get(models.BankStatementRow, row.id)

        co2 = _company(session, slug="parity2")
        _activate(session, co2, charges=True)
        _seed_coa(session, co2)
        ba2 = _bank(session, co2)
        row2 = _withdrawal_row(
            session, co2, ba2, description="POS KOMISYON", file_hash="p2"
        )
        batch = erp_app._bsi_execute_bank_fee_batch_post(
            session, co2.id, [row2.id], user_id=1
        )[0]
        batch_row = session.get(models.BankStatementRow, row2.id)
        assert batch["status"] == "posted"
        assert single_row.match_type == batch_row.match_type == "bank_charge"
        assert single["charge_subtype"] == "card_settlement_fee"

    def test_match_post_unchanged(self):
        src = MATCH_POST.read_text(encoding="utf-8")
        assert "def post_bank_charge_outflow" in src
        assert "def _bsi_execute_bank_fee_batch_post" not in src


class TestLocales:
    @pytest.mark.parametrize("key", _P22_KEYS)
    def test_en_and_tr_keys_exist(self, key):
        assert key in TRANSACTIONAL_EN
        assert key in TRANSACTIONAL_TR
