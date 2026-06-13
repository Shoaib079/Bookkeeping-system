# POSTING-SERVICE-01 — PS-P4 Pre-Extraction Audit (Banking family)

**Phase:** PS-P4 (audit only — no code changes)
**Predecessors:** PS-P0…PS-P3 complete; PS-P3 docs closed
**State at audit:** suite green (1693 passed, 2 xfailed); working tree clean
**Scope:** `post_bank_transaction`, `post_bank_transfer`, `void_bank_transaction`, `void_reconciliation`
**Verdict:** **GO** for the poster pair + `void_bank_transaction` (after CHAR). **`void_reconciliation` is NOT a banking-transaction function — exclude it from PS-P4** (defer to the PS-P5 close family).

---

## 1. Dependency graph

```
post_bank_transaction (app.py:6023)        GL-ONLY — no balance mutation
  ├─ get_account_by_name("Cash"/"Bank", currency) ... shim → service
  └─ create_journal_entry(...) ...................... shim → service
        deposit:    Dr Bank / Cr Cash   ref="BankDeposit"
        withdrawal: Dr Cash / Cr Bank   ref="BankWithdrawal"

post_bank_transfer (app.py:6076)           GL-ONLY — no balance mutation, no currency
  ├─ gl_for(name): "cash" in name → Cash else Bank   (get_account_by_name)
  ├─ if !src_gl or !dest_gl or src_gl.id == dest_gl.id → return (NO-OP, no JE)
  └─ create_journal_entry: Dr dest_gl / Cr src_gl   ref="BankTransfer"

void_bank_transaction (app.py:2488)        GL REVERSAL + BALANCE + PAIRED CASCADE
  ├─ session.get(BankTransaction) ........ guard: missing/void → False
  ├─ guard: statement_ref "bsr:" → raise ValueError (must unpost via Reconciliation)
  ├─ guard: desc "Card Sale " → return False
  ├─ guard: desc "Capital Contribution #" / "Owner Drawing #" → return False
  ├─ reverse_journal_entries_for × ("BankDeposit","BankWithdrawal","BankTransfer") ... shim → service [commit per JE found]
  ├─ from reconciliation.company_card import reverse_account_balance_delta
  ├─ deposit/withdrawal: reverse_account_balance_delta(acct, txn.type, amount)
  ├─ transfer:
  │     ├─ destination record ("Transfer from …"): acct.balance −= amount
  │     └─ source record: acct.balance += amount; find paired via
  │            cq(BankTransaction).filter(date, amount, type=="transfer", id!=, !void,
  │                                        description.like("Transfer from {acct.name}%")).first()
  │            → dest_acct.balance −= paired.amount; paired.is_void = True (+ voided_at/reason)
  ├─ txn.is_void / voided_at / void_reason = …
  ├─ session.commit()
  └─ log_audit("Void","BankTransaction",…)

void_reconciliation (app.py:6395) → str   ◄── NOT a BankTransaction void
  ├─ session.get(DailyCashReconciliation) ... guards return error strings ("", "not found", "draft", …)
  ├─ if journal_entry_id: reverse_journal_entries_for("CashReconciliation", id) + cq(JournalEntry) reversal lookup → reversed_je_id
  ├─ is_void / voided_by_id (= owner_id) / voided_at / void_reason = …
  ├─ session.commit()
  └─ log_audit(...)   — returns "" on success; does NOT touch BankTransaction or BankAccount.balance
```

---

## 2. `BankAccount.balance` mutation paths

**Central asymmetry:** the posters do **not** mutate `BankAccount.balance`; the void does.

| Path | Balance mutation? | Where |
|------|-------------------|-------|
| `post_bank_transaction` / `post_bank_transfer` | **No** — GL only | Balance is applied **separately by callers** via `apply_account_balance_delta`: banking form (`15437`/`15453` through `_record_named_bank_movement` `:5860`), statement import (`21360–21395`), opening balance (`10786`). |
| `void_bank_transaction` | **Yes** — owns it | `reverse_account_balance_delta(acct, type, amt)` for deposit/withdrawal; inline `± amount` for transfer source/destination + the paired destination. |
| `void_reconciliation` | **No** | Only reverses the variance JE. |

Consequence: a service-side `void_bank_transaction` will own balance-cache reversal, while the forward balance mutation remains scattered across Streamlit callers (out of PS-P4 scope). Note this as a consistency debt (forward posters and the void disagree on who owns the cache) — do **not** try to fix it during extraction.

---

## 3. JournalEntry reference types & line tuples

