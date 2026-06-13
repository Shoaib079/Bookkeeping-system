# POSTING-SERVICE-01 — PS-P3-2 Pre-Extraction Audit

**Phase:** PS-P3-2 (audit only — no code changes)
**Predecessors:** PS-P0…PS-P2c, PS-P3-CHAR, PS-P3-1 (reversal primitives extracted) — all complete
**State at audit:** suite green (1669 passed, 2 xfailed); working tree clean
**Scope:** `void_expense`, `void_purchase`, `void_payable`
**Verdict:** **GO** for `void_expense` + `void_payable`. **NO-GO** for `void_purchase` in this slice (defer to PS-P3-3 with the payable-cascade helpers).

---

## 1. Dependency graph

PS-P3-1 already extracted the reversal primitives: `create_reversing_journal_entry` (`app.py:2339` shim → service, `company_id=_current_company_id()`) and `reverse_journal_entries_for` (`app.py:2347` shim → service, **`company_id=current_company_required()`** — note: raises if no active company). `reverse_cc_subledgers_for_gl_reference` lives in `reconciliation/company_card.py` (clean module, already imported at `app.py:236`; `services/posting.py` already imports from this module — no cycle).

```
void_expense (app.py:2370)
  ├─ session.get(ExpenseRecord) ......... guard: missing/already-void → return False (no commit, no audit)
  ├─ reverse_cc_subledgers_for_gl_reference("Expense", expense_id) ... reconciliation/company_card
  ├─ reverse_journal_entries_for("Expense", expense_id) ............. shim → service  [commit #1 per reversed JE, in kernel]
  ├─ expense.is_void / voided_at / void_reason = …
  ├─ session.commit() .................................. [commit #2]
  └─ log_audit("Void","ExpenseRecord",…) ............... app.py:1557  [commit #3]  (uses _current_user ambient)

void_payable (app.py:2486)
  ├─ session.get(Payable) ............... guard → False
  ├─ reverse_cc_subledgers_for_gl_reference("PayablePayment", payable_id)
  ├─ reverse_journal_entries_for("PayableCreation", payable_id) ..... [commit per JE]
  ├─ reverse_journal_entries_for("PayablePayment", payable_id) ...... [commit per JE]
  ├─ payable.is_void / voided_at / void_reason = …
  ├─ session.commit() .................................. [commit]
  └─ log_audit("Void","Payable",…) ..................... [commit]
        (independent of the purchase cascade — does NOT call _void_purchase_linked_payable)

void_purchase (app.py:2384)
  ├─ session.get(Purchase) .............. guard → False
  ├─ _purchase_ref_type(purchase.purchase_type) ........ shim → service.purchase_ref_type (pure, PS-P2c-3)
  ├─ reverse_cc_subledgers_for_gl_reference(ref_type, purchase_id)
  ├─ reverse_journal_entries_for(ref_type, purchase_id) ............. [commit per JE]
  ├─ purchase.is_void / voided_at / void_reason = …
  ├─ _void_purchase_linked_payable(purchase_id, reason) ◄── CASCADE
  │     ├─ _linked_purchase_payable(purchase_id) → cq(Payable).filter_by(purchase_id)   [company-scoped, ambient]
  │     └─ if linked & not void:
  │           if linked.paid: reverse_cc_subledgers_for_gl_reference("PayablePayment", linked.id)
  │                           reverse_journal_entries_for("PayablePayment", linked.id)  [extra commits]
  │           linked.is_void / voided_at / void_reason = …
  ├─ session.commit() .................................. [commit]
  └─ log_audit("Void","Purchase",…) .................... [commit]
```

---

## 2. Exact dependencies on the named helpers

