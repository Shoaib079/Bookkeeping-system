from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from db import Base


class MigrationFlag(Base):
    __tablename__ = "migration_flags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    applied_at = Column(Date, nullable=False)


class AppSetting(Base):
    """Key-value store for application settings.

    Replaces settings.json so settings are backed up with the database.
    All values are stored as strings; callers coerce as needed.
    """
    __tablename__ = "app_settings"

    key   = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)


class User(Base):
    """Application users with role-based access.

    Roles:
      owner    — full access (all pages, all actions, user management)
      cashier  — add/edit own transactions; no reports, no settings
      partner  — read-only (dashboard + reports only)
    """
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(100), nullable=False, unique=True)
    display_name  = Column(String(200), nullable=True)
    password_hash = Column(String(256), nullable=False)
    role          = Column(String(50),  nullable=False, default="cashier")
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, nullable=True)
    email         = Column(String(200), nullable=True)
    phone         = Column(String(100), nullable=True)
    last_login    = Column(DateTime,    nullable=True)


# ── Phase 14A — Multi-company models ─────────────────────────────────────────

class Company(Base):
    """Multi-company root entity.

    Slug is set once at creation and never changed — used for file path
    isolation, audit context, and MigrationFlag guards. The default company
    for all existing data is slug='company_1'.
    """
    __tablename__ = "companies"

    id                 = Column(Integer,     primary_key=True, index=True)
    name               = Column(String(200), nullable=False)
    slug               = Column(String(50),  nullable=False, unique=True)
    is_active          = Column(Boolean,     nullable=False, default=True)
    created_at         = Column(DateTime,    nullable=False)
    # Phase 14D-A: extended identity fields (nullable — existing rows need no backfill)
    full_name          = Column(String(300), nullable=True)   # legal company name
    email              = Column(String(200), nullable=True)   # company contact email
    phone              = Column(String(100), nullable=True)   # company contact phone
    created_by_user_id = Column(Integer,     ForeignKey("users.id"), nullable=True, index=True)

    users    = relationship("CompanyUser",    back_populates="company")
    settings = relationship("CompanySetting", back_populates="company")


class CompanyUser(Base):
    """User membership in a specific company with a company-scoped role.

    One row per (company, user) pair. A user may belong to multiple companies
    with independent roles. User.role is kept intact for Phase 14A backward
    compatibility and will be deprecated in Phase 14C.
    """
    __tablename__ = "company_users"

    id              = Column(Integer,    primary_key=True, index=True)
    company_id      = Column(Integer,    ForeignKey("companies.id"), nullable=False, index=True)
    user_id         = Column(Integer,    ForeignKey("users.id"),     nullable=False, index=True)
    role            = Column(String(50), nullable=False)
    is_active       = Column(Boolean,    nullable=False, default=True)
    created_at      = Column(DateTime,   nullable=False)
    # Phase 14D-A: who added this member (nullable — existing rows have no inviter)
    invited_by_id   = Column(Integer,    ForeignKey("users.id"), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_company_user"),
    )

    company = relationship("Company", back_populates="users")
    user    = relationship("User", foreign_keys=[user_id])


class CompanySetting(Base):
    """Per-company key-value configuration store.

    Mirrors AppSetting but scoped to a company. AppSetting remains intact and
    is still read by the current app. CompanySetting is seeded during Phase 14A
    migration and will replace AppSetting reads in Phase 14B.
    """
    __tablename__ = "company_settings"

    id         = Column(Integer,     primary_key=True, index=True)
    company_id = Column(Integer,     ForeignKey("companies.id"), nullable=False, index=True)
    key        = Column(String(100), nullable=False)
    value      = Column(Text,        nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "key", name="uq_company_setting"),
    )

    company = relationship("Company", back_populates="settings")


# ── Double-entry accounting models ────────────────────────────────────────────


