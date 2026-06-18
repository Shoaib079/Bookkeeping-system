# FASTAPI-REACT-48 — Recurring Expenses Read Page

**Mode:** React read page expansion with thin P1 recurring expense templates/drafts API.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-48** from [FASTAPI_REACT_47 audit §7](./FASTAPI_REACT_47_REACT_READ_EXTERNAL_SALES_AUDIT.md).  
**Tag:** `fastapi-react-48-react-read-recurring-expenses`

**Prerequisites:** [FASTAPI-REACT-47](./FASTAPI_REACT_47_REACT_READ_EXTERNAL_SALES_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Recurring Expenses page (`/expenses/recurring`) | ✅ `RecurringExpensesPage` |
| `GET /api/v1/recurring-expenses` | ✅ `read_recurring_expenses.compute_recurring_expenses_page` |

**Accounting / GL behavior:** **UNCHANGED** — read-only templates, pending drafts, and draft history. Post/skip/postpone/template CRUD remain Streamlit-only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/expenses/recurring` | `RecurringExpensesPage` | `/api/v1/recurring-expenses` |

**Real React read routes:** 37 (was 36). **Placeholder routes:** 5 (was 6).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (pending drafts, history, manage templates)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)
- Guard uses `manage_recurring_templates` OR `post_recurring_draft` (matches Streamlit page entry; cashier allowed)

---

## 5. Deferred (out of FR-48 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-49** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_48_react_read_recurring_expenses.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-49** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (staff expense capture, recipe costing, etc.).
