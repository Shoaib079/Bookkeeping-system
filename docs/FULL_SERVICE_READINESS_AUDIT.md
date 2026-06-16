# FULL-SERVICE-READINESS-AUDIT

**Mode:** Audit only. **No runtime behavior change.**

**Date:** 2026-06-05  
**Trigger:** Pre-extraction checkpoint across posting, reads, banking, auth, receipt AI, FastAPI, PostgreSQL, React.

**Test baseline:** `pytest tests/` — **3925 passed**, 9 skipped, 2 xfailed (BS-02-CHAR run).

---

## 1. Full status table

| Area | Status | Notes |
|------|--------|-------|
| **Posting / accounting (POSTING-SERVICE-01)** | **Complete** | Kernel in `services/posting.py`; app shims delegate; PS-P7 hardening **Deferred** |
| **Reports / reads (REPORTS-SERVICE-01)** | **Partial** | Query layer in `services/read_*`; presentation + trial balance loop in `app.py` |
| **Banking / reconciliation (BANKING-SERVICE-01)** | **Partial** | `write_*` + `read_reconciliation` shipped; `match_post`/`company_card` `_app()` debt |
| **Auth / sessions (AUTH-SESSION-02)** | **Partial** | IMPL-1/2 wired (`session_policy`); idle/remember/revocation **Not started** |
| **Receipt AI / learning** | **Partial** | Services + prefill UI; approval/void learning hooks **Deferred** |
| **FastAPI foundation** | **Partial** | P0–P2 routes + 38 test files; writes flag-gated; gaps in settings/staff/DSC |
| **PostgreSQL / Alembic** | **Partial** | SQLite runtime; PG test-only; Alembic behind `ERP_ALEMBIC_AUTHORITATIVE` |
| **React** | **Not started** | `ERP_DS_05` spec only; no SPA |
| **Audit service** | **Partial** | `services/audit.py` exists; `app.log_audit` shim + 80+ ambient call sites |
| **Context / permissions** | **Partial** | `services/context.py`, `user_access.py`; `app._can` / `cq()` ambient |
| **Other domain services (DSC, RC, SC, UA)** | **Complete** (service layer) | Thin UI in `ui/*`; staff capture `post_fn` seam |

---

## 2. Service inventory (primary + migration-critical)

