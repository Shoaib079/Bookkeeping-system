# P2-HARDEN-01 — Company Stamp Audit

**Mode:** Audit only (2026-06-16 refresh). No implementation. No accounting, schema, feature-flag, or runtime activation changes.

**Goal:** Verify every API-created ORM row receives explicit `company_id` (or an API-session stamp equivalent) before broadening FastAPI write runtime use.

**Baseline:** `pytest tests/test_fastapi_p2_*` + full suite — **4015 passed** (post BS-03/04/05).

---

## Executive summary

| Layer | Verdict |
|-------|---------|
| **Route layer (13 POST writes)** | ✅ All pass `company_id` from `X-Company-Id` → `require_company_write_access`; never from body |
| **`write_*` wrappers (9 modules)** | ✅ All accept explicit `company_id`; none call `app.py` or `_current_company_id()` |
| **Primary entity creation (sales/expense/purchase/banking/receivable)** | ✅ Service sets `company_id` on ORM constructors |
| **Kernel-delegated paths (recon/closing/partner-worker)** | 🟡 Mostly explicit; **2 wrapper-side post-stamps** compensate for kernel gaps |
| **API session `before_flush` hook** | ❌ **Absent** — `get_db()` yields bare `SessionLocal`; hook only active when Streamlit registers it on startup |
| **Overall readiness to enable write flags broadly** | 🟡 **Partial** — known gaps patched at wrapper layer; systemic hook + test matrix still recommended |

---

## 1. Route / service matrix

All write routes are **POST**, feature-flagged (404 when off), and call a `services/write_*` function with **`company_id=company_id`**.

| # | Route | Flag env | Permission | Service | Service function |
|---|-------|----------|------------|---------|------------------|
| 1 | `POST /api/v1/sales` | `ERP_API_WRITE_SALES` | `create_transaction` | `write_sales` | `create_and_post_sale` |
| 2 | `POST /api/v1/expenses` | `ERP_API_WRITE_EXPENSES` | `create_transaction` | `write_expenses` | `create_and_post_expense` |
| 3 | `POST /api/v1/purchases` | `ERP_API_WRITE_PURCHASES` | `create_transaction` | `write_purchases` | `create_and_post_purchase` |
| 4 | `POST /api/v1/receivable-payments` | `ERP_API_WRITE_RECEIVABLE_PAYMENTS` | `create_transaction` | `write_receivable_payments` | `record_receivable_payment` |
| 5 | `POST /api/v1/voids` | `ERP_API_WRITE_VOIDS` | `void_transaction` | `write_voids` | `void_record` |
| 6 | `POST /api/v1/partner-movements` | `ERP_API_WRITE_PARTNER_WORKER` | `post_partner_movement` | `write_partner_worker` | `post_partner_movement_record` |
| 7 | `POST /api/v1/worker-payments` | `ERP_API_WRITE_PARTNER_WORKER` | `post_worker_movement` | `write_partner_worker` | `post_worker_payment_record` |
| 8 | `POST /api/v1/bank-transactions` | `ERP_API_WRITE_BANKING` | `manage_banking` | `write_banking` | `create_manual_bank_transaction` |
| 9 | `POST /api/v1/reconciliation/match` | `ERP_API_WRITE_RECONCILIATION` | `import_bank_statement` | `write_reconciliation` | `match_statement_row` |
| 10 | `POST /api/v1/reconciliation/unmatch` | `ERP_API_WRITE_RECONCILIATION` | `import_bank_statement` | `write_reconciliation` | `unmatch_statement_row` |
| 11 | `POST /api/v1/periods/{id}/close` | `ERP_API_WRITE_CLOSING` | `close_fiscal_period` | `write_closing` | `close_period` |
| 12 | `POST /api/v1/profit-allocations` | `ERP_API_WRITE_CLOSING` | `allocate_profit` | `write_closing` | `allocate` |
| 13 | `POST /api/v1/profit-allocations/{id}/void` | `ERP_API_WRITE_CLOSING` | `void_profit_allocation` | `write_closing` | `void_allocation` |

**Read routes** (`banking`, `reports`, `ledger`, `payables`, `receivables`, `partners`) — out of scope; no mutating POST in audited files.

