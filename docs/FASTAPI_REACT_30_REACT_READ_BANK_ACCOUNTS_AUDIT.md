# FASTAPI-REACT-30 — Bank Accounts Read Page

**Mode:** React read page expansion. No new P1 read APIs — reuses existing list endpoint from FR-22. Adds hidden NAV route `/banking/accounts` for React routing only.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-30** from [FASTAPI_REACT_29 audit §7](./FASTAPI_REACT_29_REACT_READ_PURCHASES_AUDIT.md).  
**Tag:** `fastapi-react-30-react-read-bank-accounts`

**Prerequisites:** [FASTAPI-REACT-22](./FASTAPI_REACT_22_REACT_WRITE_PICKERS_AUDIT.md) (bank accounts list API)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Bank accounts page (`/banking/accounts`) | ✅ `BankAccountsPage` |
| New P1 read APIs | ❌ none — existing `GET /api/v1/bank-accounts` |
| NAV route | ✅ hidden `NAV_BANK_ACCOUNTS` → `/banking/accounts` (43 routes) |

**Accounting / GL behavior:** **UNCHANGED** — read-only list page.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/banking/accounts` | `BankAccountsPage` | `/api/v1/bank-accounts` |

`/banking` remains `BankingReadinessPage` (reconciliation readiness).

**Real React read routes:** 19 (was 18). **Placeholder routes:** 23 (was 24).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (hidden route not in sidebar)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-30 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-31** | Further read page expansion |
| **fiscal periods read page** | `/books/fiscal-periods` remains PlaceholderPage |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_30_react_read_bank_accounts.py -q
pytest tests/test_nav_arch_s4_react_route_contract.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-31** — fiscal periods read page (reuse `/api/v1/fiscal-periods`) or production `COMMIT_MODE_*` characterization flip.
