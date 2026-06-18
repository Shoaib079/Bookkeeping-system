# FASTAPI-REACT-27 — Workers Read Page

**Mode:** React read page expansion. No new P1 read APIs — reuses existing list endpoint from FR-22.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-27** from [FASTAPI_REACT_26 audit §7](./FASTAPI_REACT_26_REACT_READ_SALES_EXPENSES_AUDIT.md).  
**Tag:** `fastapi-react-27-react-read-workers`

**Prerequisites:** [FASTAPI-REACT-22](./FASTAPI_REACT_22_REACT_WRITE_PICKERS_AUDIT.md) (workers list API)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Workers page (`/workers`) | ✅ `WorkersPage` |
| New P1 read APIs | ❌ none — existing `GET /api/v1/workers` |

**Accounting / GL behavior:** **UNCHANGED** — read-only list page.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/workers` | `WorkersPage` | `/api/v1/workers` |

**Real React read routes:** 16 (was 15). **Placeholder routes:** 25 (was 26).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-27 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-28** | Further read page expansion |
| **customers read page** | `/customers` remains PlaceholderPage |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_27_react_read_workers.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-28** — customers read page (need thin P1 read API) or production `COMMIT_MODE_*` characterization flip.
