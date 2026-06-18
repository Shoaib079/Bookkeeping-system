# OPERATOR-ROLLOUT-OR01 — React Read Pages Staging Enable

**Mode:** Staging operator config + gate tests. **No accounting / GL / posting behavior change.**

**Date:** 2026-06-05  
**Authority:** First stage of Operator Rollout Readiness Audit staging sequence.  
**Tag:** `operator-rollout-or01-react-read-staging`

**Prerequisites:** PRODUCTION-HARDENING-01 complete · FASTAPI-REACT-06–50 read pages shipped

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Staging frontend env template (`VITE_ERP_REACT_PAGES=1`) | ✅ `config/staging/frontend.env.example` |
| Operator rollout contract | ✅ `registry/operator_rollout_contract.py` |
| React read gate tests | ✅ `tests/test_operator_rollout_or01_react_read_staging.py` |
| Full SQLite pytest suite | ✅ Required gate |
| Production flag flip | ⬜ **Not in this slice** — staging template only |

**Posting / GL behavior:** **UNCHANGED** — read-only React pages; no write flags enabled.

---

## 2. Staging enablement

| Env var | Value | Effect |
|---------|-------|--------|
| `VITE_ERP_REACT_PAGES` | `1` | 42 read routes render real pages instead of `PlaceholderPage` |

**Operator steps:**

```bash
set -a && source config/staging/frontend.env.example && set +a
cd frontend && npm run dev
```

FastAPI read API must be running. Streamlit remains primary UI for operators.

---

## 3. Gate verification

```bash
pytest tests/test_operator_rollout_or01_react_read_staging.py -q
pytest tests/test_fastapi_react_06_react_pages.py -q
pytest tests/ -q
```

---

## 4. What must NOT change (verified)

- Default commit mode (`internal`)
- Journal math and GL pairs
- `ERP_API_WRITE_*` flags (off)
- `COMMIT_MODE_*` env (unset)
- Streamlit primary UI
- Frozen `FRxx_DEFERRED_ITEMS` blocks

---

## 5. Deferred (next stage)

| Item | Notes |
|------|-------|
| **OPERATOR-ROLLOUT-OR02** | PG matrix on disposable test DB |
| **production operator sign-off** | Human gate before production |
| **production COMMIT_MODE_* flip** | Not in OR-01 — staging read only |

---

## 6. Test plan

```bash
pytest tests/test_operator_rollout_or01_react_read_staging.py -q
pytest tests/ -q
```

**Next:** **OPERATOR-ROLLOUT-OR02** — PostgreSQL boundary matrix on staging.
