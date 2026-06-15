# BANKING-SERVICE-01 — Extraction Readiness Audit

**Mode:** Audit only. **No runtime behavior change.**

**Date:** 2026-06-05  
**Scope:** Banking subledger + reconciliation orchestration readiness before `BANKING-SERVICE-01` code moves.

**Goal:** Map what already lives in `services/`, what still couples to `app.py`, who owns GL posting vs `BankAccount.balance`, safe extraction slices, and test gaps.

---

## 1. Current banking architecture map

### Layer A — Already in `services/` (FastAPI-ready seams)

| Module | Role | GL posting | Balance mutation |
|--------|------|------------|------------------|
| `services/write_banking.py` | Manual deposit/withdrawal/transfer (P2.7) | `posting_svc.post_bank_transaction` / `post_bank_transfer` | `apply_account_balance_delta` **before** GL |
| `services/write_reconciliation.py` | Match/unmatch API wrapper (P2.8) | Delegates to `reconciliation/*` kernels | Via kernels |
| `services/read_reconciliation.py` | Statement readiness / tie-out reads | None | None |
| `services/posting.py` | `post_bank_transaction`, `post_bank_transfer`, `void_bank_transaction` | **GL only** (PS-P4-1) | **Void only** via `reverse_account_balance_delta` |

### Layer B — `reconciliation/` orchestration (partial service extraction)

| Module | Role | `_app()` imports | JE path |
|--------|------|------------------|---------|
| `match_post.py` | Statement row match/post kernels | **8 functions** use `_app()` for `get_account_by_name`, `get_worker_advance_balance`, clearing callback | `_create_je` → `services.posting.create_journal_entry` (explicit `company_id`) |
| `company_card.py` | CC subledger + bill payment + health | **3 sites** (`compute_cc_payable_recon_health`, `post_credit_card_bill_payment`, `void_credit_card_bill_payment`) | Bill payment uses **`app.create_journal_entry`** (ambient company risk) |
| `statement_import.py` | Import staging (no GL) | None | None |
| `clearing.py`, `settlement_import.py`, etc. | POS/settlement helpers | Mostly read/orchestration | Varies |

**Canonical balance helpers (not yet a `services/` module):**

- `reconciliation/company_card.py`: `apply_account_balance_delta`, `reverse_account_balance_delta`
- Imported by: `write_banking.py`, `match_post._create_bank_txn`, `app.py` (`render_banking`, `_record_named_bank_movement`, opening balance), `services/posting.void_bank_transaction`

### Layer C — `ui/banking.py` (presentation + `_erp()` coupling)

- Delegates readiness to `services.read_reconciliation` via thin wrappers (`compute_banking_statement_readiness`)
- **15+ `_erp()` call sites** for translations, bank-fee batch helpers, cockpit, POS settlement UI
- Does **not** own posting kernels; calls into `app.py` helpers for fee batch and visibility blocks

### Layer D — `app.py` (Streamlit primary + duplicate manual-bank path)

| Function / area | Responsibility |
|-----------------|----------------|
| `render_banking` (~21454) | Section router; **inline manual bank form** duplicates `write_banking` logic (`apply_account_balance_delta` + `post_bank_transaction`/`post_bank_transfer`) |
| `_render_banking_statement_import` (~21359) | Legacy CSV quick-import + dispatches to `render_bank_statement_import` |
| `_record_named_bank_movement` (~5944) | Add Transaction bank lines — balance delta + txn row (not always GL) |
| `post_bank_transaction` / `post_bank_transfer` shims | Delegate to `services.posting` |
| `void_bank_transaction` shim | Delegates to `services.posting` (balance reversal inside service) |
| Statement import UI (`_bsi_*`, `render_bank_statement_import`) | Match queue, review, post handlers calling `reconciliation.match_post` directly |

### Layer E — FastAPI (partial parity)

| Route | Service | Flag |
|-------|---------|------|
| `GET /api/v1/banking/readiness` | `read_reconciliation` | None (read) |
| `POST /api/v1/bank-transactions` | `write_banking.create_manual_bank_transaction` | `ERP_API_WRITE_BANKING=1` |
| `POST /api/v1/reconciliation/match` | `write_reconciliation.match_statement_row` → `match_post`/`company_card` | `ERP_API_WRITE_RECONCILIATION=1` |
| `POST /api/v1/reconciliation/unmatch` | `write_reconciliation.unmatch_statement_row` | `ERP_API_WRITE_RECONCILIATION=1` |

**Not exposed via API:** Streamlit statement import staging, legacy CSV path, bank-fee batch UI, full `render_banking` section orchestration, POS settlement posting from UI.

---

## 2. Existing tests map

### Service / API tests (direct)

