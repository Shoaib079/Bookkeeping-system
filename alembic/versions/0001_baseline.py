"""P3.4-D — Alembic baseline revision 0001.

Create-only baseline representing ``Base.metadata`` plus all ``migrate_schema()``
indexes/constraints not declared on ORM models. PostgreSQL-safe partial predicates
use ``is_void IS FALSE`` (not ``is_void = 0``).

**Not applied to production.** ``migrate_schema()`` remains authoritative until cutover.
See ``docs/P3_4_D_BASELINE_MIGRATION.md``.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


# migrate_schema()-only indexes (final company_id partial uniques included).
_SUPPLEMENTAL_INDEX_SQL: tuple[str, ...] = (
    'CREATE INDEX ix_je_entry_date ON journal_entries (entry_date)',
    'CREATE INDEX ix_je_reference_type ON journal_entries (reference_type)',
    'CREATE INDEX ix_jel_account_id ON journal_entry_lines (account_id)',
    'CREATE INDEX ix_jel_je_id ON journal_entry_lines (journal_entry_id)',
    'CREATE INDEX ix_sale_date ON sales (date)',
    'CREATE INDEX ix_sale_is_void ON sales (is_void)',
    'CREATE INDEX ix_sale_status ON sales (status)',
    'CREATE INDEX ix_sale_sale_type ON sales (sale_type)',
    'CREATE INDEX ix_exp_date ON expense_records (date)',
    'CREATE INDEX ix_exp_is_void ON expense_records (is_void)',
    'CREATE INDEX ix_pur_date ON purchases (date)',
    'CREATE INDEX ix_pur_is_void ON purchases (is_void)',
    'CREATE INDEX ix_pay_paid ON payables (paid)',
    'CREATE INDEX ix_pay_due_date ON payables (due_date)',
    'CREATE INDEX ix_pay_is_void ON payables (is_void)',
    'CREATE INDEX ix_btxn_date ON bank_transactions (date)',
    'CREATE INDEX ix_btxn_is_void ON bank_transactions (is_void)',
    'CREATE INDEX ix_ret_template_id ON recurring_expense_drafts (template_id)',
    'CREATE INDEX ix_ret_status ON recurring_expense_drafts (status)',
    'CREATE INDEX ix_ret_due_date ON recurring_expense_drafts (due_date)',
    'CREATE INDEX ix_retmpl_next_due ON recurring_expense_templates (next_due_date)',
    'CREATE INDEX ix_retmpl_is_active ON recurring_expense_templates (is_active)',
    'CREATE INDEX ix_eod_date ON end_of_day_closes (date)',
    'CREATE INDEX ix_eod_status ON end_of_day_closes (status)',
    'CREATE INDEX ix_eod_is_void ON end_of_day_closes (is_void)',
    'CREATE INDEX ix_eod_had_warnings ON end_of_day_closes (had_warnings)',
    'CREATE INDEX ix_att_entity ON attachments (entity_type, entity_id, is_deleted)',
    'CREATE INDEX ix_partner_is_active ON partners (is_active)',
    'CREATE INDEX ix_pmov_partner_id ON partner_movements (partner_id)',
    'CREATE INDEX ix_pmov_date ON partner_movements (date)',
    'CREATE INDEX ix_pmov_movement_type ON partner_movements (movement_type)',
    'CREATE INDEX ix_pmov_is_void ON partner_movements (is_void)',
    'CREATE INDEX ix_worker_is_active ON workers (is_active)',
    'CREATE INDEX ix_wmov_worker_id ON worker_movements (worker_id)',
    'CREATE INDEX ix_wmov_date ON worker_movements (date)',
    'CREATE INDEX ix_wmov_movement_type ON worker_movements (movement_type)',
    'CREATE INDEX ix_wmov_is_void ON worker_movements (is_void)',
    'CREATE INDEX ix_palloc_period_id ON partner_profit_allocations (fiscal_period_id)',
    'CREATE INDEX ix_palloc_is_void ON partner_profit_allocations (is_void)',
    'CREATE INDEX ix_palline_allocation_id ON partner_profit_allocation_lines (allocation_id)',
    'CREATE INDEX ix_palline_partner_id ON partner_profit_allocation_lines (partner_id)',
    'CREATE INDEX ix_yec_status ON year_end_closes (status)',
    'CREATE INDEX ix_coa_company_id ON chart_of_accounts (company_id)',
    'CREATE INDEX ix_je_company_id ON journal_entries (company_id)',
    'CREATE INDEX ix_jel_company_id ON journal_entry_lines (company_id)',
    'CREATE INDEX ix_sale_company_id ON sales (company_id)',
    'CREATE INDEX ix_exp_company_id ON expense_records (company_id)',
    'CREATE INDEX ix_pur_company_id ON purchases (company_id)',
    'CREATE INDEX ix_pay_company_id ON payables (company_id)',
    'CREATE INDEX ix_cust_company_id ON customers (company_id)',
    'CREATE INDEX ix_vend_company_id ON vendors (company_id)',
    'CREATE INDEX ix_ba_company_id ON bank_accounts (company_id)',
    'CREATE INDEX ix_btxn_company_id ON bank_transactions (company_id)',
    'CREATE INDEX ix_fp_company_id ON fiscal_periods (company_id)',
    'CREATE INDEX ix_yec_company_id ON year_end_closes (company_id)',
    'CREATE INDEX ix_partner_company_id ON partners (company_id)',
    'CREATE INDEX ix_pmov_company_id ON partner_movements (company_id)',
    'CREATE INDEX ix_worker_company_id ON workers (company_id)',
    'CREATE INDEX ix_wmov_company_id ON worker_movements (company_id)',
    'CREATE INDEX ix_palloc_company_id ON partner_profit_allocations (company_id)',
    'CREATE INDEX ix_palline_company_id ON partner_profit_allocation_lines(company_id)',
    'CREATE INDEX ix_att_company_id ON attachments (company_id)',
    'CREATE INDEX ix_budget_company_id ON budgets (company_id)',
    'CREATE INDEX ix_dcr_company_id ON daily_cash_reconciliation (company_id)',
    'CREATE INDEX ix_eod_company_id ON end_of_day_closes (company_id)',
    'CREATE INDEX ix_esv_business_date ON external_sales_verifications (business_date)',
    'CREATE INDEX ix_esv_company_id ON external_sales_verifications (company_id)',
    'CREATE INDEX ix_esv_is_void ON external_sales_verifications (is_void)',
    'CREATE INDEX ix_esv_status ON external_sales_verifications (status)',
    "CREATE UNIQUE INDEX uq_esv_active ON external_sales_verifications (company_id, business_date, COALESCE(branch_location, '')) WHERE is_void IS FALSE",
    'CREATE INDEX ix_ingredient_company_id ON ingredients (company_id)',
    'CREATE INDEX ix_ingredient_is_active ON ingredients (is_active)',
    'CREATE INDEX ix_recipe_company_id ON recipes (company_id)',
    'CREATE INDEX ix_recipe_is_active ON recipes (is_active)',
    'CREATE INDEX ix_rline_recipe_id ON recipe_lines (recipe_id)',
    'CREATE INDEX ix_rline_ingredient_id ON recipe_lines (ingredient_id)',
    'CREATE INDEX ix_rline_sub_recipe_id ON recipe_lines (sub_recipe_id)',
    'CREATE INDEX ix_menuitem_company_id ON menu_items (company_id)',
    'CREATE INDEX ix_menuitem_is_active ON menu_items (is_active)',
    'CREATE INDEX ix_menuitem_recipe_id ON menu_items (recipe_id)',
    'CREATE INDEX ix_mph_company_id ON menu_price_history (company_id)',
    'CREATE INDEX ix_mph_menu_item_id ON menu_price_history (menu_item_id)',
    'CREATE INDEX ix_mph_effective_at ON menu_price_history (effective_at)',
    'CREATE INDEX ix_upo_company_id ON user_permission_overrides (company_id)',
    'CREATE INDEX ix_upo_user_id ON user_permission_overrides (user_id)',
    'CREATE INDEX ix_upo_permission_key ON user_permission_overrides (permission_key)',
    'CREATE INDEX ix_expdraft_company_id ON expense_drafts (company_id)',
    'CREATE INDEX ix_expdraft_created_by ON expense_drafts (created_by_id)',
    'CREATE INDEX ix_expdraft_status ON expense_drafts (status)',
    'CREATE INDEX ix_expdraft_expense_ref ON expense_drafts (expense_record_id)',
    'CREATE INDEX ix_draftatt_company_id ON draft_attachments (company_id)',
    'CREATE INDEX ix_draftatt_draft ON draft_attachments (draft_type, draft_id)',
    'CREATE INDEX ix_rcptsugg_company_id ON receipt_draft_suggestions (company_id)',
    'CREATE INDEX ix_rcptsugg_draft_id ON receipt_draft_suggestions (draft_id)',
    'CREATE INDEX ix_rcptsugg_attachment_sha ON receipt_draft_suggestions (attachment_sha256)',
    'CREATE INDEX ix_txcat_company_id ON transaction_categories (company_id)',
    'CREATE INDEX ix_txsub_company_id ON transaction_subcategories (company_id)',
    'CREATE INDEX ix_retmpl_company_id ON recurring_expense_templates (company_id)',
    'CREATE INDEX ix_red_company_id ON recurring_expense_drafts (company_id)',
    'CREATE INDEX ix_invtx_company_id ON inventory_transactions (company_id)',
    'CREATE INDEX ix_cl_company_id ON customer_ledger (company_id)',
    'CREATE INDEX ix_prod_company_id ON products (company_id)',
    'CREATE INDEX ix_auditlog_company_id ON audit_log (company_id)',
    'CREATE UNIQUE INDEX uq_coa_code_company ON chart_of_accounts (company_id, account_code)',
    'CREATE UNIQUE INDEX uq_products_sku_company ON products (company_id, sku) WHERE sku IS NOT NULL',
    'CREATE UNIQUE INDEX uq_eod_date_active ON end_of_day_closes (company_id, date) WHERE is_void IS FALSE',
    'CREATE UNIQUE INDEX uq_palloc_period ON partner_profit_allocations (company_id, fiscal_period_id) WHERE is_void IS FALSE',
    'CREATE UNIQUE INDEX uq_yec_year ON year_end_closes (company_id, fiscal_year) WHERE is_void IS FALSE',
)


def _create_orm_schema() -> None:
    """All tables/columns/FKs from Base.metadata."""
    import models  # noqa: F401 — register ORM tables

    from db import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind)


def _create_supplemental_indexes() -> None:
    """Indexes/constraints migrate_schema adds beyond ORM metadata."""
    bind = op.get_bind()
    for ddl in _SUPPLEMENTAL_INDEX_SQL:
        bind.execute(text(ddl))


def upgrade() -> None:
    """Create full authoritative schema on an empty database."""
    _create_orm_schema()
    _create_supplemental_indexes()


def downgrade() -> None:
    """Drop all ORM tables.

    **UNSAFE for real accounting data** — destroys every table and row created by
    this revision (the entire ERP schema). Intended for ephemeral/test databases
    only. Never run against production ``erp_data.db``.
    """
    import models  # noqa: F401

    from db import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind)