| Service file | Purpose | Main callers | Tests | FastAPI-ready | Remaining `app.py` dependency |
|--------------|---------|--------------|-------|---------------|------------------------------|
| `posting.py` | GL kernel, `post_*`, `void_*`, close | app shims, `write_*`, `match_post._create_je` | 38× `test_posting_service01_*` | Structurally yes; boundary debt (TD-PS-01/03) | Shims + audit on success |
| `read_reports.py` | P&L, BS, CF DTOs | app wrappers, `api/routes/reports` | `test_fastapi_p0_reports_read_service` | Yes | `render_profit_loss*` UI |
| `read_ledger.py` | GL page DTO | app, `api/routes/ledger` | `test_fastapi_p0_ledger_read_service` | Yes | `render_general_ledger` UI |
| `read_ar_ap.py` | AR/AP pages | app, `api/routes/receivables|payables` | `test_fastapi_p0_ar_ap_read_service` | Yes | `render_receivables/payables` UI |
| `read_balances.py` | Balances, liquid position | app, dashboard | `test_fastapi_p0_balance_read_service`, `test_dash_cash_01_*` | Yes | `sync_account_balances`, trial balance loop |
| `read_partner_statement.py` | Partner statements | app, `api/routes/partners` | `test_fastapi_p0_partner_statement_read_service` | Yes | Partner pages UI |
| `read_reconciliation.py` | Statement readiness | `ui/banking`, `api/routes/banking` | `test_fastapi_p0_reconciliation_readiness_service` | Yes | None (reads) |
| `write_banking.py` | Manual bank writes | `api/routes/bank_transactions` | `test_fastapi_p2_banking_write` | Yes | `render_banking` delegates (**BS-04 ✅**) |
| `write_reconciliation.py` | Match/unmatch API | `api/routes/reconciliation` | `test_fastapi_p2_reconciliation_write` | Yes (wrapper) | Kernels use `_app()` |
| `write_sales.py` … `write_closing.py` | P2 write families | respective `api/routes/*` | `test_fastapi_p2_*` | Yes with flags | Streamlit AT/sales still in app |
| `audit.py` | `record_audit` | `write_*`, some kernels | `test_fastapi_p0_audit_service` | Yes | `app.log_audit` ambient shim |
| `context.py` | `RequestContext` | FastAPI deps | `test_fastapi_p0_request_context` | Yes | `app._current_*` not replaced |
| `tokens.py` | JWT access | `api/routes/auth` | `test_fastapi_p1_auth_tokens` | Partial | No refresh; Streamlit separate |
| `session_policy.py` | TTL policy | `app.py` auth | `test_auth_session_02_impl_1/2` | Yes | Idle extension not wired |
| `auth.py`, `login.py`, `auth_profile.py` | Password + API login | FastAPI auth | `test_fastapi_p1_auth_*` | Yes | Streamlit `_login` separate |
| `receipt_ai.py` | Extractor seam | adapter | `test_receipt_ai_01_service` | Yes | No OCR |
| `receipt_ai_adapter.py` | Draft/suggestion UI seam | `ui/staff_capture` | `test_receipt_ai_01_impl_2_adapter` | Yes | `_erp()` in UI |
| `receipt_learning.py` | Learn on approval | **tests only** (not app void) | `test_receipt_ai_02_*` | Yes | Approval hook not wired |
| `receipt_learning_store.py` | Persistent map | learning service | `test_receipt_ai_02_impl_3` | Yes | — |
| `receipt_learning_prefill.py` | Category prefill | adapter + UI | `test_receipt_ai_02_impl_5` | Yes | — |
| `receipt_suggestion_capture.py` | Suggestion rows | adapter | `test_receipt_ai_02_impl_2` | Yes | — |
| `staff_capture.py` | Expense drafts | `ui/staff_capture`, app `post_fn` | `test_staff_capture01_*` | Yes | `_erp()` UI |
| `daily_sales_close.py` | ESV service | `ui/external_sales_verification` | `test_daily_sales_close_*` | Yes | `_erp()` UI |
| `recipe_costing.py` | RC service | `ui/recipe_costing` | `test_recipe_costing_*` | Yes | `_erp()` UI |
| `user_access.py` | Permissions | app `_can`, UI | `test_user_access01_*` | Yes | Session cache in app |
| `schema_startup*.py` | Alembic gate | app startup | `test_p3_8_*`, `test_p3_9_*` | N/A (infra) | `migrate_schema()` default |

---

## 3. `app.py` dependency map

### A. Extracted — shims only (safe to keep until React)

All `post_*` / `void_*` / `create_journal_entry` at ~1633–8264 delegate to `posting_service` (**56 call sites**). Shims add:

- Ambient `company_id` resolution
- `log_audit` on success (ambient `performed_by`)
- Some orchestration (partner/worker movement wrappers, cash recon submit/approve)

### B. Partial — business logic still in `app.py`

| Category | Examples | Risk if moved without char tests |
|----------|----------|----------------------------------|
| **Report presentation** | `render_profit_loss`, `render_reports`, `render_trial_balance` | Low (UI) |
| **Report compute wrappers** | `compute_*_report` → already delegate to `read_*` | Low |
| **Trial balance aggregation** | `render_trial_balance` loops `calculate_account_balance` | Med — extract to `read_balances` |
| **Banking manual form** | ~~`render_banking` duplicates `write_banking`~~ **BS-04 ✅** — delegates to `create_manual_bank_transaction` | Resolved |
| **Statement import UI** | `render_bank_statement_import`, `_bsi_*` | **High** |
| **Add Transaction** | `render_add_transaction` ~14093 | **High** — multi-post orchestration |
| **Opening balances** | `render_opening_balances` | Med |
| **Cash recon / EOD** | `render_cash_reconciliation`, `render_end_of_day_close` | Med |
| **Balance cache** | `sync_account_balances` ~2379 | Med |
| **Advance balances** | `get_worker/partner_advance_balance` | Med — used by `match_post._app()` |
| **Auth** | `_login`, `_establish_auth_session`, restore cookie JS | Med |
| **Audit shim** | `log_audit` ~1582 → `_audit_svc` with ambient user | Med |
| **Company stamp hook** | `_stamp_company_id_on_new_objects` ~3068 | **High** (P2-HARDEN-01) |
| **Ambient context** | `_current_user`, `_current_company_id`, `cq`, `_can` | **High** |

