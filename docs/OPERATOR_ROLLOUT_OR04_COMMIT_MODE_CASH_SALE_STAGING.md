# OPERATOR-ROLLOUT-OR04 — COMMIT_MODE Cash Sale Boundary (Staging)

**Mode:** Staging operator config + gate tests. **No accounting / GL / posting behavior change.**

**Date:** 2026-06-05  
**Authority:** Fourth stage of Operator Rollout Readiness Audit staging sequence (PH-04 tier 1).  
**Tag:** `operator-rollout-or04-commit-mode-cash-sale-staging`

**Prerequisites:** [OR-03](./OPERATOR_ROLLOUT_OR03_API_WRITE_SALES_STAGING.md) · [PH-04](./PRODUCTION_HARDENING_01_PH04_COMMIT_MODE_ROLLOUT_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Staging `COMMIT_MODE_POST_CASH_SALE=boundary` | ✅ `config/staging/api.env.example` |
| P0 cash sale characterization gate | ✅ `test_fastapi_p0_commit_ownership_cash_sale.py` |
| Full suite with tier-1 env | ✅ Required gate |
| Other `COMMIT_MODE_*` families | ⬜ Remain default `internal` in template |
| Production flip | ⬜ **Not in this slice** |

**Posting / GL behavior:** **UNCHANGED** — boundary commit scope only; same GL pairs as characterization tests.

---

## 2. Staging enablement

| Env var | Value | Effect |
|---------|-------|--------|
| `COMMIT_MODE_POST_CASH_SALE` | `boundary` | Cash sale posts via `boundary_commit_scope` |
| (OR-03 flags) | unchanged | `ERP_API_WRITE_SALES=1` + React write sales |

**Operator steps:**

```bash
set -a && source config/staging/api.env.example && set +a
uvicorn api.main:create_app --factory --reload
```

For pytest gates, keep `COMMIT_MODE_*` unset (see § Gate verification).

**Rollback:** `unset COMMIT_MODE_POST_CASH_SALE` or `COMMIT_MODE_POST_CASH_SALE=internal`

---

## 3. Gate verification

CI and local gates run **without** `COMMIT_MODE_*` exported (default `internal`). The staging template arms boundary mode for the **staging uvicorn process only**.

```bash
pytest tests/test_operator_rollout_or04_commit_mode_cash_sale_staging.py -q
unset ERP_TEST_POSTGRES_URL
unset COMMIT_MODE_POST_CASH_SALE
pytest tests/test_fastapi_p0_commit_ownership_cash_sale.py -q
pytest tests/ -q
```

**Staging runtime** (operator shell running API):

```bash
set -a && source config/staging/api.env.example && set +a
uvicorn api.main:create_app --factory --reload
```

Do **not** export `COMMIT_MODE_POST_CASH_SALE=boundary` when running the full pytest suite — env precedence breaks default-internal characterization tests (PH-04 § precedence).

---

## 4. What must NOT change (verified)

- Journal math and GL pairs
- Other `COMMIT_MODE_*` families (default `internal` when unset)
- Streamlit primary UI
- Production env

---

## 5. Deferred (next stage)

| Item | Notes |
|------|-------|
| **OPERATOR-ROLLOUT-OR05** | `COMMIT_MODE_POST_EXPENSE=boundary` staging |
| **production operator sign-off** | Human gate before production |
| **production COMMIT_MODE_* flip** | Not in OR-04 |

---

## 6. Test plan

```bash
pytest tests/test_operator_rollout_or04_commit_mode_cash_sale_staging.py -q
unset COMMIT_MODE_POST_CASH_SALE
pytest tests/ -q
```

**Next:** **OPERATOR-ROLLOUT-OR05** — `COMMIT_MODE_POST_EXPENSE=boundary` on staging.
