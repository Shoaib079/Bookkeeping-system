# FASTAPI-REACT-03 — Reconciliation Boundary + `_app()` Removal

**Mode:** Service boundary cleanup. **No accounting behavior change.**

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-03** from [FASTAPI_REACT_02 audit §9](./FASTAPI_REACT_02_API_WRITE_HARDENING_AUDIT.md).  
**Tag:** `fastapi-react-03-recon-boundary-commit`

**Prerequisites:** [FASTAPI-REACT-01](./FASTAPI_REACT_01_POSTING_BOUNDARY_AUDIT.md) · [FASTAPI-REACT-02](./FASTAPI_REACT_02_API_WRITE_HARDENING_AUDIT.md) · [P2-HARDEN-01 closure](./P2_HARDEN_01_AUDIT_CLOSURE.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| TD-POSTING-06 `_app()` removal | ✅ **Closed** — `match_post.py` + `company_card.py` call services directly |
| Explicit `company_id` on recon kernels | ✅ Preserved — unchanged from P0.5c / P2 writes |
| TD-PS-01 boundary commit flip | 🟡 **Ready, not flipped** — `write_*` + kernels honor `commit_modes`; default `internal` |
| TD-PS-03 kernel DTOs | ⬜ Deferred — route-layer DTOs only (FR-04+) |
| React bootstrap | ⬜ Not started (out of scope) |

**Posting / GL behavior:** **UNCHANGED** — same JE pairs, match/post orchestration, void cascades.

---

## 2. Characterization — `_app()` removal map

### Before (TD-POSTING-06 debt)

| Module | `_app()` use | Symbol reached |
|--------|--------------|----------------|
| `match_post.py` | `post_worker_statement_match` | `app.get_worker_advance_balance` |
| `company_card.py` | `compute_cc_payable_recon_health` | `app.get_account_by_name`, `app.calculate_account_balance` |
| `company_card.py` | `void_credit_card_bill_payment` | dead `app = _app()` (unused) |

### After (FR-03)

| Module | Replacement |
|--------|-------------|
| `match_post.py` | `services.posting.get_worker_advance_balance(..., company_id=)` |
| `match_post.py` | `services.banking_balance.apply_account_balance_delta` (was via `company_card` import) |
| `company_card.py` | `services.posting.get_account_by_name(..., company_id=)` |
| `company_card.py` | `services.read_balances.calculate_account_balance(..., company_id=)` |

**Frozen contract:** `registry/recon_boundary_contract.py` — forbidden patterns + module list.

---

## 3. TD-PS-01 boundary commit readiness (not flipped)

All `services/write_*.py` modules wrap post/void families in `boundary_commit_scope` when `commit_modes.is_boundary_mode(<FAMILY>)`. Default remains **`internal`**.

| Layer | Boundary hook |
|-------|----------------|
| Streamlit shims | `services.posting_boundary.posting_boundary_scope` / `recon_boundary_scope` / `void_boundary_scope` |
| API write services | `boundary_commit_scope` per family inside `write_*` |
| Recon kernels | `_kernel_persist(..., commit_family=RECONCILIATION_FAMILY)` |

**Dual-run characterization:** `tests/test_fastapi_p0_commit_ownership_*.py` (Streamlit fixtures) + `tests/test_fastapi_p2_*.py` (API writes).

**Production flip:** deferred to **FASTAPI-REACT-04** or dedicated `COMMIT_MODE_*` rollout — requires operator approval and full dual-run matrix green on PG test runtime.

---

## 4. What must NOT change (verified)

- Journal debit/credit math and GL account pairs per match type
- Void/unmatch cascades and audit semantics
- Default commit mode (`internal`)
- Feature flags (`ERP_API_WRITE_*`)
- Docker / React / new API routes

---

## 5. Test plan

```bash
pytest tests/test_fastapi_react_03_recon_boundary.py \
  tests/test_banking_service01_char_match_post_account_resolution.py \
  tests/test_cc_recon_health.py \
  tests/test_fastapi_p0_reconciliation_company_stamp.py \
  tests/test_fastapi_p2_reconciliation_write.py -q

pytest tests/ -q
```

---

## 6. Recommendation / next slice

**FASTAPI-REACT-04** — read API stabilization + TD-PS-01 boundary commit rollout characterization on PostgreSQL test runtime. **Defer React** until FR-04 green.
