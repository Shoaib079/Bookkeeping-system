# P3.4-B — Alembic Baseline (`0001`) Authoring Plan

**Mode:** Documentation + lightweight contract test only. **The `0001` migration is NOT authored here.** No `alembic revision`, no `alembic upgrade`, no revision files created, no DB stamped, no model changes, no runtime DB change, `migrate_schema()` not removed, no `Float → Decimal`.
**Inputs:** `docs/P3_3_ALEMBIC_BASELINE_PLAN.md`, `docs/P3_4_ALEMBIC_BASELINE_REVIEW.md`, `migrate_schema()` raw DDL (`app.py`), `Base.metadata` (`models.py`).
**Premise (from P3.4):** a **blind autogenerate is incomplete** — the true source of truth for indexes/constraints is `migrate_schema()`, which declares ~38 indexes/constraints absent from the models. This plan defines exactly how `0001` will be authored and reviewed to close that gap.

## 1. Generation approach

- **Draft only against an EMPTY database.** `0001` is generated/inspected against a fresh DB so autogenerate emits **create-only** output (no spurious `DROP`/`ALTER` from comparing against a populated migrate_schema-evolved DB).
- **Autogenerate output is a DRAFT of tables / columns / FKs / declared `__table_args__` constraints only.** It is **not** the deliverable.
- **No blind autogenerate acceptance.** Every line is manually reviewed; the index/constraint set is hand-reconciled (§2) before `0001` is considered complete.
- `migrate_schema()` and models are **not** modified to produce the draft.

## 2. Manual reconciliation list (hand-added to `0001`)

All indexes/constraints below exist **only** in `migrate_schema()` raw DDL and must be added to `0001` verbatim (predicates normalized per §3).

**Accounting-integrity uniques (mandatory):**
- `uq_yec_year` — one non-void year-end-close per `fiscal_year`.
- `uq_palloc_period` — one non-void profit allocation per `fiscal_period_id` *(the guard the P2.9 duplicate-allocation fix depends on — must not be dropped)*.
- `uq_eod_date_active` — one non-void EOD close per `date`.
- `uq_esv_active` — one non-void external-sales verification per `(company_id, business_date, COALESCE(branch_location, ''))`.
- `uq_coa_code_company` — unique `(company_id, account_code)` on `chart_of_accounts`.
- products unique `(company_id, sku)`.

**Performance indexes:**
- All `ix_*_company_id` indexes (~30) on the Phase-14A business tables (their `company_id` columns are not `index=True` in models, so only `migrate_schema` creates them).
- Composite indexes `ix_att_entity` `(entity_type, entity_id, is_deleted)` and `ix_draftatt_draft` `(draft_type, draft_id)`.
- The remaining named single-column indexes (`ix_je_*`, `ix_sale_*`, etc.) — reconciled per the naming decision (§4).

## 3. PostgreSQL predicate normalization

- **`WHERE is_void = 0` → `is_void IS FALSE`** for every partial unique index (`uq_yec_year`, `uq_palloc_period`, `uq_eod_date_active`, `uq_esv_active`). `IS FALSE` is valid on **both** SQLite and PostgreSQL; `= 0` is a boolean=integer type error on PG. Author as a single `is_void IS FALSE` predicate (or dialect-split `postgresql_where` / `sqlite_where` if a dialect needs the legacy form).
- **`uq_esv_active` functional predicate `COALESCE(branch_location, '')`** — kept as a parenthesized index expression; valid on both engines. Review quoting/expression rendering in the Alembic op.
- No other predicate or expression rewrites; **no `Float → Decimal`**.

## 4. Naming convention

- **Adopt SQLAlchemy's `ix_<table>_<column>` convention going forward** for autogenerate stability (avoids perpetual "missing/extra index" churn on future autogenerate diffs).
- **Document the legacy `migrate_schema` names** (e.g. `ix_je_entry_date`, `ix_pmov_partner_id`) **vs the Alembic names** in `0001` (a legacy→new map), so existing migrated DBs (which carry the legacy names) and fresh Alembic DBs are understood to differ only by index name, not by coverage.
- Constraint names (`uq_*`) are **preserved verbatim** from `migrate_schema` so the accounting-integrity uniques keep stable, recognizable names.

## 5. Review checklist (must all pass before acceptance)

- [ ] **No `DROP`** statements (baseline is create-only).
- [ ] **No destructive `ALTER`** (no column/table drops, no type narrowing).
- [ ] **No data migrations** (schema-only; any data move would need explicit backup/rollback notes per P3.3 — not expected in `0001`).
- [ ] **No `Float → Decimal`** (money columns stay `Float`; reject any such autogenerate diff).
- [ ] **No accidental loss of legacy tables** (`cash_sales`, `credit_sales`, `salaries`, `expenses` present as CREATE).
- [ ] **All accounting-critical constraints present** (the six §2 uniques).
- [ ] **All `company_id` + composite indexes present** (§2 performance list).
- [ ] **All partial predicates are `is_void IS FALSE`** (§3).

## 6. Acceptance gate — baseline-equivalence test (required)

`0001` is **not accepted** until a baseline-equivalence test passes:

- Build DB **A** via Alembic `upgrade head` (from `0001`); build DB **B** via a full `migrate_schema()` evolution (the current authoritative path).
- **Compare A vs B:** tables, columns (name/type/nullability), indexes (coverage; names per §4 map), unique constraints, and foreign keys must match (modulo the documented index-name differences).
- **SQLite first** (default fast path); **PostgreSQL optional later** (when PG fixtures exist).
- Any divergence = `0001` is incomplete → fix and re-run. This test is the acceptance gate (a future P3.4-C deliverable).

## 7. Rollout / stamping strategy

- **Existing SQLite DBs:** **backup first**, then `alembic stamp 0001` only (writes the `alembic_version` row, **runs no DDL** — they already have the `0001` schema via `migrate_schema`). Non-destructive.
- **New DBs:** Alembic creates the schema via `upgrade head` (PG always; SQLite may also keep `create_all` for fast tests, equivalence-guarded by §6).
- **`migrate_schema()` remains active and authoritative** until a separate, approved cutover task — it is not removed in P3.4-B.

## No-change decisions (P3.4-B)

- **No `0001` authored, no revision file created, no DB stamped, no alembic command run.**
- **`migrate_schema()` stays authoritative and active.**
- **Models / `Float` unchanged** (NUMERIC excluded).
- **No runtime DB / Streamlit / FastAPI change.**

## Recommended next steps

- **P3.4-C:** implement the baseline-equivalence test harness (§6) — the acceptance gate.
- **P3.4-D:** author `0001` per §1–§4, run the §5 checklist, pass §6, then (separately) stamp existing DBs per §7.
- **P3.4-E (later):** startup cutover to Alembic + retire `migrate_schema`, after green equivalence on SQLite (and PG when available).

---

*Planning only — no migration authored, no revision file, no stamping, `migrate_schema()` authoritative, models/`Float` unchanged. `0001` will be drafted against an empty DB (create-only), with autogenerate treated as a tables/columns/FKs draft and the ~38 `migrate_schema`-only indexes/constraints hand-added — including the six accounting-integrity uniques — partial predicates normalized to `is_void IS FALSE` (and `COALESCE(branch_location, '')` preserved), names reconciled to avoid churn, and acceptance gated on a baseline-equivalence test (SQLite first, PostgreSQL later).*