| Helper | Location | Used by (void scope) | Notes |
|--------|----------|----------------------|-------|
| `log_audit` | `app.py:1557` | all three | Writes `AuditLog` + **`session.commit()`**; stamps `_current_user()` (ambient/Streamlit). **Cannot move to service** (purity + ambient user). It is the 3rd commit. |
| `reverse_cc_subledgers_for_gl_reference` | `reconciliation/company_card.py:181` | all three (+ cascade) | Clean module; already a service-importable dependency. Voids `BankTransaction` subledger rows by `statement_ref`; for `"PayablePayment"` it iterates the JEs (the `je.id`-keyed asymmetry from PS-P2c). No `import app`. |
| payable cascade helpers (`_create_purchase_payable`, `_update_purchase_payable`, `_sync_purchase_payable_lifecycle`) | `app.py:2428/2450/2468` | **forward/edit path only** — NOT the voids | Share `_linked_purchase_payable` with the void cascade; relevant only because they pin `_linked_purchase_payable` in app.py. |
| `_void_purchase_linked_payable` | `app.py:2415` | `void_purchase` **and** `_sync_purchase_payable_lifecycle` (edit Credit→Cash) | Shared between void and edit lifecycle → entangles `void_purchase` extraction. |
| `_linked_purchase_payable` | `app.py:2411` | `_void_purchase_linked_payable`, `_create/_update_purchase_payable`, `_sync_purchase_payable_lifecycle` | Uses **`cq()`** (company-scoped, ambient). 4 forward-path callers remain in app.py → moving it needs explicit `company_id` + an app shim. |
| `_apply_payable_payment_state` | `app.py:18965` | **NOT a void dependency** — only `app.py:15365` (forward payment UI flow) | Out of scope for PS-P3-2. Listed for completeness: it updates `paid_amount`/`balance`/`paid` *before* a payment GL post; no void path touches it. |

---

## 3. Move-alone analysis

- **`void_expense` — can move alone.** Depends only on `reverse_cc_subledgers_for_gl_reference` (importable), `reverse_journal_entries_for` (already service), entity flags, and `log_audit` (kept app-side). No cascade. ✅
- **`void_payable` — can move alone.** Independent of the purchase cascade (does *not* call `_void_purchase_linked_payable`). Same shape as `void_expense` plus a second `reverse_journal_entries_for("PayableCreation", …)`. ✅
- **`void_purchase` — must move with the payable cascade helpers** (`_void_purchase_linked_payable` + `_linked_purchase_payable`). Because `_linked_purchase_payable` uses `cq()` and is shared with four forward/edit-path callers still in app.py, a clean extraction requires (a) parameterizing it to explicit `company_id` and (b) leaving an app shim for the forward callers — a materially larger surface. **Defer to PS-P3-3.** ❌ for this slice.

---

## 4. Remaining characterization gaps

PS-P3-CHAR (`tests/test_posting_service01_p3_char.py`) is strong: `void_expense` (GL + CC subledger), `void_purchase` (linked-payable cascade + paid `PayablePayment` reversal), `void_payable` (standalone + paid), `void_bank_transaction` guards, **and the commit/audit boundary pinned via `mock_commit.call_count == 3`** for `void_expense` and `void_purchase` (Cash, unpaid).

Small gaps to close before each move:

1. **`void_payable` commit-count pin** — there is a 3-commit assertion for `void_expense` and `void_purchase` but **not** for `void_payable`. Add `call_count` assertion (note: with both a `PayableCreation` and a `PayablePayment` reversal the count differs from 3 — pin the actual current number) before extracting it.
2. **`void_purchase` paid-cascade commit count** (PS-P3-3 prerequisite) — the existing 3-commit pin uses a Cash, unpaid purchase (no cascade). The paid-credit path (`test_void_paid_linked_payable_reverses_payable_payment_gl`) asserts GL effects but **not** the commit count, which is higher there. Pin it before moving `void_purchase`.
3. **`_void_purchase_linked_payable` via edit lifecycle** (PS-P3-3 prerequisite) — confirm the Credit→Cash type-change void path (`_sync_purchase_payable_lifecycle`) is covered (likely in `test_purchase_payable_lifecycle.py` / `test_card_purchase_void_edit.py`) before relocating the shared helper.

None of these block the `void_expense` + `void_payable` slice (item 1 is a quick add).

---

## 5. Recommended smallest safe PS-P3-2 slice

