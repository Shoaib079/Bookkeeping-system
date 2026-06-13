# POSTING-SERVICE-01 — PS-P2b Pre-Extraction Audit

**Phase:** PS-P2b (audit only — no code changes)
**Predecessors:** PS-P0 (characterization), PS-P1 (`create_journal_entry` + guard), PS-P2a (sales trio + `get_account_by_name`)
**Scope:** Business *payment* posting family — `post_expense`, `post_purchase`, `post_payable_creation`, `post_payable_payment`, and the shared resolver `_resolve_payment_credit_account`.
**State at audit:** test suite green, working tree clean.
**Verdict:** **GO** for a narrow leading slice; **NO-GO** for extracting the full family in one wave.

---

## 1. Dependency graph

### `_resolve_payment_credit_account(session, payment_method, *, currency, company_id)`  — `app.py:5968`
Leaf resolver: payment method → GL account to **credit**.

| Calls | Module | Notes |
|-------|--------|-------|
| `get_account_by_name` | **services/posting.py** (already extracted) | Bank / Credit Card Payable / Cash |
| `company_card_enabled` | reconciliation/company_card.py | → `registry.service.get_setting("banking.company_card_enabled")` |
| `_current_company_id()` | **app.py / st.session_state** | **AMBIENT** fallback: `cid = company_id or _current_company_id()` |
| `_t(...)` | app.py | raises `ValueError(_t("form.err.company_cc_disabled"))`, `_t("form.err.company_cc_gl_missing"))` |

### `post_purchase(...)` — `app.py:6058`
| Calls | Module |
|-------|--------|
| `_resolve_purchase_debit_account` | app.py (purchase-only helper) → `get_account_by_name` |
| `_purchase_ref_type` | app.py (purchase-only helper, pure) |
| `get_account_by_name` (Cash/Bank/AP) | services/posting.py |
| `_resolve_payment_credit_account` | app.py (Credit Card branch) |
| `session.get(Purchase, …)` | reads `Purchase.company_id`, `Purchase.credit_card_account_id` |
| `create_journal_entry` | services/posting.py |
| `_COMPANY_CC_METHOD` const | app.py:172 (`"Credit Card"`) |
| `_sync_company_cc_subledger` | app.py (CC branch only) |
| `NAV_INVENTORY` default | app.py constant |

### `post_expense(...)` — `app.py:6110`
| Calls | Module |
|-------|--------|
| `session.get(ExpenseRecord, …)` | reads `.company_id`, `.credit_card_account_id` |
| `_resolve_payment_credit_account` | app.py |
| `get_account_by_name` (category accounts) | services/posting.py |
| `create_journal_entry` | services/posting.py |
| `_sync_company_cc_subledger` | app.py — **called unconditionally**; internally no-ops unless method == `"Credit Card"` |

### `post_payable_creation(...)` — `app.py:6197`  *(cleanest — no payment leg)*
| Calls | Module |
|-------|--------|
| `get_account_by_name` (AP + expense account, pure category map) | services/posting.py |
| `create_journal_entry` | services/posting.py |
| — | no resolver, no `session.get`, no CC subledger |

### `post_payable_payment(...)` — `app.py:6223`
| Calls | Module |
|-------|--------|
| `get_account_by_name` (AP) | services/posting.py |
| `session.get(Payable, …)` | reads `.company_id`, `.credit_card_account_id` |
| `_resolve_payment_credit_account` | app.py |
| `create_journal_entry` | services/posting.py |
| `_sync_company_cc_subledger` | app.py — **`reference_id=je.id`** (not `payable_id`) — pin this |

### Shared sink — `_sync_company_cc_subledger(...)` — `app.py:5758`
| Calls | Module |
|-------|--------|
| `_COMPANY_CC_METHOD` | app.py:172 |
| `_current_company_id()` | **AMBIENT** fallback: `company_id = company_id or _current_company_id()` |
| `resolve_company_credit_card_account_id` | reconciliation/company_card.py → raises `CompanyCardError` |
| `post_cc_subledger_charge` | reconciliation/company_card.py |
| `_t("form.err.company_cc_no_cards")` | app.py |
| mutates `record.credit_card_account_id` + `session.flush()` | side effect on Purchase/Expense/Payable |

