# FASTAPI-REACT-42 — Backup & Restore Read Page

**Mode:** React read page expansion with thin P1 backup status API.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-42** from [FASTAPI_REACT_41 audit §7](./FASTAPI_REACT_41_REACT_READ_COMPANY_SETTINGS_AUDIT.md).  
**Tag:** `fastapi-react-42-react-read-backup-restore`

**Prerequisites:** [FASTAPI-REACT-41](./FASTAPI_REACT_41_REACT_READ_COMPANY_SETTINGS_AUDIT.md)

---

## 1. Executive summary

| Item | Status |
|------|--------|
| Backup & Restore page (`/settings/backup-restore`) | ✅ `BackupRestorePage` |
| `GET /api/v1/backup-status` | ✅ `read_backup_status.compute_backup_status_page` |

**Accounting / GL behavior:** **UNCHANGED** — read-only backup inventory snapshot. Backup create/restore actions remain Streamlit-only.

---

## 2. Page inventory

| React path | Component | Read API |
|------------|-----------|----------|
| `/settings/backup-restore` | `BackupRestorePage` | `/api/v1/backup-status` |

**Real React read routes:** 31 (was 30). **Placeholder routes:** 11 (was 12).

---

## 3. Feature flag

Unchanged: `VITE_ERP_REACT_PAGES=1` / `ERP_REACT_PAGES=1`.

---

## 4. What must NOT change (verified)

- Streamlit primary UI (backup create/restore forms)
- No GL / posting kernel edits
- No new write API routes
- Read page uses `apiGet` only (`companyScoped: true`)
- Filesystem paths are not exposed in API responses (filename only)

---

## 5. Deferred (out of FR-42 scope)

| Item | Notes |
|------|-------|
| **FASTAPI-REACT-43** | Further read page expansion or ops slices |
| **production COMMIT_MODE_* flip** | Operator rollout |

---

## 6. Test plan

```bash
pytest tests/test_fastapi_react_42_react_read_backup_restore.py -q
pytest tests/test_fastapi_p1_read_endpoints.py -q
pytest tests/ -q
```

---

## 7. Recommendation / next slice

**FASTAPI-REACT-43** — production `COMMIT_MODE_*` characterization flip or next NAV read placeholder (year-end close, my account, etc.).
