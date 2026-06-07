"""Phase 18-MVP-4 — Bank charges + settlement statement."""

import datetime
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].session_state = {}

from db import Base
import models
import app as erp_app
from reconciliation.match_post import (
    MatchPostError,
    card_deposit_style,
    infer_bank_charge_subtype,
    looks_like_commission,
    looks_like_credit_card_account_fee,
    looks_like_credit_card_bill_payment,
    looks_like_interest,
    post_bank_charge_outflow,
    post_deposit_clearing_match,
)
from reconciliation.settlement_import import import_settlement_statement_file
from registry.coa_seed import ensure_accounts_for_company
from registry.service import set_setting


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "reconciliation.settlement_import.SETTLEMENT_UPLOAD_ROOT",
        str(tmp_path / "settlements"),
    )
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    erp_app.st.session_state = {}
    with Session() as session:
        yield session


def _seed_coa(db, co):
    for code, name, atype in (
        ("1010", "Bank", "Asset"),
        ("1150", "Card Sales Clearing", "Asset"),
        ("4000", "Sales Revenue", "Income"),
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


def _company(db):
    co = models.Company(
        name="Acme",
        slug="acme",
        is_active=True,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(co)
    db.commit()
    erp_app.st.session_state["active_company_id"] = co.id
    _seed_coa(db, co)
    ensure_accounts_for_company(db, co.id)
    db.commit()
    return co


def _bank(db, co):
    ba = models.BankAccount(
        name="Main TRY",
        currency="TRY",
        company_id=co.id,
        is_active=True,
        balance=0.0,
    )
    db.add(ba)
    db.commit()
    return ba


def _stmt_row(db, co, ba, *, amount=100.0, credit=True):
    imp = models.BankStatementImport(
        company_id=co.id,
        bank_account_id=ba.id,
        file_name="t.csv",
        file_hash="abc",
        file_size=10,
        file_path="/tmp/t.csv",
        status="staging",
        import_date=datetime.date.today(),
        row_count=1,
        valid_count=1,
        flagged_count=0,
        error_count=0,
        currency="TRY",
        created_at=datetime.datetime.utcnow(),
    )
    db.add(imp)
    db.flush()
    row = models.BankStatementRow(
        bank_statement_import_id=imp.id,
        status="staging",
        import_row_index=1,
        date=datetime.date.today(),
        description="Card settlement deposit",
        debit_amount=None if credit else amount,
        credit_amount=amount if credit else None,
        amount=amount,
        currency="TRY",
        original_amount=amount,
        parsed_successfully=True,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    return row


def _card_sale(db, co, amount=100.0):
    sale = models.Sale(
        date=datetime.date.today(),
        invoice_number=f"INV-{amount}",
        customer_name="Walk-in",
        amount=amount,
        sale_type="Card",
        status="Paid",
        company_id=co.id,
    )
    db.add(sale)
    db.commit()
    erp_app.post_card_sale(db, sale.id, amount, sale.date, currency="TRY")
    return sale


class TestInferredFee:
    def test_posts_bank_charges_when_fee_confirmed(self, db):
        co = _company(db)
        set_setting(db, "banking.card_settlement_enabled", True, company_id=co.id)
        set_setting(db, "banking.bank_charges_enabled", True, company_id=co.id)
        db.commit()
        ba = _bank(db, co)
        sale = _card_sale(db, co, amount=100.0)
        row = _stmt_row(db, co, ba, amount=97.0)

        result = post_deposit_clearing_match(
            db,
            row_id=row.id,
            company_id=co.id,
            sale_ids=[sale.id],
            user_id=1,
            confirm_inferred_fee=True,
        )
        assert result["fee_amount"] == 3.0
        assert result["fee_source"] == "inferred"

        db.refresh(row)
        assert row.status == "posted"
        charges = erp_app.get_account_by_name(db, "Bank Charges")
        fee_line = (
            db.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=row.posted_journal_entry_id, account_id=charges.id)
            .one()
        )
        assert fee_line.debit == pytest.approx(3.0)

        btxn = db.get(models.BankTransaction, row.bank_transaction_id)
        assert btxn.charge_subtype == "card_settlement_fee"

    def test_fee_without_confirm_raises(self, db):
        co = _company(db)
        set_setting(db, "banking.card_settlement_enabled", True, company_id=co.id)
        set_setting(db, "banking.bank_charges_enabled", True, company_id=co.id)
        db.commit()
        ba = _bank(db, co)
        sale = _card_sale(db, co, amount=100.0)
        row = _stmt_row(db, co, ba, amount=97.0)
        with pytest.raises(MatchPostError, match="Confirm the fee"):
            post_deposit_clearing_match(
                db,
                row_id=row.id,
                company_id=co.id,
                sale_ids=[sale.id],
                user_id=None,
            )

    def test_fee_without_bank_charges_setting_raises(self, db):
        co = _company(db)
        set_setting(db, "banking.card_settlement_enabled", True, company_id=co.id)
        db.commit()
        ba = _bank(db, co)
        sale = _card_sale(db, co, amount=100.0)
        row = _stmt_row(db, co, ba, amount=97.0)
        with pytest.raises(MatchPostError, match="Enable"):
            post_deposit_clearing_match(
                db,
                row_id=row.id,
                company_id=co.id,
                sale_ids=[sale.id],
                user_id=None,
                confirm_inferred_fee=True,
            )


class TestCardDepositLabels:
    def test_pesin_satis_is_gross(self):
        assert card_deposit_style("PEŞİN SATIŞ") == "gross"
        assert card_deposit_style("PESIN SATIS ODEME") == "gross"

    def test_net_satis_tutari_is_net(self):
        assert card_deposit_style("NET SATIŞ TUTARI") == "net"
        assert card_deposit_style("Net Satis Tutari") == "net"

    def test_unrelated_returns_none(self):
        assert card_deposit_style("KIRA ODEMESI") is None


class TestBankChargeOutflow:
    def test_looks_like_commission(self):
        assert looks_like_commission("POS KOMISYON KESINTISI")
        assert looks_like_commission("UYE ISYERI UCRETI")
        assert looks_like_commission("Üye İşyeri Ücreti")
        assert not looks_like_commission("KIRA ODEMESI")
        assert not looks_like_commission("HAVALE UCRETI")

    def test_infer_transfer_fee_subtype(self):
        assert infer_bank_charge_subtype("HAVALE UCRETI") == "transfer_fee"
        assert infer_bank_charge_subtype("POS KOMISYON") == "card_settlement_fee"
        assert infer_bank_charge_subtype("GECIKME FAIZI") == "interest"
        assert infer_bank_charge_subtype("KK YILLIK UCRET") == "credit_card_fee"

    def test_cc_fee_not_pos_commission(self):
        assert looks_like_credit_card_account_fee("KREDI KARTI YILLIK UCRET")
        assert not looks_like_commission("KREDI KARTI YILLIK UCRET")
        assert looks_like_interest("GECIKME FAIZI")
        assert not looks_like_commission("GECIKME FAIZI")

    def test_cc_bill_payment_not_fee(self):
        assert looks_like_credit_card_bill_payment("KK ODEME")
        assert looks_like_credit_card_bill_payment("KREDI KARTI ODEME")
        assert not looks_like_credit_card_bill_payment("KK YILLIK UCRET")
        assert not looks_like_credit_card_bill_payment("GECIKME FAIZI")

    def test_commission_line_posts_to_bank_charges(self, db):
        co = _company(db)
        set_setting(db, "banking.bank_charges_enabled", True, company_id=co.id)
        db.commit()
        ba = _bank(db, co)
        row = _stmt_row(db, co, ba, amount=150.0, credit=False)
        row.description = "POS KOMISYON"
        db.commit()

        post_bank_charge_outflow(
            db, row_id=row.id, company_id=co.id, user_id=1
        )
        db.refresh(row)
        assert row.status == "posted"
        assert row.match_type == "bank_charge"

        charges = erp_app.get_account_by_name(db, "Bank Charges")
        fee_line = (
            db.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=row.posted_journal_entry_id, account_id=charges.id)
            .one()
        )
        assert fee_line.debit == 150.0

        btxn = db.get(models.BankTransaction, row.bank_transaction_id)
        assert btxn.charge_subtype == "card_settlement_fee"

    def test_transfer_fee_subtype_when_not_commission(self, db):
        co = _company(db)
        set_setting(db, "banking.bank_charges_enabled", True, company_id=co.id)
        db.commit()
        ba = _bank(db, co)
        row = _stmt_row(db, co, ba, amount=25.0, credit=False)
        row.description = "EFT MASRAFI"
        db.commit()
        result = post_bank_charge_outflow(
            db, row_id=row.id, company_id=co.id, user_id=1
        )
        assert result["charge_subtype"] == "transfer_fee"


class TestSettlementStatement:
    def test_settlement_import_parses_csv(self, db):
        co = _company(db)
        csv_body = (
            "Date,Description,Gross,Fee,Net\n"
            "05.06.2026,Batch A,100.00,3.00,97.00\n"
        ).encode("utf-8")
        imp = import_settlement_statement_file(
            db,
            company_id=co.id,
            file_bytes=csv_body,
            filename="settle.csv",
            column_mapping={
                "date": "Date",
                "description": "Description",
                "gross": "Gross",
                "fee": "Fee",
                "net": "Net",
                "batch_reference": None,
            },
            user_id=1,
        )
        assert imp.valid_count == 1
        row = (
            db.query(models.SettlementStatementRow)
            .filter_by(settlement_statement_import_id=imp.id)
            .one()
        )
        assert row.gross_amount == 100.0
        assert row.fee_amount == 3.0
        assert row.net_amount == 97.0

    def test_settlement_linked_clearing_match(self, db):
        co = _company(db)
        set_setting(db, "banking.card_settlement_enabled", True, company_id=co.id)
        set_setting(db, "banking.bank_charges_enabled", True, company_id=co.id)
        db.commit()
        ba = _bank(db, co)
        sale = _card_sale(db, co, amount=100.0)
        stmt_row = _stmt_row(db, co, ba, amount=97.0)

        csv_body = (
            "Date,Description,Gross,Fee,Net\n"
            "05.06.2026,Batch A,100.00,3.00,97.00\n"
        ).encode("utf-8")
        stl_imp = import_settlement_statement_file(
            db,
            company_id=co.id,
            file_bytes=csv_body,
            filename="settle.csv",
            column_mapping={
                "date": "Date",
                "description": "Description",
                "gross": "Gross",
                "fee": "Fee",
                "net": "Net",
                "batch_reference": None,
            },
            user_id=1,
        )
        stl_row = (
            db.query(models.SettlementStatementRow)
            .filter_by(settlement_statement_import_id=stl_imp.id)
            .one()
        )
        stl_row.date = datetime.date.today()
        db.commit()

        result = post_deposit_clearing_match(
            db,
            row_id=stmt_row.id,
            company_id=co.id,
            sale_ids=[sale.id],
            user_id=1,
            settlement_row_id=stl_row.id,
        )
        assert result["fee_amount"] == 3.0
        assert result["fee_source"] == "settlement"

        db.refresh(stl_row)
        assert stl_row.status == "posted"
        assert stl_row.bank_statement_row_id == stmt_row.id
        db.refresh(stmt_row)
        assert stmt_row.settlement_row_id == stl_row.id
