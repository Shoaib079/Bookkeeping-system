# MONEY-DECIMAL-04b — Profit Allocation Money Helpers

**Mode:** Allocation rounding only (2026-06-16). No schema, model, Alembic, or report changes.

**Goal:** Wire `services.money` into `allocate_profit_to_partners` share calculation while preserving every MD-04b-CHAR and MD-02 golden vector.

**Change:** `services/posting.py` — `_allocation_share_float` → `money_to_float`

---

## What changed

| Before (MD-04b-CHAR) | After (MD-04b) |
|----------------------|----------------|
| `round(abs_income × pct / 100, 2)` | `_allocation_share_float(...)` → `money_to_float(...)` |
| `round(abs_income − running, 2)` | `_allocation_share_float(...)` → `money_to_float(...)` |

```python
def _allocation_share_float(value) -> float:
    return money_to_float(value)
```

Last-partner remainder absorption unchanged: still `abs_income − running` on the final iteration.

---

## Parity proof

For all characterized vectors, `money_to_float` on the same float expressions reproduces legacy `round(..., 2)` results:

| Net | Shares | Partner amounts (order) |
|-----|--------|-------------------------|
| 100.01 | 50 / 50 | 50.01 + 50.0 (sorted `[50.0, 50.01]`) |
| −100.01 | 50 / 50 | −50.01 + −50.0 (sorted `[-50.01, -50.0]`) |
| 100.01 | 33.33 / 66.67 | 33.33 + 66.68 |
| 100.01 | 33.33 / 33.33 / 33.34 | 33.33 + 33.33 + 33.35 |
| 0.01 | 50 / 50 | 0.01 + 0.0 |
| 0.01 | 33.33 × 3 | 0.0 + 0.0 + 0.01 |

JE orientation, void reversal, share validation messages, and float balance guard unchanged.

---

## What did NOT change

- `create_journal_entry` balance guard
- `amount_native` (`round(net × fx_rate, 4)`)
- `_normalize_money_amount` / `_je_line_money` posting boundaries
- Reports, BankAccount.balance, ORM Float columns
- `_validate_partner_shares` tolerance

---

## Next slice

**MONEY-DECIMAL-04c+** — JE balance guard / FX native Decimal math (requires intentional golden-vector updates where float semantics diverge).
