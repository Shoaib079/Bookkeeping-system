# ERP-DS-02 — Theme Options

**Phase:** DS-2  
**Mode:** Selection document — no implementation  
**Date:** 2026-06-05  
**Prerequisite:** [ERP_DS_01_RESEARCH.md](./ERP_DS_01_RESEARCH.md)

---

## Selection criteria

1. Desktop and mobile must feel like one product
2. Accounting readability beats dashboard aesthetics
3. Mono accent policy preserved
4. Token-driven — maps from existing `--theme-*`
5. FastAPI + React buildable without stripping a template

---

## Five candidate directions

---

## Direction A — **shadcn Foundation** (Recommended)

**Tagline:** Own the components. One token system. Accounting-first.

### Philosophy

- Copy-in shadcn/ui primitives
- shadcn-admin for desktop shell reference
- Refine or custom hooks for FastAPI data
- ERP mono policy as default theme

### Desktop

| Surface | Treatment |
|---------|-----------|
| **Dashboard** | 3–4 KPI chips (flat, bordered, no gradients) + today activity list + quick actions |
| **Banking** | Left queue panel + right detail (existing cockpit IA); TanStack Table for statement lines |
| **Reconciliation** | Status pills + match queue cards; command palette for jump-to-account |
| **Reports** | Tab strip + date bar + HTML financial tables (P&L sections, not chart-first) |
| **Settings** | Grouped form sections in cards; sidebar sub-nav |

### Tablet (768–1024px)

- Collapsible sidebar (icon-only rail)
- Banking: queue above detail (stacked)
- Reports: horizontal tab scroll

### Mobile (≤968px)

- Bottom nav: Home · Money · + · Reports · More
- Hub sheets for Money/Reports/More (existing IA)
- List cards with right-aligned amounts
- FAB for New Transaction
- Full-screen sheets for pickers and reconciliation detail

### Token preview

| ERP (today) | shadcn (target) |
|-------------|-----------------|
| `--theme-info` | `--primary` |
| `--theme-card` | `--card` |
| `--theme-bg` | `--background` |
| `--theme-border` | `--border` |
| `--theme-success-text` | semantic success (amounts only) |
| `--mob-space-*` | `--spacing-*` scale |

### Pros / Cons

| Pros | Cons |
|------|------|
| Best match to live ERP + tests | More assembly than a template |
| Full code ownership | Dashboard widgets built manually |
| Cleanest Streamlit → React path | Cmd+K waits for React |

**Scores:** Accounting 5 · Banking 5 · Mobile 4 · React 5 · Mono 5

---

## Direction B — **Refine + shadcn Hybrid**

**Tagline:** Headless ERP framework with shadcn skin.

### Philosophy

- Refine handles auth, CRUD, routing, access control
- shadcn/ui for every visible component
- OpenAPI inferencer for rapid CRUD pages (COA, vendors, customers)

### Desktop

| Surface | Treatment |
|---------|-----------|
| **Dashboard** | Refine `<Authenticated>` wrapper + custom dashboard component |
| **Banking** | Custom page (not inferencer) — too workflow-heavy |
| **Reconciliation** | Custom queue + Refine `useShow` for detail |
| **Reports** | Custom renderers (financial tables) |
| **Settings** | Inferencer-generated CRUD for Members, Permissions |

### Tablet / Mobile

Same IA as Direction A — Refine does not dictate mobile chrome.

### Pros / Cons

| Pros | Cons |
|------|------|
| Fastest CRUD page generation | Extra framework dependency |
| Built-in auth/RBAC patterns | Learning curve |
| FastAPI data provider mature | Overkill for bespoke banking flows |

**Scores:** Accounting 5 · Banking 4 · Mobile 4 · React 5 · Mono 5

**Best when:** Team wants auto-generated admin CRUD + custom banking/reports.

---

## Direction C — **Dense Ledger** (QuickBooks/Xero inspired)

**Tagline:** Maximum data density. Minimal chrome.

### Philosophy

- shadcn foundation (same as A)
- Tighter spacing scale (4/6/8/12)
- Register-style transaction lists on desktop
- Fewer cards, more inline rows

### Desktop

| Surface | Treatment |
|---------|-----------|
| **Dashboard** | Single row KPIs + compact recent transactions table |
| **Banking** | Spreadsheet-like statement grid; keyboard navigation |
| **Reconciliation** | Split pane: statement left, ledger right, match in center |
| **Reports** | Print-first tables; export prominent |
| **Settings** | Flat form lists, minimal cards |

### Tablet

- Sidebar collapses early
- Tables horizontal scroll with frozen amount column

### Mobile

- Same bottom nav as A
- Denser list rows (32px touch min vs 44px comfort)
- Optional user preference: Compact / Comfortable density

### Pros / Cons

| Pros | Cons |
|------|------|
| Power-user / accountant favorite | Harder for non-accountants |
| Excellent for GL and ledger | Mobile AT keypad needs comfort mode |
| Differentiator vs colorful dashboards | More design work on density tokens |

**Scores:** Accounting 5 · Banking 5 · Mobile 3 · React 4 · Mono 5

**Best when:** Primary users are bookkeepers, not counter staff.

---

## Direction D — **Rich Dashboard** (TailAdmin-inspired flavor)

**Tagline:** Executive summary forward — still mono-compliant.

### Philosophy

