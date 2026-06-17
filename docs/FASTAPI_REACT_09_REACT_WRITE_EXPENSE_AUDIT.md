# FASTAPI-REACT-09 — Expense Write Tab (New Transaction)

**Mode:** Expense tab on existing write page. No accounting logic in React.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-09** from [FASTAPI_REACT_08 audit §10](./FASTAPI_REACT_08_REACT_WRITE_AUDIT.md).  
**Tag:** `fastapi-react-09-react-write-expense`

**Prerequisites:** [FASTAPI-REACT-08](./FASTAPI_REACT_08_REACT_WRITE_AUDIT.md) · P2.2 expense write API · FR-07 expense boundary matrix

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Expense tab on `/transactions/new` | ✅ Cash expense form |
| Write API | ✅ `POST /api/v1/expenses` (existing P2.2) |
| Client write gate | ✅ `VITE_ERP_REACT_WRITE_EXPENSES=1` |
| Sales tab (FR-08) | ✅ Unchanged — `VITE_ERP_REACT_WRITE_SALES=1` |
| Page mount | ✅ Either write flag + `VITE_ERP_REACT_PAGES=1` |
| Server write gate | ✅ `ERP_API_WRITE_EXPENSES=1` |
| Card / credit / bank expense | ⬜ **Deferred** |

**Accounting / GL behavior:** **UNCHANGED** — React calls existing write API only.

---

## 2. Page inventory

| Tab | API | Scope |
|-----|-----|-------|
| Sale | `POST /api/v1/sales` | Cash sale (FR-08) |
| Expense | `POST /api/v1/expenses` | Cash expense + category name |

Contract: `registry/react_write_contract.py`.

**Expense form fields:** date, amount, currency, notes, `category_name` (default `Office`), optional `subcategory_name` (`Other`). `payment_method` fixed to `Cash`.

---

## 3. Feature flags

| Env | Layer | Effect |
|-----|-------|--------|
| `VITE_ERP_REACT_PAGES` | Vite | Shell + read pages |
| `VITE_ERP_REACT_WRITE_SALES` | Vite | Sale tab |
| `VITE_ERP_REACT_WRITE_EXPENSES` | Vite | Expense tab |
| `ERP_API_WRITE_EXPENSES` | FastAPI | 404 when off |

`reactWriteEnabled()` = sales **or** expenses client flag.

---

## 4. What must NOT change (verified)

- Streamlit primary UI
- No new FastAPI routes
- No GL / posting kernel edits
- FR-08 cash sale tab behavior
- Docker untouched

---

## 5. Test plan

```bash
pytest tests/test_fastapi_react_09_react_write_expense.py -q
pytest tests/test_fastapi_react_08_react_write.py -q
pytest tests/ -q
```

**Dev smoke:**
```bash
ERP_API_WRITE_SALES=1 ERP_API_WRITE_EXPENSES=1 uvicorn api.main:create_app --factory --reload
cd frontend && VITE_ERP_REACT_PAGES=1 VITE_ERP_REACT_WRITE_SALES=1 VITE_ERP_REACT_WRITE_EXPENSES=1 npm run dev
```

---

## 6. Deferred (out of FR-09 scope)

| Item | Notes |
|------|-------|
| **card sale form** | P2 supports Card |
| **credit sale form** | Customer required |
| **bank expense payment** | `bank_account_id` field deferred |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 7. Recommendation / next slice

**FASTAPI-REACT-10** — card/credit sale fields **or** bank expense payment on same page.
