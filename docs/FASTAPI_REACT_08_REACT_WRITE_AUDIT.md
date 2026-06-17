# FASTAPI-REACT-08 — First React Write Page (Cash Sale)

**Mode:** Single write form behind dual feature flags. No accounting logic in React.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-08** from [FASTAPI_REACT_07 audit §10](./FASTAPI_REACT_07_PG_BOUNDARY_MATRIX_AUDIT.md).  
**Tag:** `fastapi-react-08-react-write`

**Prerequisites:** [FASTAPI-REACT-06](./FASTAPI_REACT_06_REACT_PAGES_AUDIT.md) · [FASTAPI-REACT-07](./FASTAPI_REACT_07_PG_BOUNDARY_MATRIX_AUDIT.md) · P2.1 sales write API

---

## 1. Executive summary

| Item | Status |
|------|--------|
| New Transaction page (`/transactions/new`) | ✅ Cash sale form only |
| Write API | ✅ `POST /api/v1/sales` (existing P2.1) |
| Client write gate | ✅ `VITE_ERP_REACT_WRITE_SALES=1` |
| Read pages gate | ✅ `VITE_ERP_REACT_PAGES=1` (unchanged) |
| Server write gate | ✅ `ERP_API_WRITE_SALES=1` |
| `apiPost` in `writeClient.ts` only | ✅ |
| Card / credit / expense writes | ⬜ **Deferred** |
| Default commit mode | ✅ `internal` unchanged |

**Accounting / GL behavior:** **UNCHANGED** — React calls existing write API only.

---

## 2. Page inventory

| React path | Component | API | Scope |
|------------|-----------|-----|-------|
| `/transactions/new` | `NewTransactionPage` | `POST /api/v1/sales` | Cash sale only |

Contract: `registry/react_write_contract.py` → `WRITE_PAGE_ROUTES`.

**Form fields:** date, amount, currency (default TRY), notes. `payment_method` fixed to `Cash`.

---

## 3. Feature flags (triple gate)

| Env | Layer | Default | Effect |
|-----|-------|---------|--------|
| `VITE_ERP_REACT_PAGES` | Vite | off | Read pages + write route shell |
| `VITE_ERP_REACT_WRITE_SALES` | Vite | off | `NewTransactionPage` vs placeholder |
| `ERP_API_WRITE_SALES` | FastAPI | off | 404 on `POST /api/v1/sales` |

All three required for a successful save in dev.

---

## 4. API client (write)

- `frontend/src/lib/api/writeClient.ts` — `apiPost()` only
- Shared auth headers: Bearer + `X-Company-Id` (same session as read pages)
- **Rule:** no `apiPut` / `apiDelete` / posting kernel imports in SPA

---

## 5. Router wiring

`AppRouter` renders `NewTransactionPage` when `reactPagesEnabled()` **and** `reactWriteSalesEnabled()`; otherwise `PlaceholderPage`.

Read pages (`/`, `/books/general-ledger`) unchanged from FR-06.

---

## 6. Boundary / commit ownership

- Default `internal` — no production `COMMIT_MODE_*` flip
- Dev may set `COMMIT_MODE_POST_CASH_SALE=boundary` for boundary characterization
- FR-07 matrix proves API write-path parity before this slice

---

## 7. Deferred (out of FR-08 scope)

| Item | Notes |
|------|-------|
| **card sale form** | P2 supports Card — UI deferred |
| **credit sale form** | Customer field required — UI deferred |
| **expense write page** | FR-09+ |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 8. What must NOT change (verified)

- Streamlit `app.py` remains primary UI
- No new FastAPI routes
- No GL / posting kernel edits in React or new Python posting code
- Docker files untouched
- Read pages flag behavior unchanged

---

## 9. Test plan

```bash
pytest tests/test_fastapi_react_08_react_write.py -q
cd frontend && VITE_ERP_REACT_PAGES=1 VITE_ERP_REACT_WRITE_SALES=1 npm run build  # when Node available
pytest tests/ -q
```

**Dev smoke:**
```bash
ERP_API_WRITE_SALES=1 uvicorn api.main:create_app --factory --reload
cd frontend && VITE_ERP_REACT_PAGES=1 VITE_ERP_REACT_WRITE_SALES=1 npm run dev
```

---

## 10. Recommendation / next slice

**FASTAPI-REACT-09** — expense write on `/transactions/new` tab **or** card/credit sale fields on same page.
