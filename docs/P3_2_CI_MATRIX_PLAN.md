# P3.2-E — CI Matrix Plan

**Status:** Plan only (documentation + contract tests)  
**Mode:** No GitHub Actions workflow in this slice. No runtime or test-behavior change.

**Related:** [P3.2 PostgreSQL Test Fixtures](./P3_2_POSTGRES_TEST_FIXTURES.md) · [P3.2 Dual-Run Parity Harness](./P3_2_DUAL_RUN_PARITY_HARNESS.md) · `pytest.ini` · `tests/postgres_utils.py`

---

## Purpose

Document the **future CI strategy** for this ERP test suite:

- **SQLite remains the default** — fast, no external services, matches production runtime today
- **PostgreSQL remains optional** — parity confidence when `ERP_TEST_POSTGRES_URL` is provisioned
- **Clear job split** — default job runs full SQLite path; optional job runs `optional_postgres` tests only

P3.2-E does **not** add `.github/workflows` yet. It defines the contract so a later slice can wire GitHub Actions without redesign.

---

## Current local test behavior

| Command | Behavior |
|---------|----------|
| `pytest` | Full suite; in-memory / isolated SQLite fixtures; **no PostgreSQL required** |
| `pytest tests/test_p3_2_dual_run_parity.py` | SQLite parity tests run; PG tests **skip** without env |
| `pytest -m optional_postgres` | Only tests marked `optional_postgres`; **skip** if `ERP_TEST_POSTGRES_URL` unset |
| `pytest -m "not optional_postgres"` | Everything except optional PG integration (future CI default filter) |

No local developer needs PostgreSQL installed for a green default run.

---

## SQLite default CI job

**Job name (proposed):** `test-sqlite`

| Aspect | Plan |
|--------|------|
| **Trigger** | Every push / PR to `main` (and feature branches) |
| **Runner** | `ubuntu-latest` (or equivalent) |
| **Services** | None |
| **Env** | Do **not** set `ERP_TEST_POSTGRES_URL` |
| **Install** | `pip install -r requirements.txt` |
| **Command** | `pytest` (or `pytest -m "not optional_postgres"` once PG job exists) |
| **Expectation** | All non-optional tests pass; `optional_postgres` tests **skip** |

This job is the **merge gate**. It mirrors today’s local default.

### Tests in the SQLite job

- Entire suite **except** tests that require a live PostgreSQL connection
- Includes all P3.2 contract tests (`test_p3_2_alembic_intro.py`, `test_p3_2_sqlite_dialect_guards.py`, `test_p3_2_postgres_fixture.py` validator tests, `test_p3_2_dual_run_parity.py` SQLite paths, `test_p3_2_ci_matrix_plan.py`)
- Dual-run harness: `test_sqlite_*` parametrized flows — **always run**

---

## Optional PostgreSQL CI job

**Job name (proposed):** `test-postgres-optional`

| Aspect | Plan |
|--------|------|
| **Trigger** | Same as SQLite job, or nightly / manual `workflow_dispatch` initially |
| **Runner** | `ubuntu-latest` |
| **Services** | `postgres:16` (or managed ephemeral DB) with database name containing a **test marker** (e.g. `erp_pytest`) |
| **Env** | `ERP_TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/erp_pytest` (example only) |
| **Extra install** | `psycopg2-binary` or `psycopg` (not in default `requirements.txt`) |
| **Command** | `pytest -m optional_postgres -v` |
| **Expectation** | PG integration + dual-run parity assertions pass |

This job is **informational or non-blocking** until exit criteria below are met.

### Tests in the PostgreSQL job

| Test module | What runs |
|-------------|-----------|
| `tests/test_p3_2_postgres_fixture.py` | `@pytest.mark.optional_postgres` integration smoke |
| `tests/test_p3_2_dual_run_parity.py` | `test_sqlite_postgres_parity_matches` (per flow) |
| Future parity tests | Same marker pattern |

Validator-only tests (URL safety, doc contracts) stay in the **SQLite job** — they do not need a running server.

---

## Required env vars

| Variable | SQLite job | PostgreSQL job |
|----------|------------|----------------|
| `ERP_TEST_POSTGRES_URL` | **Unset** | **Required** — validated test/dev URL |
| `ERP_JWT_SECRET` / test secrets | As needed by FastAPI tests | Same |
| `ERP_DEV_MODE` | Default off in CI | Default off |