---

## 2. Explicit `company_id` coverage map

### Stamp hook characterization

| Mechanism | Where | API behavior |
|-----------|-------|--------------|
| Streamlit `before_flush` | `app.py` → `_stamp_company_id_on_new_objects` on `SessionLocal` at startup | **No-op on API** — reads `st.session_state.active_company_id`; empty in API process |
| FastAPI `get_db` | `api/dependencies.py` | Yields `SessionLocal()`; **no stamp hook registered** |
| Test fixtures (partial) | `test_fastapi_p2_banking_write`, `test_fastapi_p2_partner_worker_write`, `test_fastapi_p2_reconciliation_write` | Register `before_flush` manually — **overstates production API safety** for those families unless ambient cleared |

### Per-model / per-path coverage

| Model / path | `company_id` source on API path | Safe? | Notes |
|--------------|----------------------------------|-------|-------|
| **Sale** | `write_sales` constructor | ✅ | |
| **ExpenseRecord** | `write_expenses` constructor | ✅ | |
| **Purchase / Payable** | `write_purchases` constructor | ✅ | |
| **BankTransaction** (manual banking) | `write_banking` constructor | ✅ | |
| **BankTransaction** (sales card path) | `write_sales` when card settlement | ✅ | |
| **BankTransaction** (expense/purchase/receivable bank paths) | respective `write_*` | ✅ | |
| **BankTransaction** (recon `_create_bank_txn`) | `match_post` explicit | ✅ | |
| **BankTransaction** (CC bill CC leg) | `company_card` explicit | ✅ | |
| **BankTransaction** (partner/worker movement) | Kernel omits → **`write_partner_worker._stamp_company_on_movement`** (P2-HARDEN-01a) | ✅ patched | Wrapper post-stamp if NULL |
| **PartnerMovement** | Kernel omits → wrapper stamp (01a) | ✅ patched | |
| **WorkerMovement** | Kernel sets explicit | ✅ | Bank txn still needs wrapper stamp |
| **PartnerProfitAllocation** | Kernel omits → **`write_closing.allocate` post-stamp** (P2.9) | ✅ patched | Duplicate guard depends on stamped row |
| **JournalEntry / lines** | `services.posting.create_journal_entry(..., company_id=...)` | ✅ | Recon kernels pass explicit `company_id` (BS-03 fixed CC bill JE) |
| **BankStatementRow** | Import creates (Streamlit); API match **updates** existing row | ✅ | No API create path |
| **AuditLog** | `audit_svc.record_audit(..., company_id=...)` on all write wrappers | ✅ | |
| **ReceivablePayment** | N/A — JE ref_type + Sale mutation | ✅ | |

### `write_*` module summary

| Module | Explicit ORM stamp | Post-kernel stamp | Delegates to kernels |
|--------|-------------------|-------------------|----------------------|
| `write_sales` | Sale, BankTransaction | — | posting |
| `write_expenses` | ExpenseRecord, BankTransaction | — | posting |
| `write_purchases` | Purchase, Payable, BankTransaction | — | posting |
| `write_receivable_payments` | BankTransaction (bank path) | — | posting |
| `write_banking` | BankTransaction (×2 transfer) | — | posting |
| `write_voids` | — (void only) | — | posting void kernels |
| `write_partner_worker` | — | `_stamp_company_on_movement` | posting movement kernels |
| `write_closing` | — | `allocate` patches allocation | posting close/allocate/void |
| `write_reconciliation` | — | — | `match_post` / `company_card` |

---

## 3. Risk list

| ID | Risk | Severity | Status |
|----|------|----------|--------|
| **PH-01** | API sessions lack Streamlit `before_flush` — NULL `company_id` on unstamped rows | High | Open (systemic) |
| **PH-02** | Posting kernels create movement/allocation rows without `company_id` | Medium | **Mitigated** by wrapper stamps (01a, P2.9) — fragile if new callers skip wrapper |
| **PH-03** | P2 tests register `before_flush` in some fixtures — hides NULL regressions | Medium | Open |
| **PH-04** | No parametrized cross-family `company_id` contract test | Medium | Open |
| **PH-05** | Reconciliation API tests lack explicit `BankTransaction.company_id` / JE assertions after match | Low–Med | Open |
| **PH-06** | Void API tests assert isolation but not stamped entity `company_id` on side effects | Low | Open |
| **PH-07** | Future write endpoints may omit wrapper stamp pattern | Medium | Open until systemic hook (PH-08) |
| **PH-08** | No request-scoped API `before_flush` / contextvar stamp | Medium | Recommended strategic fix |

