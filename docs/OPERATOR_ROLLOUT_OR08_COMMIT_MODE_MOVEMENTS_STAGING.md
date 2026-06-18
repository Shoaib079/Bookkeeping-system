# OPERATOR-ROLLOUT-OR08 — COMMIT_MODE Partner/Worker/Equity (Staging)

**Tag:** `operator-rollout-or08-commit-mode-movements-staging` · **Tier 5** per PH-04

## Executive summary

Partner · worker · equity movement families enabled as `boundary` in staging template.

## Staging enablement

Cumulative tiers 1–5 in `config/staging/api.env.example`.

## Gate verification

```bash
pytest tests/test_operator_rollout_or08_commit_mode_movements_staging.py -q
pytest tests/test_fastapi_p0_commit_ownership_movements.py -q
pytest tests/ -q
```

## What must NOT change

Journal math · GL pairs · production env.

## Deferred

**OPERATOR-ROLLOUT-OR09** · production operator sign-off · production COMMIT_MODE_* flip

## Test plan

`pytest tests/test_operator_rollout_or08_commit_mode_movements_staging.py -q`

**Next:** **OPERATOR-ROLLOUT-OR09**
