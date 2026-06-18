# FASTAPI-REACT-49 — Staff Expense Capture Read Page

**Mode:** React read page expansion with thin P1 staff expense draft read API.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-49** from [FASTAPI_REACT_48 audit §7](./FASTAPI_REACT_48_REACT_READ_RECURRING_EXPENSES_AUDIT.md).  
**Tag:** `fastapi-react-49-react-read-staff-capture`

**Prerequisites:** [FASTAPI-REACT-48](./FASTAPI_REACT_48_REACT_READ_RECURRING_EXPENSES_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Staff Expenses page (`/expenses/staff-capture`) | ✅ `StaffCapturePage` |
| `GET /api/v1/staff-expense-drafts` | ✅ `read_staff_expense_drafts.compute_staff_expense_drafts_page` |

**Accounting / GL behavior:** **UNCHANGED** — read-only my submissions and approval inbox. Submit/approve/reject/return actions remain Streamlit-only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/expenses/staff-capture` | `StaffCapturePage` | `/api/v1/staff-expense-drafts` |

**Real React read routes:** 38 (was 37). **Placeholder routes:** 4 (was 5).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (submit form, receipts, inbox actions)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)
- Guard uses `submit_expense_drafts` OR `approve_expense_drafts` (matches Streamlit page entry; cashier allowed via submit)

---

## 5. Deferred (out of FR-49 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-50** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_49_react_read_staff_capture.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-50** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (recipe costing routes).
