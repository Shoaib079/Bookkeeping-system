# OPERATOR-ROLLOUT-OR03 — API Write Sales Staging Enable

**Mode:** Staging operator config + gate tests. **No accounting / GL / posting behavior change.**

**Date:** 2026-06-05  
**Authority:** Third stage of Operator Rollout Readiness Audit staging sequence.  
**Tag:** `operator-rollout-or03-api-write-sales-staging`

**Prerequisites:** [OR-02](./OPERATOR_ROLLOUT_OR02_PG_MATRIX_STAGING.md) · [FR-08](./FASTAPI_REACT_08_REACT_WRITE_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Staging API write gate (`ERP_API_WRITE_SALES=1`) | ✅ `config/staging/api.env.example` |
| Staging React write tab (`VITE_ERP_REACT_WRITE_SALES=1`) | ✅ `config/staging/frontend.env.example` |
| P2 sales write gate tests | ✅ `test_fastapi_p2_sales_write.py` |
| React write gate tests | ✅ `test_fastapi_react_08_react_write.py` |
| `COMMIT_MODE_*` flip | ⬜ **Not in this slice** — default `internal` |
| Production flag flip | ⬜ **Not in this slice** |

**Posting / GL behavior:** **UNCHANGED** — staging templates only; default commit mode remains `internal`.

---

## 2. Staging enablement

| Env var | Value | Effect |
|---------|-------|--------|
| `VITE_ERP_REACT_PAGES` | `1` | (OR-01) Read shell + pages |
| `VITE_ERP_REACT_WRITE_SALES` | `1` | Cash sale tab on `/transactions/new` |
| `ERP_API_WRITE_SALES` | `1` | `POST /api/v1/sales` returns 201 (not 404) |

**Operator steps:**

```bash
set -a && source config/staging/frontend.env.example && set +a
set -a && source config/staging/api.env.example && set +a
cd frontend && npm run dev
# separate shell:
uvicorn api.main:create_app --factory --reload
```

---

## 3. Gate verification

```bash
pytest tests/test_operator_rollout_or03_api_write_sales_staging.py -q
pytest tests/test_fastapi_p2_sales_write.py -q
pytest tests/test_fastapi_react_08_react_write.py -q
unset ERP_TEST_POSTGRES_URL
pytest tests/ -q
```

---

## 4. What must NOT change (verified)

- Default commit mode (`internal`)
- Journal math and GL pairs
- Other `ERP_API_WRITE_*` / `VITE_ERP_REACT_WRITE_*` families (off in staging template)
- Streamlit primary UI
- Production env

---

## 5. Deferred (next stage)

| Item | Notes |
|------|-------|
| **OPERATOR-ROLLOUT-OR04** | `COMMIT_MODE_POST_CASH_SALE=boundary` staging |
| **production operator sign-off** | Human gate before production |
| **production COMMIT_MODE_* flip** | Not in OR-03 |

---

## 6. Test plan

```bash
pytest tests/test_operator_rollout_or03_api_write_sales_staging.py -q
pytest tests/ -q
```

**Next:** **OPERATOR-ROLLOUT-OR04** — `COMMIT_MODE_POST_CASH_SALE=boundary` on staging.
