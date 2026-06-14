# P2-HARDEN-01 — Company-Stamp Audit (audit only)

**Mode:** Audit only. No implementation. No accounting/audit/permission/UI/schema/kernel changes.
**Goal:** verify every API-created ORM row receives an explicit `company_id` without relying on the Streamlit `SessionLocal` `before_flush` hook.

## Characterization of the stamp hook

`app.py:3032` registers `@event.listens_for(SessionLocal, "before_flush")` → `_stamp_company_id_on_new_objects`, which stamps `obj.company_id = _current_company_id()` for new objects **only when `_current_company_id()` (Streamlit `st.session_state`) is not None.**

Implications for the API:
- The hook is bound to `db.SessionLocal`. The API's `get_db` uses `db.SessionLocal`, **but** the hook reads `st.session_state`, which is empty/mocked in an API process → `_current_company_id()` returns `None` → **the hook returns early and stamps nothing.**
- Therefore the hook is effectively a **no-op on the API path.** API-created rows are correctly company-scoped **only if the row's `company_id` is assigned explicitly** (constructor or service/wrapper), never via the hook.
- Test sessions in `tests/test_fastapi_p2_*` don't register the hook at all, so they faithfully reproduce the API's "no hook" behaviour.

## Audit table

| Model | Current source of `company_id` (API path) | API safe? | Risk | Recommendation |
|-------|-------------------------------------------|-----------|------|----------------|
| **Sale** | Service explicit — `write_sales.py:115` (`company_id=company_id`) | ✅ Yes | None | No change; add test guard (D) |
| **ExpenseRecord** | Service explicit — `write_expenses.py:263/279`; recon ad-hoc `match_post.py:844` explicit | ✅ Yes | None | No change; add test guard (D) |
| **Purchase** | Service explicit — `write_purchases.py:345/358` | ✅ Yes | None | No change; add test guard (D) |
| **Payable** | Service explicit — `write_purchases.py:249, 403/412` | ✅ Yes | None | No change; add test guard (D) |
| **PartnerProfitAllocation** | Kernel `posting.py:2280` has **no** `company_id`; **now stamped by wrapper** `write_closing.allocate` (P2.9 fix) | ✅ Yes (post-P2.9) | Was NULL; fixed | Keep wrapper stamp; lock with test (already added) |
| **BankTransaction** (sales/expense/purchase/receivable/banking) | Service explicit — `write_*.py` (e.g. `write_expenses:201/207`, `write_receivable_payments:121/127`, `write_purchases:206/212`, `write_banking:200/290/298`) | ✅ Yes | None | No change; add test guard (D) |
| **BankTransaction** (reconciliation match/post, CC subledger) | Service explicit — `match_post.py:107` (`_create_bank_txn`), `company_card.py:138/330` | ✅ Yes | None | No change |
| **BankTransaction** (partner movement) | **Kernel `posting.py:1852` — NO `company_id`** | ❌ **No** | **NULL in API** | **Wrapper stamp (A)** or shared hook (B) |
| **BankTransaction** (worker movement) | **Kernel `posting.py:2069` — NO `company_id`** | ❌ **No** | **NULL in API** | **Wrapper stamp (A)** or shared hook (B) |
| **PartnerMovement** | **Kernel `posting.py:1866` — NO `company_id`** | ❌ **No** | **NULL in API** | **Wrapper stamp (A)** or shared hook (B) |
| **WorkerMovement** | Kernel explicit — `posting.py:2087/2102` (`company_id=company_id`) | ✅ Yes | None | No change; add test guard (D) |
| **ReceivablePayment** | **No such model** — receivable payment = `JournalEntry` (ref_type `ReceivablePayment`, kernel-stamped) + `Sale` mutation + optional service-explicit `BankTransaction` | ✅ Yes (n/a) | None | No change |
| **Reconciliation rows** — `DailyCashReconciliation` | Streamlit-only (`app.py`); **no API endpoint creates it** | ✅ Yes (no API path) | None now | No change; guard if a cash-recon write API is added |
| **Reconciliation rows** — `BankStatementRow` | Created at import (Streamlit); match/post **updates** existing rows, doesn't create them | ✅ Yes (no API create) | None | No change |
| **JournalEntry / JournalEntryLine** | Kernel explicit — `create_journal_entry` sets `company_id=_cje_cid` on entry + lines | ✅ Yes | None | No change |

## Findings (detail)

