# P3.2-A — Alembic Introduction + Migration Boundary Plan

**Status:** Scaffold only (2026-06-05)  
**Mode:** Scaffolding + documentation + lightweight contract tests. No runtime behavior change.

**Related:** [P3.1 PostgreSQL Compatibility Audit](./P3_1_POSTGRES_COMPATIBILITY_AUDIT.md) · [ROADMAP § ALEMBIC-01](../ROADMAP.md#alembic-01) · [TECH_DEBT § ALEMBIC-01](./TECH_DEBT_AND_MIGRATION_CLEANUP.md)

---

## Purpose

Introduce [Alembic](https://alembic.sqlalchemy.org/) as the **future** schema-migration authority for this ERP while keeping today's SQLite runtime **unchanged**.

P3.1 identified the SQLite-specific schema-evolution layer (`migrate_schema`, `PRAGMA table_info`, raw `sqlite3` table rebuild, `sqlite_master`, partial indexes with `is_void = 0`) as the **highest portability blocker** for PostgreSQL. Alembic is the planned replacement: versioned, reviewable DDL in `alembic/versions/` instead of silent `ALTER TABLE` attempts on every Streamlit startup.

This slice adds only:

- `alembic` dependency
- `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, empty `alembic/versions/`
- `env.py` wired to `db.Base.metadata` (all models registered via `import models`)
- This plan document and contract tests

No revision scripts, no `alembic upgrade`, no cutover from `migrate_schema()`.

---

## Non-goals (P3.2-A)

| Excluded | Reason |
|----------|--------|
| Switch database engine (SQLite → PostgreSQL) | Engine swap is a later phase; needs Alembic + dialect guards first |
| Run migrations against production or shared `erp_data.db` | Risk of accidental schema drift before baseline is characterized |
| Change `models.py` | Schema definition stays identical; migrations come later |
| Change accounting, FastAPI, or Streamlit behavior | P3.2-A is infrastructure scaffolding only |
| Remove `migrate_schema()` or `MigrationFlag` | Current path remains authoritative until explicit cutover |
| Convert `Float` → `Decimal` / `NUMERIC` | Separate accounting-sensitive project (MONEY-DECIMAL-01 / P3.2-F) |
| Add PostgreSQL test fixtures | Shipped in **P3.2-C** — see [P3_2_POSTGRES_TEST_FIXTURES.md](./P3_2_POSTGRES_TEST_FIXTURES.md) |
| Autogenerate or hand-write real DDL revisions | Baseline snapshot must be planned in P3.2-B+ |

---

## Current SQLite migration helpers remain active

**Authoritative today:** `app.migrate_schema(session)` runs on every Streamlit startup inside `main()` → `get_session()`.

That function:

- Issues incremental `ALTER TABLE ADD COLUMN` (idempotent via try/rollback)
- Creates indexes with `CREATE INDEX IF NOT EXISTS`
- Uses SQLite-only primitives (`PRAGMA table_info`, raw `sqlite3` rebuild, `sqlite_master`)
- Guards one-time data migrations via `MigrationFlag`

**Nothing in P3.2-A disables or replaces this path.** Fresh installs and daily Streamlit use continue to rely on `migrate_schema()` + `Base.metadata.create_all` patterns exactly as before.

---

## Alembic is introduced but not authoritative yet

| Layer | P3.2-A state |
|-------|----------------|
| `alembic.ini` + `alembic/env.py` | Present; `target_metadata = Base.metadata` |
| `alembic/versions/` | Empty (`.gitkeep` only) — **no revision chain** |
| CI / startup hooks | **Do not** call `alembic upgrade head` |
| Developers | May inspect config and `env.py`; must not treat Alembic as source of truth until cutover |

Alembic becomes authoritative only after a future slice:

1. Baseline revision capturing current schema (or stamped head matching live DB)
2. New DDL only via new revisions
3. `migrate_schema()` reduced to no-op / removed behind a feature flag
4. Deployment runbook updated

Until then, Alembic is **documentation + tooling readiness**, not runtime.

---

## Future cutover plan

Recommended sequence (aligned with P3.1 § Recommended P3.2 tasks):

| Phase | Task | Scope |
|-------|------|--------|
| **P3.2-A** (this slice) | Alembic scaffold + boundary plan | No revisions, no upgrade |
| **P3.2-B** | Engine dialect guard | ✅ **Shipped** — `db.py` connect listener runs `PRAGMA foreign_keys=ON` only when `dialect.name == "sqlite"`; see `tests/test_p3_2_sqlite_dialect_guards.py` |
| **P3.2-C** | PG optional test fixtures | ✅ **Shipped** — `ERP_TEST_POSTGRES_URL` + `tests/postgres_utils.py`; see [P3_2_POSTGRES_TEST_FIXTURES.md](./P3_2_POSTGRES_TEST_FIXTURES.md) |
| **P3.2-D** | Baseline revision strategy | Decide: stamp existing DB vs. autogenerate from metadata vs. hand-written baseline |
| **P3.2-F** | Dual-run parity harness | ✅ **Shipped** — `tests/p3_dual_run_utils.py`; see [P3_2_DUAL_RUN_PARITY_HARNESS.md](./P3_2_DUAL_RUN_PARITY_HARNESS.md) |
| **P3.2-E** | CI matrix plan | ✅ **Shipped** — [P3_2_CI_MATRIX_PLAN.md](./P3_2_CI_MATRIX_PLAN.md); workflow deferred |
| **P3.2-G** (separate) | `Float` → `NUMERIC` | Characterized rounding project — not bundled with engine swap |

**Cutover gate (owner decision):**

- All environments have a known Alembic head
- `pytest` green on SQLite with Alembic-managed test DBs (optional path)
- Streamlit startup no longer depends on silent `ALTER TABLE` for new columns
- Rollback runbook tested on a copy of production data

---

## Rules for creating migrations (future)

When P3.2-C+ begins adding revisions:

1. **One concern per revision** — additive column, index, or table rebuild; avoid kitchen-sink migrations.
2. **Idempotent thinking** — prefer explicit `op.add_column` / `op.create_index` over SQLite-only `IF NOT EXISTS` strings unless dialect branches are documented.
3. **Dual-dialect review** — any raw SQL must be checked for PostgreSQL (partial indexes: `is_void IS FALSE`, not `is_void = 0`).
4. **No data migrations in DDL revisions** — use separate revisions with `op.execute` and `MigrationFlag`-style guards if one-time backfills are needed.
5. **No accounting logic** — migrations change schema only; posting rules stay in `services/posting.py` / kernels.
6. **Review + test** — every revision gets a downgrade (or documented irreversibility) and a contract or integration test where feasible.
7. **Never autogenerate against production** — use dev DB or metadata diff from a controlled snapshot.
8. **Batch mode** — `env.py` sets `render_as_batch=True` for SQLite `ALTER` limitations; verify PG path does not rely on batch-only workarounds incorrectly.

---

## Rollback strategy

| Situation | Action |
|-----------|--------|
| Revision not yet deployed | Delete or fix branch before merge; no DB impact |
| Revision deployed to dev only | `alembic downgrade -1` (if downgrade implemented) or restore DB backup |
| Revision deployed to production | **Prefer forward-fix revision** over downgrade in production; downgrades are for dev/staging |
| Failed mid-migration | Alembic transaction wraps online migration; investigate partial state; restore from backup if needed |
| Cutover from `migrate_schema()` | Keep `migrate_schema()` as no-op shim until all environments report same Alembic head; rollback = redeploy previous app version + downgrade Alembic if safe |

**P3.2-A rollback:** remove `alembic/` tree and `alembic` dependency — zero runtime effect because nothing invokes Alembic yet.

---

## How this affects local Streamlit use

**No change in P3.2-A.**

- `streamlit run app.py` still opens `erp_data.db` via `paths.DATABASE_URL`
- Startup still runs `migrate_schema()` inside the session context
- Developers do **not** need to run `alembic upgrade` before using the app
- Installing `alembic` adds a dependency only; it is not invoked by the app

Optional developer commands (manual, dev DB copy only — **not** against production `erp_data.db`):

```bash
# Inspect config (safe — no DB writes; use the alembic CLI, not bare import alembic)
alembic -c alembic.ini history

# Future only, after revisions exist:
# alembic -c alembic.ini current
# alembic -c alembic.ini upgrade head   # dev copy only
```

**Note:** The project directory contains an `alembic/` migration tree. From the repo root, bare `import alembic` in Python can resolve to that folder instead of the pip package. Use the **`alembic` CLI** or load `alembic.config` from site-packages (as the contract test does). The Alembic CLI sets up `sys.path` correctly via `prepend_sys_path = .` in `alembic.ini`.

---

## How this affects FastAPI tests

**No change in P3.2-A.**

- FastAPI tests continue to use in-memory SQLite (`sqlite://` + `StaticPool`) fixtures
- Schema is created via `Base.metadata.create_all` and/or test helpers — **not** Alembic
- No test calls `alembic upgrade head`
- Contract tests in `tests/test_p3_2_alembic_intro.py` verify scaffold files and doc sections only

When Alembic is authoritative (future):

- Add optional fixture: `alembic upgrade head` on ephemeral DB before tests
- Keep default fast path as `create_all` until dual-path parity is proven
- API behavior remains unchanged — only schema creation mechanism differs

---

## Why Float → Decimal is deferred

P3.1 concluded that a raw SQLite → PostgreSQL engine swap **preserves accounting arithmetic** while money columns remain SQLAlchemy `Float` (IEEE-754 double). Moving to `NUMERIC`/`Decimal`:

- Changes rounding and accumulation semantics
- Requires golden-value characterization against existing posting tests
- Is tracked as **MONEY-DECIMAL-01** / **P3.2-F** — intentionally **not** bundled with Alembic introduction or engine cutover

Alembic migrations for a future `Float` → `NUMERIC` conversion would be a **dedicated, characterized revision series**, separate from P3.2-A scaffolding.

---

## P3.2-A deliverables checklist

| Deliverable | Location |
|-------------|----------|
| Dependency | `requirements.txt` → `alembic` |
| Config | `alembic.ini` |
| Environment | `alembic/env.py` → `db.Base.metadata` |
| Template | `alembic/script.py.mako` |
| Versions dir | `alembic/versions/.gitkeep` (no `.py` revisions) |
| Plan | This document |
| Contract tests | `tests/test_p3_2_alembic_intro.py` |

---

*Scaffolding only. SQLite runtime unchanged. `migrate_schema()` remains authoritative. Alembic is not invoked in app startup, CI upgrade steps, or production.*
