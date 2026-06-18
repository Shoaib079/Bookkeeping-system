# OPERATOR-ROLLOUT-OR02 — PostgreSQL Boundary Matrix Staging

**Mode:** PG matrix execution + gate tests. **No accounting / GL / posting behavior change.**

**Date:** 2026-06-05  
**Authority:** Second stage of Operator Rollout Readiness Audit staging sequence.  
**Tag:** `operator-rollout-or02-pg-matrix-staging`

**Prerequisites:** [OR-01](./OPERATOR_ROLLOUT_OR01_REACT_READ_STAGING.md) · [PH-03](./PRODUCTION_HARDENING_01_PH03_PG_MATRIX_EXECUTION_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Disposable PG test DB provisioned | ✅ Docker `erp-pytest-pg` (`postgres:16-alpine`) |
| Staging PG URL template | ✅ `config/staging/postgres.env.example` |
| PG boundary matrix (4 flows) | ✅ **4 passed** |
| PH-03 equity PG test kwargs fix | ✅ Test-only (invalid `company_id` kwargs removed) |
| Production PG runtime cutover | ⬜ **Not in this slice** |

**Posting / GL behavior:** **UNCHANGED** — test harness only.

---

## 2. Matrix execution results

**Command:**

```bash
export ERP_TEST_POSTGRES_URL='postgresql+psycopg://postgres@localhost/erp_pytest'
pytest tests/test_fastapi_react_07_pg_boundary_matrix.py \
  tests/test_production_hardening_01_ph03_pg_matrix_execution.py \
  -m optional_postgres -q
```

**Result:** `4 passed` (2026-06-05)

| Flow ID | Family | Test |
|---------|--------|------|
| boundary_cash_sale | `post_cash_sale` | `test_fastapi_react_07_pg_boundary_matrix.py` |
| boundary_void_sale | `void_cascade` | `test_fastapi_react_07_pg_boundary_matrix.py` |
| boundary_bank_deposit | `bank_transaction` | `test_production_hardening_01_ph03_pg_matrix_execution.py` |
| boundary_equity_contribution | `post_equity_movement` | `test_production_hardening_01_ph03_pg_matrix_execution.py` |

---

## 3. Gate verification

```bash
pytest tests/test_operator_rollout_or02_pg_matrix_staging.py -q
pytest tests/ -q
```

---

## 4. What must NOT change (verified)

- `DATABASE_URL` / production SQLite unchanged
- Default commit mode (`internal`)
- No production `COMMIT_MODE_*` flip

---

## 5. Deferred (next stage)

| Item | Notes |
|------|-------|
| **OPERATOR-ROLLOUT-OR03** | API write sales staging flags |
| **production operator sign-off** | Human gate before production |
| **production COMMIT_MODE_* flip** | Not in OR-02 — matrix validation only |

---

## 6. Test plan

```bash
export ERP_TEST_POSTGRES_URL='postgresql+psycopg://postgres@localhost/erp_pytest'
pytest tests/test_operator_rollout_or02_pg_matrix_staging.py -q
pytest tests/ -q
```

**Next:** **OPERATOR-ROLLOUT-OR03** — `ERP_API_WRITE_SALES=1` + `VITE_ERP_REACT_WRITE_SALES=1`.
