# P4.1 — Local PostgreSQL Validation Guide

**Mode:** Operator documentation + contract test only. **No runtime switch in this slice.**

**Status:** PostgreSQL is **optional and test-only**. SQLite (`erp_data.db` via `DATABASE_URL`) remains the application runtime database. This guide describes how operators validate PostgreSQL locally using a **disposable test database**.

## Scope

| In scope | Out of scope |
|----------|--------------|
| Local disposable PG test DB | Changing `DATABASE_URL` |
| `ERP_TEST_POSTGRES_URL` only | Switching app runtime to PostgreSQL |
| `optional_postgres` pytest marker | Touching production DB |
| Dual-run parity validation | Running migrations against production |
| Full SQLite suite (unchanged) | Model changes or `Float` → `Decimal` |

## Prerequisites

- PostgreSQL server installed and running locally (e.g. Homebrew, Postgres.app, Docker).
- Python environment with project dependencies installed.
- **Driver (optional):**

```bash
pip install psycopg
```

`psycopg` (psycopg 3) is an **optional** dependency. SQLite-only installs do not require it.

## Step 1 — Create a disposable test database

Use a database name that includes a test marker (required by the safety validator). Example:

```bash
createdb erp_pytest
```

**Never** use `erp_data`, `production`, or other production-like names for PostgreSQL validation.

## Step 2 — Set the test URL (not `DATABASE_URL`)

Export the test URL **only** for the current shell session:

```bash
export ERP_TEST_POSTGRES_URL='postgresql+psycopg://localhost/erp_pytest'
```

Rules:

- **`DATABASE_URL` is unchanged** — the app continues to use `sqlite:///…/erp_data.db`.
- **`ERP_TEST_POSTGRES_URL` only** — PostgreSQL tests read this env var; if unset, PG tests **skip**.
- **Production markers rejected** — URLs pointing at `erp_data`, `production`, `prod`, or similar are rejected by `tests/postgres_utils.py`.

## Step 3 — Run optional PostgreSQL tests

```bash
pytest -m optional_postgres
```

Tests marked `@pytest.mark.optional_postgres` connect only when `ERP_TEST_POSTGRES_URL` is set and passes validation. Without the env var, they skip safely.

## Step 4 — Run dual-run parity

Compare SQLite vs. PostgreSQL posting/void/allocation behavior:

```bash
pytest tests/test_p3_2_dual_run_parity.py -m optional_postgres -v
```

See also [P3_2_DUAL_RUN_PARITY_HARNESS.md](./P3_2_DUAL_RUN_PARITY_HARNESS.md).

## Step 5 — Run the full SQLite suite separately

PostgreSQL validation does **not** replace the main test run. Always run the full SQLite suite with no PG env var (or in a clean shell):

```bash
unset ERP_TEST_POSTGRES_URL
pytest
```

The default CI path runs all non-optional tests; `optional_postgres` tests skip when the URL is unset.

## Safety rules

1. **Never use a production DB URL** for `ERP_TEST_POSTGRES_URL`.
2. **`ERP_TEST_POSTGRES_URL` only** — never point PG tests at `DATABASE_URL` / `erp_data.db`.
3. **`DATABASE_URL` unchanged** — do not export a PostgreSQL URL as the app database.
4. **Production markers rejected** — the safety validator in `tests/postgres_utils.py` rejects forbidden database name fragments and requires test/dev markers (`pytest`, `_test`, `_dev`, etc.).
5. **No runtime switch** — `streamlit run app.py` and production startup remain on SQLite.

## Success criteria

Local PostgreSQL validation is **green** when all of the following hold:

- **Optional PG tests green** — `pytest -m optional_postgres` passes with no skips due to connection failures.
- **Dual-run parity green** — `pytest tests/test_p3_2_dual_run_parity.py -m optional_postgres -v` passes.
- **No accounting mismatch** — parity harness reports identical balances and journal arithmetic vs. SQLite.
- **No schema mismatch** — Alembic-built PG schema matches the SQLite reference (tables, indexes, constraints); see P3.4 equivalence harness.
- **Full SQLite suite green** — `pytest` (without `ERP_TEST_POSTGRES_URL`) remains green.

If any criterion fails, **do not proceed** toward production PostgreSQL. See [P4_0_POSTGRES_ENABLEMENT_PLAN.md](./P4_0_POSTGRES_ENABLEMENT_PLAN.md).

## Troubleshooting

### Missing driver

**Symptom:** `ModuleNotFoundError: No module named 'psycopg'` (or similar).

**Fix:**

```bash
pip install psycopg
```

Use a URL scheme the driver supports: `postgresql+psycopg://…`.

### Database does not exist

**Symptom:** `FATAL: database "erp_pytest" does not exist`.

**Fix:**

```bash
createdb erp_pytest
```

Confirm the database name in `ERP_TEST_POSTGRES_URL` matches the created DB.

### Connection refused

**Symptom:** `connection refused`, `could not connect to server`, or timeout.

**Fix:**

- Start PostgreSQL (`brew services start postgresql`, Postgres.app, or your container).
- Verify host/port in the URL (default `localhost:5432`).
- Check `pg_isready` or `psql -l` before re-running tests.

### URL rejected by safety validator

**Symptom:** `UnsafePostgresTestUrlError` — forbidden fragment, missing test marker, or SQLite URL.

**Fix:**

- Use a disposable name with a test marker, e.g. `erp_pytest` (contains `pytest`).
- Do **not** use `erp_data`, `production`, or `prod` in the database name.
- Use a PostgreSQL scheme (`postgresql+psycopg://…`), not `sqlite://`.
- Set `ERP_TEST_POSTGRES_URL`, not `DATABASE_URL`.

Example valid URL:

```bash
export ERP_TEST_POSTGRES_URL='postgresql+psycopg://localhost/erp_pytest'
```

## Related documents

- [P3_2_POSTGRES_TEST_FIXTURES.md](./P3_2_POSTGRES_TEST_FIXTURES.md) — fixture helpers and env var
- [P3_2_DUAL_RUN_PARITY_HARNESS.md](./P3_2_DUAL_RUN_PARITY_HARNESS.md) — parity harness details
- [P4_0_POSTGRES_ENABLEMENT_PLAN.md](./P4_0_POSTGRES_ENABLEMENT_PLAN.md) — production enablement plan (later)

---

*Operator guide only — no runtime switch, `DATABASE_URL` unchanged, SQLite remains runtime DB. Validate locally via `ERP_TEST_POSTGRES_URL` + `optional_postgres` + dual-run parity; full SQLite suite runs separately.*