- shadcn foundation (not TailAdmin code)
- Borrow KPI row layouts and chart placement from TailAdmin/MatDash
- **No gradient cards** — flat tokens only
- Charts supplement tables; never replace P&L/Balance Sheet HTML tables

### Desktop

| Surface | Treatment |
|---------|-----------|
| **Dashboard** | 4 KPI chips + 2 charts (sales trend, expense breakdown) + activity feed |
| **Banking** | Account cards with sparkline + cockpit queue |
| **Reconciliation** | Progress ring + queue (subtle, mono) |
| **Reports** | Chart summary header + drill-down table |
| **Settings** | Card grid for settings categories |

### Tablet / Mobile

- Charts simplify to single-metric sparklines on mobile
- Dashboard becomes KPI grid + list (no charts on phone)

### Pros / Cons

| Pros | Cons |
|------|------|
| Polished executive view | Risk of dashboard creep |
| Good for owner/partner roles | Chart library decision needed |
| Motivating for non-finance users | Must enforce mono discipline |

**Scores:** Accounting 4 · Banking 4 · Mobile 4 · React 4 · Mono 3*

\*Requires strict token rules to maintain mono.

**Best when:** Owners want visual summaries; accountants still have table drill-down.

---

## Direction E — **Material Neutral** (React Admin data + shadcn visuals)

**Tagline:** React Admin patterns, zero Material chrome.

### Philosophy

- Resource/List/Edit/Show routing from React Admin
- 100% shadcn component rendering
- Marmelab data provider patterns for FastAPI

### Desktop

| Surface | Treatment |
|---------|-----------|
| **Dashboard** | Custom (outside RA resources) |
| **Banking** | Custom resource with bespoke UI |
| **Reconciliation** | Custom |
| **Reports** | Custom |
| **Settings** | RA `<Resource name="members">` etc. |

### Pros / Cons

| Pros | Cons |
|------|------|
| Proven CRUD routing | Hybrid complexity |
| Enterprise Edition option for RBAC | Two mental models (RA + custom) |
| Mature ecosystem | Less clean than Refine + shadcn |

**Scores:** Accounting 4 · Banking 3 · Mobile 3 · React 4 · Mono 4

**Best when:** Team already knows React Admin.

---

## Side-by-side: key surfaces

### Dashboard

| Direction | Desktop | Mobile |
|-----------|---------|--------|
| A shadcn | KPI grid + today list | KPI grid + FAB |
| B Refine+shadcn | Same as A | Same as A |
| C Dense | Compact table + KPI row | Dense list |
| D Rich | KPI + 2 charts | KPI only |
| E RA+shadcn | Same as A | Same as A |

### Banking / Reconciliation

| Direction | Desktop | Mobile |
|-----------|---------|--------|
| A | Queue + detail panel | Money hub → Banking → card list |
| B | Custom workflow page | Same |
| C | Split-pane spreadsheet | Stacked cards, frozen amounts |
| D | Account cards + sparkline | List + summary chip |
| E | Custom | Same as A |

### Reports

| Direction | Desktop | Mobile |
|-----------|---------|--------|
| A | Tabs + financial HTML tables | Reports hub → statement cards |
| C | Print-first dense tables | Scrollable sections |
| D | Chart header + table body | KPI + section list |

### Settings

| Direction | Desktop | Mobile |
|-----------|---------|--------|
| A | Grouped cards + sidebar | More hub → Admin accordion |
| B | Inferencer CRUD for simple entities | Same |
| C | Flat forms | Same |

---

## Decision matrix

| Criterion | A | B | C | D | E |
|-----------|---|---|---|---|---|
| Mono policy | ●●●●● | ●●●●● | ●●●●● | ●●●○○ | ●●●●○ |
| Streamlit continuity | ●●●●● | ●●●●○ | ●●●●○ | ●●●○○ | ●●●○○ |
| Banking workflows | ●●●●● | ●●●●○ | ●●●●● | ●●●○○ | ●●●○○ |
| Owner-friendly dashboard | ●●●○○ | ●●●○○ | ●●○○○ | ●●●●● | ●●●○○ |
| Accountant density | ●●●●○ | ●●●●○ | ●●●●● | ●●●○○ | ●●●●○ |
| Build speed (DS-6) | ●●●○○ | ●●●●● | ●●●○○ | ●●●○○ | ●●●●○ |
| Long-term ownership | ●●●●● | ●●●●○ | ●●●●● | ●●●●○ | ●●●○○ |

---

## Recommended selection

### Primary: **Direction A** (shadcn Foundation)

Default for DS-3 mockups and DS-4 master spec.

### Optional module: **Direction C density mode**

User preference toggle (`comfortable` | `compact`) — does not change brand, only spacing.

### Optional module: **Direction D dashboard charts**

Reports hub and Home only — gated behind role (owner/manager).

### Data layer: **Direction B (Refine)** if team wants inferencer CRUD

Visual layer still Direction A.

---

## Explicitly rejected as primary direction

| Direction | Reason |
|-----------|--------|
| TailAdmin clone | Colorful KPIs, template lock-in |
| Flowbite clone | Visual identity mismatch |
| Pure React Admin MUI | Material chrome conflicts |
| Tremor-first | Chart-heavy, maintenance declining |
| ERPNext/Odoo fork | License + full rewrite |

---

## Next step

Approve **Direction A** (with optional C density + D charts) → proceed to [ERP_DS_03_MOCKUPS.md](./ERP_DS_03_MOCKUPS.md).