**Resolved since 2026-06-14 initial audit:**
- Partner/worker movement + bank txn NULL → **P2-HARDEN-01a** (`write_partner_worker._stamp_company_on_movement`)
- PartnerProfitAllocation NULL → **P2.9** (`write_closing.allocate` post-stamp)
- CC bill payment JE ambient company → **BS-03** (explicit `posting.create_journal_entry`)

---

## 4. Tests already covering company stamping

| Test file | Coverage |
|-----------|----------|
| `test_fastapi_p2_sales_write.py` | `Sale.company_id`, JE `company_id`; cross-company rejection; body `company_id` rejected |
| `test_fastapi_p2_expense_write.py` | `ExpenseRecord.company_id`, JE `company_id` |
| `test_fastapi_p2_purchase_write.py` | `Purchase` / `Payable.company_id` |
| `test_fastapi_p2_receivable_payment_write.py` | JE `company_id` |
| `test_fastapi_p2_banking_write.py` | `BankTransaction.company_id`; cross-company bank account |
| `test_fastapi_p2_partner_worker_write.py` | **P2-HARDEN-01a** — movement + bank txn with ambient cleared; boundary mode |
| `test_fastapi_p2_closing_write.py` | `PartnerProfitAllocation.company_id` after allocate; cross-company period/allocation |
| `test_fastapi_p2_void_write.py` | Cross-company void rejection (entity `company_id` match) |
| `test_fastapi_p2_reconciliation_write.py` | Cross-company row/import rejection; body `company_id` rejected |
| `test_fastapi_p0_reconciliation_company_stamp.py` | Recon JE uses explicit `company_id` not ambient (generic deposit, bank charge) |
| `test_banking_service01_char_cc_bill_je_company_stamp.py` | CC bill JE explicit `company_id` (BS-03) |
| `test_fastapi_p2_write_api_inventory.py` | Doc contract — invariants include `X-Company-Id`, never body `company_id` |

**Fixture note:** Banking, partner/worker, and reconciliation P2 tests register Streamlit-style `before_flush` in DB fixtures. Partner/worker additionally **clear ambient** in stamp tests — best current pattern.

---

## 5. Missing tests (recommended before flag broadening)

| Priority | Test | Rationale |
|----------|------|-----------|
| **P0** | `test_p2_harden_01_company_stamp_matrix.py` — parametrized guard: each write family creates rows with `company_id == header company`, **no `before_flush` in fixture** | Systemic regression net |
| **P1** | Reconciliation match: assert `BankTransaction.company_id` + `JournalEntry.company_id` after each match type (ambient cleared) | Kernel-delegated path |
| **P1** | Banking write: drop `before_flush` from fixture; rely on service explicit stamp only | Validates true API path |
| **P2** | Void write: assert voided entity retains correct `company_id`; reversal JE scoped | Side-effect stamp |
| **P2** | Closing close_period: assert `YearEndClose` / period snapshot rows if any lack explicit stamp | Low-volume path |
| **P3** | Contract test referencing this audit doc sections | Doc drift guard (ROADMAP hygiene) |

---

## 6. Safe hardening slices (ordered)

| Slice | Scope | Risk | Notes |
|-------|-------|------|-------|
| **H-01** | Add `test_p2_harden_01_company_stamp_matrix.py` (tests only) | Low | No production change |
| **H-02** | Remove `before_flush` from P2 fixtures where service already stamps explicitly; add assertions | Low | Test-only fidelity |
| **H-03** | Reconciliation match stamp assertions (tests only) | Low | |
| **H-04** | **Systemic:** API session `before_flush` from `RequestContext.company_id` contextvar in `get_db` | Med | Defense-in-depth; mirrors Streamlit |
| **H-05** | Optional: posting kernel explicit `company_id` on movement rows (discouraged per posting rules — prefer H-04 or keep wrappers) | Med–High | Only if wrappers removed |

