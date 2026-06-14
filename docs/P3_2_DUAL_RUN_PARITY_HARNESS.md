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

- Creates an isolated schema via `Base.metadata.create_all` (no Alembic `upgrade`)
- Drops schema after each PostgreSQL run
- Never connects to `db.engine` or `erp_data.db`

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

## Limitations (P3.2-D)

- **No dual-run in production** — test harness only
- **No Alembic-managed schema** on PostgreSQL — `create_all` from ORM metadata (indexes/constraints from `migrate_schema()` not replicated)
- **No `Float` → `Decimal` work** — money remains `Float` on both engines
- **Small flow set** — not exhaustive of all posting families
- **Aggregate comparison** — does not compare every column value or GL account ID mapping across engines
- **Partner/worker `company_id`** — kernel rows may still have NULL `company_id` on movement/bank rows (same on both engines; counted in `company_id_null_counts`)
- **No Streamlit/API path** — calls `services.posting` directly with explicit `company_id` (via `import app` warmup to avoid circular imports)

---

## Future P3.3 / Alembic relationship

When Alembic becomes authoritative (post P3.2 baseline + cutover):

| Today (P3.2-D) | Future (P3.3+) |
|----------------|----------------|
| `Base.metadata.create_all` on both engines | `alembic upgrade head` on ephemeral PG test DB |
| Schema may diverge from long-lived SQLite `migrate_schema()` extras | Single revision chain defines both engines |
| Parity harness compares posting outcomes | Same harness + schema parity pre-check |

P3.2-D intentionally avoids Alembic execution so parity tests do not depend on a revision chain that does not exist yet.

---

## CI future plan

| Job | Scope |
|-----|--------|
| **default** | `pytest` — all SQLite parity tests green |
| **postgres-optional** | Service container + `ERP_TEST_POSTGRES_URL` + `pytest -m optional_postgres` |

---

*Test infrastructure only. Runtime remains SQLite via `paths.DATABASE_URL`.*
