# P3.2-C — Optional PostgreSQL Test Fixtures

**Status:** Shipped (test infrastructure only)  
**Mode:** Pytest helpers + documentation. No runtime engine switch.

**Related:** [P3.1 PostgreSQL Compatibility Audit](./P3_1_POSTGRES_COMPATIBILITY_AUDIT.md) · [P3.2 Alembic Introduction Plan](./P3_2_ALEMBIC_INTRODUCTION_PLAN.md) · `tests/postgres_utils.py`

---

## Purpose

Provide **optional** PostgreSQL pytest infrastructure so future dual-engine parity tests can run when a dedicated test database URL is supplied. The default test path remains fast in-memory SQLite; nothing in this slice changes `db.py`, Streamlit, FastAPI, or production `erp_data.db`.

---

## How to set `ERP_TEST_POSTGRES_URL`

Export a PostgreSQL connection URL before running pytest:

```bash
export ERP_TEST_POSTGRES_URL='postgresql://localhost:5432/erp_pytest'
pytest tests/test_p3_2_postgres_fixture.py -m optional_postgres
```

Requirements when using PostgreSQL tests:

- Python driver: `psycopg2-binary` or `psycopg` (not added to default `requirements.txt` — install only on machines that run PG tests)
- A **dedicated** PostgreSQL database created for tests (not `erp_data.db`, not production)

### Local example

```bash
# One-time: create a throwaway test database
createdb erp_pytest

export ERP_TEST_POSTGRES_URL='postgresql://localhost:5432/erp_pytest'
pip install psycopg2-binary   # or: psycopg[binary]

# Optional integration smoke (connect + create/drop ORM tables)
pytest tests/test_p3_2_postgres_fixture.py -m optional_postgres -v
```

Without the env var, PostgreSQL-specific tests **skip cleanly** — CI and local default runs stay SQLite-only.

---

## Safety rules

The validator in `tests/postgres_utils.py` **fails fast** on unsafe URLs:

| Rule | Rationale |
|------|-----------|
| Scheme must be `postgresql` / `postgresql+psycopg2` / `postgresql+psycopg` | No SQLite or other engines |
| Database name required | Prevents accidental default-db connections |
| Database name must include a **test/dev marker** (`_test`, `pytest`, `_dev`, etc.) | Prevents pointing at ambiguous production names |
| Forbidden fragments: `erp_data`, `production`, `prod_db`, `bookkeeping_prod` | Blocks production-like targets |
| Must not reference `erp_data.db` | SQLite production file guard |
| Helpers never read `paths.DATABASE_URL` or `db.engine` | Runtime DB stays isolated |

Schema helpers use `Base.metadata.create_all` / `drop_all` on the **test engine only**. No Alembic `upgrade`, no `migrate_schema()`.

---

## Pytest API

| Symbol | Role |
|--------|------|
| `get_test_postgres_url()` | Read env var; `None` if unset |
| `validate_test_postgres_url(url)` | Safety check; raises `UnsafePostgresTestUrlError` |
| `require_test_postgres_url()` | Validated URL or `pytest.skip` |
| `create_test_postgres_engine()` | Engine after validation (+ driver skip) |
| `create_test_schema` / `drop_test_schema` | ORM table create/drop on test engine |
| `postgres_test_engine()` | Context manager: create → yield → drop → dispose |
| `@pytest.fixture postgres_engine` | Session-scoped engine (skips if unset) |
| `@pytest.fixture postgres_db` | Per-test fresh schema |

Importing `postgres_utils` does **not** connect to PostgreSQL.

---

## CI future plan

| Phase | Action |
|-------|--------|
| **Now (P3.2-C)** | Contract tests always run; PG integration tests marked `optional_postgres` and skip without env |
| **P3.2-E (shipped)** | CI matrix documented — see [P3_2_CI_MATRIX_PLAN.md](./P3_2_CI_MATRIX_PLAN.md) |
| **Next** | Add `.github/workflows/test.yml` per plan outline (owner decision) |
| **Later** | Extend parity harness with more flows on SQLite + PG |

Do **not** add `ERP_TEST_POSTGRES_URL` to default CI until a managed test database is provisioned.

---

## Current limitation: no dual-run parity yet

P3.2-C delivers **fixtures and safety gates only**:

- No dual-run parity harness
- No automatic comparison of SQLite vs PostgreSQL test outcomes
- No Alembic-managed schema on PostgreSQL (still `create_all` from ORM metadata)
- No change to money types (`Float` remains)

Dual-run parity is a follow-up slice — **shipped in P3.2-D**; see [P3_2_DUAL_RUN_PARITY_HARNESS.md](./P3_2_DUAL_RUN_PARITY_HARNESS.md).

---

## Non-goals (P3.2-C)

- Switch runtime database engine
- Modify `db.py` connect listener or `DATABASE_URL`
- Change models, accounting, API, or UI behavior
- Run Alembic migrations in tests
- `Float` → `Decimal` / `NUMERIC` work
- Require PostgreSQL for default `pytest` runs

---

*Test infrastructure only. Production and Streamlit continue to use SQLite via `paths.DATABASE_URL`.*