1. **The risk is concentrated in three kernel-created rows in the partner/worker movement path** (`posting.py`):
   - `PartnerMovement` (`:1866`) — no `company_id`.
   - Partner-movement `BankTransaction` (`:1852`) — no `company_id`.
   - Worker-movement `BankTransaction` (`:2069`) — no `company_id`.
   These are reached by the API via `services/write_partner_worker.py` → `posting.post_partner_movement` / `post_worker_movement`. On the API session (no stamp), they persist with `company_id = NULL`.

2. **Asymmetry within the same kernel function:** `WorkerMovement` (`:2087`) sets `company_id` explicitly, but the worker's paired `BankTransaction` (`:2069`) does not; `PartnerMovement` (`:1866`) sets neither itself nor its `BankTransaction` (`:1852`). This is an inconsistency, not a design choice.

3. **Consequences of NULL `company_id`** (not just cosmetic):
   - Company-scoped **banking** views/queries filter `BankTransaction.company_id` → a NULL-company movement bank-txn is **invisible/orphaned** for that company.
   - **Partner statement** aggregation filters `PartnerMovement` by `company_id` → an API-created partner movement with NULL company would be **excluded**, producing an incorrect statement.
   - `void_bank_transaction`'s paired-transfer lookup is `cq`/company-scoped → a NULL-company txn won't be found.
   - This is the **same class of latent bug** that surfaced as the P2.9 duplicate-allocation failure (guard filtered on `company_id`, row had NULL).

4. **Everything else is safe:** all `write_*` boundary wrappers, the reconciliation `match_post`/`company_card` orchestrators, the worker movement record, and the JE kernel assign `company_id` explicitly. `ReceivablePayment` is not a model. `DailyCashReconciliation`/`BankStatementRow` have no API creation path today.

5. **Existing test coverage:** `tests/test_fastapi_p2_partner_worker_write.py` exercises the partner/worker API but (per this audit) does not assert `company_id` on the created movement/bank-txn rows, so the NULL would pass unnoticed today. `tests/test_fastapi_p2_closing_write.py::test_allocate_duplicate_rejected` now locks the allocation case. Other write families have entity-creation tests but should add explicit `company_id` assertions (D).

## Proposed patches (described — NOT applied)

**Targeted (tactical), for the three risk rows:**
- In `services/write_partner_worker.py`, after the kernel returns the movement id, re-fetch the `PartnerMovement`/`WorkerMovement` and its linked `BankTransaction` and stamp `company_id = company_id` when `None` — mirroring the P2.9 `write_closing.allocate` precedent. (Wrapper-side; no kernel edit.)

**Systemic (strategic):**
- Register a `before_flush` stamp hook on the **API session** (in `api/dependencies.get_db`, or a dedicated API sessionmaker) that sources `company_id` from a **request-scoped context** (a `contextvar` set by `get_request_context` from `RequestContext.company_id`), stamping any new row whose `company_id is None`. This reproduces the Streamlit guarantee for the API uniformly and prevents recurrence as new write endpoints are added.

**Safety net (regardless of which above):**
- Add assertions to the partner/worker write tests (and a small parametrized guard across write families) that every API-created row has `company_id == active company`.

## Recommendation on fix form (A / B / C / D)

| Option | Verdict |
|--------|---------|
| **A — wrapper-side stamp** | **Recommended as the immediate tactical fix** for the 3 risk rows (consistent with the approved P2.9 precedent; no kernel change; minimal blast radius). |
| **B — shared API session stamp hook** | **Recommended as the strategic fix.** It is the only option that *systemically* guarantees the invariant for **all current and future** API rows (defense-in-depth), mirroring Streamlit's existing hook. Slightly larger but well-bounded, non-accounting change (needs a request-scoped `company_id` contextvar). |
| **C — service/kernel explicit assignment** | **Discouraged for the kernel** (rules: prefer wrapper over kernel; no kernel change unless unavoidable). Acceptable only as wrapper-level explicit assignment, which collapses into A. |
| **D — test-only guard** | **Necessary but not sufficient** — add as a safety net alongside A or B; it detects regressions but does not fix the NULL data. |

**Overall:** pursue **B (systemic hook) as the durable fix**, with **A (wrapper stamps)** as the immediate remediation for the three known rows if B is deferred, and **D (assertions)** added either way. Avoid **C** (kernel edits) per the stated rules.

---

*Audit only. No code changed. The single concrete API-path defect class remaining is NULL `company_id` on kernel-created PartnerMovement and partner/worker BankTransactions; all other audited models are explicitly stamped (or have no API creation path). Awaiting approval before implementing.*