class ChartOfAccounts(Base):
    __tablename__ = "chart_of_accounts"

    id = Column(Integer, primary_key=True, index=True)
    # unique=True removed — compound UNIQUE(company_id, account_code) enforced
    # via uq_coa_code_company index created in migrate_schema() after rebuild.
    account_code = Column(String(50), nullable=False)
    account_name = Column(String(200), nullable=False)
    account_type = Column(String(50), nullable=False)  # Asset, Liability, Equity, Income, Expense
    currency     = Column(String(10), nullable=True)   # Step 1.1 — None means "any / reporting currency"
    balance = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    company_id = Column(Integer, nullable=True)        # Phase 14A

    journal_lines = relationship("JournalEntryLine", back_populates="account")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    entry_date = Column(Date, nullable=False, index=True)
    description = Column(Text, nullable=False)
    reference_type = Column(String(50), nullable=True, index=True)
    reference_id = Column(Integer, nullable=True)
    company_id = Column(Integer, nullable=True)        # Phase 14A

    lines = relationship("JournalEntryLine", back_populates="journal_entry")


class JournalEntryLine(Base):
    __tablename__ = "journal_entry_lines"

    id = Column(Integer, primary_key=True, index=True)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=False, index=True)
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    currency = Column(String(10), nullable=True)      # transaction currency (e.g. "USD")
    amount_native = Column(Float, nullable=True)      # debit-credit net in reporting currency
    company_id = Column(Integer, nullable=True)       # Phase 14A

    journal_entry = relationship("JournalEntry", back_populates="lines")
    account = relationship("ChartOfAccounts", back_populates="journal_lines")


# Existing Phase 1 models


class CashSale(Base):
    __tablename__ = "cash_sales"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    customer_name = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, default="")
    company_id = Column(Integer, nullable=True)       # Phase 14A


class CreditSale(Base):
    __tablename__ = "credit_sales"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    customer_name = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    due_date = Column(Date, nullable=False)
    description = Column(Text, default="")
    company_id = Column(Integer, nullable=True)       # Phase 14A


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    invoice_number = Column(String(100), nullable=False)
    customer_name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    amount = Column(Float, nullable=False)
    sale_type = Column(String(20), nullable=False, index=True)
    paid_amount = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)
    due_date = Column(Date, nullable=True)
    status = Column(String(50), nullable=False, index=True)
    is_void = Column(Boolean, default=False, index=True)
    voided_at = Column(Date, nullable=True)
    void_reason = Column(Text, nullable=True)
    tx_category_id = Column(Integer, nullable=True)
    tx_subcategory_id = Column(Integer, nullable=True)
    created_by_id = Column(Integer, nullable=True)  # FK → users.id (soft ref)
    customer_id   = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
    # Step 1.3 — FX fields
    currency      = Column(String(10),  nullable=True)
    fx_rate       = Column(Float,       default=1.0)
    native_amount = Column(Float,       nullable=True)
    company_id    = Column(Integer,     nullable=True)  # Phase 14A


class ExpenseRecord(Base):
    __tablename__ = "expense_records"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    expense_type = Column(String(50), nullable=False)
    category = Column(String(100), nullable=True)
    description = Column(Text, default="")
    amount = Column(Float, nullable=False)
    payment_method = Column(String(100), nullable=True)
    employee_name = Column(String(200), nullable=True)
    pay_period = Column(String(100), nullable=True)
    gross_salary = Column(Float, default=0.0)
    deductions = Column(Float, default=0.0)
    net_salary = Column(Float, default=0.0)
    is_void = Column(Boolean, default=False, index=True)
    voided_at = Column(Date, nullable=True)
    void_reason = Column(Text, nullable=True)
    tx_category_id = Column(Integer, nullable=True)
    tx_subcategory_id = Column(Integer, nullable=True)
    created_by_id = Column(Integer, nullable=True)  # FK → users.id (soft ref)
    # Step 1.3 — FX fields
    currency      = Column(String(10), nullable=True)
    fx_rate       = Column(Float,      default=1.0)
    native_amount = Column(Float,      nullable=True)
    company_id    = Column(Integer,    nullable=True)  # Phase 14A


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    contact = Column(String(200), nullable=True)
    phone = Column(String(100), nullable=True)
    email = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    company_id = Column(Integer, nullable=True)       # Phase 14A

    purchases = relationship("Purchase", back_populates="vendor")
    payables = relationship("Payable", back_populates="vendor")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)
    purchase_number = Column(String(100), nullable=True)
    amount = Column(Float, nullable=False)
    description = Column(Text, default="")
    purchase_type = Column(String(20), default="Credit")
    gl_debit = Column(String(100), default="Inventory")
    is_void = Column(Boolean, default=False, index=True)
    voided_at = Column(Date, nullable=True)
    void_reason = Column(Text, nullable=True)
    tx_category_id = Column(Integer, nullable=True)
    tx_subcategory_id = Column(Integer, nullable=True)
    created_by_id = Column(Integer, nullable=True)  # FK → users.id (soft ref)
    # Step 1.3 — FX fields
    currency      = Column(String(10), nullable=True)
    fx_rate       = Column(Float,      default=1.0)
    native_amount = Column(Float,      nullable=True)
    company_id    = Column(Integer,    nullable=True)  # Phase 14A

    vendor = relationship("Vendor", back_populates="purchases")


