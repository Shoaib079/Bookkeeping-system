# FASTAPI-REACT-46 — Cash Reconciliation Read Page

**Mode:** React read page expansion with thin P1 daily cash reconciliation history API.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-46** from [FASTAPI_REACT_45 audit §7](./FASTAPI_REACT_45_REACT_READ_EOD_CLOSE_AUDIT.md).  
**Tag:** `fastapi-react-46-react-read-cash-recon`

**Prerequisites:** [FASTAPI-REACT-45](./FASTAPI_REACT_45_REACT_READ_EOD_CLOSE_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Cash Reconciliation page (`/closings/cash-recon`) | ✅ `CashReconPage` |
| `GET /api/v1/cash-reconciliations` | ✅ `read_cash_reconciliations.compute_cash_reconciliations_list` |

**Accounting / GL behavior:** **UNCHANGED** — read-only reconciliation history. Submit/approve/void actions remain Streamlit-only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/closings/cash-recon` | `CashReconPage` | `/api/v1/cash-reconciliations` |

**Real React read routes:** 35 (was 34). **Placeholder routes:** 7 (was 8).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (today submit, pending approval, reports)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)
- Guard uses `create_reconciliation` (matches Streamlit page entry)

---

## 5. Deferred (out of FR-46 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-47** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_46_react_read_cash_recon.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-47** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (external sales close, recurring expenses, recipes, etc.).
