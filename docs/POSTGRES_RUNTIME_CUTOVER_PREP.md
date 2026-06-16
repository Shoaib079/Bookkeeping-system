# POSTGRES Runtime Cutover Prep

**Status:** ✅ **Prep slice closed** (2026-06-16)  
**Tag:** `postgres-runtime-cutover-prep`  
**Verdict:** **Production runtime cutover still blocked** — prep harness + gate module only

## Purpose

Characterize and test the **SQLite → PostgreSQL data migration path** on disposable databases before any production `DATABASE_URL` switch. Builds on completed prerequisites:

| Prerequisite | Status |
|--------------|--------|
| Alembic authority (P3.9 / ALEMBIC-01) | ✅ |
| MD-05 Numeric (`0002`, `services/money.py`) | ✅ |
| PG Alembic build + dual-run parity | ✅ |
| P3.8 / MD-05 flag-gated schema cutover | ✅ (SQLite only) |

## What this slice shipped

| Deliverable | Role |
|-------------|------|
| `tests/pg_sqlite_data_migration_utils.py` | Test-only SQLite file → PG row copy + money snapshot verify |
| `services/postgres_runtime_cutover.py` | Parse-only runtime cutover gate (**not wired** to `db.py`) |
| `tests/test_postgres_runtime_cutover_prep.py` | Safety + SQLite build + optional PG copy tests |

## Standing rules (locked)

1. **Production remains SQLite** — `paths.DATABASE_URL` unchanged.
2. **`erp_data.db` never touched** by prep/copy helpers.
3. **PG tests use `ERP_TEST_POSTGRES_URL` only** — skip when unset.
4. **Schema on PG via Alembic** — `bootstrap_postgres_via_alembic()` → revision `0002`.
5. **Runtime switch is a separate future slice** — requires operator approval phrase + backup.

## Runtime cutover gate (prep-only, not wired)

| Env var | Default | Meaning |
|---------|---------|---------|
| `ERP_POSTGRES_RUNTIME_CUTOVER` | off | Future flag to allow PG runtime URL |
| `ERP_POSTGRES_RUNTIME_APPROVAL` | unset | Must equal `APPROVE PRODUCTION POSTGRES CUTOVER` |

Module: `services/postgres_runtime_cutover.py` — **does not mutate `DATABASE_URL`**.

Separate from `ERP_MONEY_NUMERIC_CUTOVER` (SQLite schema 0001→0002).

## Verification

```bash
# SQLite-only (CI default)
pytest tests/test_postgres_runtime_cutover_prep.py -v

# With PostgreSQL
export ERP_TEST_POSTGRES_URL='postgresql+psycopg://localhost/erp_pytest'
pytest tests/test_postgres_runtime_cutover_prep.py -m optional_postgres -v
```

## Remaining blockers (production cutover)

1. **Full production data migration** — characterized export/load for real `erp_data.db` (not built).
2. **Balance/report verification at scale** — smoke tenant only today.
3. **Runtime wiring** — connect gate to startup + `DATABASE_URL` switch (future slice).
4. **Operator backup + approval** — P3.8-style cutover ceremony.
5. **FastAPI smoke on PG** — recommended before production.

Historical audit [POSTGRES_P4_2_CUTOVER_AUDIT.md](./POSTGRES_P4_2_CUTOVER_AUDIT.md) predates MD-05/PG-build completion; treat this doc as current prep status.

## Next slice

**PostgreSQL production runtime cutover** — wire gate, migrate production-shaped data, verify reports, flag-gated switch (operator-only).
