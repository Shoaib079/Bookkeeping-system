# MONEY-DECIMAL-04-CHAR — Posting Kernel Money Math Characterization

**Mode:** Tests only (2026-06-16). No posting, model, schema, Alembic, or Decimal wiring changes.

**Goal:** Characterize current **Float** money semantics in `services/posting.py` immediately before MD-04 wires `services/money` into the kernel.

**Contract:** `tests/test_money_decimal_04_char_posting_math.py`  
**Prerequisites:** [MONEY_DECIMAL_01_AUDIT.md](./MONEY_DECIMAL_01_AUDIT.md) · [MONEY_DECIMAL_02_GOLDEN_VECTORS.md](./MONEY_DECIMAL_02_GOLDEN_VECTORS.md) · [MONEY_DECIMAL_03_HELPERS.md](./MONEY_DECIMAL_03_HELPERS.md)

---

## Executive summary

| Area | Current behavior (pinned) |
|------|---------------------------|
| **Import boundary** | `posting.py` does **not** import `services.money` or `decimal` |
| **JE amounts** | Stored as caller-supplied floats — **no** kernel quantize |
| **Balance guard** | `abs(total_debit - total_credit) > 0.01` (float accumulation) |
| **FX native** | `round(net * fx_rate, 4)` on each JE line |
| **post_* family** | Passes amount through to `create_journal_entry` unchanged |
| **Profit allocation** | Python `round(..., 2)`; last partner absorbs remainder |
| **Void/reversal** | Exact debit/credit swap; net balance returns to zero |
| **Reports** | `read_reports` / `read_ledger` / `read_balances` consume posted floats |

---

## 1. Source-level contracts

Verified by AST / source scan (no DB):

- No `services.money` import
- No `decimal` import
- Balance guard literal: `> 0.01`
- `amount_native=round(net * fx_rate, 4)`
- Allocation: `round(abs_income * pct / 100, 2)` + last-partner `round(abs_income - running, 2)`

---

## 2. create_journal_entry

| Behavior | Detail |
|----------|--------|
| Amount normalization | **None** — e.g. `100.012345` persisted as-is |
| Balanced 100.01 | Accepted |
| 100.00 vs 99.99 | **Rejected** (float overshoot > 0.01) |
| 128.03 vs 128.02 | Accepted |
| 100.00 vs 99.98 | Rejected with exact MD-02 message |

---

## 3. post_* amount handling (100.01)

| Function | JE ref type | Pinned |
|----------|-------------|--------|
| `post_cash_sale` | `CashSale` | debit/credit == 100.01 |
| `post_credit_sale` | `CreditSale` | AR debit 100.01 |
| `post_expense` | `Expense` | line sums == 100.01 |
| `post_purchase` (Cash) | `CashPurchase` | line sums == 100.01 |
| `post_bank_transaction` | `BankDeposit` / `BankWithdrawal` | line sums == 100.01 |

---

## 4. Profit allocation

| Net income | Partner lines (sorted) | JE partner credits |
|------------|------------------------|----------------------|
| +100.01 (50/50) | `[50.0, 50.01]` | sum == 100.01 |
| −100.01 (50/50) | `[-50.01, -50.0]` | — |

Algorithm unchanged from MD-02 golden vectors.

---

## 5. Void / reversal

| Entity | After void |
|--------|------------|
| Cash sale | Cash balance == 0 |
| Expense | Cash + expense account == 0 |
| Purchase | Cash + inventory == 0 |
| Reversal JE | `(debit, credit)` swapped exactly |

---

## 6. Multi-line accumulation

100 × 0.01 debit + 1.00 credit → accepted; `sum(debit) == sum(credit) == 1.0` (MD-02 aligned).

---

## 7. Reports dependency chain

Posting → JE lines (float) → `calculate_account_balance` / `compute_profit_loss` / `compute_balance_sheet` / `compute_ledger_page`.

Pinned: P&L net **100.01**, balance sheet balanced, GL cash debit total **100.01**.

---

## MD-02 alignment

`MD02_GOLDEN_MANIFEST` in the test file documents shared expected values. MD-04-CHAR and MD-02 must stay aligned until MD-04 implementation deliberately updates both.

---

## Next slice

**MONEY-DECIMAL-04** — wire `services/money` into posting kernel internal math (SQLite Float columns unchanged). Re-run MD-02 + MD-04-CHAR + full `test_posting_service01_*` after any kernel change.
