# FASTAPI-REACT-44 — My Account Read Page

**Mode:** React read page expansion with thin P1 my-account profile API.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-44** from [FASTAPI_REACT_43 audit §7](./FASTAPI_REACT_43_REACT_READ_YEAR_END_CLOSE_AUDIT.md).  
**Tag:** `fastapi-react-44-react-read-my-account`

**Prerequisites:** [FASTAPI-REACT-43](./FASTAPI_REACT_43_REACT_READ_YEAR_END_CLOSE_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| My Account page (`/account`) | ✅ `MyAccountPage` |
| `GET /api/v1/my-account` | ✅ `read_my_account.compute_my_account_page` |

**Accounting / GL behavior:** **UNCHANGED** — read-only self profile snapshot. Profile/password/preference writes remain Streamlit-only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/account` | `MyAccountPage` | `/api/v1/my-account` |

**Real React read routes:** 33 (was 32). **Placeholder routes:** 9 (was 10).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (profile, security, preferences, notifications tabs)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)
- Endpoint requires membership but no elevated permission (all roles including cashier)

---

## 5. Deferred (out of FR-44 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-45** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_44_react_read_my_account.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-45** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (closings, recipes, recurring expenses, etc.).
