# PostgreSQL Build + Dual-Run Parity

**Status:** ✅ **Closed** (2026-06-16)  
**Tag:** `postgres-pg-build-dual-run-parity`  
**Mode:** Test infrastructure only — **no production runtime switch**

## Verdict

PostgreSQL test databases are now built via **`alembic upgrade head`** (revision **`0002`**, Numeric money columns). The P3.2 dual-run harness compares SQLite (in-memory ORM) vs Alembic-built PostgreSQL on the same golden posting flows, including **report fingerprints** (P&L net, balance sheet totals).

Production remains **SQLite** (`erp_data.db`). **`0002` is not applied to production** without the MD-05 cutover gate.

## What changed

| Component | Before | After |
|-----------|--------|-------|
| PG schema in dual-run | `Base.metadata.create_all` | `bootstrap_postgres_via_alembic()` → `alembic upgrade head` |
| Parity summary | counts + journal + voids | + **`reports`** (P&L / BS fingerprints) |
| PG reset | `drop_all` on metadata | `drop_all_pg_objects` + Alembic rebuild |
| Shared helpers | duplicated in MD-05 smoke | `drop_all_pg_objects` centralized in `tests/postgres_utils.py` |

## How to run

### SQLite-only (default CI)

```bash
pytest tests/test_p3_2_dual_run_parity.py tests/test_pg_build_dual_run_parity.py -v
```

### With PostgreSQL

```bash
createdb erp_pytest
export ERP_TEST_POSTGRES_URL='postgresql+psycopg://localhost/erp_pytest'
pip install psycopg2-binary  # or psycopg

pytest tests/test_p3_2_dual_run_parity.py tests/test_pg_build_dual_run_parity.py \
  tests/test_money_decimal_05_impl4_migration_smoke.py \
  -m optional_postgres -v
```

Safety rules: `tests/postgres_utils.py` rejects production DB names and `erp_data.db`.

## Golden flows (unchanged registry)

Cash sale · expense · credit purchase + payable · receivable payment · partner capital · worker advance — see [P3_2_DUAL_RUN_PARITY_HARNESS.md](./P3_2_DUAL_RUN_PARITY_HARNESS.md).

## Optional PG tests when URL unset

All `@pytest.mark.optional_postgres` tests **skip safely** when `ERP_TEST_POSTGRES_URL` is unset.

## Not in scope (remaining PG blockers)

- **Production runtime cutover** — still blocked; see [POSTGRES_P4_2_CUTOVER_AUDIT.md](./POSTGRES_P4_2_CUTOVER_AUDIT.md) (update pending)
- **SQLite → PG data migration** — separate project
- **Flag-gated `DATABASE_URL` switch** — operator action only

## Next slice

**PostgreSQL production cutover prep** — SQLite→PG data migration + flag-gated runtime switch (after operator approval). Or **NAV-ARCH** (deferred, post-PG parity).
