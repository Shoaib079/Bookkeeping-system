# ERP-DESIGN-SYSTEM-01 — Future UI / UX Roadmap

**Status:** Approved program — documentation phases DS-1 through DS-5 complete; DS-6 gated on FastAPI + React + design approval  
**Goal:** One design language for desktop, mobile, FastAPI, and React across accounting, banking, partners, and reports  
**Grounding:** Extends the live Streamlit system (`docs/UI_STYLE_GUIDE.md`, `ui/mobile_components.css`, `registry/nav_keys.py`) — not a replacement

---

## Current rule (Streamlit until React)

| Allowed in Streamlit | Not allowed in Streamlit |
|----------------------|--------------------------|
| Navigation cleanup | Major visual redesign |
| Consistency / spacing fixes | Theme replacement |
| Workflow improvements | Dashboard rebuild |
| Responsive / usability fixes | Template adoption |
| Token alignment (MOBILE-UX-02-A pattern) | React-style UI recreation |

**Reason:** Design work happens once. Avoid redesigning twice.

---

## Preferred direction (locked)

| Layer | Choice |
|-------|--------|
| **Foundation** | shadcn/ui philosophy — CSS variables, owned components, mono default |
| **Shell reference** | shadcn-admin (collapsible sidebar, Cmd+K) — reference only |
| **Pattern libraries** | TailAdmin / MatDash finance layouts — inspiration only |
| **Accounting grammar** | Existing ERP: token-driven KPI chips, HTML financial tables, status pills |
| **Not** | TailAdmin clone, Flowbite clone, QuickBooks clone |

Optional flavors later: richer dashboard widgets (TailAdmin-inspired), dense-table mode (QuickBooks/Xero-inspired).

---

## Phase map

| Phase | Title | Owner | Output | Implementation |
|-------|-------|-------|--------|----------------|
| **DS-1** | Design System Research | Claude | [ERP_DS_01_RESEARCH.md](./ERP_DS_01_RESEARCH.md) | None |
| **DS-2** | Theme Selection | Claude | [ERP_DS_02_THEME_OPTIONS.md](./ERP_DS_02_THEME_OPTIONS.md) | None |
| **DS-3** | Visual Mockups | Claude | [ERP_DS_03_MOCKUPS.md](./ERP_DS_03_MOCKUPS.md) | None |
| **DS-4** | Master Design System | Claude | [ERP_DS_04_MASTER_DESIGN_SYSTEM.md](./ERP_DS_04_MASTER_DESIGN_SYSTEM.md) | Spec only — implementation-grade |
| **DS-5** | React Architecture Mapping | Claude | [ERP_DS_05_REACT_ARCHITECTURE.md](./ERP_DS_05_REACT_ARCHITECTURE.md) | None |
| **DS-6** | FastAPI + React Build | Cursor | Code | **Gated:** FastAPI online, React online, DS-4 approved |

---

## Relationship to existing work

| Existing artifact | Role in DS program |
|-------------------|-------------------|
| `docs/UI_STYLE_GUIDE.md` | Live Streamlit grammar — DS-4 supersedes for React target, extends for Streamlit |
| `docs/MOBILE_UX_02_THEME_DESIGN_AUDIT.md` | DS-1 precursor — candidate evaluation |
| `docs/MOBILE_UI_SYSTEM.md` | Mobile IA / behavior — feeds DS-3 and DS-5 |
| `ui/mobile_components.css` | Streamlit MVP of DS-4 component tokens (MOBILE-UX-02-A) |
| `registry/nav_keys.py` | Canonical route keys — DS-5 maps 1:1 to React routes |
| `tests/test_ui1_design_language.py` | Regression guard until React parity tests exist |

---

## DS-6 entry criteria

Before Cursor implements React UI:

1. FastAPI backend exposes stable REST (or GraphQL) for all transactional domains
2. React app scaffold exists (Vite/Next + shadcn/ui per DS-4)
3. DS-04_MASTER_DESIGN_SYSTEM.md reviewed and signed off
4. DS-02 theme direction selected (recommended: **Direction A — shadcn foundation**)
5. No visual guessing — every component traces to DS-4 spec

---

## Success criteria

Desktop and mobile feel like the **same ERP**:

- Same tokens (`--theme-*` → shadcn CSS variables)
- Same mono accent policy (one primary, semantic colors for amounts/status only)
- Same navigation IA (desktop sidebar accordions ↔ mobile bottom hubs)
- Same financial readability (tabular nums, wrap names, no Glide on statements)
- Same component names (`erp-mob-kpi-chip` grammar → React `KpiChip`)

---

## Next actions

| Priority | Action |
|----------|--------|
| 1 | Review DS-02 and select final theme direction |
| 2 | Capture reference screenshots from shadcn-admin + MatDash finance pages (DS-1 URLs) |
| 3 | Validate DS-03 mockups against stakeholder workflows (banking queue, EOD, P&L) |
| 4 | Approve DS-04 before any React component work |
| 5 | Continue Streamlit consistency passes only (MOBILE-UX-02 pattern) — no redesign |
