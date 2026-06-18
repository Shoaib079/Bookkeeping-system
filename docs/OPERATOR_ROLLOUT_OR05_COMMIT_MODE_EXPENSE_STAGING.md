# OPERATOR-ROLLOUT-OR05 — COMMIT_MODE Expense Boundary (Staging)

**Mode:** Staging operator config + gate tests. **No accounting / GL / posting behavior change.**

**Date:** 2026-06-05  
**Authority:** Fifth stage of Operator Rollout Readiness Audit staging sequence (PH-04 tier 2).  
**Tag:** `operator-rollout-or05-commit-mode-expense-staging`

**Prerequisites:** [OR-04](./OPERATOR_ROLLOUT_OR04_COMMIT_MODE_CASH_SALE_STAGING.md) · [PH-04](./PRODUCTION_HARDENING_01_PH04_COMMIT_MODE_ROLLOUT_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Staging `COMMIT_MODE_POST_EXPENSE=boundary` | ✅ `config/staging/api.env.example` |
| Cumulative tier 1+2 (`post_cash_sale` + `post_expense`) | ✅ Documented |
| P0 expense characterization gate | ✅ `test_fastapi_p0_commit_ownership_expense.py` |
| Full suite without `COMMIT_MODE_*` exported | ✅ Required gate |
| Production flip | ⬜ **Not in this slice** |

**Posting / GL behavior:** **UNCHANGED** — boundary commit scope only.

---

## 2. Staging enablement

| Env var | Value | Effect |
|---------|-------|--------|
| `COMMIT_MODE_POST_CASH_SALE` | `boundary` | (OR-04) Cash sale boundary |
| `COMMIT_MODE_POST_EXPENSE` | `boundary` | Expense GL post + audit boundary |
| (OR-03 flags) | unchanged | `ERP_API_WRITE_SALES=1` |

**Staging runtime:**

```bash
set -a && source config/staging/api.env.example && set +a
uvicorn api.main:create_app --factory --reload
```

**Rollback:** comment or remove `COMMIT_MODE_POST_EXPENSE=boundary` (keep OR-04 cash sale if desired).

---

## 3. Gate verification

CI gates run **without** `COMMIT_MODE_*` exported. Staging template arms boundary for the uvicorn process only.

```bash
pytest tests/test_operator_rollout_or05_commit_mode_expense_staging.py -q
unset ERP_TEST_POSTGRES_URL
unset COMMIT_MODE_POST_CASH_SALE
unset COMMIT_MODE_POST_EXPENSE
pytest tests/test_fastapi_p0_commit_ownership_expense.py -q
pytest tests/ -q
```

---

## 4. What must NOT change (verified)

- Journal math and GL pairs
- Families beyond tier 2 (default `internal` when unset)
- Streamlit primary UI
- Production env

---

## 5. Deferred (next stage)

| Item | Notes |
|------|-------|
| **OPERATOR-ROLLOUT-OR06** | `COMMIT_MODE_POST_PURCHASE` + `POST_PAYABLE_PAYMENT` boundary |
| **production operator sign-off** | Human gate before production |
| **production COMMIT_MODE_* flip** | Not in OR-05 |

---

## 6. Test plan

```bash
pytest tests/test_operator_rollout_or05_commit_mode_expense_staging.py -q
unset COMMIT_MODE_POST_CASH_SALE
unset COMMIT_MODE_POST_EXPENSE
pytest tests/ -q
```

**Next:** **OPERATOR-ROLLOUT-OR06** — purchase + payable payment boundary on staging.
