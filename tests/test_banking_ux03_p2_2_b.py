"""BANKING-UX-03 P2.2-B — transfer-charge classification safety (heuristics only)."""
from __future__ import annotations

import datetime
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
    infer_bank_charge_subtype,
    looks_like_commission,
    looks_like_interest,
    looks_like_credit_card_account_fee,
    looks_like_statement_bank_fee,
    looks_like_transfer_fee,
    post_bank_charge_outflow,
    suggest_withdrawal_match_kind,
)
from registry.service import set_setting
from ui.banking import banking_bank_fee_batch_candidates

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

erp_app.DEVELOPMENT_MODE = True
erp_app.DEV_MODE = True

MATCH_POST = Path(__file__).resolve().parents[1] / "reconciliation" / "match_post.py"
POSTING = Path(__file__).resolve().parents[1] / "services" / "posting.py"

_PRINCIPAL_NOT_FEE = (
    "EFT GIDEN ACME LTD",
    "HAVALE KIRA",
    "SWIFT PAYMENT",
    "EFT MAAS ODEME",
    "GIDEN HAVALE ODEME",
    "WIRE TO SUPPLIER",
)

_TRANSFER_FEE_CORPUS = (
    ("HAVALE UCRETI", "transfer_fee"),
    ("HAVALE MASRAFI", "transfer_fee"),
    ("EFT UCRETI", "transfer_fee"),
    ("EFT MASRAFI", "transfer_fee"),
    ("SWIFT MASRAFI", "transfer_fee"),
    ("ISLEM UCRETI", "transfer_fee"),
    ("TRANSFER FEE", "transfer_fee"),
    ("HAVALE MASRAF", "transfer_fee"),
)


@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    sys.modules["streamlit"].session_state["auth_user"] = dict(erp_app._DEV_USER)
    sys.modules["streamlit"].session_state["auth_expires"] = (
        datetime.datetime.now() + datetime.timedelta(hours=24)
    )
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