| Function | ref_type | Lines (Dr, Cr) | Notes |
|----------|----------|----------------|-------|
| `post_bank_transaction` deposit | `BankDeposit` | Dr Bank `amount` / Cr Cash `amount` | `currency` threaded |
| `post_bank_transaction` withdrawal | `BankWithdrawal` | Dr Cash `amount` / Cr Bank `amount` | |
| `post_bank_transfer` | `BankTransfer` | Dr dest_gl / Cr src_gl | **only when src_gl ≠ dest_gl**; same-GL (e.g. Bank→Bank) is a no-op with no JE; no `currency` param |
| `void_*` | `Reversal` (ref_id = original JE id) | swapped | via `reverse_journal_entries_for` |
| `void_reconciliation` | reverses `CashReconciliation` | — | captures the reversal JE id into `reversed_je_id` |

---

## 4. Paired-transfer behavior

- **Source transaction** (description does *not* start with "Transfer from"): on void, `balance += amount` (restore the withdrawal), then **look up the paired destination** and reverse it too.
- **Destination transaction** (description starts with "Transfer from {src}"): on void, `balance −= amount` only (no further cascade).
- **Lookup logic:** `cq(BankTransaction)` filtered by equal `date`, equal `amount`, `type == "transfer"`, `id != self`, `is_void == False`, and `description.like("Transfer from {acct.name}%")`. **Fragile string match** — must be preserved verbatim on extraction.
- **Void cascade:** the paired destination's `balance −= paired.amount`, and it is marked `is_void=True` with `void_reason = f"Paired with voided transfer TXN#{txn_id}: …"`. Both legs are committed by the single `session.commit()`.

---

## 5. Guard behavior (`void_bank_transaction`)

| Guard | Trigger | Outcome |
|-------|---------|---------|
| Statement-linked | `statement_ref` startswith `"bsr:"` | **raises `ValueError`** ("must be unposted from Bank Reconciliation") |
| Card-sale deposit | `description` startswith `"Card Sale "` | returns `False` (void via originating Sale) |
| Equity movement | `description` startswith `"Capital Contribution #"` or `"Owner Drawing #"` | returns `False` (void via Equity Movements) |
| Already void / missing | record null or `is_void` | returns `False` |

All four are **string/flag based** and move verbatim. They are the contract boundary that keeps banking voids from corrupting reconciliation, sales, and equity flows.

---

## 6. Commit & audit behavior

| Function | Commits | Audit |
|----------|---------|-------|
| `post_bank_transaction` | 1 per JE (in kernel); deposit/withdrawal only | none |
| `post_bank_transfer` | 1 (cross-GL) or **0** (same-GL no-op) | none |
| `void_bank_transaction` | reverse JEs (kernel commits, only the matching ref_type has rows) + **1 explicit `session.commit()`** (persists balance + paired void) + `log_audit` commit | `log_audit` app-side |
| `void_reconciliation` | reverse `CashReconciliation` (kernel) + **1 `session.commit()`** + `log_audit` | `log_audit`; takes explicit **`owner_id`** as voider (not ambient) and **returns a `str`** |

`void_reconciliation`'s `owner_id` + `str` return + no balance/cascade make it contractually unlike the BankTransaction trio.

---

## 7. Company-scoping / `cq` dependencies

- `post_bank_transaction` / `post_bank_transfer`: `get_account_by_name` only (app version uses the ambient shim; service version takes explicit `company_id`). **No `cq`.**
- `void_bank_transaction`: **`cq(BankTransaction)`** for the paired-transfer lookup (company-scoped, ambient) → must become an explicit `company_id` filter on extraction; `reverse_journal_entries_for` shim already uses `current_company_required()`.
- `void_reconciliation`: `session.get` + `cq(JournalEntry)` for the reversal lookup.

---

## 8. Existing characterization coverage

| Path | Test |
|------|------|
| `void_bank_transaction` deposit balance reversal + flag | `tests/test_posting_service01_p3_char.py::test_void_deposit_reverses_balance_and_marks_void` |
| `void_bank_transaction` `bsr:` guard raises | `…::test_bsr_statement_ref_raises_value_error` |
| `void_bank_transaction` Card-sale guard returns False | `…::test_card_sale_deposit_returns_false_without_voiding` |
| `void_reconciliation` (variance JE reversal, error-string contract) | `tests/test_cash_reconciliation.py` |
| Banking posters (indirect, UI-level) | `test_banking_ux02_*`, `test_banking_desktop_b1b2`, `test_banking_pos_workflow_p1p2` |

---

## 9. Missing characterization (before extraction)

