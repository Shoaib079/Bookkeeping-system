# P3.4-D — Alembic Baseline Migration (`0001`)

**Status:** Shipped (migration authored + tests; **not applied to production**)  
**Mode:** Migration authoring + equivalence tests only.

**Related:** [P3.4-B Authoring Plan](./P3_4_B_BASELINE_AUTHORING_PLAN.md) · [P3.4-C Equivalence Harness](./P3_4_C_BASELINE_EQUIVALENCE_HARNESS.md) · `alembic/versions/0001_baseline.py`

---

## Summary

| Item | Status |
|------|--------|
| Revision `0001` authored | Yes — `alembic/versions/0001_baseline.py` |
| Applied to production `erp_data.db` | **No** |
| Any DB stamped | **No** — not stamped |
| `migrate_schema()` authoritative | **Yes** — unchanged at runtime |
| Baseline equivalence (SQLite) | **Pass** — Alembic 0001 vs `create_all` + `migrate_schema()` |
| Models / `Float` / runtime behavior | Unchanged |

---

## What `0001` contains

1. **ORM schema** — `Base.metadata.create_all()` (all tables, columns, FKs from `models.py`).
2. **Supplemental indexes** — 105 `migrate_schema()`-only indexes/constraints, including:
   - Accounting-integrity uniques: `uq_yec_year`, `uq_palloc_period`, `uq_eod_date_active`, `uq_esv_active`, `uq_coa_code_company`, `uq_products_sku_company`
   - Composite indexes: `ix_att_entity`, `ix_draftatt_draft`
   - ~30 `ix_*_company_id` performance indexes
   - Legacy short-name single-column indexes (`ix_je_*`, `ix_sale_*`, etc.)

### PostgreSQL-safe predicates

Partial unique indexes use **`is_void IS FALSE`** (not `is_void = 0`).  
`uq_esv_active` preserves **`COALESCE(branch_location, '')`**.

### Create-only upgrade

- No `DROP` in `upgrade()`
- No destructive `ALTER`
- No data migrations
- No `Float → Decimal`

### Downgrade

`downgrade()` calls `Base.metadata.drop_all()` — **unsafe for real accounting data**. Documented for ephemeral/test use only.

---

## Acceptance status

| Gate | Result |
|------|--------|
| `0001` file exists | Pass |
| `upgrade()` has no DROP | Pass |
| Required indexes/uniques in source | Pass |
| `is_void IS FALSE` present; `is_void = 0` absent | Pass |
| No Float→Decimal | Pass |
| Production DB untouched | Pass |
| Ephemeral SQLite: 0001 ≡ migrate_schema-evolved | Pass (`tests/test_p3_4_d_alembic_baseline.py`) |
| Pre-0001 drift still detected (create_all vs migrate) | Pass (`tests/test_p3_4_c_baseline_equivalence_harness.py`) |

---

## Remaining before cutover

These are **out of scope for P3.4-D**:

1. **`alembic stamp 0001`** on existing SQLite DBs (after backup).
2. **Startup cutover** — replace `create_all` + `migrate_schema()` with Alembic `upgrade head`.
3. **Retire `migrate_schema()`** as authoritative path.
4. **PostgreSQL equivalence** on CI (optional PG fixtures).
5. **P3.4-E** — production rollout + documentation update for operators.

Until cutover, every app startup still runs `migrate_schema()` on `erp_data.db`.

---

## How to run tests

```bash
pytest tests/test_p3_4_d_alembic_baseline.py
pytest tests/test_p3_4_c_baseline_equivalence_harness.py
pytest
```

Tests apply revision `0001` only on **in-memory SQLite** via the harness — never `alembic upgrade` against `erp_data.db`.

---

*P3.4-D complete: baseline authored, equivalence green on ephemeral SQLite, production untouched, `migrate_schema()` still authoritative.*
