# P4.0 — PostgreSQL Production Enablement Plan

**Mode:** Documentation + lightweight contract test only. **No runtime switch in this slice.** `DATABASE_URL` is unchanged (still SQLite); no runtime switch to PostgreSQL; no migrations run against any PostgreSQL production database; models unchanged; `Float` **not** converted to `Decimal`; `migrate_schema()` **not** removed; no schema/accounting/API/UI change.
**Status:** **SQLite remains the runtime database.** This defines the **safe path to enable PostgreSQL later**, validated test-DB-first and gated on equivalence + parity.
**Context:** Alembic `0001` baseline exists; the SQLite DB is stamped; flag-gated Alembic startup wiring exists (P3.8-K2, off by default); `migrate_schema()` retirement is planned (P3.9) not executed; optional PostgreSQL test fixtures and a dual-run parity harness exist.

## 1. Current state

- **SQLite remains the runtime DB** — `DATABASE_URL = sqlite:///…/erp_data.db`; no change here.
- **PG fixtures optional** — PostgreSQL test fixtures run only when an explicit test URL is provided; they are skipped otherwise and never touch production.
- **Alembic-only PG path** — any PostgreSQL schema is created and evolved **exclusively** through Alembic (`upgrade head` from `0001`).
- **No `migrate_schema()` on PG** — its SQLite-only DDL/PRAGMA is invalid on PostgreSQL; it never runs there (already dialect-aware in `db.py`).

## 2. PostgreSQL prerequisites

- **Driver choice** — use **`psycopg`** (psycopg 3) as the PostgreSQL driver (`postgresql+psycopg://…`); pin it as an **optional** dependency, not a core runtime requirement, so SQLite installs are unaffected.
- **Test DB only first** — all initial work targets a **local/CI PostgreSQL test database**; production PG is never the first target.
- **`ERP_TEST_POSTGRES_URL` safety rules** — PostgreSQL tests read the test URL from `ERP_TEST_POSTGRES_URL`; if unset, PG tests are **skipped** (never silently fall back to production). The URL must point at a disposable test DB; production markers (e.g. `erp_data`, `/production/`, `prod`) are rejected. PG tests must never run against `DATABASE_URL`.
- **`alembic upgrade head` on an empty PG test DB** — schema is built only via Alembic on a fresh empty PG database (no `create_all` shortcuts in the PG validation path).
- **Schema equivalence** — the Alembic-built PG schema must be proven equivalent to the SQLite reference (tables, columns, indexes, uniques, FKs; PG predicate normalizations like `is_void IS FALSE` accounted for).
- **Dual-run parity green** — the existing dual-run parity harness must pass on PG (posting/void/allocation arithmetic and balances identical to SQLite).
- **Backup/restore plan for production** — a `pg_dump`/`pg_restore` backup + restore procedure must be defined and tested **before** any production PG involvement.

## 3. Validation sequence

Test-DB-first; **never touch production first**:

1. **Local PG test DB** — provision a disposable PostgreSQL database; set `ERP_TEST_POSTGRES_URL` to it.
2. **Run `optional_postgres` tests** — execute the PG-marked test suite against the test DB.
3. **Run dual-run parity** — the parity harness must be green on PG vs. SQLite.
4. **Inspect schema / indexes / constraints** — compare the Alembic-built PG schema against the SQLite reference (tables, columns, indexes, uniques, FKs).
5. **Run a FastAPI smoke** — exercise the API write/read paths against the PG test DB.
6. **Never touch production first** — production PG is approached only after steps 1–5 are clean and a backup/restore is verified.

## 4. Known limitations

- **`Float` money unchanged** — money stays `Float` (IEEE-754 double, identical on SQLite and PG for the swap); `NUMERIC`/`Decimal` is a **separate future project**, explicitly out of scope here.
- **Naive datetimes unchanged** — `datetime.now()` naive values map to PG `timestamp without time zone` identically; timezone-aware handling is a future design note, not part of this enablement.
- **Case-sensitivity differences** — PG `LIKE` is case-sensitive (SQLite is ASCII case-insensitive); `ILIKE` is used where insensitivity is needed; the one business `.like()` (transfer pairing) compares app-generated same-case text and is safe — to be re-verified on PG.
- **SQLite-only code guarded** — the `PRAGMA foreign_keys` connect listener and `migrate_schema()` are dialect-guarded / SQLite-only and never run on PG.
- **Performance / index checks later** — query plans, index usage, and PG-specific tuning are a **later** task, not part of enablement validation.

## 5. Production cutover (later)

- **Create a fresh PG DB via Alembic** — production PostgreSQL schema is built with `alembic upgrade head` from `0001`, never `migrate_schema()`.
- **Migrate data only in a separate project** — any data migration from SQLite → PG is a **distinct, separately-scoped project** with its own characterization and validation; not bundled into enablement.
- **Verify balances / reports** — after any data migration, account balances and financial reports must match the SQLite source exactly before go-live.
- **Rollback plan** — keep the SQLite runtime and a PG backup; if cutover fails, revert `DATABASE_URL` to SQLite and restore from backup; never hand-edit accounting tables.

## 6. Do-not-proceed criteria

Stop and remediate if **any** occur during validation:

- **Schema mismatch** — PG schema differs from the SQLite reference.
- **Parity mismatch** — dual-run parity harness diverges between PG and SQLite.
- **Missing indexes / constraints** — any index, unique, or FK absent on PG.
- **Money rounding difference** — any monetary value differs between engines.
- **Report difference** — any financial report/balance differs between engines.
- **Any accounting mismatch** — any divergence in journal entries, balances, or derived accounting outputs.

## No-change decisions (P4.0)

- **No runtime switch; `DATABASE_URL` unchanged (SQLite); no PG migrations against production; models unchanged; `migrate_schema()` retained.**
- **No `Float → Decimal`, no schema/accounting/API/UI change.**
- **Enablement is planned, not executed** — all PG work is test-DB-first and gated on equivalence + parity.

---

*Plan only — no runtime switch, `DATABASE_URL` unchanged (SQLite), no PG migrations against production, models unchanged, Float not converted to Decimal, migrate_schema retained. Safe later enablement: psycopg (psycopg 3) optional driver; test DB only first via `ERP_TEST_POSTGRES_URL` (skip if unset, reject production markers, never use DATABASE_URL); `alembic upgrade head` on an empty PG test DB; prove schema equivalence + dual-run parity green; backup/restore (pg_dump/pg_restore) before any production. Validation sequence: local PG test DB → optional_postgres tests → dual-run parity → inspect schema/indexes/constraints → FastAPI smoke → never touch production first. Known limitations: Float money unchanged, naive datetimes unchanged, LIKE case-sensitivity, SQLite-only code dialect-guarded, performance/index checks later. Production cutover (later): fresh PG DB via Alembic, data migration as a separate project, verify balances/reports, rollback to SQLite + restore. Do-not-proceed on schema mismatch, parity mismatch, missing indexes/constraints, money rounding difference, report difference, or any accounting mismatch.*