### C. UI-only — can stay until React Phase D

- All `render_*` page shells (dashboard, COA, members, settings, backup)
- `render_export_buttons`, pagination, sidebar filters
- `ui/banking.py`, `ui/staff_capture.py`, etc. (presentation; `_erp()` debt is CONTEXT-AUDIT-01)

### D. Dangerous to move now (uncharacterized)

- `reconciliation/match_post.py` finalize + commit boundaries
- `apply_account_balance_delta` formulas
- `company_card.post_credit_card_bill_payment` JE path
- `void_bank_transaction` transfer pairing
- Receipt learning approval/void hooks into expense lifecycle
- Any `migrate_schema()` / startup sequencing

---

## 4. Test coverage map

| Area | Characterization / contract tests | Gaps before extraction |
|------|--------------------------------|------------------------|
| **Posting** | 38× `test_posting_service01_*` (P0–P6) | PS-P7 commit ownership char |
| **Reads** | `test_fastapi_p0_*_read_service` (6 modules) | Trial balance service char |
| **Banking** | Phase18, CC, UX02/03, `test_fastapi_p2_banking_write` | `test_banking_service01_char_*` (none yet) |
| **Recon match** | `test_phase18_mvp*`, `test_fastapi_p2_reconciliation_write` | `_app()` removal char per match type |
| **Auth session** | `test_auth_session_02_impl_1/2`, `test_ux01_session_restore` | IMPL-3 idle extension char |
| **FastAPI writes** | 10× `test_fastapi_p2_*` + P0 commit ownership | P2-HARDEN-01 company stamp matrix |
| **Receipt AI** | 13× `test_receipt_ai_*` | Approval/void wiring integration char |
| **PostgreSQL** | `test_p3_*`, `test_p4_*` (29+ files) | Runtime cutover char (deferred) |
| **React** | None | N/A |

---

## 5. Contradictory docs

| Doc | Says | Code truth |
|-----|------|------------|
| `docs/AUDIT_HISTORY.md` § 2026-06-13 | POSTING-SERVICE-01 is key blocker | **Complete** — `services/posting.py` |
| `docs/fastapi_p2_write_api_inventory.md` footer | "No endpoints implemented" | P2.1–P2.9 routes exist in `api/routes/` |
| `docs/FASTAPI_MIGRATION_01_AUDIT.md` §2 | Reports/ledger "not in services" | `services/read_*` extracted (wrappers remain) |
| `docs/AUTH_SESSION_02_AUDIT.md` §8 | IMPL-2 = remember-me checkbox | Working tree: IMPL-2 = `browser_session` policy wiring |
| `ROADMAP.md` changelog 2026-06-13 | Keystone POSTING open | Superseded by DOCS-MIGRATION-CHECKPOINT-01 (if committed) |
| `docs/RECEIPT_AI_02_IMPL_3.md` | Store not wired to approval | Still true for `record_approval` in app flow |

**Aligned docs:** `POSTING_SERVICE_01_STATUS.md`, `BANKING_SERVICE_01_AUDIT.md`, `DOCS_MIGRATION_CHECKPOINT_01.md` (local/uncommitted).

---

## 6. Recommended next 5 actions (safest order)

1. **BS-02 char tests** — `match_post` account resolution via `posting.get_account_by_name` (no behavior change yet)
2. ~~**BS-04 char tests**~~ **BS-04 ✅** — `render_banking` manual form → `write_banking.create_manual_bank_transaction`
3. **AUTH-SESSION-02-IMPL-3 char** — idle extension contract before wiring `should_extend_idle`
4. **P2-HARDEN-01 audit tests** — API-created ORM rows `company_id` matrix across `write_*` paths
5. **Receipt learning wiring char** — define approval/void hook points in `staff_capture` / `void_expense` before calling `record_approval`

---

## 7. Do-not-touch list

1. `services/posting.py` GL line construction and void pairing logic  
2. `apply_account_balance_delta` / `reverse_account_balance_delta`  
3. `match_post._finalize_row` and immutable row history guards  
4. `write_reconciliation._assert_row_history_immutable`  
5. `company_card.post_credit_card_bill_payment` dual-txn pairing  
6. Restore cookie HMAC format and `ph_frag` validation  
7. `migrate_schema()` + `MigrationFlag` one-time seeds  
8. UX tests asserting `match_post` unchanged (update only after char supersedes)  
9. POS AI / cash-card / Z-report surfaces (out of scope)  
10. PS-P7 internal commit semantics without characterization  

