# ERP-DS-01 — Design System Research

**Phase:** DS-1  
**Mode:** Research only — no implementation  
**Date:** 2026-06-05  
**Screenshot note:** Reference URLs below. Capture live screenshots during DS-2 review from each project's demo/docs site.

---

## Evaluation dimensions

Each candidate scored **1–5** (5 = best fit) across:

| Dimension | Weight for ERP |
|-----------|----------------|
| Accounting / finance fit | Critical |
| Banking / reconciliation fit | Critical |
| Mobile quality | High |
| React + FastAPI suitability | High |
| Mono / token discipline | High |
| Table / data density | High |
| License clarity | Required |
| Maintenance / community | Medium |

---

## 1. shadcn/ui

| Field | Detail |
|-------|--------|
| **URL** | https://ui.shadcn.com |
| **Stack** | Radix UI primitives + Tailwind CSS + copy-in components |
| **License** | MIT |
| **Stars** | ~116k (2026) |
| **Character** | Design-system *primitives* — you own every component file |

### Strengths

- CSS-variable theming (`--primary`, `--background`, `--radius`) maps directly to existing `--theme-*` tokens
- Neutral, restrained defaults — aligns with ERP mono policy
- Radix accessibility (dialogs, sheets, command palette, dropdowns)
- No npm lock-in for UI — components live in your repo
- Pairs with TanStack Table for ledger grids
- AI/agent-friendly open code

### Weaknesses

- Not a complete admin shell — you assemble dashboard, nav, layouts yourself
- No built-in CRUD — needs Refine/React Admin or custom data layer
- Chart story is bring-your-own (Recharts, Tremor blocks, or Altair server-side)

### ERP suitability: **5/5**

Best philosophical match. Accounting-first because it imposes no colorful dashboard opinions.

### Accounting suitability: **5/5**

Token-driven tables, forms, and dialogs suit GL, JE lines, and statement sections.

### Mobile quality: **4/5**

Radix Sheet/Drawer patterns map to existing hub sheets. Touch targets configured via Tailwind.

### React suitability: **5/5**

Primary target. Existing Streamlit tokens translate almost 1:1.

### Screenshot targets

- Component gallery (Button, Table, Sheet, Command)
- Dark mode toggle specimen
- Form + data table combo page

---

## 2. shadcn-admin (satnaing)

| Field | Detail |
|-------|--------|
| **URL** | https://github.com/satnaing/shadcn-admin |
| **Stack** | Next.js + shadcn/ui + TanStack Router/Table |
| **License** | MIT |
| **Stars** | ~12k |
| **Character** | Admin *shell reference* — layout, Cmd+K, sidebar |

### Strengths

- Collapsible sidebar + command palette (Cmd+K) — ideal desktop ERP shell
- Light/dark, RTL-ready
- Dashboard layout patterns without forcing finance chrome
- Fork-friendly — copy layout, not dependency

### Weaknesses

- Generic admin demo — no accounting workflows
- Next.js App Router opinions (adaptable to Vite)
- Not a library — fork/reference only

### ERP suitability: **4/5**

Shell/IA reference, not data model.

### Accounting suitability: **3/5**

Dashboard widgets are placeholders — replace with ERP KPI grammar.

### Mobile quality: **3/5**

Responsive sidebar collapse; bottom-nav pattern not included (use ERP mobile IA).

### React suitability: **5/5**

Best layout reference for desktop ERP shell.

### Screenshot targets

- Sidebar collapsed/expanded states
- Command palette open
- Settings page layout
- Dashboard grid

---

## 3. TailAdmin React

| Field | Detail |
|-------|--------|
| **URL** | https://tailadmin.com |
| **Stack** | React 19 + Tailwind v4 + Vite |
| **License** | MIT (free tier); Pro paid |
| **Character** | Batteries-included dashboard template |

### Strengths

- Fastest path to rich dashboard visuals
- 500+ elements, multiple dashboard variants
- Strong mobile responsive grids
- Finance-looking KPI card layouts (as *pattern* inspiration)

### Weaknesses

- Colorful, gradient-prone KPI cards — **fights ERP mono policy**
- Template structure lock-in — harder to own long-term
- Stripping opinions costs more than building on shadcn
- Pro features gated

### ERP suitability: **3/5**

Good for widget layout ideas; poor as foundation.

### Accounting suitability: **2/5**

Dashboard-centric, not statement-table-centric.

### Mobile quality: **4/5**

Polished responsive breakpoints.

### React suitability: **4/5**

Works, but you'd discard half the chrome.

### Screenshot targets