**Do not combine with:** posting formula changes, GL rule changes, schema migrations, or enabling write flags globally in same PR.

---

## 7. Do-not-touch list

- `services/posting.py` GL kernels and void accounting rules (stamp-only wrappers preferred)
- `apply_account_balance_delta` / `reverse_account_balance_delta` formulas (`services/banking_balance.py`)
- `reconciliation/match_post.py` posting semantics (stamp tests first)
- Streamlit `before_flush` hook behavior in `app.py` (keep until API hook parity proven)
- Feature-flag defaults (remain off until H-01–H-03 green without fixture hook)
- Auth/JWT/session policy (AUTH-SESSION-02 separate track)

---

## 8. Feature-flag recommendation

**Keep all write flags OFF** (`ERP_API_WRITE_*` unset) for production until:

1. H-01 matrix test exists and passes **without** fixture `before_flush`
2. Partner/worker + closing wrapper stamps remain covered (01a / P2.9)
3. Reconciliation stamp assertions added (H-03) or systemic hook shipped (H-04)

| Flag | Safe to enable in dev/staging today? | Blocker |
|------|--------------------------------------|---------|
| `ERP_API_WRITE_SALES` | 🟡 Caution | Missing matrix test; primary entities OK |
| `ERP_API_WRITE_EXPENSES` | 🟡 Caution | Same |
| `ERP_API_WRITE_PURCHASES` | 🟡 Caution | Same |
| `ERP_API_WRITE_RECEIVABLE_PAYMENTS` | 🟡 Caution | Same |
| `ERP_API_WRITE_BANKING` | 🟡 Caution | Fixture registers hook; service explicit OK |
| `ERP_API_WRITE_VOIDS` | 🟡 Caution | Validates entity match; no create stamp issue |
| `ERP_API_WRITE_PARTNER_WORKER` | 🟢 Better | 01a stamp + dedicated tests |
| `ERP_API_WRITE_RECONCILIATION` | 🟡 Caution | Kernels explicit post-BS-03; missing btxn/JE asserts |
| `ERP_API_WRITE_CLOSING` | 🟢 Better | P2.9 stamp + allocation assert |

---

## 9. ROADMAP update recommendation

Update `ROADMAP.md` § P2-HARDEN-01:

- **Status:** Audit complete (2026-06-16) — route + service inventory done; wrapper patches (P2.9, 01a, BS-03) documented
- **Next:** H-01 test matrix (characterization) → H-02 fixture fidelity → optional H-04 systemic hook
- **Do not** mark P2-HARDEN-01 complete until matrix test passes without fixture hook
- Add decision-log entry: `P2-HARDEN-01 audit refresh` pointing to this doc
- Keep priority **#4** in current priority list (after AUTH-SESSION-02-IMPL-3 per latest ROADMAP)

---

## Answers to audit questions

1. **Which write APIs explicitly pass `company_id`?** — All 13 POST write routes (see §1).
2. **Which service functions stamp `company_id` themselves?** — `write_sales`, `write_expenses`, `write_purchases`, `write_banking`, `write_receivable_payments` on constructors; `write_partner_worker` + `write_closing.allocate` post-stamp; `write_reconciliation` delegates to kernels that pass explicit `company_id`.
3. **Which objects may still rely on Streamlit `before_flush`?** — Kernel-created `PartnerMovement`, partner/worker movement `BankTransaction`, `PartnerProfitAllocation` **if wrapper stamp skipped**; any future ORM row created without explicit `company_id` in a code path that only worked on Streamlit.
4. **Which paths are safe?** — Primary-entity write families (sales/expense/purchase/banking/receivable); partner/worker/closing with wrapper stamps; recon kernels post-BS-03.
5. **Which paths need hardening tests?** — Reconciliation match outcomes; banking fixture without hook; parametrized matrix across all families (§5).
6. **Which feature flags should remain off until fixed?** — All write flags for production; dev enablement OK for partner/worker and closing first (§8).

---

*Audit only. No code changed. Doc: `docs/P2_HARDEN_01_COMPANY_STAMP_AUDIT.md`.*
