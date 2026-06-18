# FASTAPI-REACT-41 — Company Settings Read Page

**Mode:** React read page expansion with thin P1 company settings API.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-41** from [FASTAPI_REACT_40 audit §7](./FASTAPI_REACT_40_REACT_READ_PERMISSIONS_AUDIT.md).  
**Tag:** `fastapi-react-41-react-read-company-settings`

**Prerequisites:** [FASTAPI-REACT-40](./FASTAPI_REACT_40_REACT_READ_PERMISSIONS_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Company settings page (`/settings/company`) | ✅ `CompanySettingsPage` |
| `GET /api/v1/company-settings` | ✅ `read_company_settings.compute_company_settings_page` |

**Accounting / GL behavior:** **UNCHANGED** — read-only company profile and financial settings snapshot. Settings batch save remains Streamlit-only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/settings/company` | `CompanySettingsPage` | `/api/v1/company-settings` |

**Real React read routes:** 30 (was 29). **Placeholder routes:** 12 (was 13).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (company settings forms and wizard)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-41 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-42** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_41_react_read_company_settings.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-42** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (year-end close, backup-restore, my account, etc.).