**`void_expense` + `void_payable` together.**
- Extract a **reverse-and-flag core** for each into `services/posting.py` (e.g. `void_expense(session, expense_id, void_reason, *, company_id)` returning `bool`): performs the CC-subledger reversal + `reverse_journal_entries_for` + entity-flag set + the post-flag `session.commit()`. The early-return guards (missing / already void) stay in the core and return `False` with no commit.
- Keep an `app.py` shim that supplies the ambient `company_id` and, on a `True` result, calls `log_audit(...)` — preserving audit placement and the ambient user stamp.
- Import `reverse_cc_subledgers_for_gl_reference` from `reconciliation.company_card` (already done for the kernel).
- Add the §4.1 `void_payable` commit-count pin first.

Pairing them is preferable to two micro-waves: identical structure, shared test fixtures, one shim pattern to review.

**Defer:** `void_purchase` + `_void_purchase_linked_payable` + `_linked_purchase_payable` → **PS-P3-3**, after §4.2/§4.3 land and a decision on the `_linked_purchase_payable` `cq`→explicit-`company_id` + forward-caller shim.

---

## 6. Preserving the 3-commit behavior

The three commits, in order, are:
1. **Reversal-JE commit** inside the extracted `create_journal_entry` kernel (reached via `reverse_journal_entries_for → create_reversing_journal_entry`). Commits internally per TD-PS-01 — **unchanged**.
2. **Post-flag `session.commit()`** after setting `is_void`/`voided_at`/`void_reason`.
3. **`log_audit` commit**.

To preserve exactly (pinned by `call_count == 3`):
- The **service core** owns commits #1 (already, via the primitive) and #2 (the explicit post-flag commit). Do **not** convert to flush or consolidate — that is TD-PS-01 territory and explicitly out of scope for a verbatim move.
- **`log_audit` stays in the app shim** (commit #3), called only on a `True` return, after the core — identical ordering to today. It must not move to the service (ambient `_current_user` + import purity).
- Pass company explicitly: the core calls the **service** `reverse_journal_entries_for` with a required `company_id` (today's shim uses `current_company_required()`, which *raises* when absent) — reproduce that "company required" semantics so void behavior under a missing company context is unchanged.
- Preserve the **early-return `False`** guards before any commit/audit (missing record or already void → no commit, no audit row).
- For `void_payable`, the same pattern holds but the commit count is **not 3** (two `reverse_journal_entries_for` calls over `PayableCreation` + `PayablePayment`, each committing per JE, plus the post-flag and audit commits) — pin the actual number (§4.1) and preserve it; do not "normalize" toward 3.

---

## Risk map

| Item | Risk | Rationale / mitigation |
|------|------|------------------------|
| `void_expense` extraction | **Low** | Flat reverse+flag; fully characterized incl. CC subledger + 3-commit. |
| `void_payable` extraction | **Low** | Same shape; independent of cascade. Add commit-count pin (§4.1) first. |
| `void_purchase` (this slice) | **High** | Cascade helper shared with edit lifecycle; `cq` ambient scoping; variable commit count when payable paid. → **defer**. |
| `log_audit` boundary | **Low (if respected)** | Must stay app-side; moving it breaks purity + drops the ambient user stamp and changes commit #3 placement. |
| `reverse_journal_entries_for` company requirement | **Medium** | Core must pass a *required* company_id (matches `current_company_required()`); using nullable `_current_company_id()` would change missing-context behavior. |
| Commit consolidation temptation | **Medium** | Keeping commits #1/#2 verbatim is mandatory; any flush conversion is TD-PS-01, out of scope. |

---

## Go / No-Go

| Decision | Verdict |
|----------|---------|
| Extract `void_expense` + `void_payable` (reverse-and-flag core to service; `log_audit` in app shim; commits preserved), after the `void_payable` commit-count pin | **GO** |
| Include `void_purchase` in this slice | **NO-GO** — defer to PS-P3-3 with `_void_purchase_linked_payable` + `_linked_purchase_payable` |
| Move `log_audit` to service or consolidate/flush the commits | **NO-GO** — verbatim move only (TD-PS-01 out of scope) |

---

*Audit only. No code modified. Update `POSTING_SERVICE_01_CASCADE_MAP.md` and `AUDIT_HISTORY.md` when PS-P3-2 lands; reconcile the still-missing PS-P2c/PS-P3 ledger entries noted in the PS-P2 completion audit.*
