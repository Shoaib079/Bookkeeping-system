# MONEY-DECIMAL-04b-CHAR — Profit Allocation Rounding Characterization

**Mode:** Tests only (2026-06-16). No posting, model, schema, Alembic, or Decimal wiring changes.

**Goal:** Deep-pin float/Python `round` profit/loss allocation semantics before MD-04b changes allocation math.

**Contract:** `tests/test_money_decimal_04b_char_profit_allocation_rounding.py`  
**Prerequisites:** MD-02 golden vectors · MD-04-CHAR · MD-04a posting helpers

---

## Executive summary

| Area | Pinned behavior |
|------|-----------------|
| Share algorithm | `round(abs_income × pct / 100, 2)`; last partner `round(abs_income − running, 2)` |
| Rounding mode | Python built-in `round` (banker's rounding on halves) |
| Money helpers | `_allocation_share_float` → `money_to_float` (MD-04b); parity with vectors below |
| Share validation | Active partners must sum to 100 ± 0.01% |
| Profit JE | Dr Retained Earnings / Cr Partner Current |
| Loss JE | Dr Partner Current / Cr Retained Earnings |
| Void | Reversal JE + `is_void` / `voided_by_id` / `void_reason` / `voided_at` |

---

## 1. Profit allocation vectors

| Net income | Shares | Partner line amounts (sorted or by id) | Sum |
|------------|--------|----------------------------------------|-----|
| 100.01 | 50 / 50 | `[50.0, 50.01]` | 100.01 |
| 100.00 | 33.33 / 66.67 | `[33.33, 66.67]` | 100.00 |
| 100.01 | 33.33 / 33.33 / 33.34 | `[33.33, 33.33, 33.35]` | 100.01 |
| 100.01 | 33.33 / 66.67 | 33.33 + **66.68** (last absorbs) | 100.01 |
| 0.01 | 50 / 50 | `[0.0, 0.01]` | 0.01 |
| 0.01 | 33.33 / 33.33 / 33.34 | `[0.0, 0.0, 0.01]` | 0.01 |

---

## 2. Loss allocation vectors

| Net loss | Shares | Line amounts (sorted) | Sum |
|----------|--------|----------------------|-----|
| −100.01 | 50 / 50 | `[-50.01, -50.0]` | −100.01 |

Loss lines stored as negative `PartnerProfitAllocationLine.amount`; JE uses positive debit magnitudes on partner current accounts.

---

## 3. Journal entries

- Allocation JE `reference_type = ProfitAllocation`
- Balanced under current float guard (`abs(deb − cred) > 0.01`)
- Partner credits (profit) or debits (loss) sum to `abs(net_income)`

---

## 4. Void allocation

- `void_profit_allocation` → `create_reversing_journal_entry` on allocation JE
- Partner current account balances return to **0** after void
- Void fields set; duplicate void returns `"Allocation not found or already voided."`

---

## 5. Error messages (exact)

| Condition | Message |
|-----------|---------|
| Shares sum to 80% | `Partner shares sum to 80.00% — must equal 100%.` |
| No active partners | `No active partners defined.` |

---

## Source contract (post MD-04b)

`allocate_profit_to_partners` block in `services/posting.py` must contain:

- `_allocation_share_float(abs_income * p.profit_share_pct / 100.0)`
- `_allocation_share_float(abs_income - running)` on last partner
- `_allocation_share_float` → `money_to_float`
- No bare `round(..., 2)` in the allocation share loop

Semantic parity with the pre-MD-04b `round` vectors in §1–2 is required (see MD-04b-CHAR tests).

---

## Status

**MONEY-DECIMAL-04b ✅** — `money_to_float` wired; MD-04b-CHAR + MD-02 vectors green.

**Next:** **MD-04c+** — posting-kernel Decimal math. Re-run `test_money_decimal_04b_char_profit_allocation_rounding.py` first; failures document semantic drift.
