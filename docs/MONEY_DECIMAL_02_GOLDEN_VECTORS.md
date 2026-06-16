# MONEY-DECIMAL-02 — Golden Posting Vectors (Float Baseline)

**Mode:** Tests only (2026-06-16). No schema, model, posting, report, or Decimal conversion changes.

**Goal:** Pin current **Float** posting behavior with golden vectors before any `Decimal`/`Numeric` migration. Any future MD-04+ change that alters these assertions is a **semantic regression** unless the test file is deliberately updated.

**Contract:** `tests/test_money_decimal_02_golden_posting_vectors.py`  
**Prerequisite audit:** [MONEY_DECIMAL_01_AUDIT.md](./MONEY_DECIMAL_01_AUDIT.md)

---

## Executive summary

| Vector | What is pinned |
|--------|----------------|
| JE balance guard | `abs(deb − cred) > 0.01` tolerance; exact rejection message |
| Basic posting | Sale / expense / purchase / bank deposit at **100.01** |
| Profit allocation | Net **100.01** or **−100.01** split 50/50 → penny absorbed on last partner |
| Multi-line JE | 100 × **0.01** debit lines sum to **1.00** |
| Void symmetry | Post + void → net **0**; reversal swaps exact float amounts |
| Reports | P&L / Balance Sheet / GL ledger totals for **100.01** |
| Multi-currency | TRY / USD / EUR `amount_native = round(net × fx_rate, 4)` |

---

## 1. Journal Entry balance guard

**Kernel:** `services/posting.py` → `create_journal_entry`

| Case | Debit | Credit | Expected |
|------|-------|--------|----------|
| Balanced | 100.01 | 100.01 | Accepted |
| 1-cent nominal (float-safe) | 128.03 | 128.02 | **Accepted** (`abs(diff) ≤ 0.01` after float accumulation) |
| 1-cent nominal (float trap) | 100.00 | 99.99 | **Rejected** — accumulation yields `diff > 0.01` |
| 2-cent imbalance | 100.00 | 99.98 | **Rejected** |

**Exact error (100.00 vs 99.99):**

```
Journal entry is not balanced: Debit $100.00 vs Credit $99.99
```

No JE or JE lines persist on rejection.

---

## 2. Basic posting amounts (100.01)

All vectors use amount **100.01** and assert JE line tuples `(account_id, debit, credit)`.

| Posting function | Reference type | Debit account | Credit account |
|------------------|----------------|---------------|----------------|
| `post_cash_sale` | `CashSale` | Cash | Sales Revenue |
| `post_expense` (Office / Cash) | `Expense` | Office Expense | Cash |
| `post_purchase` (Cash) | `CashPurchase` | Inventory | Cash |
| `post_bank_transaction` (deposit) | `BankDeposit` | Bank | Cash |

---

## 3. Profit allocation penny absorption

**Kernel:** `allocate_profit_to_partners` — last partner gets `round(abs_income − running, 2)`.

Setup: closed period with two 50% partners.

| Net income | Partner line amounts (sorted) | Sum |
|------------|-------------------------------|-----|
| **+100.01** | `[50.0, 50.01]` | 100.01 |
| **−100.01** | `[-50.01, -50.0]` | −100.01 |

First partner share uses `round(abs_income × pct / 100, 2)` (Python `round`, bankers rounding on halves).

---

## 4. Multi-line JE accumulation

100 debit lines of **0.01** + one credit line of **1.00**:

- `sum(debit) == 1.0`
- `sum(credit) == 1.0`
- Entry accepted (101 lines)

Pins float accumulation order in the kernel loop (`total_debit += debit`).

---

## 5. Void / reversal symmetry

1. `post_cash_sale` **100.01**
2. Cash balance == **100.01** (`calculate_account_balance`)
3. `void_sale` → Cash balance == **0.0**
4. Reversal JE (`reference_type=Reversal`) swaps every `(debit, credit)` pair exactly

---

## 6. Reports parity

After a **100.01** cash-sale JE in Jun 2025:

| Report | Pinned field | Expected |
|--------|--------------|----------|
| P&L | `total_income`, `net` | 100.01 |
| Balance Sheet | `total_assets`, `net_income`, `balanced` | 100.01, 100.01, `True` |
| GL ledger (Cash) | `total_debit`, `closing_balance` | 100.01 |

Uses `services/read_reports` and `services/read_ledger` — no Streamlit.

---

## 7. Multi-currency (TRY / USD / EUR)

`post_cash_sale` with `currency` + `fx_rate`:

| Currency | Cash account | fx_rate (test) | `amount_native` per line |
|----------|--------------|----------------|--------------------------|
| TRY | Cash | 1.0 | ±100.01 |
| USD | Cash USD | 34.5678 | ±`round(100.01 × 34.5678, 4)` |
| EUR | Cash EUR | 37.1234 | ±`round(100.01 × 37.1234, 4)` |

Debit line: `+amount_native`; credit line: `−amount_native`.

---

## Next slice

**MONEY-DECIMAL-04** — posting kernel internal Decimal math (helpers in `services/money.py` ready; not wired yet).

When MD-04 changes the posting kernel, re-run this suite first; failures document semantic drift.
