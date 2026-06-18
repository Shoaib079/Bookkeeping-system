# PRODUCTION-HARDENING-01-PH04 — COMMIT_MODE_* Operator Rollout Characterization

**Mode:** Audit + env-var characterization tests. **No production env flip in this slice.**

**Date:** 2026-06-05  
**Authority:** Implements slice **PRODUCTION-HARDENING-01-PH04** from [PH-03 audit §8](./PRODUCTION_HARDENING_01_PH03_PG_MATRIX_EXECUTION_AUDIT.md).  
**Tag:** `production-hardening-01-ph04-commit-mode-rollout`

**Prerequisites:** [PH-03](./PRODUCTION_HARDENING_01_PH03_PG_MATRIX_EXECUTION_AUDIT.md) · [FASTAPI-REACT-04](./FASTAPI_REACT_04_READ_API_BOUNDARY_AUDIT.md) · [FASTAPI-REACT-07](./FASTAPI_REACT_07_PG_BOUNDARY_MATRIX_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Operator env var contract (`COMMIT_MODE_<FAMILY>`) | ✅ `registry/commit_mode_rollout_contract.py` |
| Env precedence characterization (test override > env > default) | ✅ PH-04 tests |
| Safest-first rollout order (14 families) | ✅ Documented |
| Staging operator preflight checklist | ✅ Documented |
| Env-driven write path wiring (`post_cash_sale`) | ✅ PH-04 tests |
| Production flip | ⬜ **Operator only** — not enabled by this slice |

**Posting / GL behavior:** **UNCHANGED** — CI defaults remain `internal`; no production deployment edits.

---

## 2. COMMIT_MODE_* operator contract

| Rule | Detail |
|------|--------|
| **Env prefix** | `COMMIT_MODE_` |
| **Valid values** | `boundary` · `internal` |
| **Example** | `COMMIT_MODE_POST_CASH_SALE=boundary` |
| **Default** | `internal` for all families when unset |
| **Precedence** | Test override → env var → default |
| **Invalid values** | Ignored; family stays default `internal` |

Implementation: `services/commit_modes.py` → `_env_commit_mode()` + `get_commit_mode()`.

---

## 3. Safest-first rollout order

Flip **one family at a time** in staging; re-run pytest after each flip.

| Tier | Family | P0 test | Write module |
|------|--------|---------|--------------|
| 1 | `post_cash_sale` | `test_fastapi_p0_commit_ownership_cash_sale.py` | `write_sales` |
| 2 | `post_expense` | `test_fastapi_p0_commit_ownership_expense.py` | `write_expenses` |
| 3 | `post_purchase` | `test_fastapi_p0_commit_ownership_purchase_payable.py` | `write_purchases` |
| 3 | `post_payable_payment` | same | posting kernel / Streamlit |
| 4 | `post_receivable_payment` | `test_fastapi_p0_commit_ownership_receivable_payment.py` | `write_receivable_payments` |
| 4 | `bank_transaction` | `test_fastapi_p0_commit_ownership_banking.py` | `write_banking` |
| 5 | `post_partner_movement` | `test_fastapi_p0_commit_ownership_movements.py` | `write_partner_worker` |
| 5 | `post_worker_movement` | same | `write_partner_worker` |
| 5 | `post_equity_movement` | same | `write_partner_worker` |
| 6 | `profit_allocation` | `test_fastapi_p0_commit_ownership_close_allocation.py` | `write_closing` |
| 6 | `period_close` | same | `write_closing` |
| 6 | `year_end_close` | same | `write_closing` |
| 7 | `reconciliation` | `test_fastapi_p0_commit_ownership_reconciliation.py` | `write_reconciliation` |
| 8 | `void_cascade` | `test_fastapi_p0_commit_ownership_voids.py` | `write_voids` |

Machine-readable: `registry/commit_mode_rollout_contract.py` → `ROLLOUT_FAMILIES`.

---

## 4. Operator preflight checklist

Before enabling `COMMIT_MODE_<FAMILY>=boundary` in staging or production:

1. **`pytest tests/` green on staging** (SQLite, no `COMMIT_MODE_*` set)
2. **Family P0 characterization test green**
3. **Optional PG boundary matrix green** when `ERP_TEST_POSTGRES_URL` set
4. **Flip one `COMMIT_MODE_<FAMILY>=boundary` at a time**
5. **Re-run full pytest after each family flip**
6. **Rollback:** unset env var or set `COMMIT_MODE_<FAMILY>=internal`
7. **Never flip production without operator sign-off**

---

## 5. Staging operator examples

```bash
# Tier 1 — cash sale boundary (staging only)
export COMMIT_MODE_POST_CASH_SALE=boundary
pytest tests/test_fastapi_p0_commit_ownership_cash_sale.py -q
pytest tests/ -q

# Tier 2 — add expense (keep prior flips if desired)
export COMMIT_MODE_POST_EXPENSE=boundary

# Rollback single family
unset COMMIT_MODE_POST_CASH_SALE
# or
export COMMIT_MODE_POST_CASH_SALE=internal
```

**Production:** Do **not** set `COMMIT_MODE_*=boundary` in production until PH-05 launch gate + explicit operator approval.

---

## 6. Deferred (out of PH-04 scope)

| Item | Notes |
|------|-------|
| **PRODUCTION-HARDENING-05** | Launch-readiness verification gate + epic closure |
| **production operator sign-off** | Human gate before prod flip |
| **TD-PS-03** | Route-layer DTO adapters |
| **CI optional_postgres job** | Managed test DB provisioning |

---

## 7. What must NOT change (verified)

- Default commit mode (`internal`) in code and CI
- Journal math and GL pairs
- Streamlit primary UI
- No production deployment env edits in this slice
- No Docker file edits

---

## 8. Test plan

```bash
pytest tests/test_production_hardening_01_ph04_commit_mode_rollout.py -q
pytest tests/ -q
```

---

## 9. Recommendation / next slice

**PRODUCTION-HARDENING-01-PH05** — launch-readiness verification gate + epic closure.
