# Phase UI-1 Consistency Re-Audit

**Date:** 2026-06-07  
**Baseline score:** 6 / 10  
**Post UI-1 score:** **7 / 10**  
**UI-2 gate:** Approved to plan; do not start page sweeps until stakeholders review this re-audit.

---

## What UI-1 delivered

| Item | Status |
|---|---|
| Style Guide (`docs/UI_STYLE_GUIDE.md`) | Done |
| Visual specimen (`docs/ui_style_guide_preview.html`) | Done |
| Global `--erp-chip-*` tokens | Done |
| Unified selected-chip grammar (AT, Reports, Radio, Tabs, Sidebar) | Done |
| Solid primary reserved for CTAs (Save, FAB, form submit) | Done |
| Global secondary button rule | Done |
| Danger button key convention (`erp_void_*`, `erp_danger_*`) | Done (CSS only; UI-2 wires keys) |
| Token cleanup `#fff` → `--erp-on-primary` (FAB, profile) | Partial |
| CSS dedup (duplicate FAB 24px blocks removed) | Done |
| Accent banner policy documented | Done |
| Frozen surfaces layout | Unchanged |

---

## Consistency matrix — post UI-1

| Surface | Before | After |
|---|---|---|
| **Primary buttons** | 3 meanings (solid / sidebar tint / reports solid) | 2 meanings: **solid CTA** vs **chip-selected** |
| **Secondary buttons** | Streamlit default | Global card+border rule |
| **Danger buttons** | Default gray | CSS ready; keys pending UI-2 |
| **Selected chips** | AT tinted, Reports solid, sidebar 22% mix | All use `--erp-chip-active-*` |
| **Active tabs** | 10% info mix | `--erp-chip-active-*` + bottom accent |
| **Radio chips** | 10% mix | `--erp-chip-active-*` |
| **Page banners** | Multi-accent | Policy documented; accents unchanged until UI-2 |
| **Forms** | Themed inputs only | Unchanged (UI-2) |
| **Tables** | Default | Unchanged (UI-3) |
| **Mobile bottom nav** | Frozen | Unchanged; secondary carve-out added |
| **Mobile calculator** | Frozen | Unchanged |
| **Dark mode** | Mostly OK | Role colors / search SVG still open |

---

## Page classification — post UI-1

**No page moved from Legacy → Modern** (UI-1 is foundation only).  
**Transitional pages gained consistent chip/button grammar** when they use shared widgets (Reports mobile, Banking radio, any `st.tabs` page).

| Class | Count (approx.) | Notes |
|---|---|---|
| Modern | 12 | Unchanged |
| Transitional | 10 | Reports/Banking tabs now visually aligned |
| Legacy | 18 | Awaiting UI-2 |

---

## Remaining gaps (UI-2 / UI-3)

### High (UI-2)
- Sales, Expenses, Purchases, Customers, Suppliers — banners, bordered forms, primary submit, danger void keys
- Receivables inline KPI / aging hex
- Fiscal, Year-End, Backup — banner + sections
- Dashboard desktop `_sec()` headers
- Per-page accent banners → default info

### Medium (UI-2–3)
- Desktop Add Transaction inline styles → `.txn-*` classes
- Table action column standard
- Currency `$` literals
- `erp_void_*` keys on void buttons

### Low (UI-3)
- Mobile CRUD cardification
- Role color dark-mode pass
- Search icon SVG theme-aware
- Typography scale tokens

---

## Frozen references — verification

| Surface | Layout changed? | Token alignment? |
|---|---|---|
| Header | No | Profile text uses `--erp-on-primary` |
| Sidebar | No | Active nav uses `--erp-chip-*` |
| Bottom nav | No | Carve-out preserves transparent tabs |
| Mobile calculator | No | Chips alias `--erp-chip-*` |
| Transaction History | No | Unchanged |
| Reports Hub | No | Chips tinted (grammar only) |
| Company Settings | No | Unchanged |

---

## Tests

```
28 passed — test_ui1_design_language, test_phase16a_theme, test_mobile_layout_contract
```

---

## Recommendation

**Proceed to UI-2** with Sales / Expenses / Purchases as the first CRUD batch, using:

- `docs/UI_STYLE_GUIDE.md` as the implementation reference
- `key="erp_void_*"` / `key="erp_danger_*"` for void buttons
- `section_header_html` + `st.caption` + bordered forms
- No accent banners on routine page titles
