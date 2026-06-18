# FASTAPI-REACT-36 — Audit Log Read Page

**Mode:** React read page expansion with thin P1 audit log list API.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-36** from [FASTAPI_REACT_35 audit §7](./FASTAPI_REACT_35_REACT_READ_OPENING_BALANCES_AUDIT.md).  
**Tag:** `fastapi-react-36-react-read-audit-log`

**Prerequisites:** [FASTAPI-REACT-35](./FASTAPI_REACT_35_REACT_READ_OPENING_BALANCES_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Audit log page (`/settings/audit-log`) | ✅ `AuditLogPage` |
| `GET /api/v1/audit-log` | ✅ `read_audit_log.compute_audit_log_list` |

**Accounting / GL behavior:** **UNCHANGED** — read-only audit trail. Nav role parity: owner/manager only (cashier/viewer denied via `edit_transaction` / `manage_settings` guard).

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/settings/audit-log` | `AuditLogPage` | `/api/v1/audit-log` |

**Real React read routes:** 25 (was 24). **Placeholder routes:** 17 (was 18).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (audit log remains in Settings accordion)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)

---

## 5. Deferred (out of FR-36 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-37** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_36_react_read_audit_log.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-37** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (budget, year-end close, members, inventory, etc.).
