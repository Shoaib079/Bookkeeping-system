# OPERATOR-ROLLOUT-OR07 — COMMIT_MODE Receivable + Bank (Staging)

**Tag:** `operator-rollout-or07-commit-mode-receivable-bank-staging` · **Tier 4** per PH-04

## Executive summary

| Item | Status |
|------|--------|
| `COMMIT_MODE_POST_RECEIVABLE_PAYMENT=boundary` | ✅ |
| `COMMIT_MODE_BANK_TRANSACTION=boundary` | ✅ |

## Staging enablement

Cumulative tiers 1–4 in `config/staging/api.env.example`. Staging uvicorn only.

## Gate verification

```bash
pytest tests/test_operator_rollout_or07_commit_mode_receivable_bank_staging.py -q
pytest tests/test_fastapi_p0_commit_ownership_receivable_payment.py -q
pytest tests/test_fastapi_p0_commit_ownership_banking.py -q
pytest tests/ -q
```

## What must NOT change

Journal math · GL pairs · production env.

## Deferred

**OPERATOR-ROLLOUT-OR08** · production operator sign-off · production COMMIT_MODE_* flip

## Test plan

`pytest tests/test_operator_rollout_or07_commit_mode_receivable_bank_staging.py -q`

**Next:** **OPERATOR-ROLLOUT-OR08**