No other PostgreSQL-specific env vars are required for P3.2.

---

## Safety rules for `ERP_TEST_POSTGRES_URL`

Enforced by `tests/postgres_utils.py` (`validate_test_postgres_url`):

- PostgreSQL scheme only (`postgresql`, `postgresql+psycopg2`, `postgresql+psycopg`)
- Database name must include a test/dev marker (`_test`, `pytest`, `_dev`, etc.)
- Forbidden fragments: `erp_data`, `production`, `prod_db`, `bookkeeping_prod`
- Must not reference `erp_data.db`
- Helpers never read `paths.DATABASE_URL` or `db.engine`

CI must use a **throwaway database** created for the job, not a shared production or staging instance.

---

## How the `optional_postgres` marker works

Registered in `pytest.ini`:

```ini
markers =
    optional_postgres: PostgreSQL integration tests; require ERP_TEST_POSTGRES_URL
```

**Contract:**

1. Tests decorated with `@pytest.mark.optional_postgres` call `get_test_postgres_url()` or helpers that skip when unset
2. Default `pytest` run: these tests skip cleanly (no failure, no connection attempt)
3. PG CI job: set env, run `pytest -m optional_postgres`
4. Importing `postgres_utils` or `p3_dual_run_utils` does **not** connect to PostgreSQL

---

## Future GitHub Actions outline

**Not implemented in P3.2-E.** Proposed skeleton for a later slice:

```yaml
# .github/workflows/test.yml  (FUTURE — not added in P3.2-E)
name: Test

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test-sqlite:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -r requirements.txt
      - run: pytest -m "not optional_postgres"

  test-postgres-optional:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: erp_pytest
        ports:
          - 5432:5432
    env:
      ERP_TEST_POSTGRES_URL: postgresql://postgres:postgres@localhost:5432/erp_pytest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install -r requirements.txt psycopg2-binary
      - run: pytest -m optional_postgres -v
```

Owner decision required before adding this file.

---

## Why PostgreSQL remains optional for now

| Reason | Detail |
|--------|--------|
| **Production runtime** | Streamlit + FastAPI still use SQLite (`paths.DATABASE_URL`) |
| **Schema parity gap** | PG tests use `create_all`; production SQLite uses `migrate_schema()` extras |
| **No Alembic head yet** | Revision chain not authoritative — PG job would not reflect production DDL evolution |
| **CI cost / complexity** | Service container, driver install, and flake surface not justified until engine cutover nears |
| **Developer ergonomics** | Default clone + `pytest` must stay one-command green |
| **Float money** | Engine swap preserves `Float` semantics; no mandatory PG gate until portability blockers shrink |

---

## Exit criteria before making PostgreSQL mandatory

PostgreSQL should become a **required** CI check (blocking merge) only when **all** of the following are true:

1. **Alembic baseline shipped** — known head; test DB created via `alembic upgrade head` (or documented equivalent)
2. **`migrate_schema()` cutover plan executed** or PG schema proven equivalent for test purposes
3. **Dual-run parity green** — all `PARITY_FLOWS` pass SQLite == PostgreSQL on CI for N consecutive weeks
4. **Engine cutover decision** — owner approves PostgreSQL as staging/production target
5. **Managed test DB** — ephemeral per-job DB with safety validator enforced in CI config review
6. **Flake budget** — PG job stable; no driver/service startup failures blocking merges
7. **Documented rollback** — failed PG parity has a clear owner and triage path

Until then: SQLite job = **required**; PostgreSQL job = **optional / non-blocking**.

---

## P3.2-E deliverables

| Deliverable | Location |
|-------------|----------|
| CI matrix plan | This document |
| Contract tests | `tests/test_p3_2_ci_matrix_plan.py` |
| GitHub Actions workflow | **Deferred** — outline only above |

---

## Cross-links (P3.2 test infrastructure)

| Slice | Doc |
|-------|-----|
| P3.2-C | [P3_2_POSTGRES_TEST_FIXTURES.md](./P3_2_POSTGRES_TEST_FIXTURES.md) |
| P3.2-D | [P3_2_DUAL_RUN_PARITY_HARNESS.md](./P3_2_DUAL_RUN_PARITY_HARNESS.md) |
| P3.2-E | This document |

---

*Plan only. No workflow file added. SQLite default unchanged. PostgreSQL optional.*