class Payable(Base):
    __tablename__ = "payables"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    balance = Column(Float, nullable=True)
    due_date = Column(Date, nullable=False, index=True)
    paid = Column(Boolean, default=False, index=True)
    description = Column(Text, default="")
    expense_category = Column(String(100), default="Rent")
    payment_method = Column(String(50), nullable=True)
    purchase_id = Column(Integer, nullable=True)
    is_void = Column(Boolean, default=False, index=True)
    voided_at = Column(Date, nullable=True)
    void_reason = Column(Text, nullable=True)
    company_id = Column(Integer, nullable=True)       # Phase 14A

    vendor = relationship("Vendor", back_populates="payables")


class Salary(Base):
    __tablename__ = "salaries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    employee_name = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    pay_period = Column(String(200), nullable=True)
    description = Column(Text, default="")
    company_id = Column(Integer, nullable=True)       # Phase 14A


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    category = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, default="")
    company_id = Column(Integer, nullable=True)       # Phase 14A


# Phase 2 models: customers, ledger, products, inventory, banking


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    contact = Column(String(200), nullable=True)
    phone = Column(String(100), nullable=True)
    email = Column(String(200), nullable=True)
    address = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    company_id = Column(Integer, nullable=True)       # Phase 14A

    ledger_entries = relationship("CustomerLedgerEntry", back_populates="customer")


class CustomerLedgerEntry(Base):
    __tablename__ = "customer_ledger"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    date = Column(Date, nullable=False)
    type = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, default="")
    company_id = Column(Integer, nullable=True)       # Phase 14A

    customer = relationship("Customer", back_populates="ledger_entries")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    # unique=True removed — compound UNIQUE(company_id, sku) enforced via
    # uq_products_sku_company index created in migrate_schema() after rebuild.
    sku = Column(String(100), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    subcategory = Column(String(100), nullable=True)
    unit_of_measure = Column(String(50), nullable=True)
    cost_price = Column(Float, default=0.0)
    unit_price = Column(Float, default=0.0)
    quantity = Column(Float, default=0)
    min_stock = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    company_id = Column(Integer, nullable=True)       # Phase 14A

    inventory_transactions = relationship("InventoryTransaction", back_populates="product")


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    date = Column(Date, nullable=False)
    change = Column(Float, nullable=False)
    notes = Column(Text, default="")
    is_void = Column(Boolean, default=False)
    voided_at = Column(Date, nullable=True)
    void_reason = Column(Text, nullable=True)
    company_id = Column(Integer, nullable=True)       # Phase 14A

    product = relationship("Product", back_populates="inventory_transactions")


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    bank_name = Column(String(200), nullable=True)
    account_number = Column(String(200), nullable=True)
    balance = Column(Float, default=0.0)
    currency = Column(String(10), nullable=True, default="TRY")
    is_active = Column(Boolean, default=True)
    kind = Column(String(20), nullable=False, default="bank")  # bank | credit_card (18-MVP-5)
    company_id = Column(Integer, nullable=True)       # Phase 14A

    transactions = relationship("BankTransaction", back_populates="account")


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    type = Column(String(50), nullable=False)
    description = Column(Text, default="")
    is_void = Column(Boolean, default=False, index=True)
    voided_at = Column(Date, nullable=True)
    void_reason = Column(Text, nullable=True)
    company_id = Column(Integer, nullable=True)       # Phase 14A
    # Phase 18-MVP-1 — bank reconciliation foundation
    is_reconciled = Column(Boolean, default=False, index=True)
    statement_ref = Column(String(100), nullable=True, index=True)
    charge_subtype = Column(String(50), nullable=True)  # transfer_fee / card_settlement_fee / credit_card_fee / interest / monthly_fee

    account = relationship("BankAccount", back_populates="transactions")


class FiscalPeriod(Base):
    __tablename__ = "fiscal_periods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_closed = Column(Boolean, default=False)
    closed_at = Column(Date, nullable=True)
    closing_je_id = Column(Integer, nullable=True)
    company_id = Column(Integer, nullable=True)       # Phase 14A


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    performed_by = Column(String(100), nullable=True)
    # Nullable: NULL = system-level event; set = company-level event
    company_id = Column(Integer, nullable=True)       # Phase 14A


class TransactionCategory(Base):
    __tablename__ = "transaction_categories"

    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(String(50), nullable=False)  # Sale, Expense, Purchase
    name = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    company_id = Column(Integer, nullable=True)       # Phase 14A

    subcategories = relationship("TransactionSubcategory", back_populates="category")


class TransactionSubcategory(Base):
    __tablename__ = "transaction_subcategories"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("transaction_categories.id"), nullable=False)
    name = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True)
    company_id = Column(Integer, nullable=True)       # Phase 14A

    category = relationship("TransactionCategory", back_populates="subcategories")


