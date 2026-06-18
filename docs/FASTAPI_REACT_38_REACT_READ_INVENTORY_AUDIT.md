# FASTAPI-REACT-38 — Inventory Read Page

**Mode:** React read page expansion with thin P1 product catalog API.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-38** from [FASTAPI_REACT_37 audit §7](./FASTAPI_REACT_37_REACT_READ_MEMBERS_AUDIT.md).  
**Tag:** `fastapi-react-38-react-read-inventory`

**Prerequisites:** [FASTAPI-REACT-37](./FASTAPI_REACT_37_REACT_READ_MEMBERS_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Inventory page (`/inventory`) | ✅ `InventoryPage` |
| `GET /api/v1/products` | ✅ `read_products.compute_products_list` |

**Accounting / GL behavior:** **UNCHANGED** — read-only product catalog and stock KPIs. Product add/edit and stock movements remain Streamlit-only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/inventory` | `InventoryPage` | `/api/v1/products` |

**Real React read routes:** 27 (was 26). **Placeholder routes:** 15 (was 16).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (inventory forms and stock adjustments)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-38 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-39** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_38_react_read_inventory.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-39** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (budget, permissions, year-end close, company settings, etc.).