| Test file | Covers |
|-----------|--------|
| `tests/test_fastapi_p2_banking_write.py` | `write_banking` via HTTP; deposit/withdrawal/transfer; CC guards; audit; void guards |
| `tests/test_fastapi_p2_reconciliation_write.py` | `write_reconciliation` via HTTP; match types incl. `cc_bill_payment`, `bank_charge` |
| `tests/test_fastapi_p0_reconciliation_readiness_service.py` | `read_reconciliation` DTOs |
| `tests/test_fastapi_p0_commit_ownership_reconciliation.py` | Recon commit/boundary scaffold |
| `tests/test_fastapi_p0_reconciliation_company_stamp.py` | JE `company_id` on recon posts |

### Reconciliation kernel tests (indirect banking)

| Test file | Covers |
|-----------|--------|
| `tests/test_phase18_mvp3.py` | `match_post` deposit clearing, generic deposit |
| `tests/test_phase18_mvp4.py`, `mvp5.py` | Partner/vendor/equity match paths |
| `tests/test_cc_bill_payment_void.py` | `company_card` bill payment + void |
| `tests/test_cc_subledger_sync.py`, `test_cc_recon_health.py` | CC subledger + health |
| `tests/test_banking_ux02_p*.py`, `test_banking_ux03_p*.py` | UX contracts; many assert `match_post` **unchanged** |
| `tests/test_posting_service01_p4_*.py` | `post_bank_transaction` / `void_bank_transaction` extraction |

### Missing dedicated tests

- No `tests/test_banking_service01_*` characterization program
- No Streamlit `render_banking` manual form ↔ `write_banking` parity test
- No matrix test for **balance owner** (forward post: caller vs `void_bank_transaction`: service)
- No explicit test that `company_card.post_credit_card_bill_payment` JE uses explicit vs ambient `company_id`
- No audit contract for `_app()` removal readiness (until this doc + `test_banking_service_01_audit.py`)

---

## 3. Risk list

| ID | Risk | Severity | Evidence |
|----|------|----------|----------|
| **BS-AUDIT-01** | **Dual manual-bank implementations** — `render_banking` inline form vs `write_banking` can drift | High | `app.py` ~21663–21698 vs `services/write_banking.py` |
| **BS-AUDIT-02** | **Balance ownership split (TD-PS-08)** — forward posts: callers mutate balance; GL kernel does not; void: service reverses | High | `posting.py` PS-P4-1 comment; `void_bank_transaction` uses `reverse_account_balance_delta` |
| **BS-AUDIT-03** | **`_app()` lazy imports** — `match_post` (8), `company_card` (3), `ui/banking` (15+) | High | Circular dependency + ambient `get_account_by_name` / `create_journal_entry` |
| **BS-AUDIT-04** | **CC bill payment JE via `app.create_journal_entry`** — ambient company stamp | Medium | `company_card.py` ~348 |
| **BS-AUDIT-05** | **Per-row recon commits** — `match_post` uses `_recon_persist`; multi-commit variance | Medium | `_kernel_persist` + `RECONCILIATION_FAMILY` |
| **BS-AUDIT-06** | **Statement-linked void guard** — banking void blocked for `bsr:` refs | Low | `void_bank_transaction` in `posting.py` |
| **BS-AUDIT-07** | **Float balance cache** — `BankAccount.balance` is Float; PG cutover needs decimal plan | Medium | `models.BankAccount`; MONEY-DECIMAL-01 |
| **BS-AUDIT-08** | **UX tests pin `match_post` unchanged** — extractions need characterization-first | Medium | `test_banking_ux03_p2_2.py::test_match_post_unchanged`, etc. |

---

## 4. Safe extraction slices (ordered)

### Slice BS-01 — Read path consolidation (LOW risk)

**Move:** Confirm all readiness callers use `services/read_reconciliation` (already true for `ui/banking` + FastAPI).  
**Do not move:** Streamlit drill/session routing in `ui/banking.py`.

### Slice BS-02 — Replace `_app().get_account_by_name` in `match_post` (LOW–MED)

**Move:** `posting_svc.get_account_by_name(session, ..., company_id=company_id)` at 8 `_app()` call sites.  
**Pre-test:** Characterize account resolution parity per match type.  
**Do not move:** `_finalize_row` semantics, commit boundaries.

### Slice BS-03 — `company_card` JE explicit posting (MED)

**Move:** `post_credit_card_bill_payment` from `app.create_journal_entry` → `services.posting.create_journal_entry` with explicit `company_id`.  
**Pre-test:** Extend `test_fastapi_p0_reconciliation_company_stamp.py` for CC bill path.  
**Do not move:** balance delta formulas in `apply_account_balance_delta`.

### Slice BS-04 — Streamlit manual bank → `write_banking` (MED)

**Move:** `render_banking` manual form calls `create_manual_bank_transaction` instead of inline balance+post.  
**Pre-test:** Streamlit-vs-service parity characterization (amounts, paired transfer, CC guards, audit).  
**Do not move:** void UX, statement import, match queue.

### Slice BS-05 — Balance helper module (MED)