def _company(db, *, slug="p22b"):
    co = models.Company(
        name=slug.title(),
        slug=slug,
        is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(co)
    db.commit()
    return co


def _activate(db, co):
    sys.modules["streamlit"].session_state["active_company_id"] = co.id
    set_setting(db, "banking.reconciliation_enabled", True, company_id=co.id)
    set_setting(db, "banking.bank_charges_enabled", True, company_id=co.id)


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


def _withdrawal_row(db, co, ba, *, description: str, amount: float = 50.0, idx: int = 1):
    row_date = datetime.date(2025, 6, 10)
    imp = models.BankStatementImport(
        company_id=co.id,
        bank_account_id=ba.id,
        file_name=f"p22b_{idx}.csv",
        file_hash=f"p22b_{idx}",
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
        import_row_index=idx,
        date=row_date,
        description=description,
        credit_amount=None,
        debit_amount=amount,
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


class TestPrincipalNotFee:
    @pytest.mark.parametrize("description", _PRINCIPAL_NOT_FEE)
    def test_not_transfer_fee(self, description):
        assert not looks_like_transfer_fee(description)

    @pytest.mark.parametrize("description", _PRINCIPAL_NOT_FEE)
    def test_not_statement_bank_fee(self, description):
        assert not looks_like_statement_bank_fee(description)

    @pytest.mark.parametrize("description", _PRINCIPAL_NOT_FEE)
    def test_not_bank_fee_routing(self, description):
        assert (
            suggest_withdrawal_match_kind(
                description,
                company_card_on=True,
                bank_charges_on=True,
                has_workers=True,
            )
            != "bank_fee"
        )

    def test_eft_maas_resolves_worker_payroll(self):
        assert (
            suggest_withdrawal_match_kind(
                "EFT MAAS ODEME",
                company_card_on=False,
                bank_charges_on=True,
                has_workers=True,
            )
            == "worker_payroll"
        )

    def test_eft_giden_resolves_vendor(self):
        assert (
            suggest_withdrawal_match_kind(
                "EFT GIDEN ACME LTD",
                company_card_on=False,
                bank_charges_on=True,
                has_workers=False,
            )
            == "vendor"
        )


class TestTransferFeeCorpus:
    @pytest.mark.parametrize("description,subtype", _TRANSFER_FEE_CORPUS)
    def test_transfer_fee_heuristic(self, description, subtype):
        assert looks_like_transfer_fee(description)
        assert looks_like_statement_bank_fee(description)
        assert infer_bank_charge_subtype(description) == subtype

    @pytest.mark.parametrize("description,_subtype", _TRANSFER_FEE_CORPUS)
    def test_bank_fee_routing(self, description, _subtype):
        assert (
            suggest_withdrawal_match_kind(
                description,
                company_card_on=False,
                bank_charges_on=True,
                has_workers=True,
            )
            == "bank_fee"
        )


class TestPrecedencePins:
    def test_kart_komisyon_stays_commission(self):
        desc = "KART KOMISYON"
        assert looks_like_commission(desc)
        assert infer_bank_charge_subtype(desc) == "card_settlement_fee"
        assert (
            suggest_withdrawal_match_kind(
                desc,
                company_card_on=False,
                bank_charges_on=True,
                has_workers=False,
            )
            == "bank_fee"
        )

    def test_interest_precedence_unchanged(self):
        desc = "GECIKME FAIZI"
        assert looks_like_interest(desc)
        assert infer_bank_charge_subtype(desc) == "interest"
        assert not looks_like_transfer_fee(desc)

    def test_credit_card_fee_precedence_unchanged(self):
        desc = "KK YILLIK UCRET"
        assert looks_like_credit_card_account_fee(desc)
        assert infer_bank_charge_subtype(desc) == "credit_card_fee"
        assert not looks_like_commission(desc)

    def test_bsmv_stays_commission(self):
        desc = "BSMV KESINTI"
        assert looks_like_commission(desc)
        assert infer_bank_charge_subtype(desc) == "card_settlement_fee"


class TestBatchCandidateExclusion:
    def test_principal_rows_excluded_from_batch(self, session):
        from reconciliation.match_post import get_postable_rows

        co = _company(session)
        _activate(session, co)
        _seed_coa(session, co)
        ba = _bank(session, co)
        rows = []
        for i, desc in enumerate(_PRINCIPAL_NOT_FEE, start=1):
            rows.append(_withdrawal_row(session, co, ba, description=desc, idx=i))
        fee_row = _withdrawal_row(
            session,
            co,
            ba,
            description="HAVALE MASRAF",
            amount=12.0,
            idx=99,
        )
        postable = get_postable_rows(session, co.id)
        candidates = banking_bank_fee_batch_candidates(session, co.id, postable)
        candidate_ids = {c["row_id"] for c in candidates}
        assert fee_row.id in candidate_ids
        for row in rows:
            assert row.id not in candidate_ids


class TestGlNeutrality:
    def test_transfer_fee_posts_dr_bank_charges_cr_bank(self, session):
        co = _company(session, slug="gl")
        _activate(session, co)
        _seed_coa(session, co)
        ba = _bank(session, co)
        for desc, amount in (("HAVALE UCRETI", 6.5), ("EFT MASRAFI", 25.0)):
            row = _withdrawal_row(session, co, ba, description=desc, amount=amount)
            result = post_bank_charge_outflow(
                session, row_id=row.id, company_id=co.id, user_id=1
            )
            session.commit()
            session.refresh(row)
            charges = erp_app.get_account_by_name(session, "Bank Charges")
            bank = erp_app.get_account_by_name(session, "Bank", currency="TRY")
            lines = (
                session.query(models.JournalEntryLine)
                .filter_by(journal_entry_id=row.posted_journal_entry_id)
                .all()
            )
            debits = {ln.account_id: ln.debit for ln in lines if ln.debit}
            credits = {ln.account_id: ln.credit for ln in lines if ln.credit}
            assert debits[charges.id] == amount
            assert credits[bank.id] == amount
            assert result["charge_subtype"] == "transfer_fee"

    def test_commission_subtype_je_unchanged(self, session):
        co = _company(session, slug="gl2")
        _activate(session, co)
        _seed_coa(session, co)
        ba = _bank(session, co)
        row = _withdrawal_row(session, co, ba, description="POS KOMISYON", amount=150.0)
        result = post_bank_charge_outflow(
            session, row_id=row.id, company_id=co.id, user_id=1
        )
        session.commit()
        assert result["charge_subtype"] == "card_settlement_fee"


class TestNoServiceChangeGuard:
    def test_post_bank_charge_outflow_unchanged(self):
        src = MATCH_POST.read_text(encoding="utf-8")
        assert "def post_bank_charge_outflow" in src
        block = src.split("def post_bank_charge_outflow", 1)[1].split("\ndef ", 1)[0]
        assert "Bank Charges" in block
        assert "charge_subtype" in block

    def test_posting_service_untouched(self):
        src = POSTING.read_text(encoding="utf-8")
        assert "looks_like_transfer_fee" not in src
        assert "_TRANSFER_FEE_TOKEN_KEYWORDS" not in src