- Finance dashboard variant
- Table list page
- Mobile nav collapse

---

## 4. Flowbite Admin

| Field | Detail |
|-------|--------|
| **URL** | https://flowbite.com |
| **Stack** | Tailwind + Flowbite component library |
| **License** | MIT (core); Pro for admin templates |
| **Character** | Component-library-driven admin |

### Strengths

- Broad component set (tables, modals, sidebars)
- Good documentation
- MIT core components

### Weaknesses

- Distinct Flowbite visual identity — harder to merge with mono ERP
- Heavier component opinions than shadcn
- Admin templates feel generic SaaS, not accounting

### ERP suitability: **3/5**

### Accounting suitability: **3/5**

### Mobile quality: **4/5**

### React suitability: **3/5**

Package dependency vs copy-in ownership.

### Screenshot targets

- Admin dashboard template
- Data table with filters

---

## 5. MatDash

| Field | Detail |
|-------|--------|
| **URL** | https://github.com/adminmart/MatDash |
| **Stack** | React/Next + Tailwind + Flowbite + ApexCharts |
| **License** | MIT |
| **Character** | Finance-leaning admin template |

### Strengths

- Finance widgets and chart-forward dashboards
- Responsive layouts
- Useful KPI row / aging bucket layout references

### Weaknesses

- ApexCharts lock-in vs current Altair/server charts
- Flowbite coupling
- Colorful metric cards conflict with mono policy

### ERP suitability: **3/5**

Pattern library for finance widgets only.

### Accounting suitability: **4/5**

Better finance visual vocabulary than generic admin.

### Mobile quality: **4/5**

### React suitability: **3/5**

### Screenshot targets

- Finance dashboard
- Chart + table combo page

---

## 6. React Admin (Marmelab)

| Field | Detail |
|-------|--------|
| **URL** | https://marmelab.com/react-admin |
| **Stack** | React + Material UI + REST/GraphQL data provider |
| **License** | MIT (core); Enterprise Edition paid (RBAC, audit modules) |
| **Stars** | ~27k |

### Strengths

- Mature CRUD framework — List/Edit/Create/Show out of the box
- Excellent REST data provider pattern (maps to FastAPI)
- Strong community, 10+ years maintenance
- Built-in auth, i18n, notifications

### Weaknesses

- **Material Design chrome** — conflicts with shadcn/mono direction unless fully restyled
- Opinionated page structure (`<Resource>` model)
- Enterprise features (granular RBAC) are paid
- Visual identity is Google/MUI, not accounting-neutral

### ERP suitability: **4/5** (data layer) / **2/5** (visual layer)

Use as **data/routing pattern reference**, not visual foundation.

### Accounting suitability: **4/5**

CRUD for COA, vendors, customers fits well.

### Mobile quality: **3/5**

Responsive but desktop-first MUI tables.

### React suitability: **4/5**

Pair with custom shadcn UI via headless patterns, or skip visuals entirely.

### Screenshot targets

- List view with filters
- Edit form layout
- Show/detail view

---

## 7. Refine

| Field | Detail |
|-------|--------|
| **URL** | https://refine.dev |
| **Stack** | React meta-framework (headless) + optional Ant Design / MUI / Mantine / shadcn |
| **License** | MIT |
| **Stars** | ~35k |

### Strengths

- **Headless** — bring shadcn/ui as UI layer
- `useTable`, `useForm`, `useShow` hooks for CRUD-heavy ERP
- FastAPI REST data provider fits naturally
- Auth, access control, audit log modules
- Inferencer auto-generates CRUD from OpenAPI schema

### Weaknesses

- Learning curve for meta-framework concepts
- Default templates often use Ant Design (must explicitly choose headless + shadcn)
- Another abstraction layer to maintain

### ERP suitability: **5/5** (architecture) / **4/5** (visuals with shadcn)

Best **framework** candidate when paired with shadcn/ui.

### Accounting suitability: **5/5**

Built for data-intensive B2B/ERP apps.

### Mobile quality: **3/5**

Depends entirely on chosen UI kit.

### React suitability: **5/5**

Recommended: Refine (data) + shadcn (UI).

### Screenshot targets

- Headless + custom UI example
- OpenAPI inferencer demo

---

## 8. Tremor

| Field | Detail |
|-------|--------|
| **URL** | https://tremor.so / https://npm.tremor.so |
| **Stack** | React + Tailwind + Recharts |
| **License** | Apache 2.0 (note: not MIT) |
| **Stars** | ~16k (npm package) |

### Strengths

