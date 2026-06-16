# POSTGRES — Production Runtime Cutover (2026-06-16)

**Status:** ✅ **Verified** (operator cutover — testing environment)  
**Tag:** `postgres-production-cutover`  
**Mode:** Flag-gated PostgreSQL runtime with SQLite rollback preserved

## Verdict

Approved operator cutover migrated current SQLite data into PostgreSQL, verified row counts + trial balance + full accounting reports for all companies, wired the runtime gate, and confirmed post-cutover smoke flows. **SQLite backup preserved**; **`erp_data.db` not modified** during migration (read-only source).

## Cutover parameters

| Field | Value |
|-------|--------|
| **SQLite source** | `erp_data.db` (read-only) |
| **SQLite backup** | `erp_data_PRODUCTION_CUTOVER_20260616_212243.db` |
| **PostgreSQL URL (masked)** | `postgresql+psycopg://***@localhost:5432/erp_pytest` |
| **Companies verified** | `1`, `2`, `3`, `4` |
| **Alembic PG build** | `upgrade head` → revision `0002` |

## Runtime environment (required)

| Env var | Purpose |
|---------|---------|
| `ERP_POSTGRES_RUNTIME_CUTOVER=1` | Enable PostgreSQL runtime |
| `ERP_POSTGRES_RUNTIME_APPROVAL=APPROVE PRODUCTION POSTGRES CUTOVER` | Operator approval phrase |
| `ERP_POSTGRES_CUTOVER_BACKUP_PATH` | Path to pre-cutover SQLite backup (must exist) |
| `ERP_POSTGRES_RUNTIME_URL` | PostgreSQL connection URL |
| `DATABASE_URL` | Set to same PostgreSQL URL (or rely on gate resolution) |
| `ERP_ALEMBIC_AUTHORITATIVE=1` | Required — PG cannot use `migrate_schema()` |

## Verification summary

| Check | Result |
|-------|--------|
| `production_erp_data_touched` | **false** |
| `row_count_mismatches` | **{}** |
| `trial_balance_mismatches` | **{}** |
| `report_mismatches` | **{}** |
| `company_isolation_ok` | **true** |
| Post-cutover smoke (sale/expense/purchase/void/banking/reports) | **pass** |

## Reports verified (per company, SQLite vs PG)

- Trial Balance (JE debit/credit totals)
- Balance Sheet (`compute_balance_sheet`)
- Profit & Loss (`compute_profit_loss`)
- Cash Flow (`compute_cash_flow`)
- Bank balances (`BankAccount.balance`)
- AR / AP open balances
- Partner profit allocations
- Retained Earnings GL balance

## Rollback plan

1. **Stop the app** (Streamlit / FastAPI).
2. **Disable cutover:** unset `ERP_POSTGRES_RUNTIME_CUTOVER` and `DATABASE_URL` PostgreSQL value.
3. **Restore SQLite runtime:** app falls back to `paths.SQLITE_DATABASE_URL` → `erp_data.db`.
4. **If SQLite data was corrupted:** replace `erp_data.db` from `erp_data_PRODUCTION_CUTOVER_20260616_212243.db` (or latest backup in `backups/`).
5. **Never hand-edit accounting tables** — restore from backup only.

## What remains SQLite

- `erp_data.db` on disk (unchanged source + rollback target)
- Phase 14A milestone helpers still reference `DB_PATH` for legacy one-time SQLite DDL
- CI default pytest path (no `ERP_POSTGRES_*` env)

## Related docs

- [POSTGRES_REAL_DRY_RUN_20260616.md](./POSTGRES_REAL_DRY_RUN_20260616.md) — prerequisite dry run
- [POSTGRES_RUNTIME_CUTOVER_PREP.md](./POSTGRES_RUNTIME_CUTOVER_PREP.md) — harness + gate module
- `scripts/postgres_production_cutover.py` — operator migration script

## Operator commands

```bash
export ERP_POSTGRES_RUNTIME_CUTOVER=1
export ERP_POSTGRES_RUNTIME_APPROVAL='APPROVE PRODUCTION POSTGRES CUTOVER'
export ERP_POSTGRES_CUTOVER_BACKUP_PATH="$PWD/erp_data_PRODUCTION_CUTOVER_20260616_212243.db"
export ERP_POSTGRES_RUNTIME_URL='postgresql+psycopg://postgres@localhost/erp_pytest'
export DATABASE_URL="$ERP_POSTGRES_RUNTIME_URL"
export ERP_ALEMBIC_AUTHORITATIVE=1

python scripts/postgres_production_cutover.py
pytest tests/test_postgres_production_cutover_smoke.py -m optional_postgres -v
streamlit run app.py
```
