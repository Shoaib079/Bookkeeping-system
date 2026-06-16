"""MONEY-DECIMAL-04c+ — JE guard & FX native Decimal boundary verification.

Audit/closure slice: confirms ``services/money.py`` boundaries are wired and MD-02
golden vectors unchanged. No posting behavior changes.

Cross-ref: docs/MONEY_DECIMAL_04C_JE_FX_DECIMAL.md
"""

from __future__ import annotations

import datetime
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from db import Base

if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock

import app  # noqa: F401

app.DEVELOPMENT_MODE = True
app.DEV_MODE = True

from registry.coa_seed import seed_chart_of_accounts_for_company
from services import posting
from services.money import (
    fx_to_float,
    line_money,
    money_to_float,
    parse_money,
    quantize_fx,
    quantize_money,
)

ROOT = Path(__file__).resolve().parents[1]
POSTING_PATH = ROOT / "services" / "posting.py"
CLOSURE_DOC = ROOT / "docs" / "MONEY_DECIMAL_04C_JE_FX_DECIMAL.md"

AMOUNT = 100.01
COMPANY_ID = 1
POST_DATE = datetime.date(2025, 6, 15)
VOID_REASON = "MD-04c void"


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        s.add(
            models.Company(
                name="MD-04c Co",
                slug="md04c",
                is_active=True,
                created_at=datetime.datetime.now(),
            )
        )
        s.flush()
        seed_chart_of_accounts_for_company(s, COMPANY_ID)
        s.commit()
        yield s


def _acct_id(session, name: str, *, currency: str | None = None) -> int:
    acct = posting.get_account_by_name(
        session, name, currency=currency, company_id=COMPANY_ID
    )
    assert acct is not None
    return acct.id


def _je_lines(session, journal_entry_id: int) -> list[tuple[int, float, float]]:
    lines = (
        session.query(models.JournalEntryLine)
        .filter_by(journal_entry_id=journal_entry_id)
        .order_by(models.JournalEntryLine.id)
        .all()
    )
    return [(ln.account_id, line_money(ln.debit), line_money(ln.credit)) for ln in lines]


def _entries_for(session, ref_type: str, ref_id: int) -> list[models.JournalEntry]:
    return (
        session.query(models.JournalEntry)
        .filter_by(reference_type=ref_type, reference_id=ref_id)
        .order_by(models.JournalEntry.id)
        .all()
    )


class TestMd04cClosureDoc:
    def test_closure_doc_exists(self):
        assert CLOSURE_DOC.exists()
        text = CLOSURE_DOC.read_text(encoding="utf-8").lower()
        assert "closed by verification" in text
        assert "services/money.py" in text
        assert "deferred" in text


class TestPostingSourceAudit:
    @pytest.fixture(scope="module")
    def posting_source(self) -> str:
        return POSTING_PATH.read_text(encoding="utf-8")

    def test_no_round_calls_in_posting(self, posting_source: str):
        assert "round(" not in posting_source

    def test_amount_native_uses_persist_fx(self, posting_source: str):
        assert "persist_fx(net * fx_rate)" in posting_source

    def test_balance_guard_float_tolerance(self, posting_source: str):
        assert "abs(total_debit - total_credit) > 0.01" in posting_source

    def test_no_decimal_module_import(self, posting_source: str):
        assert "from decimal import" not in posting_source
        assert "import decimal" not in posting_source

    def test_dead_helpers_removed(self, posting_source: str):
        assert "_normalize_money_amount" not in posting_source
        assert "_allocation_share_float" not in posting_source