```
post_payable_creation ──► get_account_by_name ─┐
                          create_journal_entry ─┴─► [services/posting.py — already migrated]

post_expense ─┐
post_purchase ─┼─► _resolve_payment_credit_account ─► get_account_by_name (svc)
post_payable_payment ─┘                            ├─► company_card_enabled ─► get_setting (registry)
                                                   └─► _current_company_id()  [AMBIENT]
              └─► _sync_company_cc_subledger ─► resolve_company_credit_card_account_id (company_card)
                                              ├─► post_cc_subledger_charge (company_card)
                                              │        └─► apply_account_balance_delta → BankAccount.balance
                                              └─► _current_company_id()  [AMBIENT]
```

---

## 2. External-state dependency map

| Dependency | Touched by | How |
|-----------|------------|-----|
| **Company CC subledger** (`BankTransaction` rows, `statement_ref="ccc:…"`) | `post_expense`, `post_purchase`, `post_payable_payment` | via `_sync_company_cc_subledger → post_cc_subledger_charge` (writes a `withdrawal` BankTransaction). **`post_payable_creation` does NOT.** |
| **`BankAccount.balance`** (CC liability cache) | same three | `post_cc_subledger_charge → apply_account_balance_delta(card, "withdrawal", amt)` — only on `"Credit Card"` method |
| **Payable balances** (`paid_amount`/`balance`/`paid`) | **none** | These functions post GL only; payable balance maintenance is **caller-side** (UI), not in the posting functions |
| **Vendor balances** | **none** directly | Purchase→Payable cascade (`_create_purchase_payable`, `app.py:2441`) is invoked by the *caller*, outside `post_purchase` |
| **Company settings** | resolver + (sales) | `company_card_enabled` → `get_setting("banking.company_card_enabled")` |
| **Registry lookups** | resolver, guard | `registry.service.get_setting` (already imported in services/posting.py) |
| **Ambient company** (`st.session_state["active_company_id"]`) | resolver, CC sync | `company_id or _current_company_id()` — the last ambient ties (TD-PS-02) |

Note: the per-function `cid` is derived from the **record** (`session.get(X).company_id`), not ambient — good. Ambient only survives as the *fallback* inside the resolver and the CC sync.

---

## 3. Functions that MUST migrate together (co-migration set)

1. **`_resolve_payment_credit_account`** is shared by `post_expense`, `post_purchase`, `post_payable_payment`. Either move it first (with a shim) or move it in the same wave — it cannot be left behind without a cross-module call back into app.py.
2. **`_sync_company_cc_subledger`** is the shared CC sink for the same three. It must travel with them (or be extracted just ahead).
3. **`_resolve_purchase_debit_account`** + **`_purchase_ref_type`** are `post_purchase`-only pure helpers → move with `post_purchase`.
4. **Constants** `_COMPANY_CC_METHOD`, `NAV_INVENTORY` must be available service-side (import or duplicate).
5. **`_t` error strings** — the resolver and CC sync raise translated messages. PS-P0 pins these byte-identical, so services must reproduce the exact resolved strings (decide: import the translator vs. inline constants). **This is a real extraction prerequisite, not cosmetic.**

`reconciliation/company_card.py` is already a clean leaf: it imports `models`, `registry.service`, and lazy-`_app()` only inside recon/bill-pay helpers — **not** inside the leaves we need (`company_card_enabled`, `resolve_company_credit_card_account_id`, `post_cc_subledger_charge`, `CompanyCardError`). So `services/posting.py → reconciliation.company_card` introduces **no import cycle** (app → services → company_card; company_card never imports services).

---

## 4. Characterization gaps (before extraction)

PS-P0 (`tests/test_posting_service01_characterization.py`) covers only: `post_expense` Cash/Office, `post_purchase` **Credit** only, `post_payable_creation` Rent, `post_payable_payment` Cash. CC paths covered separately in `tests/test_cc_subledger_sync.py` (expense/purchase/payable-payment CC sync, multi-card, blocked-without-card, void/edit reversal).

Gaps to close first:

- **`post_purchase` Cash / Bank / CardPurchase** GL variants — not in PS-P0 (Card has `test_card_purchase_void_edit.py` + cc_subledger_sync, but Cash/Bank lines are uncharacterized at the JE-tuple level).
- **`post_expense` non-Office categories** (Rent/Salary/Utility/Advertising/Fuel) and the else-fallthrough — pure mapping, but unpinned.
- **`_resolve_payment_credit_account` direct unit characterization** — Bank path, Cash path, Cash-or-Bank fallback, `"Credit Card"` disabled `ValueError`, CC-GL-missing `ValueError`, **currency pass-through**, and **explicit `company_id` honored vs ambient fallback**. Currently only tested transitively.
- **`post_payable_payment` CC `reference_id=je.id`** nuance — pin that the subledger row keys off the JE id, not the payable id.
- **Ambient fallback** — a test that passes explicit `company_id` and asserts `_current_company_id()` is *not* consulted (locks the PS-P2a shim contract for this family).
- **`_t` string identity** — assert the exact resolved `ValueError` message text for the two CC error paths, so the service reproduction is verifiably identical.

---

## 5. Recommended extraction order (smallest safe slice)

**PS-P2b (this wave) — leading slice, lowest risk:**

1. **`_resolve_payment_credit_account` → `services/posting.py`** as `resolve_payment_credit_account(session, payment_method, *, currency, company_id)`, with an `app.py` shim that supplies `company_id=_current_company_id()`. Resolve the `_t` strings service-side (inline the two keys' text or pass a translator). It depends only on `get_account_by_name` (already in services) + `company_card_enabled` (clean import).
2. **`post_payable_creation` → `services/posting.py`** — no resolver, no CC, no `session.get`; pure category map + `create_journal_entry`. Safe companion that exercises the AP/expense pairing.

Add the **§4 characterization** for the resolver (all branches + ambient/explicit) **before** step 1.

**Defer to PS-P2c (next wave):** `post_expense`, `post_purchase`, `post_payable_payment` together with `_sync_company_cc_subledger`, `_resolve_purchase_debit_account`, `_purchase_ref_type`. These pull in the CC subledger side-effects (`BankTransaction` writes + `BankAccount.balance` mutation + `record.credit_card_account_id` flush) — a materially larger surface that wants the expanded CC/variant characterization landed first.

---

## 6. Should `_resolve_payment_credit_account` move before or with the family?

**Before — as the leading move of PS-P2b.** Rationale: it is the shared leaf for all three deferred postings; it carries one of the two remaining ambient-company fallbacks (so it benefits most from the explicit-`company_id` parameterization treatment); and extracting it first behind a shim lets the PS-P2c functions call `posting_service.resolve_payment_credit_account` cleanly without a temporary app-ward call. Moving it *with* the family would bundle the resolver's ambient/`_t` risk into the larger CC wave — avoid.

---

## 7. Hidden ambient-company dependencies still remaining

Two, both fallbacks of the form `company_id or _current_company_id()`:

1. `_resolve_payment_credit_account` (`app.py:5980`).
2. `_sync_company_cc_subledger` (`app.py:5774`).

Everywhere else in this family, `cid` comes from the **record** (`session.get(...).company_id`). These two fallbacks are the last ambient ties in the payment-posting path and are exactly the TD-PS-02 pattern (shim supplies ambient; service takes explicit param). No other hidden ambient reads found in the five functions.

---

## 8. Go / No-Go

| Decision | Verdict |
|----------|---------|
| Extract `_resolve_payment_credit_account` + `post_payable_creation` (with §4 resolver characterization added first) | **GO** |
| Extract full `post_expense` / `post_purchase` / `post_payable_payment` + `_sync_company_cc_subledger` in one wave now | **NO-GO** — defer to PS-P2c after CC/variant characterization expands and the `_t`-string + `company_card` import boundary is pinned |

**Blocking prerequisites for the GO slice:** (a) resolver branch + ambient/explicit + `_t`-string characterization; (b) decision on service-side `_t` reproduction.

---

*Audit only. No code modified. Update `POSTING_SERVICE_01_CASCADE_MAP.md` and `AUDIT_HISTORY.md` when PS-P2b lands.*