- Purpose-built dashboard KPI cards and charts
- Copy-paste components (shadcn-like distribution model)
- Good for executive summary / reports hub

### Weaknesses

- **Team shifted focus to shadcn/ui** (2025) — maintenance slowing
- Apache 2.0 license (compatible but different from MIT stack)
- Chart-heavy — risks dashboard aesthetic over accounting tables
- Colorful defaults need mono stripping

### ERP suitability: **3/5**

Use 2–3 chart/KPI blocks only, not foundation.

### Accounting suitability: **3/5**

Reports/dashboard layer only.

### Mobile quality: **3/5**

Charts resize; not transaction-first.

### React suitability: **3/5**

Supplement shadcn, don't replace.

### Screenshot targets

- KPI card row
- Area chart dashboard block

---

## 9. Other open-source ERP / admin systems

| Project | License | Notes | ERP fit |
|---------|---------|-------|---------|
| **ERPNext** (Frappe) | GPL-3.0 | Full ERP — **license incompatible** for proprietary fork; study IA only | N/A |
| **Odoo Community** | LGPL-3.0 | Module-heavy ERP — license constraints; dense accounting UI reference | Study only |
| **Apache OFBiz** | Apache 2.0 | Legacy Java ERP — dated UX | Low |
| **Solidus / Spree** | BSD | Commerce, not accounting | Low |
| **Horizon UI** | MIT | Dashboard template — Tailwind; similar to TailAdmin | 3/5 |
| **Vercel Geist / Next.js dashboard examples** | MIT | Minimal — good shell starting points | 3/5 |
| **TanStack Table + shadcn examples** | MIT | **Best table reference** for GL/ledger | 5/5 |

**QuickBooks / Xero:** Proprietary — study dense-table and register patterns only; no code adoption.

---

## Comparative matrix

| System | License | Accounting | Banking | Mobile | React | Mono fit | Verdict |
|--------|---------|------------|---------|--------|-------|----------|---------|
| **shadcn/ui** | MIT | 5 | 5 | 4 | 5 | 5 | **Foundation** |
| **shadcn-admin** | MIT | 3 | 3 | 3 | 5 | 5 | **Shell reference** |
| **Refine** | MIT | 5 | 4 | 3* | 5 | 5* | **Data framework** |
| **React Admin** | MIT | 4 | 3 | 3 | 4 | 2 | Data patterns only |
| **TailAdmin** | MIT | 2 | 3 | 4 | 4 | 2 | Pattern library |
| **MatDash** | MIT | 4 | 3 | 4 | 3 | 2 | Finance widgets |
| **Flowbite** | MIT | 3 | 3 | 4 | 3 | 3 | Skip as foundation |
| **Tremor** | Apache-2.0 | 3 | 2 | 3 | 3 | 2 | Chart blocks only |

\*With shadcn as UI layer.

---

## Recommendation (feeds DS-2)

### Primary stack for React (DS-6)

```
shadcn/ui (components + tokens)
  + shadcn-admin (desktop shell reference)
  + Refine (headless data/auth/routing) OR custom FastAPI hooks
  + TanStack Table (virtualized ledgers)
  + Recharts or server-rendered charts (reports)
```

### Streamlit interim (until React)

- Keep extending `ui/mobile_components.css` and `docs/UI_STYLE_GUIDE.md`
- Map `--theme-*` → future shadcn variables in DS-4
- No template adoption

### Do not adopt wholesale

TailAdmin, Flowbite Admin, MatDash, Tremor dashboards, React Admin MUI chrome, ERPNext/Odoo code.

---

## Screenshot capture checklist (for design review)

| # | Source | Page | Purpose |
|---|--------|------|---------|
| 1 | ui.shadcn.com | Data Table + Sheet | Ledger + mobile detail |
| 2 | ui.shadcn.com | Command | Cmd+K target |
| 3 | shadcn-admin demo | Dashboard + Sidebar | Desktop shell |
| 4 | tailadmin.com | Finance dashboard | KPI layout inspiration |
| 5 | MatDash demo | Analytics page | Report widget inspiration |
| 6 | refine.dev | Headless example | Data layer pattern |
| 7 | Current ERP Streamlit | Banking cockpit + Mobile AT | **Baseline — must match feel** |

Store captures in `docs/design_refs/` when ready (not created in DS-1).

---

## References

- `docs/MOBILE_UX_02_THEME_DESIGN_AUDIT.md` — prior candidate analysis
- `docs/UI_STYLE_GUIDE.md` — live mono policy
- `docs/MOBILE_UI_SYSTEM.md` — mobile behavior spec