class TestJeGuardDecimalUglyInputs:
    """Decimal/str inputs parse through ``parse_money``; guard semantics stay float."""

    def test_decimal_type_balanced_entry(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        entry = posting.create_journal_entry(
            session,
            POST_DATE,
            "decimal input",
            "Manual",
            None,
            [(cash_id, Decimal("100.01"), Decimal("0")), (inc_id, Decimal("0"), Decimal("100.01"))],
            company_id=COMPANY_ID,
        )
        assert _je_lines(session, entry.id) == [
            (cash_id, AMOUNT, 0.0),
            (inc_id, 0.0, AMOUNT),
        ]

    def test_string_extra_precision_quantized_on_persist(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        entry = posting.create_journal_entry(
            session,
            POST_DATE,
            "string precision",
            "Manual",
            None,
            [(cash_id, "100.012345", "0"), (inc_id, "0", "100.012345")],
            company_id=COMPANY_ID,
        )
        lines = (
            session.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=entry.id)
            .order_by(models.JournalEntryLine.id)
            .all()
        )
        assert line_money(lines[0].debit) == 100.01
        assert line_money(lines[1].credit) == 100.01

    def test_float_overshoot_rejection_unchanged(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        with pytest.raises(ValueError, match="Debit \\$100.00 vs Credit \\$99.99"):
            posting.create_journal_entry(
                session,
                POST_DATE,
                "md02 overshoot",
                "Manual",
                None,
                [(cash_id, 100.0, 0.0), (inc_id, 0.0, 99.99)],
                company_id=COMPANY_ID,
            )

    def test_float_safe_one_cent_tolerance_unchanged(self, session):
        cash_id = _acct_id(session, "Cash")
        inc_id = _acct_id(session, "Sales Revenue")
        entry = posting.create_journal_entry(
            session,
            POST_DATE,
            "md02 safe cent",
            "Manual",
            None,
            [(cash_id, 128.03, 0.0), (inc_id, 0.0, 128.02)],
            company_id=COMPANY_ID,
        )
        assert entry.id is not None


class TestFxNativeDecimalMath:
    @pytest.mark.parametrize(
        ("currency", "cash_name", "fx_rate"),
        [
            ("TRY", "Cash", 1.0),
            ("USD", "Cash USD", 34.5678),
            ("EUR", "Cash EUR", 37.1234),
        ],
    )
    def test_amount_native_matches_quantize_fx(self, session, currency, cash_name, fx_rate):
        sale = models.Sale(
            date=POST_DATE,
            invoice_number=f"MD04c-{currency}",
            customer_name="C",
            description=f"fx {currency}",
            amount=AMOUNT,
            sale_type="Cash",
            paid_amount=AMOUNT,
            balance=0.0,
            status="Paid",
            currency=currency,
            fx_rate=fx_rate,
            company_id=COMPANY_ID,
        )
        session.add(sale)
        session.flush()
        posting.post_cash_sale(
            session,
            sale.id,
            AMOUNT,
            POST_DATE,
            currency=currency,
            fx_rate=fx_rate,
            company_id=COMPANY_ID,
        )
        entry = _entries_for(session, "CashSale", sale.id)[0]
        natives = [
            fx_to_float(ln.amount_native)
            for ln in entry.lines
            if ln.amount_native is not None
        ]
        expected = fx_to_float(quantize_fx(parse_money(AMOUNT) * parse_money(fx_rate)))
        assert len(natives) == 2
        assert natives[0] == expected
        assert natives[1] == -expected

    def test_manual_je_fx_native_from_net(self, session):
        cash_id = _acct_id(session, "Cash USD", currency="USD")
        inc_id = _acct_id(session, "Sales Revenue")
        fx_rate = 34.5678
        entry = posting.create_journal_entry(
            session,
            POST_DATE,
            "manual fx",
            "Manual",
            None,
            [(cash_id, AMOUNT, 0.0), (inc_id, 0.0, AMOUNT)],
            currency="USD",
            fx_rate=fx_rate,
            company_id=COMPANY_ID,
        )
        lines = (
            session.query(models.JournalEntryLine)
            .filter_by(journal_entry_id=entry.id)
            .order_by(models.JournalEntryLine.id)
            .all()
        )
        for ln in lines:
            net = money_to_float(ln.debit) - money_to_float(ln.credit)
            expected = fx_to_float(quantize_fx(parse_money(net) * parse_money(fx_rate)))
            assert fx_to_float(ln.amount_native) == expected


class TestReversalSymmetryDecimalInputs:
    def test_void_reversal_swaps_decimal_persisted_amounts(self, session):
        sale = models.Sale(
            date=POST_DATE,
            invoice_number="MD04c-REV",
            customer_name="C",
            description="reversal",
            amount=AMOUNT,
            sale_type="Cash",
            paid_amount=AMOUNT,
            balance=0.0,
            status="Paid",
            company_id=COMPANY_ID,
        )
        session.add(sale)
        session.flush()
        posting.post_cash_sale(
            session,
            sale.id,
            Decimal("100.01"),
            POST_DATE,
            company_id=COMPANY_ID,
        )
        original = _entries_for(session, "CashSale", sale.id)[0]
        orig_lines = _je_lines(session, original.id)
        posting.void_sale(session, sale.id, VOID_REASON, company_id=COMPANY_ID)
        rev = _entries_for(session, "Reversal", original.id)[0]
        rev_lines = _je_lines(session, rev.id)
        assert rev_lines == [(a, c, d) for a, d, c in orig_lines]
        for orig, rev_ln in zip(original.lines, rev.lines):
            assert quantize_money(orig.debit) == quantize_money(rev_ln.credit)
            assert quantize_money(orig.credit) == quantize_money(rev_ln.debit)