class Budget(Base):
    """Monthly budget targets per expense category or GL account."""
    __tablename__ = "budgets"

    id          = Column(Integer, primary_key=True, index=True)
    year        = Column(Integer, nullable=False, index=True)
    month       = Column(Integer, nullable=False)
    account_id  = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True, index=True)
    category    = Column(String(200), nullable=True)
    amount      = Column(Float, nullable=False, default=0.0)
    notes       = Column(Text, nullable=True)
    company_id  = Column(Integer, nullable=True)      # Phase 14A


class RecurringExpenseTemplate(Base):
    """Template defining a recurring expense that generates periodic drafts."""
    __tablename__ = "recurring_expense_templates"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(200), nullable=False)
    category       = Column(String(100), nullable=False)
    description    = Column(Text, default="")
    amount         = Column(Float, nullable=False)
    payment_method = Column(String(50), default="Cash")
    frequency      = Column(String(20), nullable=False)
    start_date     = Column(Date, nullable=False)
    next_due_date  = Column(Date, nullable=False, index=True)
    is_active      = Column(Boolean, nullable=False, default=True, index=True)
    vendor_id      = Column(Integer, nullable=True)
    created_by_id  = Column(Integer, nullable=True)
    created_at     = Column(DateTime, nullable=True)
    company_id     = Column(Integer, nullable=True)   # Phase 14A

    drafts = relationship("RecurringExpenseDraft", back_populates="template")


class DailyCashReconciliation(Base):
    """Daily cash reconciliation for a single cash GL account."""
    __tablename__ = "daily_cash_reconciliation"

    id                  = Column(Integer, primary_key=True, index=True)
    date                = Column(Date, nullable=False, index=True)
    cash_account_id     = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=False, index=True)
    opening_cash        = Column(Float, nullable=True)
    expected_cash       = Column(Float, nullable=False)
    actual_cash         = Column(Float, nullable=False)
    difference          = Column(Float, nullable=False)
    variance_type       = Column(String(20), nullable=False)
    status              = Column(String(50), nullable=False, default="draft", index=True)
    reconciled_by_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    reconciled_at       = Column(DateTime, nullable=True)
    rejection_reason    = Column(Text, nullable=True)
    rejected_by_id      = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_at         = Column(DateTime, nullable=True)
    journal_entry_id    = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    notes               = Column(Text, nullable=True)
    created_by_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at          = Column(DateTime, nullable=False)
    updated_at          = Column(DateTime, nullable=True)
    is_void             = Column(Boolean, default=False, index=True)
    voided_by_id        = Column(Integer, ForeignKey("users.id"), nullable=True)
    voided_at           = Column(DateTime, nullable=True)
    void_reason         = Column(Text, nullable=True)
    reversed_je_id      = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    company_id          = Column(Integer, nullable=True)  # Phase 14A

    cash_account     = relationship("ChartOfAccounts")
    created_by       = relationship("User", foreign_keys=[created_by_id])
    approved_by      = relationship("User", foreign_keys=[reconciled_by_id])
    rejected_by      = relationship("User", foreign_keys=[rejected_by_id])
    voided_by        = relationship("User", foreign_keys=[voided_by_id])
    journal_entry    = relationship("JournalEntry", foreign_keys=[journal_entry_id])
    reversed_journal = relationship("JournalEntry", foreign_keys=[reversed_je_id])


