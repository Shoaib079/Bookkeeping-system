# P3.2-D — SQLite / PostgreSQL Dual-Run Parity Harness

**Status:** Shipped (test infrastructure only)  
**Mode:** Reusable pytest harness + small golden parity flows. No runtime engine switch.

**Related:** [P3.2 PostgreSQL Test Fixtures](./P3_2_POSTGRES_TEST_FIXTURES.md) · [P3.2 Alembic Introduction Plan](./P3_2_ALEMBIC_INTRODUCTION_PLAN.md) · `tests/p3_dual_run_utils.py`

---

## Purpose

Provide a **reusable dual-run parity harness** that executes the same business flow on:

1. **SQLite** (in-memory, always) — default fast path
2. **PostgreSQL** (optional) — when `ERP_TEST_POSTGRES_URL` is set

After each run, the harness builds a **normalized persisted-state summary** and compares SQLite vs PostgreSQL outcomes. This is the foundation for future broader portability confidence (P3.1 § dual-run recommendation) without switching the production runtime database.

Golden flows in P3.2-D:

| Flow | Service path |
|------|----------------|
| Cash sale | `posting.post_cash_sale` |
| Expense | `posting.post_expense` |
| Credit purchase + payable | `posting.post_purchase` + `Payable` row |
| Receivable payment | `post_credit_sale` + `post_receivable_payment` |
| Partner capital contribution | `posting.post_partner_movement` |
| Worker advance | `posting.post_worker_movement` |

---

## What is compared

Summaries are **engine-neutral aggregates** (not raw auto-increment IDs):

| Field | Content |
|-------|---------|
| `counts` | Row counts per watched table |
| `journal` | JE count, line count, debit/credit totals, balanced flag, `reference_type` histogram |
| `reports` | P&L net / totals + balance sheet assets / balanced flag |
| `audit_count` | Total `audit_logs` rows |
| `void_counts` | Voided rows per entity family |
| `company_id_null_counts` | NULL `company_id` rows on key business tables |

PostgreSQL parity passes when `sqlite_summary == postgres_summary` for the same flow.

---

## How to run SQLite-only

Default CI and local runs — no PostgreSQL required:

```bash
cd streamlit_accounting_erp
pytest tests/test_p3_2_dual_run_parity.py -v
```

Or run the full suite (SQLite parity tests always execute):

```bash
pytest
```

Programmatic use:

```python
from p3_dual_run_utils import run_parity_flow_sqlite, flow_cash_sale, DEFAULT_TABLES

summary = run_parity_flow_sqlite(flow_cash_sale, tables=DEFAULT_TABLES)
assert summary["journal"]["balanced"]
```

---

## How to run with PostgreSQL

Requires a dedicated test database and driver (`psycopg2-binary` or `psycopg`):

```bash
createdb erp_pytest
export ERP_TEST_POSTGRES_URL='postgresql://localhost:5432/erp_pytest'
pip install psycopg2-binary

pytest tests/test_p3_2_dual_run_parity.py -m optional_postgres -v
```

Safety rules for the URL are enforced by `tests/postgres_utils.py` (test/dev DB name markers; rejects `erp_data`, production names, SQLite URLs).

The harness:

- Resets disposable PostgreSQL via `drop_all_pg_objects` + **`alembic upgrade head`** (revision `0002`, Numeric money)
- Drops schema after each PostgreSQL run
- Never connects to `db.engine` or `erp_data.db`

SQLite path remains **in-memory `create_all`** for fast CI; PostgreSQL uses the Alembic build path operators will use at cutover.

---

## API overview

| Symbol | Role |
|--------|------|
| `seed_parity_tenant(session)` | Company + COA + bank account |
| `run_parity_flow_sqlite(flow, tables=...)` | Isolated in-memory SQLite run → summary |
| `run_parity_flow_postgres(flow, tables=..., url=...)` | Isolated PG run → summary |
| `dual_engine_parity(flow, tables=...)` | SQLite + optional PG with assert equality |
| `normalized_parity_summary(session, tables=...)` | Build comparison dict |
| `PARITY_FLOWS` | Named golden flow registry |

---

## Limitations (updated 2026-06-16)

- **No dual-run in production** — test harness only
- **SQLite** — in-memory ORM `create_all` (fast reference path)
- **PostgreSQL** — Alembic `upgrade head` incl. `0002` (see [POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md](./POSTGRES_PG_BUILD_DUAL_RUN_PARITY.md))
- **Small flow set** — not exhaustive of all posting families
- **Aggregate comparison** — does not compare every column value or GL account ID mapping across engines
- **Partner/worker `company_id`** — kernel rows may still have NULL `company_id` on movement/bank rows (same on both engines; counted in `company_id_null_counts`)
- **No Streamlit/API path** — calls `services.posting` directly with explicit `company_id` (via `import app` warmup to avoid circular imports)

---

## Alembic relationship (P3.3+)

| SQLite (CI default) | PostgreSQL (optional) |
|---------------------|------------------------|
| In-memory `create_all` | `bootstrap_postgres_via_alembic` → `alembic upgrade head` |
| Fast local/CI path | Validates operator PG build path incl. Numeric `0002` |
| Parity harness compares posting + report outcomes | Same harness + schema revision check |

---

## CI future plan

Documented in **[P3_2_CI_MATRIX_PLAN.md](./P3_2_CI_MATRIX_PLAN.md)** (P3.2-E).

| Job | Scope |
|-----|--------|
| **default** | `pytest` — all SQLite parity tests green |
| **postgres-optional** | Service container + `ERP_TEST_POSTGRES_URL` + `pytest -m optional_postgres` |

---

*Test infrastructure only. Runtime remains SQLite via `paths.DATABASE_URL`.*
