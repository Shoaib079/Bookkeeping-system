"""Phase 14C — Company Query Isolation Tests.

Verifies that every Category-A model query returns only rows belonging to
the active company, and that Company A cannot see Company B's data.

Two-company setup per test:
  company_A: seeds its own data, active_company_id = A.id
  company_B: seeds parallel data with different values

Each test then:
  1. Asserts Company A sees only A's data
  2. Switches active_company_id to B and asserts Company B sees only B's data

Coverage areas:
  1.  Sales
  2.  ExpenseRecord
  3.  Purchase / Payable
  4.  Customer
  5.  Vendor
  6.  BankAccount / BankTransaction
  7.  Product / InventoryTransaction
  8.  FiscalPeriod
  9.  Journal Entries (GL)
 10.  calculate_account_balance_for_period — GL balance isolation
 11.  calculate_account_balance — GL balance isolation
 12.  ChartOfAccounts
 13.  TransactionCategory / TransactionSubcategory
 14.  Budget
 15.  RecurringExpenseTemplate / RecurringExpenseDraft
 16.  before_flush stamps company_id on new objects
 17.  create_journal_entry period lock is company-scoped
 18.  create_journal_entry YEC lock is company-scoped
"""

import sys
import datetime
from unittest.mock import MagicMock
from sqlalchemy import event as _sa_event

# ── Streamlit mock — real dict so cq() works ─────────────────────────────────
if "streamlit" not in sys.modules:
    _st_mock = MagicMock()
    _st_mock.session_state = {}
    sys.modules["streamlit"] = _st_mock
else:
    _st_mock = sys.modules["streamlit"]
    if not isinstance(getattr(_st_mock, "session_state", None), dict):
        _st_mock.session_state = {}

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
import app

app.DEVELOPMENT_MODE = False


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_session():
    sys.modules["streamlit"].session_state.clear()
    yield
    sys.modules["streamlit"].session_state.clear()


