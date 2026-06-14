# P3.4 — Alembic Baseline Migration Review (audit report)

**Mode:** Audit + review only. **No migration accepted, none applied.** No `alembic upgrade`, no model changes, no runtime DB change, no `Float → Decimal`, no destructive ops, `migrate_schema()` authority preserved.
**Method note:** Alembic is not scaffolded and cannot run in this environment, and scaffolding/acceptance is out of scope for this review. This report is an **inspection-based review of the baseline `0001` candidate**, derived by enumerating `Base.metadata` (`models.py`) and cross-referencing the runtime DDL emitted by `migrate_schema()` (`app.py`). It states exactly what a `--autogenerate` baseline would and would **not** contain, so the candidate can be corrected **before** generation/acceptance.

## Verdict (up front)

**A blind `--autogenerate` baseline would be INCOMPLETE and must NOT be accepted.** Autogenerate reads only `Base.metadata`, but the **real source of truth for indexes/constraints is `migrate_schema()`'s raw DDL**, which declares ~38 indexes/constraints **not present in the models**. A baseline missing them would (a) drop **accounting-integrity uniques** (one active year-end-close per year, one active allocation per period, unique account code per company) and (b) drop **~30 performance-critical `company_id` indexes**. The reviewed `0001` must be **hand-reconciled** to include all `migrate_schema` indexes/constraints, with partial-index predicates made PG-portable.

## 1. Baseline candidate — operation inventory

| Op class | Captured by autogenerate(`Base.metadata`)? | Notes |
|----------|--------------------------------------------|-------|
| **Tables** (`create_table`) | ✅ All | Every model has `__tablename__`; legacy tables (`cash_sales`, `credit_sales`, `salaries`, `expenses`) are in models → emitted as CREATE (no DROP) |
| **Columns** | ✅ Superset | `Base.metadata` is the column superset; `migrate_schema` `ADD COLUMN` only retrofits old DBs — no column drift |
| **Primary keys** | ✅ | `id` Integer PK on every table |
| **Foreign keys** | ✅ | All `ForeignKey(...)` are declared in models (`companies.id`, `users.id`, `vendors.id`, `customers.id`, `journal_entries.id`, `chart_of_accounts.id`, …) |
| **`__table_args__` UniqueConstraints** | ✅ | `uq_company_user`, `uq_company_setting`, `uq_ingredient/recipe/menu_item_company_name`, `user_permission_overrides` unique |
| **Single-col indexes from `index=True`** | ⚠️ Captured but **RENAMED** | Autogenerate names `ix_<table>_<column>` (e.g. `ix_journal_entries_entry_date`); `migrate_schema` uses short explicit names (`ix_je_entry_date`) → name divergence |
| **`company_id` indexes** | ❌ **MISSED (~30)** | Phase-14A business-table `company_id` columns are `Column(Integer, nullable=True)` **without `index=True`** (e.g. `ChartOfAccounts.company_id`, `models.py:137`); the `ix_*_company_id` indexes are created **only** in `migrate_schema` (`app.py:2013–2075`) |
| **Compound uniques** | ❌ **MISSED (2)** | `uq_coa_code_company` (chart_of_accounts company_id+account_code) and products company_id+sku — created during the `migrate_schema` rebuild (comments at `models.py:129–130`, `381`), **not** in `__table_args__` |
| **Partial unique indexes** | ❌ **MISSED (4)** | `uq_eod_date_active`, `uq_palloc_period`, `uq_yec_year`, `uq_esv_active` — raw DDL only (`app.py:1987/2007/2011/2041`) |
| **Composite plain indexes** | ❌ **MISSED (2)** | `ix_att_entity` (entity_type, entity_id, is_deleted) and `ix_draftatt_draft` (draft_type, draft_id) — raw DDL only |

## 2. Index / constraint audit (the drift detail)

### 2a. MISSED — accounting-integrity uniques (must be in `0001`)
- `uq_yec_year` — one non-void year-end-close per `fiscal_year` (`WHERE is_void = 0`).
- `uq_palloc_period` — one non-void profit allocation per `fiscal_period_id` (`WHERE is_void = 0`). **This is the very guard the P2.9 duplicate-allocation fix relies on** — dropping it would re-open that class of bug.
- `uq_eod_date_active` — one non-void EOD close per `date` (`WHERE is_void = 0`).
- `uq_esv_active` — one non-void external-sales verification per `(company_id, business_date, COALESCE(branch_location, ''))` (`WHERE is_void = 0`) — **functional** index (COALESCE) + partial.
- `uq_coa_code_company` — unique account code per company.
- products `(company_id, sku)` unique.