class RecurringExpenseDraft(Base):
    """A single generated occurrence of a recurring expense template."""
    __tablename__ = "recurring_expense_drafts"

    id                = Column(Integer, primary_key=True, index=True)
    template_id       = Column(Integer, ForeignKey("recurring_expense_templates.id"), nullable=False, index=True)
    due_date          = Column(Date, nullable=False, index=True)
    amount            = Column(Float, nullable=False)
    description       = Column(Text, default="")
    category          = Column(String(100), nullable=False)
    payment_method    = Column(String(50), default="Cash")
    status            = Column(String(20), nullable=False, default="pending", index=True)
    posted_expense_id = Column(Integer, nullable=True)
    skip_reason       = Column(Text, nullable=True)
    postponed_to      = Column(Date, nullable=True)
    actioned_at       = Column(Date, nullable=True)
    actioned_by_id    = Column(Integer, nullable=True)
    company_id        = Column(Integer, nullable=True)  # Phase 14A

    template = relationship("RecurringExpenseTemplate", back_populates="drafts")


class EndOfDayClose(Base):
    """Daily end-of-day management record."""
    __tablename__ = "end_of_day_closes"

    id                    = Column(Integer, primary_key=True, index=True)
    date                  = Column(Date, nullable=False, index=True)
    status                = Column(String(50), nullable=False, default="closed", index=True)
    closed_by_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    closed_at             = Column(DateTime, nullable=False)
    notes                 = Column(Text, nullable=True)
    cash_sales            = Column(Float, nullable=False, default=0.0)
    card_sales            = Column(Float, nullable=False, default=0.0)
    credit_sales          = Column(Float, nullable=False, default=0.0)
    total_sales           = Column(Float, nullable=False, default=0.0)
    total_expenses        = Column(Float, nullable=False, default=0.0)
    total_purchases       = Column(Float, nullable=False, default=0.0)
    customer_payments     = Column(Float, nullable=False, default=0.0)
    supplier_payments     = Column(Float, nullable=False, default=0.0)
    bank_deposits         = Column(Float, nullable=False, default=0.0)
    bank_withdrawals      = Column(Float, nullable=False, default=0.0)
    net_cash_movement     = Column(Float, nullable=False, default=0.0)
    daily_profit_estimate = Column(Float, nullable=False, default=0.0)
    recon_status          = Column(String(50), nullable=True)
    recon_variance        = Column(Float, nullable=True, default=0.0)
    recon_id              = Column(Integer, ForeignKey("daily_cash_reconciliation.id"), nullable=True)
    je_count_snapshot     = Column(Integer, nullable=False, default=0)
    warnings_json         = Column(Text, nullable=True)
    had_warnings          = Column(Boolean, default=False, index=True)
    is_void               = Column(Boolean, default=False, index=True)
    voided_by_id          = Column(Integer, ForeignKey("users.id"), nullable=True)
    voided_at             = Column(DateTime, nullable=True)
    void_reason           = Column(Text, nullable=True)
    created_at            = Column(DateTime, nullable=False)
    company_id            = Column(Integer, nullable=True)  # Phase 14A

    closed_by      = relationship("User", foreign_keys=[closed_by_id])
    voided_by      = relationship("User", foreign_keys=[voided_by_id])
    reconciliation = relationship("DailyCashReconciliation", foreign_keys=[recon_id])


