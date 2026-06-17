# FASTAPI-REACT-06 — First React Pages (Home + Ledger Read-Only)

**Mode:** Read-only SPA pages behind feature flag. No accounting logic in React.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-06** from [FASTAPI_REACT_05 audit §9](./FASTAPI_REACT_05_REACT_BOOTSTRAP_AUDIT.md).  
**Tag:** `fastapi-react-06-react-pages`

**Prerequisites:** [FASTAPI-REACT-05](./FASTAPI_REACT_05_REACT_BOOTSTRAP_AUDIT.md) · [FASTAPI-REACT-04](./FASTAPI_REACT_04_READ_API_BOUNDARY_AUDIT.md) · P1 read API

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Home page (`/`) | ✅ P&L summary via `/api/v1/reports/profit-loss` |
| Ledger page (`/books/general-ledger`) | ✅ GL lines via `/api/v1/ledger` |
| Feature flag (default off) | ✅ `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1` |
| Auth headers (Bearer + `X-Company-Id`) | ✅ `ReadApiSetup` + session storage |
| Remaining 40 routes | ✅ `PlaceholderPage` unchanged |
| Streamlit primary UI | ✅ Unchanged |
| New FastAPI routes | ✅ None |

**Accounting / GL behavior:** **UNCHANGED** — React consumes frozen P1 read endpoints only.

---

## 2. Page inventory

| React path | Component | P1 read APIs |
|------------|-----------|--------------|
| `/` | `HomePage` | `/auth/me`, `/auth/companies`, `/api/v1/reports/profit-loss` |
| `/books/general-ledger` | `LedgerPage` | `/api/v1/ledger` |

Contract: `registry/react_pages_contract.py` → `REAL_PAGE_ROUTES`.

**Ledger account picker:** deferred — page accepts `account_id` via URL query (`?account_id=`) until a COA read endpoint exists.

---

## 3. Feature flag

| Env | Layer | Default | Effect |
|-----|-------|---------|--------|
| `VITE_ERP_REACT_PAGES` | Vite build / dev | off | When not `1`, all routes render `PlaceholderPage` |
| `ERP_REACT_PAGES` | Operator doc mirror | off | Documented alongside Vite flag |

**Rule:** No production cutover without explicit operator enablement. Streamlit remains default UI.

---

## 4. API client (read-only)

- `frontend/src/lib/api/client.ts` — `apiGet` with optional auth headers
- `frontend/src/lib/api/session.ts` — bearer token + company id in `sessionStorage`
- `frontend/src/components/ReadApiSetup.tsx` — dev session panel (not production login UI)

Headers for company-scoped reads:

```
Authorization: Bearer <token>
X-Company-Id: <company_id>
```

---

## 5. Router wiring

`AppRouter` maps `REAL_PAGE_ROUTES` when `reactPagesEnabled()` is true; all other NAV-ARCH-S4 paths stay on `PlaceholderPage`.

Desktop shell ledger link corrected to `/books/general-ledger` (was stale `/ledger`).

---

## 6. Deferred (out of FR-06 scope)

| Item | Notes |
|------|-------|
| **chart-of-accounts picker** | Ledger uses query `account_id` until COA read API |
| **TD-PS-01** | PG boundary commit flip — still `internal` |
| **FASTAPI-REACT-07** | PG boundary matrix (completed in FR-07) |
| **FASTAPI-REACT-11** | Void/purchase write UI |

---

## 7. What must NOT change (verified)

- Streamlit `app.py` remains primary UI
- No new FastAPI routes
- No GL / posting kernel edits
- Docker files untouched
- No write methods in React API client
- No transactional forms

---

## 8. Test plan

```bash
pytest tests/test_fastapi_react_06_react_pages.py -q
cd frontend && VITE_ERP_REACT_PAGES=1 npm run build   # when Node available
pytest tests/ -q
```

---

## 9. Recommendation / next slice

**FASTAPI-REACT-07** — expand React coverage (transaction ledger, reports hub) or TD-PS-01 PG boundary matrix — operator choice.