1. **`post_bank_transaction`** deposit + withdrawal JE-line tuples (`BankDeposit`/`BankWithdrawal`) — direct GL pin (currently only UI-indirect).
2. **`post_bank_transfer`** both branches: same-GL **no-op** (no JE) and cross-GL JE (Dr dest / Cr src, `BankTransfer`).
3. **`void_bank_transaction` withdrawal** balance reversal (only deposit is pinned).
4. **`void_bank_transaction` transfer** — the highest-risk path: source-leg restore + **paired-destination lookup + cascade void + dual balance arithmetic**, and the destination-leg `−amount`. Pin both record orientations.
5. **`void_bank_transaction` Capital/Owner-drawing guard** returns False (only `bsr:` and Card-sale are pinned).
6. **`void_bank_transaction` commit count + audit** (reverse + balance + commit + `log_audit`), mirroring the PS-P3 void pins.

Items 2 and 4 are the must-haves; the transfer/paired cascade is currently unpinned and is the riskiest behavior in scope.

---

## 10. Recommended PS-P4 slices

- **PS-P4-CHAR (first):** add §9.1–§9.6 characterization.
- **PS-P4-1 — poster pair (move together):** extract `post_bank_transaction` + `post_bank_transfer` → `services/posting.py` (explicit `company_id`, app shims supply ambient). Pure GL, no balance/cascade — lowest risk. They share the Cash/Bank account-resolution idiom and belong in one slice.
- **PS-P4-2 — `void_bank_transaction`:** extract the GL-reversal + balance + paired-cascade core (guards verbatim; `reverse_account_balance_delta` imported from `reconciliation.company_card`; `cq` paired lookup → explicit `company_id` filter). App shim supplies `company_id=current_company_required()` and keeps `log_audit` on `True`. Requires §9.4 transfer/paired pin landed.
- **Stay in app.py:** the forward balance-mutation callers (`_record_named_bank_movement`, banking forms, statement-import flow) — Streamlit-coupled, out of scope; they keep calling `apply_account_balance_delta` + the post shims.
- **Exclude from PS-P4 → defer to PS-P5 close family:** `void_reconciliation`. It voids a `DailyCashReconciliation` (not a `BankTransaction`), takes an explicit `owner_id`, returns an error `str`, and touches neither balance nor BankTransaction — it belongs with `void_eod_close` / the close-workflow voids.

---

## 11. Risk map

| Item | Risk | Driver / mitigation |
|------|------|---------------------|
| `post_bank_transaction` / `post_bank_transfer` | **Low** | Pure GL pairs; only gap is characterization (§9.1–9.2). Same-GL no-op must be pinned. |
| `void_bank_transaction` transfer + paired cascade | **High** | `cq` + `description.like("Transfer from {name}%")` string match, dual-leg balance arithmetic, paired void. Preserve verbatim; pin §9.4 first. |
| `void_bank_transaction` balance ownership | **Medium** | Couples GL reversal + balance cache; `reverse_account_balance_delta` importable, but the void owns cache while posters don't (consistency debt — don't fix now). |
| `void_bank_transaction` guards | **Low–Medium** | String/flag based; move verbatim; pin Capital/Owner guard (§9.5). |
| `void_reconciliation` in PS-P4 | **Medium (out of family)** | Different contract (`owner_id`, `str`); **exclude** → PS-P5. |
| Forward balance-mutation asymmetry | **Medium (debt)** | Forward posters don't own balance; void does. Register as debt; out of scope. |
| TD-PS-01/-03/-06/-07 mid-extraction | **n/a** | Verbatim moves only; no cleanup during PS-P4. |

---

## 12. Go / No-Go

| Decision | Verdict |
|----------|---------|
| PS-P4-CHAR then PS-P4-1 (extract `post_bank_transaction` + `post_bank_transfer`) | **GO** |
| PS-P4-2 (extract `void_bank_transaction` incl. paired cascade) after §9.4 pin | **GO** |
| Include `void_reconciliation` in PS-P4 | **NO-GO** — defer to PS-P5 close family (`owner_id`/`str`/no balance) |
| Move forward balance-mutation callers, or unify the balance-ownership asymmetry | **NO-GO** — Streamlit-coupled / out of scope; register as debt |
| Fix TD-PS-01/-03/-06/-07 during PS-P4 | **NO-GO** — verbatim moves only |

---

*Audit only. No code modified. Update `POSTING_SERVICE_01_CASCADE_MAP.md`, `TECH_DEBT_AND_MIGRATION_CLEANUP.md` (register the forward/void balance-ownership asymmetry), and `AUDIT_HISTORY.md` when PS-P4 lands.*
