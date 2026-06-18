# FASTAPI-REACT-40 — Permissions Read Page

**Mode:** React read page expansion with thin P1 permission provenance APIs.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-40** from [FASTAPI_REACT_39 audit §7](./FASTAPI_REACT_39_REACT_READ_BUDGET_AUDIT.md).  
**Tag:** `fastapi-react-40-react-read-permissions`

**Prerequisites:** [FASTAPI-REACT-39](./FASTAPI_REACT_39_REACT_READ_BUDGET_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Permissions page (`/settings/permissions`) | ✅ `PermissionsPage` |
| `GET /api/v1/permissions/members` | ✅ `read_permissions.compute_permission_members_page` |
| `GET /api/v1/permissions/effective` | ✅ `read_permissions.compute_effective_permissions_page` |

**Accounting / GL behavior:** **UNCHANGED** — read-only permission provenance. Grant/deny/reset writes remain Streamlit-only (`manage_permissions`, owner-only).

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/settings/permissions` | `PermissionsPage` | `/api/v1/permissions/members`, `/api/v1/permissions/effective` |

**Real React read routes:** 29 (was 28). **Placeholder routes:** 13 (was 14).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (permission override actions)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-40 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-41** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_40_react_read_permissions.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-41** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (company settings, year-end close, backup-restore, etc.).
