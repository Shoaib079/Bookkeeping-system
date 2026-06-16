# MONEY-DECIMAL-05-IMPL-3 — Quantization + Cache Re-sync

**Status:** Complete (2026-06-16)  
**Tag:** `money-decimal-05-impl3-quantization-cache`  
**Baseline:** **4625 passed**, 9 skipped, 2 xfailed

## Scope delivered

1. **Single quantization boundary** — business-critical `round(float(...))` in reconciliation/services replaced with `services/money.py` helpers (`money_to_float`, `quantize_money`, `persist_money`, `fx_to_float`, `rate_to_float`).
2. **Stale bank cache writes fixed** — `app.py` equity CC/OD non-boundary branches and bank opening-balance path now use `apply_account_balance_delta`.
3. **Payable state** — `match_post.py` and payables UI use `persist_money` / `_apply_payable_payment_state`.
4. **Cache re-sync** — `sync_account_balances` assigns via `persist_money`; new `derive_bank_account_balance` + `sync_bank_account_balances` in `services/banking_balance.py` (startup + smoke tests).
5. **Alembic `0002` PG USING** — `ROUND({column}::numeric, {scale})` for explicit ROUND_HALF_UP at migration.
6. **`ingredients.cost_per_base_unit`** — moved to `NUMERIC_19_4` in `money_numeric_columns.py` (matches model `NUMERIC_FX`).
7. **Dead helpers removed** — `_normalize_money_amount`, `_allocation_share_float` (inlined to `money_to_float`); `is_credit_card_account` canonical in `banking_balance.py`.
8. **`_je_line_money` preserved** — documented as MD-02 characterization-locked float accumulator.

## Not in scope (deferred)

- Display-only `round(...)` in `app.py` UI/report formatting (DTO edge; inputs already derived).
- `registry/partner_statement.py` running-balance display rounding (P3 display layer).
- PostgreSQL production cutover / applying `0002` to production `erp_data.db`.

## Tests

| File | Role |
|------|------|
| `test_money_decimal_03_money_helpers.py` | Ugly-double + ROUND_HALF_UP fixtures |
| `test_money_decimal_05_impl3_quantization_boundary.py` | Static contracts (match_post, 0002 ROUND, ingredients tier) |
| `test_money_decimal_05_impl3_cache_resync.py` | GL + bank cache smoke |
| Updated MD-01/04/04b/05-IMPL-1 characterization | Removed helper pins |

## Next slice

**MD-05-IMPL-4** — SQLite smoke + PG migration test + golden/report parity on migrated copy DB.