class Partner(Base):
    """A business partner (owner or profit-sharing partner)."""
    __tablename__ = "partners"

    id                  = Column(Integer, primary_key=True, index=True)
    name                = Column(String(200), nullable=False)
    profit_share_pct    = Column(Float,   nullable=False, default=0.0)
    capital_account_id  = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    current_account_id  = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    advance_account_id  = Column(Integer, ForeignKey("chart_of_accounts.id"), nullable=True)
    is_active           = Column(Boolean, default=True, index=True)
    created_at          = Column(DateTime, nullable=False)
    notes               = Column(Text, nullable=True)
    company_id          = Column(Integer, nullable=True)  # Phase 14A

    capital_account = relationship("ChartOfAccounts", foreign_keys=[capital_account_id])
    current_account = relationship("ChartOfAccounts", foreign_keys=[current_account_id])
    advance_account = relationship("ChartOfAccounts", foreign_keys=[advance_account_id])
    movements       = relationship("PartnerMovement", back_populates="partner")


class PartnerMovement(Base):
    """One financial movement for a partner."""
    __tablename__ = "partner_movements"

    id                  = Column(Integer, primary_key=True, index=True)
    partner_id          = Column(Integer, ForeignKey("partners.id"), nullable=False, index=True)
    movement_type       = Column(String(50), nullable=False, index=True)
    amount              = Column(Float, nullable=False)
    date                = Column(Date, nullable=False, index=True)
    journal_entry_id    = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=True)
    notes               = Column(Text, nullable=True)
    is_void             = Column(Boolean, default=False, index=True)
    voided_by_id        = Column(Integer, ForeignKey("users.id"), nullable=True)
    voided_at           = Column(DateTime, nullable=True)
    void_reason         = Column(Text, nullable=True)
    created_by_id       = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at          = Column(DateTime, nullable=False)
    company_id          = Column(Integer, nullable=True)  # Phase 14A

    partner          = relationship("Partner", back_populates="movements", foreign_keys=[partner_id])
    journal_entry    = relationship("JournalEntry", foreign_keys=[journal_entry_id])
    bank_transaction = relationship("BankTransaction", foreign_keys=[bank_transaction_id])


class PartnerProfitAllocation(Base):
    """One profit allocation for a specific fiscal period."""
    __tablename__ = "partner_profit_allocations"

    id                  = Column(Integer, primary_key=True, index=True)
    fiscal_period_id    = Column(Integer, ForeignKey("fiscal_periods.id"), nullable=False, index=True)
    allocated_at        = Column(DateTime, nullable=False)
    allocated_by_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    total_net_income    = Column(Float, nullable=False)
    journal_entry_id    = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    notes               = Column(Text, nullable=True)
    is_void             = Column(Boolean, default=False, index=True)
    voided_by_id        = Column(Integer, ForeignKey("users.id"), nullable=True)
    voided_at           = Column(DateTime, nullable=True)
    void_reason         = Column(Text, nullable=True)
    created_at          = Column(DateTime, nullable=False)
    company_id          = Column(Integer, nullable=True)  # Phase 14A

    fiscal_period  = relationship("FiscalPeriod", foreign_keys=[fiscal_period_id])
    journal_entry  = relationship("JournalEntry", foreign_keys=[journal_entry_id])
    lines          = relationship("PartnerProfitAllocationLine", back_populates="allocation",
                                  cascade="all, delete-orphan")


class PartnerProfitAllocationLine(Base):
    """One line per partner in a profit allocation."""
    __tablename__ = "partner_profit_allocation_lines"

    id              = Column(Integer, primary_key=True, index=True)
    allocation_id   = Column(Integer, ForeignKey("partner_profit_allocations.id"),
                             nullable=False, index=True)
    partner_id      = Column(Integer, ForeignKey("partners.id"), nullable=False, index=True)
    share_pct       = Column(Float, nullable=False)
    amount          = Column(Float, nullable=False)
    company_id      = Column(Integer, nullable=True)  # Phase 14A

    allocation = relationship("PartnerProfitAllocation", back_populates="lines")
    partner    = relationship("Partner", foreign_keys=[partner_id])


