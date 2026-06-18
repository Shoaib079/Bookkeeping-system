# FASTAPI-REACT-47 — External Sales Verification Read Page

**Mode:** React read page expansion with thin P1 external sales verification history API.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-47** from [FASTAPI_REACT_46 audit §7](./FASTAPI_REACT_46_REACT_READ_CASH_RECON_AUDIT.md).  
**Tag:** `fastapi-react-47-react-read-external-sales`

**Prerequisites:** [FASTAPI-REACT-46](./FASTAPI_REACT_46_REACT_READ_CASH_RECON_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| External Sales page (`/closings/external-sales`) | ✅ `ExternalSalesPage` |
| `GET /api/v1/external-sales-verifications` | ✅ `read_external_sales_verifications.compute_external_sales_verifications_list` |

**Accounting / GL behavior:** **UNCHANGED** — read-only verification history. Draft/verify/void actions remain Streamlit-only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/closings/external-sales` | `ExternalSalesPage` | `/api/v1/external-sales-verifications` |

**Real React read routes:** 36 (was 35). **Placeholder routes:** 6 (was 7).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (verify tab, draft/verify/void)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)
- Guard uses `view_external_sales_verification` (owner/manager)

---

## 5. Deferred (out of FR-47 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-48** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_47_react_read_external_sales.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-48** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (recurring expenses, staff capture, recipes, etc.).
