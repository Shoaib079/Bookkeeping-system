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
