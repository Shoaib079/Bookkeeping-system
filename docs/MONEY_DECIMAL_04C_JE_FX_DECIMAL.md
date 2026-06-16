# MONEY-DECIMAL-04c+ — JE Balance Guard & FX Native Decimal Math

**Status:** ✅ **Closed by verification** (2026-06-16)  
**Tag:** `money-decimal-04c-je-fx-decimal-guard`  
**Mode:** Audit + verification tests + docs only — **no runtime behavior changes**

## Verdict

**No posting-kernel changes required.** Prior slices (MD-04a, MD-04b, MD-05-IMPL-2/3) already route money math through `services/money.py`. MD-04c+ audit confirms boundaries are safe and MD-02 golden vectors remain intact.

## Audit summary

| Area | Finding | Action |
|------|---------|--------|
| **JE line parse** | `_je_line_money` → `float(parse_money(value))` | ✅ Keep — MD-02 characterization-locked float accumulator |
| **JE balance guard** | `abs(total_debit - total_credit) > 0.01` (float sum) | ✅ Keep — changing to Decimal sum would alter accept/reject semantics (128.03/128.02 edge) |
| **JE line persist** | `persist_money(debit/credit)` — 2 dp ROUND_HALF_UP | ✅ Complete (MD-05-IMPL-2) |
| **FX `amount_native`** | `persist_fx(net * fx_rate)` — 4 dp ROUND_HALF_UP | ✅ Complete (MD-05-IMPL-2/3); no `round(..., 4)` in `posting.py` |
| **Post_* amounts** | `money_to_float(amount)` at business boundaries | ✅ Complete (MD-04a/04b) |
| **Profit allocation** | `money_to_float` share loop | ✅ Complete (MD-04b) |
| **`round()` in posting.py** | None | ✅ Verified |
| **`decimal` import in posting.py** | None — only `services.money` | ✅ Verified |
| **Dead aliases** | `_normalize_money_amount`, `_allocation_share_float` | ✅ Removed in MD-05-IMPL-3 |

## Deferred (intentional)

| Item | Reason |
|------|--------|
| **Decimal JE balance guard** | Would break MD-02 golden vectors (`128.03` vs `128.02` tolerance, float overshoot at `100.00` vs `99.99`) |
| **Decimal line-sum accumulator** | Same — `_je_line_money` float order is characterization-locked per MD-05-IMPL-3 |

Exactness for balance checks lands on **PostgreSQL Numeric columns + `services/money.py` persist helpers**, not on replacing the float guard before PG cutover.

## Standing rules (locked)

1. **`services/money.py`** is the sole Decimal/money boundary module.
2. **No new rounding helpers** outside `services/money.py`.
3. **MD-02 golden vectors** must pass unchanged unless a deliberate, documented semantic migration slice updates them.
4. **Do not apply Alembic `0002` to production `erp_data.db`** without the MD-05 cutover gate.

## Verification

```bash
pytest tests/test_money_decimal_04c_je_fx_decimal.py
pytest tests/test_money_decimal_02_golden_posting_vectors.py
pytest tests/test_money_decimal_03_money_helpers.py
pytest tests/test_money_decimal_04_char_posting_math.py
pytest tests/test_money_decimal_04b_char_profit_allocation_rounding.py
pytest tests/test_money_decimal_05_impl3_quantization_boundary.py
pytest tests/test_posting_service01_p1.py
pytest tests/
```

## Related docs

- [MONEY_DECIMAL_02_GOLDEN_VECTORS.md](./MONEY_DECIMAL_02_GOLDEN_VECTORS.md)
- [MONEY_DECIMAL_04A_POSTING_HELPERS.md](./MONEY_DECIMAL_04A_POSTING_HELPERS.md)
- [MONEY_DECIMAL_04B_PROFIT_ALLOCATION_HELPERS.md](./MONEY_DECIMAL_04B_PROFIT_ALLOCATION_HELPERS.md)
- [MONEY_DECIMAL_05_IMPL_3.md](./MONEY_DECIMAL_05_IMPL_3.md)

## Next slice

**PostgreSQL build + dual-run parity** (test-only via `ERP_TEST_POSTGRES_URL`) — after MD-04c+ closure.