**Move:** `apply_account_balance_delta` / `reverse_account_balance_delta` to `services/banking_balance.py` (re-export from `company_card` during transition).  
**Pre-test:** Matrix: bank asset vs CC liability × deposit/withdrawal/transfer × forward/void.  
**Do not move:** unify forward GL+balance into `post_bank_transaction` without PS-P7 + TD-PS-08 decision.

### Slice BS-06 — Statement import orchestration (HIGH — defer)

**Move:** `statement_import.py` + `app.py` `_bsi_*` staging into `services/banking_import.py`.  
**Do not start** until BS-02–BS-04 characterized; UX tests extensive.

### Slice BS-07 — `ui/banking.py` `_erp()` decoupling (LOW priority, CONTEXT-AUDIT-01)

Inject i18n + fee-batch callbacks; not blocking GL correctness.

---

## 5. Tests to add before each slice

| Slice | Characterization tests to add first |
|-------|-------------------------------------|
| **BS-02** | `test_banking_service01_char_match_post_account_resolution.py` — each match type resolves same GL accounts via posting service |
| **BS-03** | `test_banking_service01_char_cc_bill_je_company_stamp.py` — JE `company_id` explicit under API + Streamlit paths |
| **BS-04** | `test_banking_service01_char_manual_bank_parity.py` — `render_banking` form path vs `create_manual_bank_transaction` (deposit/withdrawal/transfer/CC reject) |
| **BS-05** | `test_banking_service01_char_balance_delta_matrix.py` — forward + void round-trip per account kind |
| **BS-06** | `test_banking_service01_char_statement_import_staging.py` — import row statuses, duplicate detection, no GL side effects |

---

## 6. FastAPI impact

| Area | Current state | Extraction impact |
|------|---------------|-------------------|
| Manual bank writes | **Shipped** — `write_banking` behind `ERP_API_WRITE_BANKING` | BS-04 reduces Streamlit-only drift; API unchanged |
| Recon match writes | **Shipped** — `write_reconciliation` behind `ERP_API_WRITE_RECONCILIATION` | BS-02/BS-03 fix `_app()` debt **inside kernels API already calls** |
| Readiness | **Shipped** — clean `read_reconciliation` | BS-01 doc-only |
| Statement import | **Not in API** | Future slice BS-06 |
| P2-HARDEN-01 | Open | API `company_id` stamping on all ORM rows from write paths |

**Verdict:** FastAPI banking is **partial** — manual + match writes exist but inherit reconciliation `_app()` and balance-split risks.

---

## 7. PostgreSQL impact

| Topic | Impact |
|-------|--------|
| Runtime | SQLite today (`paths.py` `DATABASE_URL`); PG test-only (`ERP_TEST_POSTGRES_URL`) |
| `BankAccount.balance` | `Float` cache — MONEY-DECIMAL-01 required before PG production |
| Statement imports | Large row staging; verify PG parity via `optional_postgres` + dual-run (not all banking paths covered) |
| Alembic | Feature-flagged (`ERP_ALEMBIC_AUTHORITATIVE`); `migrate_schema()` still default |
| Partial indexes | TD-MIG-03 — validate statement/import uniqueness on PG before cutover |

**Verdict:** No PG-specific banking blockers beyond global decimal + migration authority; banking extraction can proceed on SQLite.

---

## 8. Do-not-touch list (until characterized)

1. **`apply_account_balance_delta` / `reverse_account_balance_delta` formulas** — business rules for bank asset vs CC liability
2. **`services/posting.post_bank_transaction` / `post_bank_transfer` GL lines** — PS-P4 characterized kernels
3. **`void_bank_transaction` transfer pairing logic** — `posting.py` ~1614–1627
4. **`match_post._finalize_row`** — row status transitions + immutable history fields
5. **`write_reconciliation._assert_row_history_immutable`** — audit guard
6. **CC bill payment sub-ledger pairing** — `company_card.post_credit_card_bill_payment` dual `BankTransaction` rows
7. **Bank-fee batch posting loop** — `app.py` `_bsi_post_bank_fee_batch` behavior
8. **Legacy CSV quick-import path** — `_render_banking_statement_import` when recon off
9. **UX contract tests that assert `match_post` unchanged** — update only after characterization supersedes them

---

## 9. Headline conclusion

**BANKING-SERVICE-01 is partial, not ready for monolithic extraction.**

- **Done:** `write_banking`, `write_reconciliation`, `read_reconciliation`, posting kernels, FastAPI P2.7/P2.8 routes.
- **Open:** `match_post`/`company_card` `_app()` coupling, duplicate Streamlit manual-bank path, balance ownership asymmetry (TD-PS-08), statement import + match UI in `app.py`, `ui/banking` `_erp()` coupling.
- **Recommended first extraction:** BS-02 (account resolution) → BS-03 (CC bill JE) → BS-04 (Streamlit uses `write_banking`) with new characterization tests.

---

*Audit only — no runtime behavior change.*
