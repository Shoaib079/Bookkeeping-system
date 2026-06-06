import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models
from db import Base


def test_customer_model_can_be_created():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with SessionLocal() as session:
        customer = models.Customer(
            name="Test Customer",
            contact="Jane Doe",
            phone="555-0100",
            email="jane@example.com",
            address="123 Test St",
        )
        session.add(customer)
        session.commit()

        assert customer.id is not None
        assert customer.name == "Test Customer"


def test_customer_ledger_entry_links_to_customer():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with SessionLocal() as session:
        customer = models.Customer(name="Ledger Customer")
        session.add(customer)
        session.commit()

        entry = models.CustomerLedgerEntry(
            customer_id=customer.id,
            date=datetime.date.today(),
            type="invoice",
            amount=150.0,
            description="Test invoice",
        )
        session.add(entry)
        session.commit()

        assert entry.id is not None
        assert entry.customer_id == customer.id
        assert entry.customer.name == "Ledger Customer"


def test_product_and_inventory_transaction():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with SessionLocal() as session:
        product = models.Product(
            sku="P001",
            name="Test Product",
            description="A test product",
            quantity=10,
            unit_price=9.99,
        )
        session.add(product)
        session.commit()

        transaction = models.InventoryTransaction(
            product_id=product.id,
            date=datetime.date.today(),
            change=-3,
            notes="Stock out",
        )
        session.add(transaction)
        session.commit()

        assert transaction.id is not None
        assert transaction.product.name == "Test Product"
        assert transaction.change == -3


def test_bank_account_and_transactions():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with SessionLocal() as session:
        account = models.BankAccount(
            name="Main Account",
            bank_name="Test Bank",
            account_number="12345678",
            balance=500.0,
        )
        session.add(account)
        session.commit()

        deposit = models.BankTransaction(
            account_id=account.id,
            date=datetime.date.today(),
            amount=200.0,
            type="deposit",
            description="Deposit funds",
        )
        withdrawal = models.BankTransaction(
            account_id=account.id,
            date=datetime.date.today(),
            amount=100.0,
            type="withdrawal",
            description="Withdrawal funds",
        )
        session.add_all([deposit, withdrawal])
        session.commit()

        assert deposit.id is not None
        assert withdrawal.id is not None
        assert deposit.account.name == "Main Account"
        assert withdrawal.account.account_number == "12345678"


def test_chart_of_accounts_and_journal_entry():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with SessionLocal() as session:
        cash = models.ChartOfAccounts(account_code="1000", account_name="Cash", account_type="Asset")
        sales = models.ChartOfAccounts(account_code="4000", account_name="Sales Revenue", account_type="Income")
        session.add_all([cash, sales])
        session.commit()

        entry = models.JournalEntry(
            entry_date=datetime.date.today(),
            description="Test cash sale",
            reference_type="CashSale",
            reference_id=1,
        )
        session.add(entry)
        session.commit()

        line1 = models.JournalEntryLine(journal_entry_id=entry.id, account_id=cash.id, debit=100.0, credit=0.0)
        line2 = models.JournalEntryLine(journal_entry_id=entry.id, account_id=sales.id, debit=0.0, credit=100.0)
        session.add_all([line1, line2])
        session.commit()

        assert entry.id is not None
        assert len(entry.lines) == 2
        assert entry.lines[0].debit == 100.0
        assert entry.lines[1].credit == 100.0
        assert entry.lines[0].account.account_name == "Cash"
        assert entry.lines[1].account.account_name == "Sales Revenue"
