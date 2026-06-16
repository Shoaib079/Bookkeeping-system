# POSTGRES — Real SQLite→PostgreSQL Dry Run (2026-06-16)

**Status:** ✅ **Verified** (operator dry run)  
**Tag:** `postgres-real-dry-run-20260616`  
**Mode:** Copy-only migration dry run on disposable databases — **no production runtime switch**

## Verdict

Real production-shaped data copied from a **timestamped SQLite backup** to a disposable PostgreSQL test database (`erp_pytest`). Row counts, trial balance, and full accounting report fingerprints **match across all four companies**. **`erp_data.db` was not modified.**

**Production runtime cutover remains blocked** until explicit operator approval, backup ceremony, and runtime gate wiring.

## Dry-run parameters

| Field | Value |
|-------|--------|
| **SQLite copy (source)** | `erp_data_pg_dry_run_source_20260616_201308.db` |
| **PostgreSQL URL (masked)** | `postgresql+psycopg://***@localhost:5432/erp_pytest` |
| **Env var** | `ERP_TEST_POSTGRES_URL` only — `DATABASE_URL` unchanged |
| **Companies verified** | `1`, `2`, `3`, `4` |
| **Alembic PG build** | `upgrade head` → revision `0002` |

## Results summary

| Check | Result |
|-------|--------|
| `production_erp_data_touched` | **false** |
| `row_count_mismatches` | **{}** (empty) |
| `trial_balance_mismatches` | **{}** (empty) |
| `report_mismatches` | **{}** (empty) |
| `safe_for_production_cutover` | **true** (data parity only — not an approval to cut over) |

## Reports verified (per company, SQLite copy vs PG)

- Trial Balance (JE debit/credit totals)
- Balance Sheet (`compute_balance_sheet`)
- Profit & Loss (`compute_profit_loss`)
- Cash Flow (`compute_cash_flow`)
- Bank balances (`BankAccount.balance`)
- AR (open `Sale.balance` sum)
- AP (open unpaid `Payable.amount` sum)
- Partner profit allocations (count)
- Retained Earnings GL balance

## Safety rules honored

1. **Production `erp_data.db` read-only** — dry run used copy only.
2. **Backup preserved** — `erp_data_before_pg_dry_run_20260616_201308.db`.
3. **`DATABASE_URL` unchanged** — app runtime remains SQLite.
4. **`ERP_POSTGRES_RUNTIME_CUTOVER` not wired** — no production switch.
5. **PG test DB dropped after run** — disposable `erp_pytest` schema reset via harness teardown.

## What this does NOT approve

| Item | Status |
|------|--------|
| Switch `DATABASE_URL` to PostgreSQL | **Not approved** |
| Wire runtime cutover gate to startup | **Not done** |
| Apply Alembic `0002` to production `erp_data.db` | **Not done** |
| Decommission SQLite | **Not done** |
| Operator backup + `APPROVE PRODUCTION POSTGRES CUTOVER` | **Still required** |

## Related docs

- [POSTGRES_RUNTIME_CUTOVER_PREP.md](./POSTGRES_RUNTIME_CUTOVER_PREP.md) — harness + gate module
- [POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md](./POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md) — Alembic PG build + dual-run
- [P4_1_LOCAL_POSTGRES_VALIDATION.md](./P4_1_LOCAL_POSTGRES_VALIDATION.md) — operator PG setup

## Next step

**PostgreSQL production runtime cutover** — operator-gated: wire runtime gate, final backup, approval phrase, `DATABASE_URL` switch with rollback plan. Data parity prerequisite **met** for this snapshot.
