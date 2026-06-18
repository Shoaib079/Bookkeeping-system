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
