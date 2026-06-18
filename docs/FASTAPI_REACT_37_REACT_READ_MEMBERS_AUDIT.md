# FASTAPI-REACT-37 — Company Members Read Page

**Mode:** React read page expansion with thin P1 member roster API.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-37** from [FASTAPI_REACT_36 audit §7](./FASTAPI_REACT_36_REACT_READ_AUDIT_LOG_AUDIT.md).  
**Tag:** `fastapi-react-37-react-read-members`

**Prerequisites:** [FASTAPI-REACT-36](./FASTAPI_REACT_36_REACT_READ_AUDIT_LOG_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Members page (`/settings/members`) | ✅ `MembersPage` |
| `GET /api/v1/members` | ✅ `read_company_members.compute_company_members_page` |

**Accounting / GL behavior:** **UNCHANGED** — read-only membership roster. Member invite/edit/remove remains Streamlit-only (`manage_users`, owner-only).

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/settings/members` | `MembersPage` | `/api/v1/members` |

**Real React read routes:** 26 (was 25). **Placeholder routes:** 16 (was 17).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (member management forms)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-37 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-38** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_37_react_read_members.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-38** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (inventory, budget, year-end close, permissions, etc.).
