# Staging operator environment templates

**Not for production.** Copy to your staging shell or deployment secrets manager.

| File | Purpose |
|------|---------|
| `frontend.env.example` | Vite build-time React feature flags |
| `api.env.example` | FastAPI server env (write gates, commit modes) |

## OR-01 — React read pages (staging)

```bash
# Frontend dev/build (from repo root)
set -a && source config/staging/frontend.env.example && set +a
cd frontend && npm run dev
```

Requires FastAPI read API running with valid JWT + `X-Company-Id`. Streamlit remains primary.

## Rules

- Never commit real `.env` files with secrets.
- Never point `ERP_TEST_POSTGRES_URL` at production databases.
- Never set `COMMIT_MODE_*=boundary` in production without operator sign-off.
- `DATABASE_URL` for the app stays SQLite on staging unless explicitly approved for PG runtime.

See `docs/OPERATOR_ROLLOUT_OR01_REACT_READ_STAGING.md` and `registry/operator_rollout_contract.py`.

## OR-02 — PostgreSQL boundary matrix

```bash
set -a && source config/staging/postgres.env.example && set +a
pytest tests/test_fastapi_react_07_pg_boundary_matrix.py \
  tests/test_production_hardening_01_ph03_pg_matrix_execution.py \
  -m optional_postgres -q
```

See `docs/OPERATOR_ROLLOUT_OR02_PG_MATRIX_STAGING.md`.

## OR-03 — API write sales (staging)

```bash
set -a && source config/staging/frontend.env.example && set +a
set -a && source config/staging/api.env.example && set +a
```

See `docs/OPERATOR_ROLLOUT_OR03_API_WRITE_SALES_STAGING.md`.

## OR-04 — COMMIT_MODE cash sale boundary (staging)

`config/staging/api.env.example` sets `COMMIT_MODE_POST_CASH_SALE=boundary` (tier 1 per PH-04).

```bash
set -a && source config/staging/api.env.example && set +a
pytest tests/test_fastapi_p0_commit_ownership_cash_sale.py -q
```

See `docs/OPERATOR_ROLLOUT_OR04_COMMIT_MODE_CASH_SALE_STAGING.md`.

## OR-05 — COMMIT_MODE expense boundary (staging)

Adds `COMMIT_MODE_POST_EXPENSE=boundary` (tier 2; cumulative with OR-04).

See `docs/OPERATOR_ROLLOUT_OR05_COMMIT_MODE_EXPENSE_STAGING.md`.

## OR-06–OR11 — COMMIT_MODE tiers 3–8 (staging)

Full cumulative `COMMIT_MODE_*=boundary` template (14 families) in `config/staging/api.env.example`.

Final slice: [OPERATOR_ROLLOUT_OR11_COMMIT_MODE_VOID_STAGING.md](./docs/OPERATOR_ROLLOUT_OR11_COMMIT_MODE_VOID_STAGING.md)

**Production:** requires operator sign-off — do not copy staging env to production.
