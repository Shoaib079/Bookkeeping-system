"""Phase 18-MVP-2 — Bank statement import to staging + provenance."""

import datetime
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].session_state = {}

from db import Base
import models
from reconciliation import (
    DuplicateFileWarning,
    delete_bank_statement_import,
    import_bank_statement_file,
    list_excel_sheets,
    read_tabular_preview,
    suggest_column_mapping,
)
from reconciliation import statement_parse as sp
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR

FIXTURE = Path(__file__).parent / "fixtures" / "bank_statement_sample.csv"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "reconciliation.statement_import.STATEMENT_UPLOAD_ROOT",
        str(tmp_path / "statements"),
    )
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as session:
        yield session


def _seed(db):
    co = models.Company(
        name="Acme",
        slug="acme",
        is_active=True,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(co)
    db.flush()
    ba = models.BankAccount(name="Main TRY", currency="TRY", company_id=co.id, is_active=True)
    db.add(ba)
    db.commit()
    return co, ba


def _mapping(**overrides):
    base = {
        "date": "Date",
        "description": "Description",
        "amount": None,
        "debit": "Debit",
        "credit": "Credit",
        "balance": "Balance",
        "bank_reference": None,
    }
    base.update(overrides)
    return base


class TestSchema:
    def test_models_exist(self):
        cols_imp = set(models.BankStatementImport.__table__.columns.keys())
        cols_row = set(models.BankStatementRow.__table__.columns.keys())
        assert "file_hash" in cols_imp
        assert "file_path" in cols_imp
        assert "raw_line_text" in cols_row
        assert "normalized_description" in cols_row


class TestParse:
    def test_read_preview_and_suggest_mapping(self):
        raw = FIXTURE.read_bytes()
        headers, preview = read_tabular_preview(raw, "sample.csv")
        assert "Date" in headers
        assert len(preview) >= 1
        mapping = suggest_column_mapping(headers)
        assert mapping["date"] == "Date"
        assert mapping["debit"] == "Debit"

    def test_parse_csv_rows(self):
        raw = FIXTURE.read_bytes()
        rows = sp.parse_bank_statement(raw, "sample.csv", _mapping(), currency="TRY")
        assert len(rows) == 7
        assert rows[0]["parsed_successfully"] is True
        assert rows[0]["amount"] == 1000.0
        assert rows[0]["raw_line_text"]

    def test_bad_date_row_is_parse_error(self):
        raw = b"Date,Description,Debit,Credit,Balance\nBAD,Test,1,,10\n"
        rows = sp.parse_bank_statement(raw, "bad.csv", _mapping())
        assert rows[0]["status"] == "parse_error"
        assert rows[0]["raw_line_text"]

    def test_suggest_turkish_tarih_header(self):
        headers = ["Statement Tarih", "Açıklama", "Tutar", "Bakiye"]
        mapping = suggest_column_mapping(headers)
        assert mapping["date"] == "Statement Tarih"
        assert mapping["description"] == "Açıklama"
        assert mapping["amount"] == "Tutar"
        assert mapping["balance"] == "Bakiye"

    def test_parse_signed_column_mapped_to_debit_credit_and_amount(self):
        """Bank exports one İşlem Tutarı column: negative = payment, positive = deposit."""
        raw = (
            "Tarih,Açıklama,İşlem Tutarı,Bakiye\n"
            "01.01.2026,PEŞİNSATIŞ,23211,100\n"
            "01.01.2026,GIDEN HAVALE,-30000,50\n"
        ).encode("utf-8")
        mapping = _mapping(
            date="Tarih",
            description="Açıklama",
            amount="İşlem Tutarı",
            debit="İşlem Tutarı",
            credit="İşlem Tutarı",
        )
        rows = sp.parse_bank_statement(raw, "tr.csv", mapping, currency="TRY")
        assert rows[0]["parsed_successfully"] is True
        assert rows[0]["credit_amount"] == 23211.0
        assert rows[0]["debit_amount"] is None
        assert rows[1]["parsed_successfully"] is True
        assert rows[1]["debit_amount"] == 30000.0
        assert rows[1]["credit_amount"] is None

    def test_parse_tutar_signed_column(self):
        raw = b"Tarih,A\xc3\xa7\xc4\xb1klama,Tutar,Bakiye\n01.02.2026,Test,-50,950\n"
        rows = sp.parse_bank_statement(
            raw,
            "tr.csv",
            _mapping(
                date="Tarih",
                description="Açıklama",
                amount="Tutar",
                debit=None,
                credit=None,
            ),
        )
        assert rows[0]["parsed_successfully"] is True
        assert rows[0]["debit_amount"] == 50.0
        assert rows[0]["amount"] == 50.0

    def test_detect_header_row_turkish(self):
        raw = (
            "Ekstre Bilgileri,,,\n"
            "Tarih,Açıklama,Borç,Alacak,Bakiye\n"
            "01.01.2026,Test,,100,100\n"
        ).encode("utf-8")
        assert sp.detect_header_row(raw, "tr.csv") == 2

    def test_parse_html_disguised_as_xlsx(self):
        html = (
            "<html><body><table>"
            "<tr><td>Tarih</td><td>Açıklama</td><td>Borç</td><td>Alacak</td><td>Bakiye</td></tr>"
            "<tr><td>01.01.2026</td><td>Test</td><td></td><td>100</td><td>100</td></tr>"
            "</table></body></html>"
        )
        raw = html.encode("utf-8")
        assert sp.detect_file_format(raw, "statement.xlsx") == "html"
        headers, preview = read_tabular_preview(raw, "statement.xlsx", header_row=1)
        assert "Tarih" in headers
        assert len(preview) >= 1
        rows = sp.parse_bank_statement(
            raw,
            "statement.xlsx",
            _mapping(
                date="Tarih",
                description="Açıklama",
                debit="Borç",
                credit="Alacak",
            ),
            currency="TRY",
        )
        assert rows[0]["parsed_successfully"] is True
        assert rows[0]["amount"] == 100.0

    def test_list_excel_sheets_non_xlsx_returns_empty(self):
        html = b"<table><tr><td>Tarih</td></tr></table>"
        assert list_excel_sheets(html) == []

    def test_parse_xlsx_rows(self):
        import io

        import pandas as pd

        df = pd.DataFrame({
            "Date": ["2026-01-01"],
            "Description": ["Test deposit"],
            "Debit": [""],
            "Credit": ["100.00"],
            "Balance": ["100.00"],
        })
        bio = io.BytesIO()
        df.to_excel(bio, index=False, engine="openpyxl")
        rows = sp.parse_bank_statement(bio.getvalue(), "sample.xlsx", _mapping(), currency="TRY")
        assert len(rows) == 1
        assert rows[0]["parsed_successfully"] is True
        assert rows[0]["amount"] == 100.0


class TestImport:
    def test_import_creates_staging_rows(self, db):
        co, ba = _seed(db)
        raw = FIXTURE.read_bytes()
        imp = import_bank_statement_file(
            db,
            company_id=co.id,
            bank_account_id=ba.id,
            file_bytes=raw,
            filename="sample.csv",
            column_mapping=_mapping(),
            user_id=None,
        )
        assert imp.status == "staging"
        assert imp.valid_count == 7
        assert imp.file_hash
        assert Path(imp.file_path).is_file()
        rows = db.query(models.BankStatementRow).filter_by(bank_statement_import_id=imp.id).all()
        assert len(rows) == 7
        assert db.query(models.JournalEntry).count() == 0

    def test_within_import_duplicate_flagged(self, db):
        co, ba = _seed(db)
        raw = FIXTURE.read_bytes()
        imp = import_bank_statement_file(
            db,
            company_id=co.id,
            bank_account_id=ba.id,
            file_bytes=raw,
            filename="sample.csv",
            column_mapping=_mapping(),
            user_id=None,
        )
        flagged = (
            db.query(models.BankStatementRow)
            .filter_by(bank_statement_import_id=imp.id, status="duplicate_flagged")
            .count()
        )
        assert flagged >= 1

    def test_delete_import_removes_rows_and_file(self, db):
        co, ba = _seed(db)
        raw = FIXTURE.read_bytes()
        imp = import_bank_statement_file(
            db,
            company_id=co.id,
            bank_account_id=ba.id,
            file_bytes=raw,
            filename="sample.csv",
            column_mapping=_mapping(),
            user_id=None,
        )
        file_path = Path(imp.file_path)
        assert file_path.is_file()
        assert delete_bank_statement_import(db, imp.id, co.id) is True
        assert db.query(models.BankStatementImport).filter_by(id=imp.id).count() == 0
        assert db.query(models.BankStatementRow).filter_by(bank_statement_import_id=imp.id).count() == 0
        assert not file_path.is_file()
        # same file can be imported again after delete
        imp2 = import_bank_statement_file(
            db,
            company_id=co.id,
            bank_account_id=ba.id,
            file_bytes=raw,
            filename="sample.csv",
            column_mapping=_mapping(),
            user_id=None,
        )
        assert imp2.valid_count == 7

    def test_file_duplicate_warning(self, db):
        co, ba = _seed(db)
        raw = FIXTURE.read_bytes()
        import_bank_statement_file(
            db,
            company_id=co.id,
            bank_account_id=ba.id,
            file_bytes=raw,
            filename="sample.csv",
            column_mapping=_mapping(),
            user_id=None,
        )
        with pytest.raises(DuplicateFileWarning):
            import_bank_statement_file(
                db,
                company_id=co.id,
                bank_account_id=ba.id,
                file_bytes=raw,
                filename="sample.csv",
                column_mapping=_mapping(),
                user_id=None,
            )
        imp2 = import_bank_statement_file(
            db,
            company_id=co.id,
            bank_account_id=ba.id,
            file_bytes=raw,
            filename="sample.csv",
            column_mapping=_mapping(),
            user_id=None,
            force_duplicate=True,
        )
        assert imp2.id is not None

    def test_cross_import_flags_existing_bank_txn(self, db):
        co, ba = _seed(db)
        db.add(
            models.BankTransaction(
                account_id=ba.id,
                date=datetime.date(2026, 1, 2),
                amount=50.0,
                type="withdrawal",
                description="Supplier payment",
                company_id=co.id,
            )
        )
        db.commit()
        raw = FIXTURE.read_bytes()
        imp = import_bank_statement_file(
            db,
            company_id=co.id,
            bank_account_id=ba.id,
            file_bytes=raw,
            filename="sample.csv",
            column_mapping=_mapping(),
            user_id=None,
        )
        match = (
            db.query(models.BankStatementRow)
            .filter_by(bank_statement_import_id=imp.id, import_row_index=2)
            .first()
        )
        assert match.status == "duplicate_flagged"
        assert match.duplicate_reason == "prior_import"


class TestI18n:
    def test_banking_import_keys_parity(self):
        keys = {k for k in TRANSACTIONAL_EN if k.startswith("banking.import.")}
        assert keys
        for k in keys:
            assert k in TRANSACTIONAL_TR

    def test_banking_section_nav_keys(self):
        for key in (
            "bank.section.accounts",
            "bank.section.import",
            "bank.section.settings",
            "bank.settings.section",
            "bank.settings.card_settlement.section",
            "banking.import.match.partner_loan_expander",
            "banking.import.match.owner_loan_expander",
            "partner.partnership_mode_hint",
            "partner.sole_prop_mode_hint",
        ):
            assert key in TRANSACTIONAL_EN
            assert key in TRANSACTIONAL_TR
