# FASTAPI-REACT-10 — Payment Method Expansion (Card/Credit Sale + Bank Expense)

**Mode:** Extend existing write tabs. No accounting logic in React.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-10** from [FASTAPI_REACT_09 audit §7](./FASTAPI_REACT_09_REACT_WRITE_EXPENSE_AUDIT.md).  
**Tag:** `fastapi-react-10-react-write-payment-methods`

**Prerequisites:** [FASTAPI-REACT-08](./FASTAPI_REACT_08_REACT_WRITE_AUDIT.md) · [FASTAPI-REACT-09](./FASTAPI_REACT_09_REACT_WRITE_EXPENSE_AUDIT.md) · P2.1/P2.2 write APIs

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Sale payment methods | ✅ Cash · Card · Credit |
| Card sale `card_bank_account_id` | ✅ numeric dev field |
| Credit sale `customer_name` | ✅ required (not walk-in) |
| Expense payment methods | ✅ Cash · Bank |
| Bank expense `bank_account_id` | ✅ numeric dev field |
| Bank account picker read API | ⬜ **Deferred** — id input like FR-06 ledger |
| New API routes | ✅ None |

**Accounting / GL behavior:** **UNCHANGED** — existing P2 write endpoints only.

---

## 2. Form inventory

| Tab | Methods | Extra fields |
|-----|---------|--------------|
| Sale | Cash, Card, Credit | `card_bank_account_id` (Card), `customer_name` (Credit) |
| Expense | Cash, Bank | `bank_account_id` (Bank) |

Contract: `registry/react_write_contract.py` → `ALLOWED_*_PAYMENT_METHODS`.

---

## 3. Feature flags (unchanged from FR-08/09)

| Env | Effect |
|-----|--------|
| `VITE_ERP_REACT_PAGES` | Shell |
| `VITE_ERP_REACT_WRITE_SALES` | Sale tab |
| `VITE_ERP_REACT_WRITE_EXPENSES` | Expense tab |
| `ERP_API_WRITE_SALES` / `ERP_API_WRITE_EXPENSES` | Server gates |

---

## 4. Client validation (UX only)

| Rule | Mirrors P2 |
|------|------------|
| Credit requires non-empty customer ≠ Walk-in Customer | `validate_credit_sale_customer` |
| Card requires `card_bank_account_id` | P2 card sale test |
| Bank expense requires `bank_account_id` | P2 bank expense test |

API remains authoritative for business rules.

---

## 5. What must NOT change (verified)

- Streamlit primary UI
- No new FastAPI routes
- No GL / posting kernel edits
- FR-08/09 cash flows unchanged when those methods selected
- `apiPost` only in `writeClient.ts`

---

## 6. Deferred (out of FR-10 scope)

| Item | Notes |
|------|-------|
| **void write page** | P2.5 exists |
| **purchase write page** | P2.3 exists |
| **bank account picker** | No COA/bank read list in P1 |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 7. Test plan

```bash
pytest tests/test_fastapi_react_10_react_write_payment_methods.py -q
pytest tests/test_fastapi_react_09_react_write_expense.py -q
pytest tests/ -q
```

---

## 8. Recommendation / next slice

**FASTAPI-REACT-11** — void write UI **or** purchase write tab on `/transactions/new`.
