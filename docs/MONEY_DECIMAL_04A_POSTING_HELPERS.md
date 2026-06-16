# MONEY-DECIMAL-04a — Posting Helper Wiring

**Mode:** Posting math only (2026-06-16). No schema, model, Alembic, or Numeric column changes.

**Goal:** Wire `services/money.py` into `services/posting.py` at safe amount boundaries while preserving MD-02 golden vectors and MD-04-CHAR runtime behavior.

**Module changes:** `services/posting.py` only  
**Contracts:** `tests/test_money_decimal_02_golden_posting_vectors.py` · `tests/test_money_decimal_04_char_posting_math.py` · `tests/test_posting_service01_*.py`

---

## What changed

| Helper | Role |
|--------|------|
| `_normalize_money_amount(value)` | `money_to_float(value)` — 2 dp `ROUND_HALF_UP` at business posting boundary |
| `_je_line_money(value)` | `float(parse_money(value))` — Decimal str parse **without** 2 dp quantize |

**Import:** `from services.money import money_to_float, parse_money`

---

## Where helpers apply

| Entry point | Normalization |
|-------------|---------------|
| `post_cash_sale` | `_normalize_money_amount(amount)` |
| `post_card_sale` | `_normalize_money_amount(amount)` |
| `post_credit_sale` | `_normalize_money_amount(amount)` |
| `post_expense` | `_normalize_money_amount(amount)` (+ CC subledger) |
| `post_purchase` | `_normalize_money_amount(amount)` (+ CC subledger) |
| `post_bank_transaction` | `_normalize_money_amount(amount)` |
| `create_journal_entry` lines | `_je_line_money(debit)`, `_je_line_money(credit)` |

---

## What did NOT change (MD-04a scope)

| Area | Status |
|------|--------|
| JE balance guard | Still `abs(total_debit - total_credit) > 0.01` (float) |
| `amount_native` | Still `round(net * fx_rate, 4)` |
| Profit allocation | Still Python `round(..., 2)` — untouched |
| Reports / read services | Unchanged |
| `BankAccount.balance` formulas | Unchanged |
| ORM column types | Still `Float` |
| `decimal` module in posting | Not imported — only `services.money` |

---

## Parity proof

All MD-02 golden vectors, MD-04-CHAR runtime tests, and `test_posting_service01_*` pass unchanged after MD-04a.

Extra-precision manual JE lines (e.g. `100.012345`) still persist via `_je_line_money` parse path.

---

## Next slice

**MONEY-DECIMAL-04b+** — extend Decimal internal math (balance guard, allocation, FX native) with intentional golden-vector updates where semantics change.
