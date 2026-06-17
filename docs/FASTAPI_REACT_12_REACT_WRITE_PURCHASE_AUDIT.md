# FASTAPI-REACT-12 — Purchase Write Tab (New Transaction)

**Mode:** Purchase tab on existing write page. No accounting logic in React.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-12** from [FASTAPI_REACT_11 audit §7](./FASTAPI_REACT_11_REACT_WRITE_VOID_AUDIT.md).  
**Tag:** `fastapi-react-12-react-write-purchase`

**Prerequisites:** [FASTAPI-REACT-08](./FASTAPI_REACT_08_REACT_WRITE_AUDIT.md) · P2.3 purchase write API · FR-07 boundary matrix (purchase family in P2 tests)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Purchase tab on `/transactions/new` | ✅ |
| Write API | ✅ `POST /api/v1/purchases` (existing P2.3) |
| Client write gate | ✅ `VITE_ERP_REACT_WRITE_PURCHASES=1` |
| Server write gate | ✅ `ERP_API_WRITE_PURCHASES=1` |
| Payment methods | ✅ Cash · Bank · Credit |
| Vendor/category resolution | ✅ `vendor_name` + `category_name` (+ optional `subcategory_name`) |
| Bank `bank_account_id` | ✅ numeric dev field (Bank method) |
| Receivable payment write | ⬜ **Deferred** — FR-13 |

**Accounting / GL behavior:** **UNCHANGED** — purchase → GL (+ payable for Credit) via existing API.

---

## 2. Form inventory

| Field | Notes |
|-------|-------|
| `payment_method` | Cash, Bank, or Credit |
| `date` / `amount` / `currency` / `notes` | Shared write-page fields |
| `vendor_name` | Required (name lookup; mirrors P2 `category_name` pattern) |
| `category_name` | Required |
| `subcategory_name` | Optional |
| `bank_account_id` | Required when `payment_method` is Bank |

Contract: `registry/react_write_contract.py` → `ALLOWED_PURCHASE_PAYMENT_METHODS`.

---

## 3. Feature flags

| Env | Effect |
|-----|--------|
| `VITE_ERP_REACT_PAGES` | Shell |
| `VITE_ERP_REACT_WRITE_PURCHASES` | Purchase tab |
| `ERP_API_WRITE_PURCHASES` | 404 when off |

`reactWriteEnabled()` includes purchases flag (sales **or** expenses **or** voids **or** purchases).

---

## 4. Client validation (UX only)

| Rule | Mirrors P2 |
|------|------------|
| Vendor name required | `VENDOR_REQUIRED_MSG` |
| Category name required | `CATEGORY_REQUIRED_MSG` |
| Bank requires `bank_account_id` | `BANK_NOT_SELECTED_MSG` |

API remains authoritative for business rules.

---

## 5. What must NOT change (verified)

- Streamlit primary UI
- No new FastAPI routes
- No GL / posting kernel edits in React
- Sale/expense/void tabs unchanged
- `apiPost` only in `writeClient.ts`

---

## 6. Deferred (out of FR-12 scope)

| Item | Notes |
|------|-------|
| **receivable payment write** | P2.4 — FR-13 |
| **bank account picker** | No bank list read API in P1 |
| **vendor picker** | Name/id text fields only |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 7. Test plan

```bash
pytest tests/test_fastapi_react_12_react_write_purchase.py -q
pytest tests/ -q
```

**Dev smoke:**
```bash
ERP_API_WRITE_PURCHASES=1 uvicorn api.main:create_app --factory --reload
cd frontend && VITE_ERP_REACT_PAGES=1 VITE_ERP_REACT_WRITE_PURCHASES=1 npm run dev
```

---

## 8. Recommendation / next slice

**FASTAPI-REACT-13** — receivable payment write tab on `/transactions/new`.
