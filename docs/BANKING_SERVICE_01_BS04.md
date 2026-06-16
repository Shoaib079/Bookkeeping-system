# BANKING-SERVICE-01-BS-04 — Streamlit manual bank → `write_banking`

**Status:** ✅ Complete (2026-06-16)

**Pre-work:** BS-04-CHAR — `tests/test_banking_service01_char_manual_bank_parity.py`

---

## What changed

`render_banking` manual **Add Transaction** form submit now calls:

```python
services.write_banking.create_manual_bank_transaction(...)
```

instead of inline `apply_account_balance_delta` + `BankTransaction` + `post_bank_transaction` / `post_bank_transfer`.

**Scope:** Manual bank form only (`app.py` ~21651–21685). Statement import, match/post, void UX, and `_record_named_bank_movement` unchanged.

---

## Preserved behavior

| Area | Notes |
|------|-------|
| Deposit / withdrawal / transfer | Same subledger + GL via `write_banking` |
| Credit card withdrawal | Subledger-only (no JE); UI still shows `bank.cc_manual_gl_hint` |
| Transfer pairing | Destination txn description `Transfer from {source}: {notes}` |
| Balance deltas | Still via `apply_account_balance_delta` inside service |
| Validations | CC deposit/transfer guards, invalid amount, dest account — service raises pinned EN strings shown via `st.error` |
| Success UX | Still `st.success(_t("bank.txn_added"))` |

---

## Documented improvement (BS-04)

| Before (inline Streamlit) | After (`write_banking`) |
|---------------------------|-------------------------|
| No `AuditLog` on manual add | **`AuditLog` Create / `BankTransaction`** on every manual deposit, withdrawal, and transfer |

This aligns Streamlit manual banking with the FastAPI `POST /api/v1/bank-transactions` path.

---

## Unchanged (do-not-touch)

- `services/write_banking.py` logic (no service changes required for BS-04)
- `services/posting.py` bank kernels
- `apply_account_balance_delta` formulas
- `reconciliation/match_post.py`
- Statement import / reconciliation orchestration

---

## Regression guard

`tests/test_banking_service01_char_manual_bank_parity.py`:

- Contract: manual submit block delegates to `create_manual_bank_transaction` (no inline balance/post)
- Parity: Streamlit helper vs direct service call — GL, `BankTransaction`, balances
- Audit: manual submit writes `AuditLog` via service

---

## Next slices (from audit)

- **BS-03** — `company_card` CC bill payment explicit `company_id` on JE
- **BS-05** — balance helper module extraction
