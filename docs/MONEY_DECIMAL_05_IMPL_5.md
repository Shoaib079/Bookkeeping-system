# MONEY-DECIMAL-05-IMPL-5 — Flag-Gated Cutover

**Status:** Complete (2026-06-16)  
**Tag:** `money-decimal-05-impl5-cutover-gate`  
**Baseline:** **4651 passed**, 11 skipped, 2 xfailed

## Scope

Wire **0001 → 0002** money NUMERIC migration into the existing P3.8 startup authority path:

| Env var | Role |
|---------|------|
| `ERP_ALEMBIC_AUTHORITATIVE=1` | Alembic authority (default-on per P3.8-N) |
| `ERP_MONEY_NUMERIC_CUTOVER=1` | Arm populated 0001→0002 auto-upgrade |
| `ERP_SCHEMA_BACKUP_PATH` | Valid backup file (P3.8-I) |
| `ERP_SCHEMA_MIGRATION_CONFIRMATION` | Exact phrase `I HAVE BACKED UP THIS DATABASE` |
| `ERP_MONEY_NUMERIC_PRODUCTION_APPROVAL` | Reserved: `APPROVE PRODUCTION POSTGRES CUTOVER` (not used in IMPL-5) |

## Behavior

1. **Default (cutover flag off):** populated DB at `0001` with head `0002` still **blocks** startup (P3.8-K2 unchanged).
2. **Cutover armed:** when `ERP_MONEY_NUMERIC_CUTOVER=1` + backup + confirmation + DB at `0001` / head `0002`:
   - Runs `alembic upgrade head` via P3.8-H runner
   - Skips `migrate_schema()`
   - Runs `run_money_numeric_post_cutover()` (GL + bank cache re-sync) in-session
3. **Production `erp_data.db`:** blocked by `alembic_runner` URL guard unless production approval env is set (IMPL-5 does **not** enable production cutover).

## Files

| File | Role |
|------|------|
| `services/money_numeric_cutover.py` | Flag parser, eligibility, gate, post-cutover cache re-sync |
| `services/schema_startup_wiring.py` | Behind-head branch + session hook |
| `tests/test_money_decimal_05_impl5_cutover_gate.py` | Contract + wiring + real Alembic integration |

## Never (IMPL-5)

- Apply `0002` to production `erp_data.db` without explicit operator approval
- PostgreSQL **production** runtime cutover
- Remove or disable `migrate_schema()` (P3.9)

## Rollback

1. Restore from backup (replace SQLite file)
2. Set `ERP_MONEY_NUMERIC_CUTOVER=0`
3. Optionally set `ERP_ALEMBIC_AUTHORITATIVE=0` to fall back to `migrate_schema()`

## Next

PostgreSQL build via Alembic (incl. `0002`) + dual-run parity on production-shaped data; PG production cutover remains gated on explicit approval.
