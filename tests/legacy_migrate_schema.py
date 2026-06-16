"""P3.9-C — archived migrate_schema() implementation (test-only).

Frozen copy of the pre-P3.9-C SQLite DDL evolution body for schema equivalence
harnesses and historical characterization. **Not used in production startup.**
"""

from __future__ import annotations

import datetime
import os

from sqlalchemy import text

from models import ChartOfAccounts, MigrationFlag


def legacy_migrate_schema(session) -> None:
    """Pre-P3.9-C migrate_schema body — test harness only."""
    # Rename invoice_number → purchase_number on purchases (idempotent: fails silently if already done).
    try:
        session.execute(text("ALTER TABLE purchases RENAME COLUMN invoice_number TO purchase_number"))
        session.commit()
    except Exception:
        session.rollback()

    migrations = [
        # Soft-delete columns (Phase 1)
        ("vendors",                "is_active BOOLEAN DEFAULT 1 NOT NULL"),
        ("customers",              "is_active BOOLEAN DEFAULT 1 NOT NULL"),
        ("products",               "is_active BOOLEAN DEFAULT 1 NOT NULL"),
        ("bank_accounts",          "is_active BOOLEAN DEFAULT 1 NOT NULL"),
        # Void/reversal columns for accounting records (Phase 2)
        ("sales",                  "is_void BOOLEAN DEFAULT 0 NOT NULL"),
        ("sales",                  "voided_at DATE"),
        ("sales",                  "void_reason TEXT"),
        ("expense_records",        "is_void BOOLEAN DEFAULT 0 NOT NULL"),
        ("expense_records",        "voided_at DATE"),
        ("expense_records",        "void_reason TEXT"),
        ("purchases",              "purchase_number TEXT"),
        ("purchases",              "purchase_type TEXT DEFAULT 'Credit'"),
        ("purchases",              "gl_debit TEXT DEFAULT 'Inventory'"),
        ("purchases",              "is_void BOOLEAN DEFAULT 0 NOT NULL"),
        ("purchases",              "voided_at DATE"),
        ("purchases",              "void_reason TEXT"),
        ("payables",               "is_void BOOLEAN DEFAULT 0 NOT NULL"),
        ("payables",               "voided_at DATE"),
        ("payables",               "void_reason TEXT"),
        ("payables",               "expense_category TEXT DEFAULT 'Rent'"),
        ("payables",               "payment_method TEXT"),
        ("payables",               "purchase_id INTEGER"),
        ("bank_transactions",      "is_void BOOLEAN DEFAULT 0 NOT NULL"),
        ("bank_transactions",      "voided_at DATE"),
        ("bank_transactions",      "void_reason TEXT"),
        ("products",               "category TEXT"),
        ("products",               "cost_price REAL DEFAULT 0"),
        ("products",               "min_stock REAL DEFAULT 0"),
        ("inventory_transactions", "is_void BOOLEAN DEFAULT 0 NOT NULL"),
        ("inventory_transactions", "voided_at DATE"),
        ("inventory_transactions", "void_reason TEXT"),
        # Vendor extended fields
        ("vendors",         "notes TEXT"),
        # Product extended fields
        ("products",        "subcategory TEXT"),
        ("products",        "unit_of_measure TEXT"),
        # Category/subcategory pointers on transactional tables
        ("sales",           "tx_category_id INTEGER"),
        ("sales",           "tx_subcategory_id INTEGER"),
        ("expense_records", "tx_category_id INTEGER"),
        ("expense_records", "tx_subcategory_id INTEGER"),
        ("purchases",       "tx_category_id INTEGER"),
        ("purchases",       "tx_subcategory_id INTEGER"),
        # Block 6: audit trail — who created each transaction
        ("sales",               "created_by_id INTEGER"),
        ("expense_records",     "created_by_id INTEGER"),
        ("purchases",           "created_by_id INTEGER"),
        ("audit_log",           "performed_by TEXT"),
        # Step 1.1: currency field on chart of accounts
        ("chart_of_accounts",   "currency TEXT"),
        # Step 1.3: FX fields on transactional tables
        ("sales",               "currency TEXT"),
        ("sales",               "fx_rate REAL DEFAULT 1.0"),
        ("sales",               "native_amount REAL"),
        ("expense_records",     "currency TEXT"),
        ("expense_records",     "fx_rate REAL DEFAULT 1.0"),
        ("expense_records",     "native_amount REAL"),
        ("purchases",           "currency TEXT"),
        ("purchases",           "fx_rate REAL DEFAULT 1.0"),
        ("purchases",           "native_amount REAL"),
        # Step 6 — partial payable payments
        ("payables",            "paid_amount REAL DEFAULT 0"),
        ("payables",            "balance REAL"),
        # Step 10 — currency on journal lines
        ("journal_entry_lines", "currency TEXT"),
        ("journal_entry_lines", "amount_native REAL"),
        # Step 11 — currency on bank accounts
        ("bank_accounts",       "currency TEXT DEFAULT 'TRY'"),
        # Step 12 — customer FK on sales
        ("sales",               "customer_id INTEGER"),
        # Phase 7.5 — user profile fields
        ("users",               "email TEXT"),
        ("users",               "phone TEXT"),
        ("users",               "last_login TIMESTAMP"),
        # Phase 9B — recurring expense postpone
        ("recurring_expense_drafts", "postponed_to DATE"),
        # Recurring template fields the create/edit code uses but the table lacked
        ("recurring_expense_templates", "is_active BOOLEAN DEFAULT 1"),
        ("recurring_expense_templates", "vendor_id INTEGER"),
        ("recurring_expense_templates", "created_by_id INTEGER"),
        ("recurring_expense_templates", "created_at TIMESTAMP"),
        # Phase 14A — company_id on all business tables
        # chart_of_accounts and products are handled by the rebuild above.
        ("journal_entries",                    "company_id INTEGER"),
        ("journal_entry_lines",                "company_id INTEGER"),
        ("sales",                              "company_id INTEGER"),
        ("expense_records",                    "company_id INTEGER"),
        ("purchases",                          "company_id INTEGER"),
        ("payables",                           "company_id INTEGER"),
        ("customers",                          "company_id INTEGER"),
        ("vendors",                            "company_id INTEGER"),
        ("bank_accounts",                      "company_id INTEGER"),
        ("bank_transactions",                  "company_id INTEGER"),
        ("fiscal_periods",                     "company_id INTEGER"),
        ("year_end_closes",                    "company_id INTEGER"),
        ("partners",                           "company_id INTEGER"),
        ("partner_movements",                  "company_id INTEGER"),
        ("partner_profit_allocations",         "company_id INTEGER"),
        ("partner_profit_allocation_lines",    "company_id INTEGER"),
        ("attachments",                        "company_id INTEGER"),
        ("budgets",                            "company_id INTEGER"),
        ("daily_cash_reconciliation",          "company_id INTEGER"),
        ("end_of_day_closes",                  "company_id INTEGER"),
        ("transaction_categories",             "company_id INTEGER"),
        ("transaction_subcategories",          "company_id INTEGER"),
        ("recurring_expense_templates",        "company_id INTEGER"),
        ("recurring_expense_drafts",           "company_id INTEGER"),
        ("inventory_transactions",             "company_id INTEGER"),
        ("customer_ledger",                    "company_id INTEGER"),
        ("audit_log",                          "company_id INTEGER"),
        ("cash_sales",                         "company_id INTEGER"),
        ("credit_sales",                       "company_id INTEGER"),
        ("salaries",                           "company_id INTEGER"),
        ("expenses",                           "company_id INTEGER"),
        # Phase 14D-A — Company extended identity fields (nullable, existing rows unaffected)
        ("companies",    "full_name TEXT"),
        ("companies",    "email TEXT"),
        ("companies",    "phone TEXT"),
        ("companies",    "created_by_user_id INTEGER"),
        # Phase 14D-A — CompanyUser audit field (nullable, existing memberships unaffected)
        ("company_users", "invited_by_id INTEGER"),
        # Phase 18-MVP-1 — bank reconciliation foundation
        ("bank_transactions", "is_reconciled BOOLEAN DEFAULT 0 NOT NULL"),
        ("bank_transactions", "statement_ref TEXT"),
        ("bank_transactions", "charge_subtype TEXT"),
        # Phase 18-MVP-3 — bank statement row match & post
        ("bank_statement_rows", "match_type TEXT"),
        ("bank_statement_rows", "posted_journal_entry_id INTEGER"),
        ("bank_statement_rows", "bank_transaction_id INTEGER"),
        ("bank_statement_rows", "vendor_id INTEGER"),
        ("bank_statement_rows", "payable_id INTEGER"),
        ("bank_statement_rows", "expense_record_id INTEGER"),
        ("bank_statement_rows", "clearing_sale_ids_json TEXT"),
        ("bank_statement_rows", "posted_at TIMESTAMP"),
        ("bank_statement_rows", "posted_by_user_id INTEGER"),
        # Phase 18-MVP-4 — settlement link + bank charges on clearing match
        ("bank_statement_rows", "settlement_row_id INTEGER"),
        # Phase 18-MVP-5 — company credit card
        ("bank_accounts",          "kind TEXT DEFAULT 'bank'"),
        ("bank_statement_rows",    "credit_card_account_id INTEGER"),
        ("bank_statement_rows",    "partner_movement_id INTEGER"),
        ("bank_statement_rows",    "worker_movement_id INTEGER"),
        # AD-011 — company CC sub-ledger linkage
        ("expense_records",        "credit_card_account_id INTEGER"),
        ("purchases",              "credit_card_account_id INTEGER"),
        ("payables",               "credit_card_account_id INTEGER"),
    ]
    _applied = 0
    _skipped = 0
    for table, col_def in migrations:
        try:
            session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_def}"))
            session.commit()
            _applied += 1
        except Exception:
            session.rollback()
            _skipped += 1
    # Uncomment to debug migration runs:
    # print(f"[migrate_schema] {_applied} applied, {_skipped} skipped (already exist)")

    # ── Performance indexes — idempotent on existing databases ─────────────────
    # CREATE INDEX IF NOT EXISTS is safe to run every startup.
    # SQLAlchemy's create_all() handles new databases; this covers existing ones.
    index_stmts = [
        "CREATE INDEX IF NOT EXISTS ix_je_entry_date       ON journal_entries     (entry_date)",
        "CREATE INDEX IF NOT EXISTS ix_je_reference_type   ON journal_entries     (reference_type)",
        "CREATE INDEX IF NOT EXISTS ix_jel_account_id      ON journal_entry_lines (account_id)",
        "CREATE INDEX IF NOT EXISTS ix_jel_je_id           ON journal_entry_lines (journal_entry_id)",
        "CREATE INDEX IF NOT EXISTS ix_sale_date           ON sales               (date)",
        "CREATE INDEX IF NOT EXISTS ix_sale_is_void        ON sales               (is_void)",
        "CREATE INDEX IF NOT EXISTS ix_sale_status         ON sales               (status)",
        "CREATE INDEX IF NOT EXISTS ix_sale_sale_type      ON sales               (sale_type)",
        "CREATE INDEX IF NOT EXISTS ix_exp_date            ON expense_records     (date)",
        "CREATE INDEX IF NOT EXISTS ix_exp_is_void         ON expense_records     (is_void)",
        "CREATE INDEX IF NOT EXISTS ix_pur_date            ON purchases           (date)",
        "CREATE INDEX IF NOT EXISTS ix_pur_is_void         ON purchases           (is_void)",
        "CREATE INDEX IF NOT EXISTS ix_pay_paid            ON payables            (paid)",
        "CREATE INDEX IF NOT EXISTS ix_pay_due_date        ON payables            (due_date)",
        "CREATE INDEX IF NOT EXISTS ix_pay_is_void         ON payables            (is_void)",
        "CREATE INDEX IF NOT EXISTS ix_btxn_date           ON bank_transactions              (date)",
        "CREATE INDEX IF NOT EXISTS ix_btxn_is_void        ON bank_transactions              (is_void)",
        "CREATE INDEX IF NOT EXISTS ix_ret_template_id     ON recurring_expense_drafts       (template_id)",
        "CREATE INDEX IF NOT EXISTS ix_ret_status          ON recurring_expense_drafts       (status)",
        "CREATE INDEX IF NOT EXISTS ix_ret_due_date        ON recurring_expense_drafts       (due_date)",
        "CREATE INDEX IF NOT EXISTS ix_retmpl_next_due     ON recurring_expense_templates    (next_due_date)",
        "CREATE INDEX IF NOT EXISTS ix_retmpl_is_active    ON recurring_expense_templates    (is_active)",
        # Phase 9D — End-of-Day Close
        "CREATE INDEX IF NOT EXISTS ix_eod_date            ON end_of_day_closes (date)",
        "CREATE INDEX IF NOT EXISTS ix_eod_status          ON end_of_day_closes (status)",
        "CREATE INDEX IF NOT EXISTS ix_eod_is_void         ON end_of_day_closes (is_void)",
        "CREATE INDEX IF NOT EXISTS ix_eod_had_warnings    ON end_of_day_closes (had_warnings)",
        # Partial unique index: only one non-voided close per calendar date
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_eod_date_active ON end_of_day_closes (date) WHERE is_void = 0",
        # Phase 11 — Attachments: composite covering index for the primary query pattern
        "CREATE INDEX IF NOT EXISTS ix_att_entity ON attachments (entity_type, entity_id, is_deleted)",
        # Phase 12 — Partners & Profit Allocation
        "CREATE INDEX IF NOT EXISTS ix_partner_is_active      ON partners (is_active)",
        "CREATE INDEX IF NOT EXISTS ix_pmov_partner_id        ON partner_movements (partner_id)",
        "CREATE INDEX IF NOT EXISTS ix_pmov_date              ON partner_movements (date)",
        "CREATE INDEX IF NOT EXISTS ix_pmov_movement_type     ON partner_movements (movement_type)",
        "CREATE INDEX IF NOT EXISTS ix_pmov_is_void           ON partner_movements (is_void)",
        # Workers — staff payroll ledger
        "CREATE INDEX IF NOT EXISTS ix_worker_is_active        ON workers (is_active)",
        "CREATE INDEX IF NOT EXISTS ix_wmov_worker_id         ON worker_movements (worker_id)",
        "CREATE INDEX IF NOT EXISTS ix_wmov_date              ON worker_movements (date)",
        "CREATE INDEX IF NOT EXISTS ix_wmov_movement_type     ON worker_movements (movement_type)",
        "CREATE INDEX IF NOT EXISTS ix_wmov_is_void           ON worker_movements (is_void)",
        "CREATE INDEX IF NOT EXISTS ix_palloc_period_id       ON partner_profit_allocations (fiscal_period_id)",
        "CREATE INDEX IF NOT EXISTS ix_palloc_is_void         ON partner_profit_allocations (is_void)",
        "CREATE INDEX IF NOT EXISTS ix_palline_allocation_id  ON partner_profit_allocation_lines (allocation_id)",
        "CREATE INDEX IF NOT EXISTS ix_palline_partner_id     ON partner_profit_allocation_lines (partner_id)",
        # One active allocation per period (voided allocations are excluded)
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_palloc_period   ON partner_profit_allocations (fiscal_period_id) WHERE is_void = 0",
        # Phase 13 — Year-End Close
        "CREATE INDEX IF NOT EXISTS ix_yec_status             ON year_end_closes (status)",
        # One active year-end close per fiscal year (voided closes are excluded)
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_yec_year        ON year_end_closes (fiscal_year) WHERE is_void = 0",
        # Phase 14A — company_id indexes on all business tables
        "CREATE INDEX IF NOT EXISTS ix_coa_company_id          ON chart_of_accounts              (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_je_company_id           ON journal_entries                (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_jel_company_id          ON journal_entry_lines            (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_sale_company_id         ON sales                          (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_exp_company_id          ON expense_records                (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_pur_company_id          ON purchases                      (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_pay_company_id          ON payables                       (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_cust_company_id         ON customers                      (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_vend_company_id         ON vendors                        (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_ba_company_id           ON bank_accounts                  (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_btxn_company_id         ON bank_transactions              (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_fp_company_id           ON fiscal_periods                 (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_yec_company_id          ON year_end_closes                (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_partner_company_id      ON partners                       (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_pmov_company_id         ON partner_movements              (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_worker_company_id        ON workers                        (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_wmov_company_id          ON worker_movements               (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_palloc_company_id       ON partner_profit_allocations     (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_palline_company_id      ON partner_profit_allocation_lines(company_id)",
        "CREATE INDEX IF NOT EXISTS ix_att_company_id          ON attachments                    (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_budget_company_id       ON budgets                        (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_dcr_company_id          ON daily_cash_reconciliation      (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_eod_company_id          ON end_of_day_closes              (company_id)",
        # DSC-P1 — External Sales Verification
        "CREATE INDEX IF NOT EXISTS ix_esv_business_date      ON external_sales_verifications   (business_date)",
        "CREATE INDEX IF NOT EXISTS ix_esv_company_id         ON external_sales_verifications   (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_esv_is_void            ON external_sales_verifications   (is_void)",
        "CREATE INDEX IF NOT EXISTS ix_esv_status             ON external_sales_verifications   (status)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_esv_active      ON external_sales_verifications (company_id, business_date, COALESCE(branch_location, '')) WHERE is_void = 0",
        # RC-P1 — Recipe Costing
        "CREATE INDEX IF NOT EXISTS ix_ingredient_company_id  ON ingredients                      (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_ingredient_is_active   ON ingredients                      (is_active)",
        "CREATE INDEX IF NOT EXISTS ix_recipe_company_id      ON recipes                          (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_recipe_is_active       ON recipes                          (is_active)",
        "CREATE INDEX IF NOT EXISTS ix_rline_recipe_id        ON recipe_lines                     (recipe_id)",
        "CREATE INDEX IF NOT EXISTS ix_rline_ingredient_id    ON recipe_lines                     (ingredient_id)",
        "CREATE INDEX IF NOT EXISTS ix_rline_sub_recipe_id    ON recipe_lines                     (sub_recipe_id)",
        # RC-P2A — Menu profitability
        "CREATE INDEX IF NOT EXISTS ix_menuitem_company_id   ON menu_items                       (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_menuitem_is_active    ON menu_items                       (is_active)",
        "CREATE INDEX IF NOT EXISTS ix_menuitem_recipe_id     ON menu_items                       (recipe_id)",
        "CREATE INDEX IF NOT EXISTS ix_mph_company_id         ON menu_price_history               (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_mph_menu_item_id       ON menu_price_history               (menu_item_id)",
        "CREATE INDEX IF NOT EXISTS ix_mph_effective_at       ON menu_price_history               (effective_at)",
        # UA-P1 — User permission overrides
        "CREATE INDEX IF NOT EXISTS ix_upo_company_id        ON user_permission_overrides        (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_upo_user_id           ON user_permission_overrides        (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_upo_permission_key    ON user_permission_overrides        (permission_key)",
        # SC-P1 — Staff Capture expense drafts
        "CREATE INDEX IF NOT EXISTS ix_expdraft_company_id     ON expense_drafts                   (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_expdraft_created_by     ON expense_drafts                   (created_by_id)",
        "CREATE INDEX IF NOT EXISTS ix_expdraft_status         ON expense_drafts                   (status)",
        "CREATE INDEX IF NOT EXISTS ix_expdraft_expense_ref    ON expense_drafts                   (expense_record_id)",
        "CREATE INDEX IF NOT EXISTS ix_draftatt_company_id     ON draft_attachments                (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_draftatt_draft          ON draft_attachments                (draft_type, draft_id)",
        "CREATE INDEX IF NOT EXISTS ix_rcptsugg_company_id     ON receipt_draft_suggestions        (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_rcptsugg_draft_id       ON receipt_draft_suggestions        (draft_id)",
        "CREATE INDEX IF NOT EXISTS ix_rcptsugg_attachment_sha ON receipt_draft_suggestions        (attachment_sha256)",
        "CREATE INDEX IF NOT EXISTS ix_rcptlearn_company_id     ON receipt_learning_map             (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_rcptlearn_signature       ON receipt_learning_map             (company_id, signature_type, signature_key)",
        "CREATE INDEX IF NOT EXISTS ix_txcat_company_id        ON transaction_categories         (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_txsub_company_id        ON transaction_subcategories      (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_retmpl_company_id       ON recurring_expense_templates    (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_red_company_id          ON recurring_expense_drafts       (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_invtx_company_id        ON inventory_transactions         (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_cl_company_id           ON customer_ledger                (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_prod_company_id         ON products                       (company_id)",
        "CREATE INDEX IF NOT EXISTS ix_auditlog_company_id     ON audit_log                      (company_id)",
        # Phase 14A — compound unique index for chart_of_accounts after rebuild
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_coa_code_company  ON chart_of_accounts (company_id, account_code)",
        # Phase 14A — compound unique index for products after rebuild
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_products_sku_company ON products (company_id, sku) WHERE sku IS NOT NULL",
    ]
    for stmt in index_stmts:
        try:
            session.execute(text(stmt))
            session.commit()
        except Exception:
            session.rollback()

    # Phase 14A — Update the three partial unique indexes to include company_id.
    # These indexes must be dropped and recreated because CREATE UNIQUE INDEX IF NOT EXISTS
    # will not update an existing index with a different column list.
    # Guard: run only once, after company_id columns are confirmed to exist.
    if not session.query(MigrationFlag).filter_by(name="update_partial_indexes_v1").first():
        _idx_updates = [
            (
                "uq_eod_date_active",
                "CREATE UNIQUE INDEX uq_eod_date_active ON end_of_day_closes (company_id, date) WHERE is_void = 0",
            ),
            (
                "uq_palloc_period",
                "CREATE UNIQUE INDEX uq_palloc_period ON partner_profit_allocations (company_id, fiscal_period_id) WHERE is_void = 0",
            ),
            (
                "uq_yec_year",
                "CREATE UNIQUE INDEX uq_yec_year ON year_end_closes (company_id, fiscal_year) WHERE is_void = 0",
            ),
        ]
        _all_ok = True
        for _idx_name, _create_sql in _idx_updates:
            try:
                session.execute(text(f"DROP INDEX IF EXISTS {_idx_name}"))
                session.execute(text(_create_sql))
                session.commit()
            except Exception:
                session.rollback()
                _all_ok = False
        if _all_ok:
            try:
                session.add(MigrationFlag(name="update_partial_indexes_v1", applied_at=datetime.date.today()))
                session.commit()
            except Exception:
                session.rollback()

    # Phase 11 — Create uploads folders on startup (idempotent)
    from paths import UPLOADS_DIR

    for _sub in ("expenses", "purchases", "statements", "settlements"):
        os.makedirs(UPLOADS_DIR / _sub, exist_ok=True)


    # Owner Drawings — added after the initial CoA seed, so must be backfilled here.
    if not session.query(ChartOfAccounts).filter_by(account_code="3200").first():
        session.add(ChartOfAccounts(
            account_code="3200",
            account_name="Owner Drawings",
            account_type="Equity",
        ))
        try:
            session.commit()
        except Exception:
            session.rollback()

    # Opening Balance Equity — added after the initial CoA seed, so must be backfilled here.
    if not session.query(ChartOfAccounts).filter_by(account_code="3900").first():
        session.add(ChartOfAccounts(
            account_code="3900",
            account_name="Opening Balance Equity",
            account_type="Equity",
        ))
        try:
            session.commit()
        except Exception:
            session.rollback()
