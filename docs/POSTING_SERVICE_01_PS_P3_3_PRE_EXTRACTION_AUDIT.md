# POSTING-SERVICE-01 — PS-P3-3 Pre-Extraction Audit

**Phase:** PS-P3-3 (audit only — no code changes)
**Predecessors:** PS-P3-1 (reversal primitives), PS-P3-2a (simple voids) — complete
**State at audit:** suite green (1676 passed, 2 xfailed); working tree clean; architecture audit docs committed
**Scope:** `void_purchase` + `_void_purchase_linked_payable`, `_linked_purchase_payable`, `_create_purchase_payable`, `_update_purchase_payable`, `_sync_purchase_payable_lifecycle`
**Verdict:** **GO** in two sub-slices (helpers → `void_purchase`). The three edit-lifecycle helpers **stay in app.py** (out of scope).

---

## 1. Dependency graph

```
void_purchase (app.py:2384)                              ── VOID concern
  ├─ session.get(Purchase) ............... guard → False (no commit/audit)
  ├─ _purchase_ref_type(...) ............. shim → service.purchase_ref_type (pure, PS-P2c-3)
  ├─ reverse_cc_subledgers_for_gl_reference(ref_type, purchase_id)  ... reconciliation/company_card (clean)
  ├─ reverse_journal_entries_for(ref_type, purchase_id) ............. shim → service [commit per JE]
  ├─ purchase.is_void / voided_at / void_reason = …
  ├─ _void_purchase_linked_payable(purchase_id, reason) ◄── CASCADE
  │     ├─ _linked_purchase_payable(purchase_id) → cq(Payable).filter_by(purchase_id)  [only cq() in cluster]
  │     └─ if linked & not linked.is_void:
  │           if linked.paid:
  │               reverse_cc_subledgers_for_gl_reference("PayablePayment", linked.id)   [no commit]
  │               reverse_journal_entries_for("PayablePayment", linked.id)             [commit per JE]
  │           linked.is_void / voided_at / void_reason = …
  ├─ session.commit() .................... [explicit void commit]
  └─ log_audit("Void","Purchase",…) ...... app.py:1557 [commit; ambient _current_user]

edit_purchase (app.py:15655)                             ── EDIT concern (Streamlit-coupled; stays in app)
  ├─ _linked_purchase_payable(purchase_id) ............. (paid-guard at 15666)
  ├─ reverse_cc_subledgers_for_gl_reference / reverse_journal_entries_for ("Correction")
  ├─ post_purchase(...) ................................ shim → service [commits in kernel]
  ├─ _sync_purchase_payable_lifecycle(purchase, orig_pt)
  │     ├─ _purchase_is_credit(orig) / _purchase_is_credit(new)
  │     ├─ Credit→Credit:  _update_purchase_payable → _linked_purchase_payable (+ fallback _create_purchase_payable)
  │     ├─ Credit→non:     _void_purchase_linked_payable   (linked never paid — tier2 edit blocked when paid)
  │     └─ non→Credit:     _create_purchase_payable
  ├─ session.commit()
  └─ log_audit("Edit","Purchase",…)
```

**Forward creation path** (`app.py:15302`, `18840`) builds `Payable(...)` **inline** — it does **not** call `_create_purchase_payable`. So the cluster cleanly separates into a *void* concern and an *edit* concern; creation touches neither helper.

---

## 2. Shared callers of `_linked_purchase_payable` (and the cluster)

| Helper | Callers | Concern |
|--------|---------|---------|
| `_linked_purchase_payable` (`:2411`) | `_void_purchase_linked_payable` (`:2417`), `_create_purchase_payable` (`:2430`), `_update_purchase_payable` (`:2452`), `edit_purchase` (`:15666`) | **void + edit** |
| `_void_purchase_linked_payable` (`:2415`) | `void_purchase` (`:2399`), `_sync_purchase_payable_lifecycle` (`:2477`) | **void + edit** |
| `_create_purchase_payable` (`:2428`) | `_update_purchase_payable` (`:2454` fallback), `_sync_purchase_payable_lifecycle` (`:2483`), tests (`p3_char:279/315`) | **edit only** |
| `_update_purchase_payable` (`:2450`) | `_sync_purchase_payable_lifecycle` (`:2475`) | **edit only** |
| `_sync_purchase_payable_lifecycle` (`:2468`) | `edit_purchase` (`:15700`) | **edit only** |

