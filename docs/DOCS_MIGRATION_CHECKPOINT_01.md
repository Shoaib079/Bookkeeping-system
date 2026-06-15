# DOCS-MIGRATION-CHECKPOINT-01 — Migration Register Drift Fix

**Mode:** Documentation only. **No runtime code changes.**

**Date:** 2026-06-05  
**Trigger:** [FASTAPI-READINESS-CHECKPOINT](./FASTAPI_READINESS_CHECKPOINT.md) (conversation audit) found register drift vs repository state.

**Purpose:** Align `ROADMAP.md`, `TECH_DEBT_AND_MIGRATION_CLEANUP.md`, and related handoff docs with code/tests. Historical audits (FUTURE-MIGRATION-AUDIT-01, 2026-06-13) remain valid *baseline snapshots*; this checkpoint supersedes their **blocker/keystone** conclusions where extraction has since shipped.

---

## Status summary (2026-06)

| Area | Status | Notes |
|------|--------|-------|
| **POSTING-SERVICE-01** | ✅ **Complete** | `services/posting.py`; app.py shims delegate; PS-P7 hardening deferred |
| **REPORTS-SERVICE-01** | 🟡 **Partial** | Query layer in `services/read_*`; Streamlit presentation in `app.py` by design |
| **BANKING-SERVICE-01** | 🟡 **Partial** | `services/write_banking.py` manual API writes; recon/import/balance ownership open |
| **FastAPI foundation** | 🟡 **Partial** | P0 reads + P1 JWT + P2 writes (feature-flagged); **not complete** |
| **PostgreSQL runtime** | 🟡 **Partial** | Test-only validation; SQLite remains runtime |
| **React migration** | ⬜ **Not started** | `ERP_DS_05` spec only; no frontend app |

---

## 1. POSTING-SERVICE-01 — Complete

**Evidence:**

- `docs/POSTING_SERVICE_01_STATUS.md` — PS-P0 through PS-P6-5 complete; PS-P7 deferred
- `services/posting.py` — GL kernel (`create_journal_entry`, `post_*`, `void_*`, close/allocation)
- `app.py` — compatibility shims delegate to `posting_service.*`
- **38** test files `tests/test_posting_service01_*.py`

**Deferred (not part of extraction complete):** PS-P7 hardening — commit ownership (TD-PS-01), DTO cleanup (TD-PS-03), reconciliation `_app()` imports (TD-POSTING-06).

---

## 2. REPORTS-SERVICE-01 — Partial (query layer extracted)

**Done (FASTAPI-P0 read services):**

| Module | Scope |
|--------|--------|
| `services/read_reports.py` | P&L, balance sheet, cash flow |
| `services/read_ledger.py` | General ledger page |
| `services/read_ar_ap.py` | Receivables / payables pages |
| `services/read_partner_statement.py` | Partner statements |
| `services/read_balances.py` | Account balances, `compute_liquid_position` |
| `services/read_reconciliation.py` | Statement readiness |

`app.py` retains thin wrappers (`compute_profit_loss_report`, etc.) that pass `company_id=current_company_required()` and **presentation** (`render_profit_loss`, `render_reports`, …). That UI layer is **intentionally** Streamlit-owned until React Phase D.

**Not done:** Formal closure of the ROADMAP item name; any report-specific aggregation still embedded in render formatters (presentation only).

---

## 3. BANKING-SERVICE-01 — Partial

**Done:**

- `services/write_banking.py` — manual deposit / withdrawal / transfer (FASTAPI-P2.7)
- `api/routes/bank_transactions.py` — behind `ERP_API_WRITE_BANKING=1`
- `ui/banking.py` — cockpit, import, recon panels (presentation)

**Open:**

- Reconciliation orchestration — `reconciliation/match_post.py`, `company_card.py` lazy `import app` via `_app()`
- Statement import / match-post workflows still split across `app.py` + `reconciliation/`
- Balance ownership asymmetry (TD-PS-08) — forward posts GL-only; `apply_account_balance_delta` in UI callers
- Full banking subledger service extraction not complete

---

## 4. FastAPI foundation — Partial (not complete)

**Shipped:** `api/main.py` (P1 reads, P2 writes), JWT auth (`services/tokens.py`), `services/write_*.py`, **38** `tests/test_fastapi_*.py`.

**Not complete:**

- Streamlit remains primary UI; write routes require per-slice `ERP_API_WRITE_*=1` flags
- No refresh token / HttpOnly cookie path (AUTH-SESSION-02 IMPL-5+)
- P2-HARDEN-01 — API `company_id` stamping vs Streamlit `before_flush` hook
- PS-P7 posting boundary debt at API layer
- FUTURE-MIGRATION-AUDIT-01 score **62/100** stands as historical baseline; blockers updated here

---

## 5. PostgreSQL runtime — Partial (test readiness only)

**Shipped:** P3.x Alembic program, P4.0/P4.1 test-only PG validation, `optional_postgres` marker, dual-run parity tests.

**Not complete:** `paths.py` `DATABASE_URL` is SQLite; production runtime unchanged; MONEY-DECIMAL-01 open; Alembic authority behind feature flag.

---

## 6. React migration — Not started

**Evidence:** `docs/ERP_DS_05_REACT_ARCHITECTURE.md` — architecture spec only; no `package.json` / SPA tree.

---

## Recommended critical path (migration prep)

Ordered; does **not** authorize FastAPI/React production cutover:

1. **AUTH-SESSION-02-IMPL-3** — true idle extension of `auth_expires`
2. **BANKING-SERVICE-01** — extraction audit; balance ownership; `_app()` removal
3. **P2-HARDEN-01** — API `company_id` stamp audit on P2 write paths
4. **MONEY-DECIMAL-01** — `Float` → `Decimal` before PostgreSQL
5. **PostgreSQL runtime cutover** — after decimal + Alembic authority
6. **React migration** — Phase D; not started

---

## Register updates applied

- `ROADMAP.md` — current priority, FUTURE-MIGRATION-AUDIT section, per-task status
- `docs/TECH_DEBT_AND_MIGRATION_CLEANUP.md` — FUTURE-MIGRATION-AUDIT table, task statuses
- `ARCHITECTURE_HANDOFF.md` — blocker / risk rows

**Contract test:** `tests/test_docs_migration_checkpoint_01.py`

---

*Docs only — no runtime behavior change.*