class YearEndClose(Base):
    """Year-level administrative lock.

    Serves as a lock + validation + audit record only — no JournalEntry is posted.
    The partial unique index (uq_yec_year) ensures only one active close per
    (company, fiscal_year) pair after Phase 14A migration.
    """
    __tablename__ = "year_end_closes"

    id                          = Column(Integer, primary_key=True, index=True)
    fiscal_year                 = Column(String(10), nullable=False)
    start_date                  = Column(Date, nullable=False)
    end_date                    = Column(Date, nullable=False)
    status                      = Column(String(20), nullable=False)
    closed_by_id                = Column(Integer, ForeignKey("users.id"), nullable=True)
    closed_at                   = Column(DateTime, nullable=False)
    notes                       = Column(Text, nullable=True)
    period_count                = Column(Integer, nullable=False)
    allocation_count            = Column(Integer, nullable=False)
    net_income_snapshot         = Column(Float, nullable=False)
    re_balance_at_close         = Column(Float, nullable=False)
    warnings_acknowledged_json  = Column(Text, nullable=True)
    is_void                     = Column(Boolean, default=False, index=True)
    voided_by_id                = Column(Integer, ForeignKey("users.id"), nullable=True)
    voided_at                   = Column(DateTime, nullable=True)
    void_reason                 = Column(Text, nullable=True)
    created_at                  = Column(DateTime, nullable=False)
    company_id                  = Column(Integer, nullable=True)  # Phase 14A

    closed_by  = relationship("User", foreign_keys=[closed_by_id])
    voided_by  = relationship("User", foreign_keys=[voided_by_id])


class Attachment(Base):
    """File attachment for any ERP entity."""
    __tablename__ = "attachments"

    id                = Column(Integer,      primary_key=True, index=True)
    entity_type       = Column(String(50),   nullable=False, index=True)
    entity_id         = Column(Integer,      nullable=False, index=True)
    original_filename = Column(String(500),  nullable=False)
    stored_filename   = Column(String(500),  nullable=False)
    file_path         = Column(String(1000), nullable=False)
    mime_type         = Column(String(100),  nullable=True)
    file_size_bytes   = Column(Integer,      nullable=True)
    sha256_hash       = Column(String(64),   nullable=True)
    document_category = Column(String(50),   nullable=True)
    is_primary        = Column(Boolean,      nullable=False, default=False)
    uploaded_by_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploaded_at       = Column(DateTime, nullable=False)
    notes             = Column(Text,         nullable=True)
    is_deleted        = Column(Boolean,      nullable=False, default=False, index=True)
    deleted_by_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    deleted_at        = Column(DateTime,     nullable=True)
    company_id        = Column(Integer,      nullable=True)  # Phase 14A

    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
    deleted_by  = relationship("User", foreign_keys=[deleted_by_id])


class BankStatementImport(Base):
    """Phase 18-MVP-2 — bank statement file import (staging only; no GL posting)."""
    __tablename__ = "bank_statement_imports"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False, index=True)

    file_name = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(1000), nullable=False)

    status = Column(String(50), nullable=False, default="staging")
    import_date = Column(Date, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    starting_balance = Column(Float, nullable=True)
    ending_balance = Column(Float, nullable=True)

    row_count = Column(Integer, nullable=False, default=0)
    valid_count = Column(Integer, nullable=False, default=0)
    flagged_count = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)

    currency = Column(String(10), nullable=False)
    column_mapping_json = Column(Text, nullable=True)
    sheet_name = Column(String(200), nullable=True)
    header_row = Column(Integer, nullable=True, default=1)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)

    rows = relationship("BankStatementRow", back_populates="import_record")


class BankStatementRow(Base):
    """One parsed line from a bank statement import."""
    __tablename__ = "bank_statement_rows"

    id = Column(Integer, primary_key=True, index=True)
    bank_statement_import_id = Column(
        Integer, ForeignKey("bank_statement_imports.id"), nullable=False, index=True
    )

    status = Column(String(50), nullable=False, default="staging")
    import_row_index = Column(Integer, nullable=False)

    date = Column(Date, nullable=True)
    description = Column(String(500), nullable=False, default="")
    debit_amount = Column(Float, nullable=True)
    credit_amount = Column(Float, nullable=True)
    amount = Column(Float, nullable=False, default=0.0)
    balance_after = Column(Float, nullable=True)
    currency = Column(String(10), nullable=False)
    original_amount = Column(Float, nullable=False, default=0.0)

    bank_reference = Column(String(100), nullable=True, index=True)
    raw_line_text = Column(Text, nullable=True)
    normalized_description = Column(String(500), nullable=True, index=True)

    parsed_successfully = Column(Boolean, nullable=False, default=True)
    parse_error = Column(Text, nullable=True)
    duplicate_reason = Column(String(50), nullable=True)
    duplicate_of_row_id = Column(Integer, ForeignKey("bank_statement_rows.id"), nullable=True)

    # Phase 18-MVP-3 — match & post provenance
    match_type = Column(String(50), nullable=True)
    posted_journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    payable_id = Column(Integer, nullable=True)
    expense_record_id = Column(Integer, nullable=True)
    partner_movement_id = Column(Integer, ForeignKey("partner_movements.id"), nullable=True)
    worker_movement_id = Column(Integer, ForeignKey("worker_movements.id"), nullable=True)
    clearing_sale_ids_json = Column(Text, nullable=True)
    settlement_row_id = Column(Integer, ForeignKey("settlement_statement_rows.id"), nullable=True)
    credit_card_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=True)
    posted_at = Column(DateTime, nullable=True)
    posted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, nullable=False)

    import_record = relationship("BankStatementImport", back_populates="rows")