The two **shared** nodes (used by both void and edit) are `_linked_purchase_payable` and `_void_purchase_linked_payable`. The other three are edit-only.

---

## 3. `cq()` / company-scoping dependencies

- **`_linked_purchase_payable`** holds the **only `cq()` in the cluster**: `cq(session, Payable).filter_by(purchase_id=…).first()`. `cq` is company-scoped via `current_company_required()` — it **raises** if no active company. Extraction must take an explicit `company_id` and reproduce both the `purchase_id` filter and the company filter, with the app shim supplying `current_company_required()` to preserve the "company required" semantics.
- `_create_purchase_payable` / `_update_purchase_payable` use `purchase.company_id` (explicit, from the record) when constructing/aligning the `Payable` — no `cq`.
- `_void_purchase_linked_payable` has no direct `cq`; it inherits scoping through `_linked_purchase_payable`.
- `void_purchase` has no direct `cq`; `reverse_journal_entries_for` (shim) already uses `current_company_required()`.

---

## 4. Commit map

All cluster helpers are **commit-free**; every commit is owned by the outermost caller (`void_purchase` or `edit_purchase`). Reversal-JE commits happen inside the extracted `create_journal_entry` kernel (TD-PS-01).

| Scenario | Commit sequence | Total |
|----------|-----------------|-------|
| **Unpaid purchase** (Cash/Bank/CC, or unpaid Credit) | reverse(purchase ref) [1] → void `session.commit()` [1] → `log_audit` [1]; cascade sets flags only (no reverse) | **3** (PS-P3-CHAR pins the Cash case) |
| **Paid Credit purchase** | reverse(Purchase) [1] → reverse(`PayablePayment`) [1] → void commit [1] → `log_audit` [1]; CC-subledger reversal adds **no** commit (voids `BankTransaction` rows in-session) | **4** (more if multiple payment JEs / installments) |
| **Credit→Cash lifecycle** (edit, not void) | driven by `edit_purchase`: reverse("Correction") → `post_purchase` (kernel commits) → `_sync` (helper, 0 commits — linked never paid because tier2 edit is blocked when paid) → edit `session.commit()` → `log_audit("Edit")` | owned by `edit_purchase`; helper contributes **0** |

Key point for extraction: relocating the cascade helpers does **not** move any commit boundary — they never commit. Only `void_purchase`'s explicit commit + `log_audit` must be preserved in the app shim (mirroring the PS-P3-2a pattern).

---

## 5. Which helpers must move together

With `void_purchase`:
- **`_void_purchase_linked_payable`** — directly called by `void_purchase`; a service `void_purchase` cannot call back into app (purity). **Must move.**
- **`_linked_purchase_payable`** — called by `_void_purchase_linked_payable`. **Must move with it** (and be parameterized to explicit `company_id`).

## 6. Which helpers can remain behind shims / stay in app

- **`_linked_purchase_payable` + `_void_purchase_linked_payable`** move to the service but keep **app shims** so the edit-path callers (`_create_purchase_payable`, `_update_purchase_payable`, `_sync_purchase_payable_lifecycle`, `edit_purchase`) continue to work unchanged.
- **`_create_purchase_payable`, `_update_purchase_payable`, `_sync_purchase_payable_lifecycle`** — **stay entirely in app.py.** They are forward/edit concerns, reach the moved helpers via the shims, and are coupled to the Streamlit edit flow (`edit_purchase` uses `st.error`, `load_settings`, `log_audit("Edit")`). No reason to move them in PS-P3-3.

---

## 7. Remaining characterization gaps

