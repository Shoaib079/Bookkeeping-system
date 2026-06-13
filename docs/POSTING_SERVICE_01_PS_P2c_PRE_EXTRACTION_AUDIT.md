# POSTING-SERVICE-01 — PS-P2c Pre-Extraction Audit

**Phase:** PS-P2c (audit only — no code changes)
**Predecessors:** PS-P0, PS-P1, PS-P2a, PS-P2b-CHAR, PS-P2b — all complete
**State at audit:** full suite green (1621 passed, 2 xfailed); working tree clean after PS-P2b commit
**Scope:** `post_expense`, `post_purchase`, `post_payable_payment`, `_sync_company_cc_subledger`, `_resolve_purchase_debit_account`, `_purchase_ref_type`
**Verdict:** **GO** — extract the CC sink first, then the postings in two follow slices. **NO-GO** on moving any posting ahead of the sink or touching TD-PS-06 in this wave.

---

## 1. Dependency graph (current, post-PS-P2b)

Already in `services/posting.py`: `create_journal_entry`, `get_account_by_name`, `resolve_payment_credit_account`, `post_payable_creation`, sales trio. app.py keeps shims (`_resolve_payment_credit_account`, `get_account_by_name`, `create_journal_entry`, …). The six in-scope functions still live in `app.py`.

```
post_expense (app.py:6095)
  ├─ session.get(ExpenseRecord) ........ cid = expense.company_id
  ├─ _resolve_payment_credit_account ... shim → svc.resolve_payment_credit_account
  │                                        (company_id=cid, gl_company_id=_current_company_id())   [TD-PS-06 split]
  ├─ get_account_by_name (category) .... shim → svc
  ├─ create_journal_entry .............. shim → svc   ref="Expense", id=expense_id
  └─ _sync_company_cc_subledger ........ app.py  (always called; no-ops unless method=="Credit Card")

post_purchase (app.py:6043)
  ├─ _resolve_purchase_debit_account ... app.py (pure map → get_account_by_name)
  ├─ _purchase_ref_type ................ app.py (pure)
  ├─ get_account_by_name (Cash/Bank/AP)  shim → svc
  ├─ session.get(Purchase) ×2 .......... cid = purchase.company_id
  ├─ _resolve_payment_credit_account ... CC branch only
  ├─ create_journal_entry .............. ref=_purchase_ref_type(...), id=purchase_id
  ├─ _COMPANY_CC_METHOD const .......... app.py:172
  ├─ NAV_INVENTORY default ............. app.py const
  └─ _sync_company_cc_subledger ........ CC branch only

post_payable_payment (app.py:6191)
  ├─ get_account_by_name ("Accounts Payable")
  ├─ session.get(Payable) .............. cid = payable.company_id
  ├─ _resolve_payment_credit_account
  ├─ create_journal_entry → je ......... ref="PayablePayment", id=payable_id  (captures je.id)
  └─ _sync_company_cc_subledger ........ reference_id = je.id  ← NOT payable_id

_sync_company_cc_subledger (app.py:5758)  ── shared keystone
  ├─ _COMPANY_CC_METHOD ................ guard: return unless method == "Credit Card"
  ├─ _current_company_id() ............. AMBIENT fallback: company_id = company_id or _current_company_id()
  ├─ _t("form.err.company_cc_no_cards")  raised if company_id is None
  ├─ resolve_company_credit_card_account_id .. reconciliation/company_card.py (→ CompanyCardError)
  ├─ record.credit_card_account_id = cc_id + session.flush()   (record side-effect)
  └─ post_cc_subledger_charge .......... reconciliation/company_card.py

_resolve_purchase_debit_account (app.py:6009)  → get_account_by_name only (pure mapping)
_purchase_ref_type (app.py:6031)               → pure string mapping
```

**Cross-cutting:** all three posting functions converge on `_sync_company_cc_subledger`. It is the single shared dependency that is not yet in services and that carries ambient + `_t` ties.

---

## 2. Company-CC subledger side-effect map

All side effects flow through `_sync_company_cc_subledger → post_cc_subledger_charge` (`reconciliation/company_card.py`), only on the `"Credit Card"` method.

