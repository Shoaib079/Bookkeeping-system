# FASTAPI-REACT-05 — React Bootstrap (Shell + Router + ThemeProvider)

**Mode:** Bootstrap only — placeholder pages, no accounting logic.

**Date:** 2026-06-05  
**Authority:** Implements slice **FASTAPI-REACT-05** from [FASTAPI_REACT_04 audit §8](./FASTAPI_REACT_04_READ_API_BOUNDARY_AUDIT.md).  
**Tag:** `fastapi-react-05-react-bootstrap`

**Prerequisites:** [FASTAPI-REACT-04](./FASTAPI_REACT_04_READ_API_BOUNDARY_AUDIT.md) · MONO-THEME-02 · NAV-ARCH-S4 · `ui/react_design_contract.py`

---

## 1. Executive summary

| Item | Status |
|------|--------|
| `frontend/` Vite + React + TypeScript | ✅ **Bootstrapped** |
| `ThemeProvider` from `react_token_bundle()` | ✅ via `design-tokens.json` export |
| Router from NAV-ARCH-S4 | ✅ 42 routes in `routes.json` |
| Desktop + mobile shells | ✅ `AppShell` media-query switch |
| FastAPI read client stub | ✅ GET-only `api/client.ts` |
| Real page implementations | ⬜ **FASTAPI-REACT-06** |
| Streamlit primary UI | ✅ Unchanged |

**Accounting / GL behavior:** **UNCHANGED** — no Python posting edits; SPA has placeholder pages only.

---

## 2. Bootstrap layout

```
frontend/
  package.json          # Vite 6 + React 19 + React Router 7
  src/
    generated/
      design-tokens.json   # SSOT export from react_token_bundle()
      routes.json          # SSOT export from registry.navigation
    theme/ThemeProvider.tsx
    routes/AppRouter.tsx
    layouts/{DesktopShell,MobileShell,AppShell}.tsx
    lib/api/client.ts      # read-only fetch helper
    pages/PlaceholderPage.tsx
scripts/export_react_bootstrap_assets.py
```

**Sync command:** `npm run sync:assets` (from `frontend/`) or `python scripts/export_react_bootstrap_assets.py`.

---

## 3. Token governance

- Python SSOT: `ui/react_design_contract.react_token_bundle()`
- React import: `frontend/src/generated/design-tokens.json` only
- `ThemeProvider` applies `light`/`dark` root vars + `componentGrammar` on `:root`
- **Rule:** do not fork hex or color-mix strings in the SPA

---

## 4. Route governance

- Python SSOT: `registry.navigation.react_route_contract_rows()` (NAV-ARCH-S4)
- React import: `frontend/src/generated/routes.json`
- `AppRouter` registers all 42 paths with `PlaceholderPage`
- Legacy aliases remain Python-side only (not separate React paths)

---

## 5. API client (read-only stub)

`frontend/src/lib/api/client.ts` — `apiGet()` only; no write methods in FR-05.

Vite dev proxy: `/api` and `/auth` → `http://127.0.0.1:8000`.

---

## 6. Deferred (out of FR-05 scope)

| Item | Notes |
|------|-------|
| **TD-PS-01** | PG boundary commit flip — still `internal`; FR-06+ or operator rollout |
| **FASTAPI-REACT-06** | Real pages (Home, Ledger read-only) |

---

## 7. What must NOT change (verified)

- Streamlit `app.py` remains primary UI
- No new FastAPI routes in this slice
- No GL / posting kernel edits
- Docker files untouched
- Placeholder pages only — no transactional forms

---

## 8. Test plan

```bash
python scripts/export_react_bootstrap_assets.py
pytest tests/test_fastapi_react_05_react_bootstrap.py -q
cd frontend && npm install && npm run build
pytest tests/ -q
```

---

## 9. Recommendation / next slice

**FASTAPI-REACT-06** — first real pages (Home + Ledger read-only) wired to P1 read API behind feature flag.