Behavioral coverage is strong: `tests/test_purchase_payable_lifecycle.py` covers edit amount/vendor, **Credit→{Cash,Bank,Credit Card} voids payable**, **{Cash,Bank,CC}→Credit creates payable**, void-credit closes payable, void-non-credit no side effects, paid-blocks-tier2-edit; PS-P3-CHAR covers the GL-level unpaid + paid void cascades and the Cash 3-commit pin.

Add before extraction:

1. **Paid-purchase void commit count** — pin `mock_commit.call_count == 4` for a paid Credit purchase (and the installment/multi-`PayablePayment` count if supported). Only the Cash unpaid `== 3` case is currently pinned; the paid path asserts GL effects but not commit count.
2. **`_linked_purchase_payable` company-scoping** — a test pinning that it returns only the **active company's** payable for a `purchase_id` (cq isolation) and that absent company context raises (matching `current_company_required()`), since extraction replaces `cq` with an explicit `company_id` filter.

Both are quick adds; neither edit-lifecycle behavior nor the unpaid cascade needs new coverage.

---

## 8. Smallest safe extraction slice & sequence

- **PS-P3-3a — cascade helpers first:** extract `_linked_purchase_payable` (→ service, explicit `company_id`, `purchase_id` + company filter) and `_void_purchase_linked_payable` (→ service, commit-free; calls service `_linked_purchase_payable`, `reverse_journal_entries_for`, and `reverse_cc_subledgers_for_gl_reference`). Leave app shims for the edit-path callers. Add §7.2 company-scoping pin first. Lowest risk; unblocks `void_purchase`.
- **PS-P3-3b — `void_purchase`:** extract the reverse-and-flag-and-cascade core to the service (`void_purchase(session, purchase_id, void_reason, *, company_id) -> bool`), guards return `False` with no commit; app shim supplies ambient company and calls `log_audit` on `True`. Add §7.1 paid-commit-count pin first.
- **Do not move** the edit-lifecycle trio.

---

## 9. Risk map

| Item | Risk | Rationale / mitigation |
|------|------|------------------------|
| `_linked_purchase_payable` `cq`→explicit `company_id` | **Medium** | Only `cq` in cluster; 4 callers (void+edit). Shim must preserve company-required semantics; add §7.2 pin. |
| `_void_purchase_linked_payable` relocation | **Medium** | Shared void+edit; **commit-free** so no boundary shift; edit Credit→non-credit path covered (`test_credit_edit_to_immediate_payment_voids_payable`). |
| `void_purchase` paid-cascade commit count | **Medium** | Not pinned (only Cash `==3`). Pin `==4` + installment case before extraction. |
| Edit-lifecycle trio staying behind | **Low** | No move; reach moved helpers via shims. |
| `log_audit` boundary | **Low (if respected)** | Keep app-side (ambient `_current_user`, purity); preserves commit #N+1 placement. |
| Multiple `PayablePayment` JEs (installments) | **Low–Medium** | Each reverses + commits → higher count; pin if installments are reachable for purchase-linked payables. |
| Commit consolidation / flush temptation | **Medium** | Verbatim move only; commit conversion is TD-PS-01, out of scope. |

---

## 10. Go / No-Go

| Decision | Verdict |
|----------|---------|
| PS-P3-3a: extract `_linked_purchase_payable` + `_void_purchase_linked_payable` (explicit `company_id`, app shims), after §7.2 pin | **GO** |
| PS-P3-3b: extract `void_purchase` core (cascade + flags), `log_audit` in app shim, commits preserved, after §7.1 pin | **GO** |
| Move `_create_purchase_payable` / `_update_purchase_payable` / `_sync_purchase_payable_lifecycle` | **NO-GO** — edit concern, stays in app.py |
| Move `log_audit` to service, or consolidate/flush commits | **NO-GO** — verbatim move only (TD-PS-01 out of scope) |

---

*Audit only. No code modified. Update `POSTING_SERVICE_01_CASCADE_MAP.md` and `AUDIT_HISTORY.md` when PS-P3-3 lands.*
