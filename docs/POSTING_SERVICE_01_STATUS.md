# POSTING-SERVICE-01 — Status

**Last updated:** 2026-06-05 (FASTAPI-REACT-01 posting boundary hardening)

---

## Repository State

| Item | Value |
|------|-------|
| Branch | `main` |
| Latest slice | **FASTAPI-REACT-01** — PS-P7 posting boundary hardening |
| Tag | `fastapi-react-01-posting-boundary-hardening` |
| Audit | [FASTAPI_REACT_01_POSTING_BOUNDARY_AUDIT.md](./FASTAPI_REACT_01_POSTING_BOUNDARY_AUDIT.md) |

---

## Migration Status

### PS-P0 — Complete

### PS-P1 — Complete

### PS-P2 — Complete

### PS-P3 — Complete

### PS-P4 — Complete

### PS-P5 — Complete

### PS-P6-0 — Complete

### PS-P6-1 — Complete

Partner movement posting extracted.

### PS-P6-2 — Complete

Worker movement posting extracted.

### PS-P6-3 — Complete

Profit allocation posting extracted.

| Phase | Commit |
|-------|--------|
| Characterization | `0f9c690` — Characterize profit allocation posting behavior |
| Extraction | `52f1dd8` — Move profit allocation posting to service |

### PS-P6-4 — Complete

Fiscal close and year-end close posting extracted.

| Phase | Commit |
|-------|--------|
| Characterization | `f2adde9` — Characterize fiscal close posting behavior |
| Extraction | `c34db84` — Move fiscal close posting to service |

Pinned:

- `close_fiscal_period`
- `perform_year_end_close`
- `_check_period_continuity`
- `_get_year_bounds`

Behavior preserved:

- 3-commit close path
- 2-commit year-end-close path
- no YEC journal entry
- `allocation_count = len(periods)` quirk
- `net_income_snapshot = Σ` period net income

### PS-P6-5 — Complete (Documentation Only)

| Phase | Commit |
|-------|--------|
| Characterization | `e0c2fff` — Characterize reconciliation posting boundary |

Finding:

- `reconciliation/match_post.py` is orchestration, not a posting kernel
- `create_journal_entry` already delegated to `services.posting`
- remaining `_app()` usage is boundary debt, not extraction debt
- direct rewrite would touch company-stamping behavior

Decision:

- No extraction
- No cleanup
- Defer to PS-P7 hardening

---

## POSTING-SERVICE-01 — Complete

All intended posting-service extraction work is finished.

---

## PS-P7 — Boundary Hardening (FASTAPI-REACT-01)

**Status:** ✅ **Complete (boundary slice)** — accounting kernels unchanged.

| Deliverable | Location |
|-------------|----------|
| Boundary scope helpers | `services/posting_boundary.py` |
| Company resolution helper | `services/posting.py` → `resolve_company_id_for_posting` |
| Additive JE DTO wrapper | `services/posting.py` → `create_journal_entry_result` |
| Streamlit shims | `app.py` — delegate only; boundary scopes imported from service |
| Audit + tests | `docs/FASTAPI_REACT_01_POSTING_BOUNDARY_AUDIT.md`, `tests/test_fastapi_react_01_posting_boundary.py` |

### Remaining hardening debt (deferred — not blockers for extraction)

Do not confuse boundary-scope extraction with kernel/commit/DTO cleanup.

| ID | Topic |
|----|-------|
| **TD-PS-01** | Commit ownership; flip families to `boundary` under API request scope |
| **TD-PS-03** | Route-layer DTO adapters for legacy ORM shim returns |
| **TD-PS-04** | Kernel rollback discarding pending work on closed-year / closed-period posts |
| **TD-PS-06** | Company-scoping cleanup (`calculate_account_balance*` still in app) |
| **TD-PS-07** | Ambient company fallback in Streamlit shims |
| **TD-PS-08** | Banking balance ownership asymmetry |
| **TD-POSTING-06** | `reconciliation/match_post.py` lazy `_app()` imports |

Additional findings (still PS-P7+ scope):

- Reconciliation ambient-vs-explicit company stamping
- `reconciliation/company_card.py` lazy `_app()` debt
- Reconciliation audit policy review (`match_post` posts with no `log_audit`)

### PS-P6-5 note (unchanged)

`reconciliation/match_post.py` is orchestration, not a posting kernel. No extraction in PS-P6-5; boundary debt addressed in FASTAPI-REACT-01 scope doc only.

---

## PS-P7 — Deferred Hardening Debt (superseded header — see above)

Legacy section retained for grep stability; authoritative PS-P7 status is **FASTAPI-REACT-01 complete** with debt table above.

Do not start kernel edits under old "Do not start before characterization" gate — characterization is done.

| ID | Topic |
|----|-------|
| **TD-PS-01** | Commit ownership; multi-commit semantics |
| **TD-PS-03** | DTO / return object cleanup |
| **TD-PS-04** | Kernel rollback discarding pending work on closed-year / closed-period posts (e.g. reconciliation bank-txn + balance delta discarded when `create_journal_entry` guard fires) |
| **TD-PS-06** | Company-scoping cleanup |
| **TD-PS-07** | Ambient company fallback cleanup |
| **TD-PS-08** | Banking balance ownership asymmetry |

Additional findings (PS-P7 scope):

- Reconciliation ambient-vs-explicit company stamping (`match_post` passes explicit `company_id` to records; JE company stamp comes from ambient shim)
- Remaining lazy `_app()` boundary cleanup (`reconciliation/match_post.py` and sibling `reconciliation/company_card.py`)
- Reconciliation audit policy review (`match_post` posts with no `log_audit`; contrast with app-side void/close audit)

### Sibling boundary note

`reconciliation/company_card.py` has the same class of lazy `_app()` debt as `match_post.py`:

- `post_credit_card_bill_payment`
- `void_credit_card_bill_payment`
- `compute_cc_payable_recon_health` (read-only; uses `app.get_account_by_name` / `app.calculate_account_balance`)

These are reconciliation/CC orchestration, not posting kernels. Any PS-P7 boundary rewrite must treat `company_card.py` alongside `match_post.py`.

### `app.py` read helpers (not posting kernels)

The following remain in `app.py` and are **not** extraction targets for POSTING-SERVICE-01:

- `calculate_account_balance` / `calculate_account_balance_for_period`
- `get_worker_advance_balance` / `get_partner_advance_balance`
- `sync_account_balances`

Relevant to TD-PS-06/07 scoping; not GL posting kernels.

---

## Architecture Rule

| Layer | Responsibility |
|-------|----------------|
| **`services/posting.py`** | Accounting kernels (GL posting, void, reversal) |
| **`services/posting_boundary.py`** | Per-family boundary commit scopes (post / void / recon) |
| **`app.py` shims** | Audit (`log_audit` on success) + ambient company resolution (`_current_company_id()` / `current_company_required()`) |
| **`reconciliation/`** | Statement-row orchestration (`match_post`, `company_card`) — creates bank txns, finalizes rows, delegates GL to the kernel |

Permanent principles:

- Service-first
- Accounting logic in services/models
- Thin UI
- No Streamlit state inside accounting logic
- Migration-safe development only

---

## Long-Term Architecture

| Current | Future |
|---------|--------|
| Streamlit | FastAPI |
| SQLAlchemy | SQLAlchemy (retained) |
| SQLite | PostgreSQL |
