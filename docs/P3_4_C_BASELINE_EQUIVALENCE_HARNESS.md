# P3.4-C — Baseline Equivalence Harness

**Status:** Shipped (harness + post-0001 equivalence)  
**Mode:** Schema fingerprint comparison harness + documentation. **Alembic `0001` authored in P3.4-D** (not applied to production).

**Related:** [P3.4-B Baseline Authoring Plan](./P3_4_B_BASELINE_AUTHORING_PLAN.md) · [P3.4 Alembic Baseline Review](./P3_4_ALEMBIC_BASELINE_REVIEW.md) · `tests/p3_schema_equivalence_utils.py`

---

## Purpose

Provide the **acceptance-gate harness** that will eventually prove:

| Path | Today (P3.4-C) | After P3.4-D (`0001` exists) |
|------|----------------|------------------------------|
| **A — Baseline** | `Base.metadata.create_all` | `alembic upgrade head` (revision `0001`) — **authored P3.4-D** |
| **B — Authoritative** | `create_all` + `migrate_schema()` | Same until cutover |

P3.4-C compares **create_all vs migrate_schema** and documents the **expected pre-0001 drift**.  
P3.4-D adds **post-0001 equivalence**: Alembic `0001` upgrade vs `migrate_schema`-evolved (must match).

No migration revision is created. No `alembic upgrade`. No stamping. No runtime DB change.

---

## What is compared now

Normalized SQLite schema summaries extracted via `sqlite_master` + PRAGMA:

| Dimension | Captured |
|-----------|----------|
| **Tables** | All non-internal table names |
| **Columns** | name, type, NOT NULL, PK per table |
| **Indexes** | name, table, unique flag, partial-index SQL when present |
| **Foreign keys** | from/to columns per table |

Drift report fields:

- `indexes_only_in_migrated` — the pre-0001 gap (primary signal)
- `indexes_only_in_create_all` — should be empty or minimal pre-0001
- `company_id_indexes_only_in_migrated`
- `accounting_uniques_only_in_migrated`
- `composite_indexes_only_in_migrated`
- `partial_indexes_only_in_migrated`
- `column_diffs` — should be empty when models are the column superset

---

## What is compared after `0001` (P3.4-D)

1. Build **A** from revision `0001` `upgrade()` on ephemeral SQLite (`build_alembic_0001_schema_summary`)
2. Build **B** from `create_all` + `migrate_schema()` (unchanged until cutover)
3. **`assert schema equivalence`** — drift must be **empty**
4. See [P3.4-D Baseline Migration](./P3_4_D_BASELINE_MIGRATION.md) for acceptance status

Pre-0001 path (create_all vs migrate) still runs and **expects drift**.

---

## Known expected drift (pre-0001)

Documented in [P3.4 Alembic Baseline Review](./P3_4_ALEMBIC_BASELINE_REVIEW.md). The harness pins these markers:

### Accounting-integrity uniques (migrate_schema only)

| Index | Role |
|-------|------|
| `uq_yec_year` | One active year-end close per company+year |
| `uq_palloc_period` | One active profit allocation per company+period |
| `uq_eod_date_active` | One active EOD close per company+date |
| `uq_esv_active` | Active external sales verification uniqueness |
| `uq_coa_code_company` | Unique account code per company |
| `uq_products_sku_company` | Unique SKU per company (partial) |

### Composite indexes (migrate_schema only)

| Index | Columns |
|-------|---------|
| `ix_att_entity` | `attachments (entity_type, entity_id, is_deleted)` |
| `ix_draftatt_draft` | `draft_attachments (draft_type, draft_id)` |

### Company-scoped indexes (~30)

All `ix_*_company_id` indexes on Phase-14A business tables — `company_id` columns lack `index=True` in models; only `migrate_schema()` creates them.

**Status today:** drift is **expected and required** to be non-empty. Absence of drift would indicate a harness bug or accidental schema merge.

---

## Acceptance gate for P3.4-D / `0001`

Before accepting revision `0001`:

| Check | P3.4-C (now) | P3.4-D (future) |
|-------|--------------|-----------------|
| Harness runs on ephemeral SQLite | Required | Required |
| Known drift detected | **Must be true** | N/A |
| `indexes_only_in_migrated` empty | **Must be false** | **Must be true** |
| Accounting uniques present in A | **Must be false** | **Must be true** |
| `company_id` indexes present in A | **Must be false** | **Must be true** |
| No Alembic revision until approved | **Must be true** | `0001` merged |

---

## How to run

```bash
cd streamlit_accounting_erp

# Harness tests only
pytest tests/test_p3_4_c_baseline_equivalence_harness.py -v

# Full suite (default — no PostgreSQL required)
pytest
```

Programmatic:

```python
from p3_schema_equivalence_utils import run_pre_0001_baseline_equivalence

result = run_pre_0001_baseline_equivalence()
print(result["report"])
# drift is expected pre-0001
```

Uses in-memory SQLite only — never `paths.DATABASE_URL` / `erp_data.db`.

---

## Limitations

- **SQLite only** in P3.4-C — PostgreSQL equivalence deferred until PG fixtures + `0001` exist
- **Index names** — create_all uses SQLAlchemy default names for `index=True` columns; migrate_schema uses short legacy names (`ix_je_entry_date` vs `ix_journal_entries_entry_date`). Post-0001 may document name-only differences on indexes present in both paths
- **Column drift** — not expected today (models are superset); harness still reports column diffs if they appear
- **Data migrations** — `MigrationFlag` one-time steps (e.g. partial index rebuild) are not compared — schema DDL only
- **No Alembic execution** — cannot validate `0001` until P3.4-D authors it
- **`migrate_schema()` remains authoritative** — harness does not replace startup evolution

---

## API

| Symbol | Role |
|--------|------|
| `build_create_all_schema_summary()` | Path A fingerprint |
| `build_migrate_evolved_schema_summary()` | Path B fingerprint |
| `compute_schema_drift(a, b)` | Normalized diff |
| `assert_known_pre_0001_drift_detected(drift)` | Pin expected pre-0001 gaps |
| `run_pre_0001_baseline_equivalence()` | Full run + report |
| `ACCOUNTING_INTEGRITY_UNIQUES` | Drift markers |
| `COMPOSITE_MIGRATE_ONLY_INDEXES` | `ix_att_entity`, `ix_draftatt_draft` |

---

*Harness only. Drift before `0001` is expected. Equivalence becomes mandatory after P3.4-D.*