---

## Area summaries (evidence)

### 1. Posting / accounting

- **Complete extraction:** `services/posting.py` (~2778 lines); PS-P0–P6-5 per `POSTING_SERVICE_01_STATUS.md`
- **App shims:** `create_journal_entry`, all `post_*`, all `void_*`, close/allocation delegate to `posting_service`
- **Deferred PS-P7:** TD-PS-01 commit ownership, TD-PS-03 DTOs, TD-PS-06/07 company scoping, TD-PS-08 balance asymmetry, TD-POSTING-06 `_app()` in recon
- **Remaining accounting in app:** `sync_account_balances`, advance balance helpers, trial balance aggregation, AT multi-post orchestration, cash recon workflow, opening balances
- **Company stamp:** Streamlit `before_flush` `_stamp_company_id_on_new_objects`; FastAPI `get_db` does not — P2-HARDEN-01 open

### 2. Reports / reads

- **Extracted computes:** `read_reports`, `read_ledger`, `read_ar_ap`, `read_balances`, `read_partner_statement`, `read_reconciliation`
- **App wrappers:** `compute_profit_loss_report` etc. pass `current_company_required()`
- **Still in app (logic):** `render_trial_balance` aggregates per-account balances inline; `sync_account_balances` updates COA cache from JE
- **UI-only:** `render_reports`, KPI formatting, export buttons — keep until React

### 3. Banking / reconciliation

- See `BANKING_SERVICE_01_AUDIT.md` for full map
- **Balance ownership:** forward posts — callers (`write_banking`, `match_post`, `render_banking`); void — `posting.void_bank_transaction`
- **`_app()`:** `match_post` (8), `company_card` (3); **`_erp()`:** `ui/banking` (15+)

### 4. Auth / sessions

- **Wired:** `session_policy` → `_active_session_policy`, `session_started_at`, `compute_session_expiry`, cookie max-age
- **Not wired:** `should_extend_idle`, remember-device, `token_version` column, refresh token, HttpOnly cookie
- **Streamlit:** restore cookie via JS; **FastAPI:** `services/tokens.py` access JWT 30m; `POST /auth/login`

### 5. Receipt AI / learning

| Component | Status |
|-----------|--------|
| `receipt_ai.py` + adapter | Complete (fake extractor, draft flow) |
| `receipt_suggestion_capture` | Complete |
| `receipt_learning` + store | Complete (service + DB) |
| `receipt_learning_prefill` | Complete — wired in `ui/staff_capture` |
| `record_approval` on approve | **Deferred** — not in app/staff_capture approval path |
| `record_void_reversal` on void | **Deferred** — not in `void_expense` |
| OCR / auto-post | **Not started** (by design) |

### 6. FastAPI

**Routes (`api/main.py` v1.4.7):**

| Prefix | Methods | Flag |
|--------|---------|------|
| `/health` | GET | — |
| `/auth` | POST login, GET me/companies | — |
| `/api/v1/reports` | GET P&L, BS | — |
| `/api/v1/ledger` | GET | — |
| `/api/v1/receivables`, `/payables` | GET | — |
| `/api/v1/partners` | GET statement | — |
| `/api/v1/banking` | GET readiness | — |
| `/api/v1/sales` … `/closing` | POST writes | `ERP_API_WRITE_*=1` |

**Not in API:** settings/registry, staff capture, DSC, attachments, transaction history list, full banking import, permissions admin writes.

### 7. PostgreSQL / Alembic

- **Runtime:** `paths.py` → `sqlite:///…/erp_data.db`
- **PG:** `ERP_TEST_POSTGRES_URL` + `@pytest.mark.optional_postgres`
- **Alembic:** `ERP_ALEMBIC_AUTHORITATIVE` default off → `migrate_schema()` on startup
- **Blockers:** MONEY-DECIMAL-01, Alembic authority bake-in, TD-MIG-03 constraints

### 8. React readiness

- **No** `package.json` / SPA source
- **Spec:** `docs/ERP_DS_05_REACT_ARCHITECTURE.md` — 42 nav routes mapped; FastAPI client assumed
- **Missing contracts:** Settings API, staff portal routes, attachment upload API, full banking import API

---

*Audit only — no runtime behavior change.*
