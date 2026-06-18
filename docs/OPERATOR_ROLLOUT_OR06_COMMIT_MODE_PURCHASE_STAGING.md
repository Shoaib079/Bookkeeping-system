# OPERATOR-ROLLOUT-OR06 — COMMIT_MODE Purchase + Payable Payment (Staging)

**Tag:** `operator-rollout-or06-commit-mode-purchase-staging` · **Tier 3** per PH-04

## Executive summary

| Item | Status |
|------|--------|
| `COMMIT_MODE_POST_PURCHASE=boundary` | ✅ |
| `COMMIT_MODE_POST_PAYABLE_PAYMENT=boundary` | ✅ |
| P0 gate | `test_fastapi_p0_commit_ownership_purchase_payable.py` |

## Staging enablement

Cumulative tiers 1–3 in `config/staging/api.env.example`. Staging uvicorn only — do not export `COMMIT_MODE_*` during pytest.

## Gate verification

```bash
pytest tests/test_operator_rollout_or06_commit_mode_purchase_staging.py -q
unset COMMIT_MODE_POST_PURCHASE COMMIT_MODE_POST_PAYABLE_PAYMENT
pytest tests/test_fastapi_p0_commit_ownership_purchase_payable.py -q
pytest tests/ -q
```

## What must NOT change

Journal math · GL pairs · production env · Streamlit primary.

## Deferred

**OPERATOR-ROLLOUT-OR07** · production operator sign-off · production COMMIT_MODE_* flip

## Test plan

`pytest tests/test_operator_rollout_or06_commit_mode_purchase_staging.py -q`

**Next:** **OPERATOR-ROLLOUT-OR07**