| Effect | Detail |
|--------|--------|
| **`BankTransaction` row** | One new row per charge: `account_id`=resolved CC card, `type="withdrawal"`, `amount=round(amt,2)`, `date=txn_date`, `company_id = company_id or cc_ba.company_id`, `statement_ref` (below). `session.flush()` after add. |
| **`BankAccount.balance`** | `apply_account_balance_delta(cc_ba, "withdrawal", amt)` → for a `credit_card` account, **balance += amt** (liability rises). No other account touched. |
| **`statement_ref`** | `cc_subledger_stmt_ref(reference_type, reference_id)` = `f"ccc:{reference_type}:{reference_id}"`. Concretely: expense → `ccc:Expense:{expense_id}`; purchase → `ccc:CardPurchase:{purchase_id}`; **payable payment → `ccc:PayablePayment:{je.id}`** (JE id, not payable id). |
| **`record.credit_card_account_id`** | Set to the resolved `cc_id` and `session.flush()` — on the Expense / Purchase / Payable record respectively (only when `record` has the attribute). |
| **`session.flush` behavior** | Two flushes: one in `_sync` after the record mutation, one inside `post_cc_subledger_charge` after adding the BankTransaction. **No `session.commit()` in this path** — the JE was already committed by `create_journal_entry`; the subledger row stays pending until the *caller's* next commit (split-commit, see §8 / TD-PS-01/04). |
| **Dedup guard** | `post_cc_subledger_charge` raises `CompanyCardError` if a non-void `BankTransaction` with the same `statement_ref` exists. |
| **Amount guard** | `CompanyCardError` if `amt <= 0`. |
| **Card resolution** | `resolve_company_credit_card_account_id`: auto-selects the sole active card; requires explicit `credit_card_account_id` when multiple; validates ownership/active/kind. |

**Key asymmetry:** expense and purchase key the subledger on the *source record id*; payable payment keys on the *journal-entry id*. This is deliberate (a payable can be paid in installments, each its own JE) and is what `reverse_cc_subledgers_for_gl_reference` special-cases for `"PayablePayment"`. Any extraction must preserve `reference_id=je.id` verbatim.

---

## 3. Existing coverage

| Path | Test |
|------|------|
| CC expense → 2110 GL + card balance + `record.credit_card_account_id` + BankTransaction `type`/`amount` + `statement_ref` (via `cc_subledger_stmt_ref("Expense", id)`) | `tests/test_cc_subledger_sync.py::TestCcExpenseSubledger` |
| CC purchase → 2110 + card balance + record mutation | `…::TestCcPurchaseSubledger` (does **not** assert `statement_ref` string) |
| CC payable payment → 2110 + card balance + record mutation | `…::TestCcPayablePaymentSubledger` (does **not** assert `statement_ref`/`je.id`) |
| Bill-pay zeros GL + card | `…::TestBillPayAfterSyncedCharge` |
| Multiple cards: explicit required / posts to selected | `…::TestMultipleCards` |
| Blocked without card account | `…::test_cc_posting_blocked_without_card_account` |
| Void CC expense/purchase reverses card; edit amount reverses+reposts | `…::test_void_cc_*`, `…::test_edit_amount_reverses_and_reposts_card` |
| `post_expense` Cash/Office, `post_purchase` **Credit**, `post_payable_payment` Cash (non-CC) JE tuples | `tests/test_posting_service01_characterization.py` (PS-P0) |
| Resolver branches + pinned EN error strings | `tests/test_posting_service01_p2b_char.py` |
| Card purchase void/edit; purchase→payable lifecycle | `test_card_purchase_void_edit.py`, `test_purchase_payable_lifecycle.py` |

CC side-effect coverage is **strong** — the GL+card+record triangle is asserted for all three functions.

---

## 4. Missing characterization (close before extraction)

1. **`statement_ref` exact strings** for purchase (`ccc:CardPurchase:{id}`) and **especially** payable payment (`ccc:PayablePayment:{je.id}`) — the je.id-vs-record.id asymmetry is currently unpinned at the string level. Highest-value gap.
2. **`post_purchase` Cash and Bank** JE-line tuples + ref_type (`CashPurchase`/`BankPurchase`) — PS-P0 pinned only Credit.
3. **`post_expense` non-Office categories** (Rent/Salary/Utility/Advertising/Fuel + else-fallback) and **Bank** payment method JE tuples.
4. **`_sync_company_cc_subledger` own `company_id`-None path** → assert the exact `ValueError` text (currently the EN string lives behind `_t`; mirror the PS-P2b pinned-constant treatment).
5. **Split-commit boundary** — a test asserting the subledger `BankTransaction` is *pending* until the caller commits (locks current behaviour before any TD-PS-01 boundary change).
6. **Dedup + amount≤0** raised through the `post_*` entry points (not just direct `post_cc_subledger_charge`).

---

## 5. Recommended extraction order (smallest safe slice)

**PS-P2c-1 (keystone — do first):** extract `_sync_company_cc_subledger` → `services/posting.py` as `sync_company_cc_subledger(...)`, with an app.py shim. Apply the PS-P2b pattern exactly:
- replace the ambient `company_id or _current_company_id()` with an explicit parameter; shim supplies `_current_company_id()`;
- replace `_t("form.err.company_cc_no_cards")` with a module-level pinned EN constant (matching `registry/locales`), like `_CC_DISABLED_MSG`/`_CC_GL_MISSING_MSG`;
- import `resolve_company_credit_card_account_id`, `post_cc_subledger_charge`, `CompanyCardError` from `reconciliation.company_card`.
- Add §4.1, §4.4, §4.5 characterization first.