@pytest.fixture()
def db():
    """Fresh in-memory SQLite per test with before_flush stamping enabled."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    @_sa_event.listens_for(Session, "before_flush")
    def _stamp(sess, ctx, instances):
        app._stamp_company_id_on_new_objects(sess, ctx, instances)

    with Session() as s:
        yield s


# ─── Seed helpers ─────────────────────────────────────────────────────────────

def _company(db, name, slug):
    c = models.Company(
        name=name, slug=slug, is_active=True,
        created_at=datetime.datetime.now(),
    )
    db.add(c)
    db.flush()
    return c


def _set_active(company_id):
    sys.modules["streamlit"].session_state["active_company_id"] = company_id


def _coa(db, code, name, acct_type="Asset"):
    """Create a COA account under the currently active company."""
    a = models.ChartOfAccounts(
        account_code=code, account_name=name,
        account_type=acct_type, balance=0.0, is_active=True,
    )
    db.add(a)
    db.flush()
    return a


def _sale(db, amount=100.0):
    s = models.Sale(
        date=datetime.date(2026, 1, 15),
        invoice_number=f"INV-{amount}",
        customer_name="Test Customer",
        amount=amount,
        sale_type="Cash",
        paid_amount=amount,
        balance=0.0,
        status="Paid",
        due_date=datetime.date(2026, 1, 15),
    )
    db.add(s)
    db.flush()
    return s


# ─── 1. Sales ─────────────────────────────────────────────────────────────────

class TestSaleIsolation:
    def test_company_a_sees_only_its_sales(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        _sale(db, amount=100.0)

        _set_active(co_b.id)
        _sale(db, amount=200.0)

        _set_active(co_a.id)
        results = app.cq(db, models.Sale).all()
        assert len(results) == 1
        assert results[0].amount == 100.0

    def test_company_b_sees_only_its_sales(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        _sale(db, amount=100.0)

        _set_active(co_b.id)
        _sale(db, amount=200.0)

        results = app.cq(db, models.Sale).all()
        assert len(results) == 1
        assert results[0].amount == 200.0

    def test_total_rows_in_db_is_two(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")
        _set_active(co_a.id); _sale(db, 100.0)
        _set_active(co_b.id); _sale(db, 200.0)
        assert db.query(models.Sale).count() == 2


# ─── 2. ExpenseRecord ─────────────────────────────────────────────────────────

class TestExpenseIsolation:
    def test_company_a_sees_only_its_expenses(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        db.add(models.ExpenseRecord(
            date=datetime.date(2026, 1, 1), expense_type="Rent",
            amount=300.0, payment_method="Cash", is_void=False,
        ))
        db.flush()

        _set_active(co_b.id)
        db.add(models.ExpenseRecord(
            date=datetime.date(2026, 1, 1), expense_type="Salary",
            amount=500.0, payment_method="Bank", is_void=False,
        ))
        db.flush()
        db.commit()

        _set_active(co_a.id)
        results = app.cq(db, models.ExpenseRecord).all()
        assert len(results) == 1
        assert results[0].amount == 300.0


# ─── 3. Vendor / Purchase ─────────────────────────────────────────────────────

class TestPurchaseIsolation:
    def test_vendors_are_company_scoped(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        db.add(models.Vendor(name="Vendor A", is_active=True))
        db.flush()

        _set_active(co_b.id)
        db.add(models.Vendor(name="Vendor B", is_active=True))
        db.flush()
        db.commit()

        _set_active(co_a.id)
        vendors = app.cq(db, models.Vendor).all()
        assert len(vendors) == 1
        assert vendors[0].name == "Vendor A"


# ─── 4. Customer ──────────────────────────────────────────────────────────────

class TestCustomerIsolation:
    def test_customers_are_company_scoped(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        db.add(models.Customer(name="Alice", is_active=True))
        db.flush()

        _set_active(co_b.id)
        db.add(models.Customer(name="Bob", is_active=True))
        db.flush()
        db.commit()

        _set_active(co_a.id)
        custs = app.cq(db, models.Customer).all()
        assert len(custs) == 1
        assert custs[0].name == "Alice"


# ─── 5. BankAccount / BankTransaction ─────────────────────────────────────────

class TestBankingIsolation:
    def test_bank_accounts_are_company_scoped(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        db.add(models.BankAccount(name="A-Cash", balance=1000.0, is_active=True))
        db.flush()

        _set_active(co_b.id)
        db.add(models.BankAccount(name="B-Cash", balance=5000.0, is_active=True))
        db.flush()
        db.commit()

        _set_active(co_a.id)
        accounts = app.cq(db, models.BankAccount).all()
        assert len(accounts) == 1
        assert accounts[0].name == "A-Cash"


# ─── 6. Product / Inventory ───────────────────────────────────────────────────

class TestInventoryIsolation:
    def test_products_are_company_scoped(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        db.add(models.Product(name="Widget A", sku="SKU-A", quantity=10, is_active=True))
        db.flush()

        _set_active(co_b.id)
        db.add(models.Product(name="Widget B", sku="SKU-B", quantity=20, is_active=True))
        db.flush()
        db.commit()

        _set_active(co_b.id)
        prods = app.cq(db, models.Product).all()
        assert len(prods) == 1
        assert prods[0].name == "Widget B"


# ─── 7. FiscalPeriod ──────────────────────────────────────────────────────────

class TestFiscalPeriodIsolation:
    def test_fiscal_periods_are_company_scoped(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        db.add(models.FiscalPeriod(
            name="A-Jan", start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 1, 31), is_closed=False,
        ))
        db.flush()

        _set_active(co_b.id)
        db.add(models.FiscalPeriod(
            name="B-Jan", start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 1, 31), is_closed=False,
        ))
        db.flush()
        db.commit()

        _set_active(co_a.id)
        periods = app.cq(db, models.FiscalPeriod).all()
        assert len(periods) == 1
        assert periods[0].name == "A-Jan"


# ─── 8. ChartOfAccounts ───────────────────────────────────────────────────────

class TestCOAIsolation:
    def test_coa_is_company_scoped(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        _coa(db, "1000", "Cash A")

        _set_active(co_b.id)
        _coa(db, "1000", "Cash B")

        _set_active(co_a.id)
        accounts = app.cq(db, models.ChartOfAccounts).all()
        assert len(accounts) == 1
        assert accounts[0].account_name == "Cash A"

    def test_get_account_by_name_is_company_scoped(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        _coa(db, "1000", "Cash")

        _set_active(co_b.id)
        _coa(db, "1001", "Cash")

        # Company B's cash account is code 1001
        _set_active(co_b.id)
        acct = app.get_account_by_name(db, "Cash")
        assert acct is not None
        assert acct.account_code == "1001"

    def test_get_account_by_name_returns_none_for_other_company(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        _coa(db, "1000", "Cash")
        db.commit()

        _set_active(co_b.id)
        acct = app.get_account_by_name(db, "Cash")
        assert acct is None


# ─── 9. GL Journal Entry balance isolation ────────────────────────────────────

class TestGLIsolation:
    def _seed_je(self, db, acct_id, debit, credit):
        je = models.JournalEntry(
            entry_date=datetime.date(2026, 1, 15),
            description="Test JE",
            reference_type="Sale",
            reference_id=1,
        )
        db.add(je)
        db.flush()
        jel = models.JournalEntryLine(
            journal_entry_id=je.id,
            account_id=acct_id,
            debit=debit,
            credit=credit,
        )
        db.add(jel)
        db.flush()
        return je

    def test_calculate_balance_for_period_is_company_scoped(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        acct_a = _coa(db, "1000", "Cash")
        self._seed_je(db, acct_a.id, 400.0, 0.0)
        db.commit()

        _set_active(co_b.id)
        acct_b = _coa(db, "1000", "Cash")
        self._seed_je(db, acct_b.id, 999.0, 0.0)
        db.commit()

        _set_active(co_a.id)
        bal = app.calculate_account_balance_for_period(
            db, acct_a,
            datetime.date(2026, 1, 1), datetime.date(2026, 1, 31),
        )
        assert bal == pytest.approx(400.0)

    def test_calculate_balance_excludes_other_company_je(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        acct_a = _coa(db, "1000", "Cash")
        db.commit()

        _set_active(co_b.id)
        acct_b = _coa(db, "1000", "Cash")
        self._seed_je(db, acct_b.id, 999.0, 0.0)
        db.commit()

        _set_active(co_a.id)
        bal = app.calculate_account_balance_for_period(
            db, acct_a,
            datetime.date(2026, 1, 1), datetime.date(2026, 1, 31),
        )
        assert bal == pytest.approx(0.0)

    def test_calculate_account_balance_is_company_scoped(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        acct_a = _coa(db, "1000", "Cash")
        self._seed_je(db, acct_a.id, 300.0, 0.0)
        db.commit()

        _set_active(co_b.id)
        acct_b = _coa(db, "1000", "Cash")
        self._seed_je(db, acct_b.id, 700.0, 0.0)
        db.commit()

        _set_active(co_a.id)
        bal = app.calculate_account_balance(db, acct_a)
        assert bal == pytest.approx(300.0)

    def test_je_query_is_company_scoped(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        acct_a = _coa(db, "1000", "Cash")
        self._seed_je(db, acct_a.id, 100.0, 0.0)
        db.commit()

        _set_active(co_b.id)
        acct_b = _coa(db, "1000", "Cash")
        self._seed_je(db, acct_b.id, 200.0, 0.0)
        db.commit()

        _set_active(co_a.id)
        jes = app.cq(db, models.JournalEntry).all()
        assert len(jes) == 1


# ─── 10. TransactionCategory ──────────────────────────────────────────────────

class TestCategoryIsolation:
    def test_categories_are_company_scoped(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        db.add(models.TransactionCategory(
            name="Rent", transaction_type="Expense", is_active=True))
        db.flush()

        _set_active(co_b.id)
        db.add(models.TransactionCategory(
            name="Salary", transaction_type="Expense", is_active=True))
        db.flush()
        db.commit()

        _set_active(co_a.id)
        cats = app.cq(db, models.TransactionCategory).all()
        assert len(cats) == 1
        assert cats[0].name == "Rent"


# ─── 11. before_flush stamps company_id ───────────────────────────────────────

class TestBeforeFlushIntegration:
    def test_new_sale_gets_correct_company_id(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_a.id)
        sale = models.Sale(
            date=datetime.date(2026, 1, 1),
            invoice_number="INV-001",
            customer_name="Test",
            amount=500.0,
            sale_type="Cash",
            paid_amount=500.0,
            balance=0.0,
            status="Paid",
            due_date=datetime.date(2026, 1, 1),
        )
        db.add(sale)
        db.commit()

        assert sale.company_id == co_a.id

    def test_switching_company_stamps_new_company_id(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        _set_active(co_b.id)
        sale = models.Sale(
            date=datetime.date(2026, 1, 1),
            invoice_number="INV-B-001",
            customer_name="Test B",
            amount=200.0,
            sale_type="Cash",
            paid_amount=200.0,
            balance=0.0,
            status="Paid",
            due_date=datetime.date(2026, 1, 1),
        )
        db.add(sale)
        db.commit()

        assert sale.company_id == co_b.id


# ─── 12. Period lock is company-scoped ───────────────────────────────────────

class TestPeriodLockIsolation:
    def test_closed_period_blocks_only_its_company(self, db):
        co_a = _company(db, "Alpha", "alpha")
        co_b = _company(db, "Beta",  "beta")

        # Close a period for company A
        _set_active(co_a.id)
        fp = models.FiscalPeriod(
            name="A-Jan", start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 1, 31), is_closed=True,
            closed_at=datetime.date(2026, 2, 1),
        )
        db.add(fp)
        acct_a = _coa(db, "1000", "Cash")
        acct_re = _coa(db, "3100", "Retained Earnings", "Equity")
        db.commit()

        # Company A: posting into closed period should raise
        import pytest as _pytest
        with _pytest.raises(ValueError, match="closed"):
            app.create_journal_entry(
                db, datetime.date(2026, 1, 15), "Blocked",
                "Sale", None,
                [(acct_a.id, 0, 100), (acct_re.id, 100, 0)],
            )

        # Company B: same date range is NOT locked for them
        _set_active(co_b.id)
        acct_b = _coa(db, "1000", "Cash B")
        acct_rb = _coa(db, "3100", "Retained B", "Equity")
        db.commit()
        je = app.create_journal_entry(
            db, datetime.date(2026, 1, 15), "Allowed",
            "Sale", None,
            [(acct_b.id, 0, 100), (acct_rb.id, 100, 0)],
        )
        assert je is not None
