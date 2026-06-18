# OPERATOR-ROLLOUT-OR09 — COMMIT_MODE Closing Families (Staging)

**Tag:** `operator-rollout-or09-commit-mode-closing-staging` · **Tier 6** per PH-04

## Executive summary

`profit_allocation` · `period_close` · `year_end_close` boundary in staging template.

## Staging enablement

Cumulative tiers 1–6 in `config/staging/api.env.example`.

## Gate verification

```bash
pytest tests/test_operator_rollout_or09_commit_mode_closing_staging.py -q
pytest tests/test_fastapi_p0_commit_ownership_close_allocation.py -q
pytest tests/ -q
```

## What must NOT change

Journal math · GL pairs · production env.

## Deferred

**OPERATOR-ROLLOUT-OR10** · production operator sign-off · production COMMIT_MODE_* flip

## Test plan

`pytest tests/test_operator_rollout_or09_commit_mode_closing_staging.py -q`

**Next:** **OPERATOR-ROLLOUT-OR10**