**PS-P2c-2:** extract `post_expense` **and** `post_payable_payment` together. They share an identical dependency set, all of which is now service-side (resolver, `get_account_by_name`, `create_journal_entry`, the new sink). Add §4.3 + the payable-payment `je.id` `statement_ref` pin first.

**PS-P2c-3:** extract `post_purchase` plus its two pure helpers `_resolve_purchase_debit_account` + `_purchase_ref_type` and the `NAV_INVENTORY` default. Add §4.2 first.

The two pure helpers can ride with `post_purchase` (P2c-3) or move trivially in P2c-1; they carry no state and no ambient ties.

---

## 6. Must the three postings move together, or can they be split?

**They can be split** — `post_expense`, `post_purchase`, `post_payable_payment` do not call one another. Once the shared sink is service-side (P2c-1, with an app shim), each posting can migrate independently in any grouping. Recommended grouping: expense+payable-payment together (identical deps), purchase separately (extra helpers). Forcing all three in one wave is unnecessary risk concentration.

## 7. Must `_sync_company_cc_subledger` move first?

**Yes.** It is the shared keystone for all three, and the import-purity contract (`test_posting_service01_p2b::test_posting_service_import_purity_ps_p2b` forbids `_current_company_id`, `_t`, `import app`, `st.session_state` in `services/posting.py`). A service-side `post_expense` therefore cannot call back into `app._sync_company_cc_subledger`. The sink must be extracted (with an app shim for legacy callers) before any posting that depends on it.

---

## 8. TD-PS-06 partial-`company_id` risk

The PS-P2b resolver split is **partial and deliberate**: on the Credit Card branch, `company_card_enabled` is gated on `company_id` (record-derived) while the "Credit Card Payable" GL lookup uses `gl_company_id` (ambient, via shim). `_sync_company_cc_subledger` carries the **same shape** of ambient fallback (`company_id or _current_company_id()`), so PS-P2c inherits a second instance of the partial-`company_id` pattern.

Implications for this wave:
- When the postings move, they must reproduce the shim wiring **verbatim**: `company_id = record.company_id`, `gl_company_id = _current_company_id()`. Do **not** collapse the two parameters.
- **Do not fix TD-PS-06 during PS-P2c.** Unifying which company scopes the GL lookup could change account resolution in multi-company setups and would silently shift behaviour mid-extraction. Defer to the dedicated cleanup pass (post-PS-P2c / before FastAPI Phase B).
- Register the sink's ambient fallback alongside TD-PS-06 (or as TD-PS-07) so the cleanup pass addresses both resolver and sink together.

Risk: **Medium**, fully mitigable by verbatim preservation + a regression test asserting the resolver/sink use the record company for gating and the ambient company for the GL/card lookup.

---

## 9. Import-cycle risk with `reconciliation/company_card.py`

**None.** `services/posting.py` already imports `from reconciliation.company_card import company_card_enabled` (PS-P2b) with no cycle. `reconciliation/company_card.py` imports only `models` and `registry.service` at module scope; it touches `app` solely through a lazy `_app()` used inside `compute_cc_payable_recon_health` and the bill-pay helpers — **not** in the leaves PS-P2c needs (`resolve_company_credit_card_account_id`, `post_cc_subledger_charge`, `CompanyCardError`). Direction stays acyclic: `app → services.posting → reconciliation.company_card`; company_card never imports services. Watch item only: keep importing the leaves, never anything that triggers `import app` at load.

---

## 10. Risk rating & Go / No-Go

**Overall risk: Medium** (vs Low for PS-P2b). New surface: real external side effects (BankTransaction rows, `BankAccount.balance` mutation, record mutation, split-commit), an ambient + `_t` sink, and the `je.id` statement_ref asymmetry. Heavily mitigated by existing CC coverage; drops to **Low–Medium** once §4 lands.

| Decision | Verdict |
|----------|---------|
| Extract `_sync_company_cc_subledger` first (ambient→param, pinned EN string, company_card leaf imports), after §4.1/4.4/4.5 | **GO** |
| Then extract `post_expense` + `post_payable_payment` (after §4.3 + payable `je.id` pin) | **GO** |
| Then extract `post_purchase` + 2 pure helpers + `NAV_INVENTORY` (after §4.2) | **GO** |
| Move any posting function before the sink | **NO-GO** |
| Fix/collapse TD-PS-06 or the sink ambient fallback during PS-P2c | **NO-GO** (defer to cleanup pass) |

**Blocking prerequisites for GO:** §4 characterization additions, and a decision to reproduce the sink's `_t` string as a pinned service-side constant.

---

*Audit only. No code modified. Update `POSTING_SERVICE_01_CASCADE_MAP.md`, `TECH_DEBT_AND_MIGRATION_CLEANUP.md` (register sink ambient fallback), and `AUDIT_HISTORY.md` when PS-P2c lands.*