class SettlementStatementImport(Base):
    """Phase 18-MVP-4 — merchant/processor settlement file (gross/fee/net per batch)."""
    __tablename__ = "settlement_statement_imports"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, nullable=False, index=True)

    file_name = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(1000), nullable=False)

    status = Column(String(50), nullable=False, default="staging")
    import_date = Column(Date, nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    row_count = Column(Integer, nullable=False, default=0)
    valid_count = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)

    currency = Column(String(10), nullable=False)
    column_mapping_json = Column(Text, nullable=True)
    sheet_name = Column(String(200), nullable=True)
    header_row = Column(Integer, nullable=True, default=1)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    notes = Column(Text, nullable=True)

    rows = relationship("SettlementStatementRow", back_populates="import_record")


class SettlementStatementRow(Base):
    """One parsed batch line from a merchant settlement statement."""
    __tablename__ = "settlement_statement_rows"

    id = Column(Integer, primary_key=True, index=True)
    settlement_statement_import_id = Column(
        Integer, ForeignKey("settlement_statement_imports.id"), nullable=False, index=True
    )

    status = Column(String(50), nullable=False, default="staging")
    import_row_index = Column(Integer, nullable=False)

    date = Column(Date, nullable=True)
    description = Column(String(500), nullable=False, default="")
    batch_reference = Column(String(100), nullable=True, index=True)
    gross_amount = Column(Float, nullable=False, default=0.0)
    fee_amount = Column(Float, nullable=False, default=0.0)
    net_amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), nullable=False)

    raw_line_text = Column(Text, nullable=True)
    parsed_successfully = Column(Boolean, nullable=False, default=True)
    parse_error = Column(Text, nullable=True)

    bank_statement_row_id = Column(Integer, ForeignKey("bank_statement_rows.id"), nullable=True)
    posted_journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    posted_at = Column(DateTime, nullable=True)
    posted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, nullable=False)

    import_record = relationship("SettlementStatementImport", back_populates="rows")


class Worker(Base):
    """Staff / employee master record (not a business partner)."""
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    phone = Column(String(100), nullable=True)
    role = Column(String(100), nullable=True)
    base_salary = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    company_id = Column(Integer, nullable=True)

    movements = relationship("WorkerMovement", back_populates="worker")


class WorkerMovement(Base):
    """Salary payment, advance, or advance repayment for a worker."""
    __tablename__ = "worker_movements"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=False, index=True)
    movement_type = Column(String(50), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False, index=True)
    pay_period = Column(String(100), nullable=True)
    gross_salary = Column(Float, default=0.0)
    deductions = Column(Float, default=0.0)
    advance_recovery = Column(Float, default=0.0)
    net_paid = Column(Float, default=0.0)
    journal_entry_id = Column(Integer, ForeignKey("journal_entries.id"), nullable=True)
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id"), nullable=True)
    notes = Column(Text, nullable=True)
    is_void = Column(Boolean, default=False, index=True)
    voided_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    voided_at = Column(DateTime, nullable=True)
    void_reason = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, nullable=False)
    company_id = Column(Integer, nullable=True)

    worker = relationship("Worker", back_populates="movements", foreign_keys=[worker_id])
    journal_entry = relationship("JournalEntry", foreign_keys=[journal_entry_id])
    bank_transaction = relationship("BankTransaction", foreign_keys=[bank_transaction_id])