### 2b. MISSED — performance indexes (~30 `ix_*_company_id` + 2 composite)
All `ix_*_company_id` (chart_of_accounts, journal_entries, journal_entry_lines, sales, expense_records, purchases, payables, customers, vendors, bank_accounts, bank_transactions, fiscal_periods, year_end_closes, partners, partner_movements, workers, worker_movements, partner_profit_allocations, partner_profit_allocation_lines, attachments, budgets, daily_cash_reconciliation, end_of_day_closes, external_sales_verifications, ingredients/recipes/menu_items/menu_price_history, user_permission_overrides, expense_drafts, draft_attachments, transaction_categories/subcategories, recurring_*, inventory_transactions, customer_ledger, products, audit_log) plus `ix_att_entity`, `ix_draftatt_draft`. Every company-scoped query depends on these.

### 2c. RENAMED — single-column `index=True` indexes
Functionally captured, but autogenerate's `ix_<table>_<col>` names differ from `migrate_schema`'s short names. On an **existing** migrated DB this is invisible (stamp runs no DDL), but a fresh `create_all`/Alembic DB will carry different index names → future autogenerate diffs will show spurious "missing/extra" indexes. The reviewed `0001` should standardize on one naming convention (recommend SQLAlchemy's `ix_<table>_<col>` going forward and document the legacy names).

## 3. Destructive-operation verification

- **No `DROP` / no data-dropping `ALTER` expected** for a baseline: `0001` is **create-only** (`op.create_table` / `op.create_index`). All model tables (incl. legacy `cash_sales`/`credit_sales`/`salaries`/`expenses`) are in `Base.metadata`, so autogenerate emits CREATE for them, not DROP.
- **Caveat (must enforce at generation):** autogenerate compares `Base.metadata` to **whatever DB the env points at**. If run against a **populated/migrated DB**, it could emit spurious `DROP`/`ALTER` for the migrate_schema-only indexes (seen as "to remove") or for naming differences. **`0001` must be generated against an EMPTY database** (or hand-authored) to guarantee create-only output. This is a generation-procedure rule, not an accepted artifact.

## 4. PostgreSQL-compatibility findings for the candidate

- **Partial-index predicate `WHERE is_void = 0`** (4 indexes) is a **boolean = integer type error on PG**. The reviewed `0001` must emit `is_void IS FALSE` (Alembic: `op.create_index(..., postgresql_where=text("is_void IS FALSE"), sqlite_where=text("is_void = 0"))`, or a single `IS FALSE` predicate which SQLite also accepts).
- **`uq_esv_active` functional predicate `COALESCE(branch_location, '')`** — valid on PG and SQLite, but must be expressed as an index expression (parenthesized) in the Alembic op; review for dialect quoting.
- **Index naming** divergence (§2c) — decide convention now to avoid perpetual autogenerate churn.
- **`Float`** columns — **no `NUMERIC` conversion in the baseline** (excluded). `0001` reflects `Float` exactly as today.
- **`alembic_version` table** — created automatically by Alembic; on existing SQLite DBs use `alembic stamp 0001` (writes the version row, **no DDL**) per the P3.3 plan.

## 5. Schema-drift / runtime-added-column check

- **Columns:** no drift — `migrate_schema` `ADD COLUMN` only retrofits columns already defined in models; `Base.metadata` is the superset.
- **Indexes/constraints:** **significant drift** — the source of truth is `migrate_schema`, not the models (§2a/2b). This is the single most important correction for `0001`.
- **Legacy migration tables** (`cash_sales`, `credit_sales`, `salaries`, `expenses`) remain in models and must be in `0001` (data-bearing on old DBs; never dropped).

## 6. Recommended next steps (still P3.4 — no acceptance yet)

1. **Do not accept a blind autogenerate.** Treat autogenerate output as a draft of *tables/columns/FKs/declared-constraints only*.
2. **Hand-add the missing indexes/constraints** (§2a/2b) to `0001`, sourced verbatim from the `migrate_schema` DDL list, with `WHERE is_void = 0` → `IS FALSE`.
3. **Generate against an empty DB** to guarantee create-only (no DROP/ALTER).
4. **Decide the index-naming convention** and document the legacy→new name map.
5. **Baseline-equivalence test (P3.4-C):** assert a DB built from `0001` has the *same* tables/indexes/uniques as a fully `migrate_schema`-evolved SQLite DB (catch any remaining drift) — this is the acceptance gate.
6. Only after (1)–(5) green: stamp existing SQLite DBs at `0001` (non-destructive), per P3.3.

---

*Audit report only — no migration generated/accepted/applied, `migrate_schema()` still authoritative, models/`Float` unchanged. Headline: the baseline's true content lives in `migrate_schema()`'s raw DDL, not `Base.metadata`; a blind autogenerate would drop ~38 indexes/constraints including accounting-integrity uniques (notably `uq_palloc_period`, which the P2.9 fix depends on). `0001` must be hand-reconciled, generated against an empty DB (create-only), and validated for equivalence against a migrated SQLite schema before any acceptance or stamping.*
