# MONEY-DECIMAL-05-IMPL-3 — Pre-Audit

**Date:** 2026-06-16 · **Baseline:** MD-05-IMPL-2 (`51e1bd6`, 4611 passed)

Audit-only input for IMPL-3 implementation. See [MONEY_DECIMAL_05_IMPL_3.md](./MONEY_DECIMAL_05_IMPL_3.md) for slice outcome.

## Findings summary

| Issue | Location | IMPL-3 action |
|-------|----------|---------------|
| Stale bank balance writes | `app.py` 9867, 9975, 10087 | Route through `apply_account_balance_delta` |
| Payable float writes | `match_post.py`, `app.py` 19185 | `persist_money` / `_apply_payable_payment_state` |
| Bare PG cast | `0002_money_numeric.py` | `ROUND(col::numeric, scale)` |
| `ingredients.cost_per_base_unit` tier | model 4dp vs classification 2dp | Move to `NUMERIC_19_4` |
| GL cache assign | `sync_account_balances` | `persist_money` |
| No bank cache rebuild | — | Add `sync_bank_account_balances` |
| 60+ `round(float(...))` | reconciliation/services | Route through `services/money.py` |
| Duplicate helpers | `_normalize_money_amount`, `_allocation_share_float`, dual CC check | Remove / consolidate |

## Canonical boundaries (keep)

- **Quantization:** `services/money.py` — `quantize_money/fx/rate` (ROUND_HALF_UP)
- **ORM write:** `persist_money/fx/rate`
- **Bank delta:** `services/banking_balance.py` — `apply/reverse_account_balance_delta`
- **JE accumulator:** `_je_line_money` — float sum before persist (MD-02 locked)

## Never

- Second rounding module
- PG production cutover
- Apply `0002` to production `erp_data.db`
- Remove `_je_line_money`
