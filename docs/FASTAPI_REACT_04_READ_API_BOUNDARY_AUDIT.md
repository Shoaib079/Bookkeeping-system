# FASTAPI-REACT-04 — Read API Stabilization + Commit Boundary Characterization

**Mode:** Verification + contract closure. **No accounting behavior change.**

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-04** from [FASTAPI_REACT_03 audit §6](./FASTAPI_REACT_03_RECON_BOUNDARY_AUDIT.md).  
**Tag:** `fastapi-react-04-read-api-boundary-commit`

**Prerequisites:** [FASTAPI-REACT-02](./FASTAPI_REACT_02_API_WRITE_HARDENING_AUDIT.md) · [FASTAPI-REACT-03](./FASTAPI_REACT_03_RECON_BOUNDARY_AUDIT.md) · P1.1/P1.2 read API · P0.5d commit ownership

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Read API OpenAPI spine | ✅ **Closed** — 11 GET paths + auth; P1.1/P1.2 tests |
| HTTP error contract | ✅ **Frozen** — 401/400/403/404/422 mapping |
| Read services (DTO-oriented) | ✅ `services/read_*` + `api/serialization.py` |
| TD-PS-01 dual-run characterization | ✅ **Closed (SQLite)** — 9 `test_fastapi_p0_commit_ownership_*` files |
| TD-PS-01 production boundary flip | ⬜ **Deferred** — default `internal`; `COMMIT_MODE_*` env only |
| TD-PS-01 PG dual-run matrix | 🟡 **Substrate exists** — `test_postgres_*` runtime; family matrix not re-pinned on PG |
| React bootstrap | ⬜ Not started (out of scope) |

**Posting / GL behavior:** **UNCHANGED** — no commit mode flips, no kernel edits.

---

## 2. Read API inventory (frozen)

Contract: `registry/api_read_contract.py` → `READ_API_PATHS`.

| Path | Tag | Service |
|------|-----|---------|
| `/health` | health | inline |
| `/auth/login` | auth | JWT issue |
| `/auth/me` | auth | user context |
| `/auth/companies` | auth | membership list |
| `/api/v1/reports/profit-loss` | reports | `read_reports` |
| `/api/v1/reports/balance-sheet` | reports | `read_reports` |
| `/api/v1/ledger` | ledger | `read_ledger` |
| `/api/v1/receivables` | receivables | `read_ar_ap` |
| `/api/v1/payables` | payables | `read_ar_ap` |
| `/api/v1/partners/{partner_id}/statement` | partners | `read_partner_statement` |
| `/api/v1/banking/readiness` | banking | `read_reconciliation` |

**Consumer smoke:** `tests/test_fastapi_p1_api_contract.py` (OpenAPI + errors) · `tests/test_fastapi_p1_read_endpoints.py` (200 + JSON primitives).

---

## 3. Error contract (frozen)

Documented in `api/main.py` description and `api/errors.py`:

| Status | Condition |
|--------|-----------|
| **401** | Missing/invalid bearer token |
| **400** | Missing `X-Company-Id` (`active_company_id`) |
| **403** | Membership denied or permission denied |
| **404** | Scoped resource not found |
| **422** | Query/path/body validation |

**Invariant:** GET handlers do not commit (`api/dependencies.get_db` yields bare session).

---

## 4. TD-PS-01 boundary characterization

Contract: `registry/commit_boundary_contract.py` → `COMMIT_FAMILY_CHARACTERIZATION`.

| Layer | Boundary hook |
|-------|----------------|
| Streamlit | `services/posting_boundary.py` |
| API writes | `services/write_*` → `is_boundary_mode` + `boundary_commit_scope` |
| Kernels | `_kernel_persist(..., commit_family=...)` |

**Dual-run tests (SQLite):** one or more `test_fastapi_p0_commit_ownership_*.py` per family — internal vs boundary persisted-state parity.

**Default mode:** all families `CommitMode.INTERNAL` (`services/commit_modes.py`).

**Production flip:** `COMMIT_MODE_<FAMILY>=boundary` env override exists; **not enabled** in production. PG re-pin deferred to **FASTAPI-REACT-05** or operator cutover slice.

---

## 5. Documented gaps (deferred)

| ID | Gap | Next slice |
|----|-----|------------|
| **TD-PS-01** | PG dual-run matrix for all families | FASTAPI-REACT-05 or operator rollout |
| **TD-PS-03** | Kernel ORM → stable JSON DTOs at route layer | FASTAPI-REACT-05+ serialization |

---

## 6. What must NOT change (verified)

- Journal math and GL pairs
- Default commit mode (`internal`)
- Read route paths and error status mapping
- Feature flags (`ERP_API_WRITE_*`)
- Docker / React / new routes

---

## 7. Test plan

```bash
pytest tests/test_fastapi_react_04_read_api_boundary.py \
  tests/test_fastapi_p1_api_contract.py \
  tests/test_fastapi_p1_read_endpoints.py \
  tests/test_fastapi_p0_commit_ownership_*.py -q

pytest tests/ -q
```

---

## 8. Recommendation / next slice

**FASTAPI-REACT-05** — React bootstrap (`react_token_bundle()`, NAV-ARCH-S4 shell) **or** TD-PS-01 PG boundary matrix — operator choice. **Defer React pages** until FR-05 contract tests green.
