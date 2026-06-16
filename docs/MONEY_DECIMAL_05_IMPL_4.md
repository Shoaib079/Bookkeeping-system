# MONEY-DECIMAL-05-IMPL-4 — Migration Smoke + PG Test

**Status:** Complete (2026-06-16)  
**Tag:** `money-decimal-05-impl4-migration-smoke`  
**Baseline:** **4633 passed**, 11 skipped, 2 xfailed

## Scope

1. **SQLite populated smoke** — seed tenant at `0001`, capture money snapshot (JE totals, cash balance, P&L net, bank cache), upgrade to `0002`, verify:
   - Alembic head `0002`
   - Index/FK/table integrity preserved (batch rebuild + supplemental index re-apply)
   - Numeric column affinity on money columns; Float remain on quantity/percentage
   - Money snapshot unchanged to the cent
   - Post-migration posting + cache re-sync works
2. **Golden amount check** — cash balance `100.01` after migrated DB seed
3. **Ugly double** — ORM `Sale.amount` reads as quantized `Decimal` after `0002`
4. **Optional PostgreSQL** (`ERP_TEST_POSTGRES_URL`, `@pytest.mark.optional_postgres`):
   - `alembic upgrade head` → column scales 19,2 / 19,4 / 19,8
   - `0.1 + 0.2 == 0.30` exact NUMERIC round-trip

## Alembic fix (0002)

SQLite `batch_alter_table` rebuilds drop 0001 supplemental partial indexes (e.g. `uq_esv_active`). Revision `0002` now re-applies supplemental index DDL from `0001_baseline` for every batch-rebuilt table.

## Never

- Apply `0002` to production `erp_data.db`
- PostgreSQL production runtime cutover (IMPL-5)

## Tests

| File | Role |
|------|------|
| `tests/md05_migration_smoke_utils.py` | Alembic runner, seed, snapshots |
| `tests/test_money_decimal_05_impl4_migration_smoke.py` | SQLite + optional PG smoke |

## Next slice

**MD-05-IMPL-5** — flag-gated cutover (P3.8 backup-first machinery).
