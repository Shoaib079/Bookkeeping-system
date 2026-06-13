# MOBILE-UX-02 — Theme & Design-System Audit

**Mode:** Research + recommendation. No code, no implementation, no theme copying.
**Goal:** a complete mobile UI direction for the ERP (accounting / finance / bookkeeping, mobile-first, future FastAPI + React), not partial styling patches.
**Grounding:** the existing ERP already runs a mature, intentional design system (see `docs/UI_STYLE_GUIDE.md`): **design tokens** (`--theme-*`), **one primary accent (mono policy)**, **light/dark**, **HTML financial tables** (not Glide), **KPI grids**, **bottom-nav + FAB**, all **regression-tested** (`test_ui1_design_language.py`). Any direction must *extend* this, not replace it.

---

## Candidate templates (current facts)

| Template | Stack | License | Character |
|----------|-------|---------|-----------|
| **shadcn/ui** | Radix + Tailwind, copy-in components (you own the code) | MIT | Design-system *primitives*; CSS-variable tokens; neutral/mono by default |
| **shadcn-admin (satnaing)** | Next.js + shadcn/ui | MIT, ~12k★ — "the foundation everyone forks" | Admin *shell* reference: collapsible sidebar, **Cmd+K** command palette, light/dark, RTL |
| **TailAdmin React** | React 19 + Tailwind v4 + Vite | MIT (free; Pro paid) | Batteries-included: 500+ elements, 7 dashboard variants, AI pages |
| **Flowbite Admin** | Tailwind + Flowbite component library | MIT | Component-library-driven; broad component set |
| **MatDash** | React/Next + Tailwind + TS + Flowbite UI + ApexCharts | MIT | Finance-leaning widgets, charts, responsive |

---

## Evaluation across 13 dimensions

| # | Dimension | shadcn/ui (+shadcn-admin) | TailAdmin | Flowbite / MatDash |
|---|-----------|---------------------------|-----------|--------------------|
| 1 | Overall design quality | High, restrained, "deliberate" | High but busy/dashboard-y | Good, more generic |
| 2 | Mobile responsiveness | Strong (Radix + Tailwind) | Strong | Strong |
| 3 | Accounting/ERP fit | **Best** — neutral, data-dense, mono-friendly | Medium — colorful KPI cards fight mono | Medium-high (MatDash finance widgets) |
| 4 | Navigation patterns | Collapsible sidebar + **Cmd+K** (shadcn-admin) | Sidebar + topbar variants | Sidebar/topbar |
| 5 | Card/KPI design | Token-driven, subtle | Rich, gradient-prone | Rich, chart-coupled |
| 6 | Table/list design | Clean; pairs with TanStack Table | Decent | Flowbite tables/ApexCharts |
| 7 | Forms | Excellent (Radix primitives + validation patterns) | Good | Good |
| 8 | Reports | Neutral, print-friendly | Dashboard-styled | Chart-heavy |
| 9 | Banking/reconciliation | Best for dense queues + command palette | Workable | Workable |
| 10 | Dark/light | First-class CSS-variable theming | Yes | Yes |
| 11 | FastAPI/React fit | **Best** — own the components, no lock-in | Good (template) | Good (template) |
| 12 | Approximable in Streamlit now | **High** — tokens already map | Partial | Partial |
| 13 | Should wait for React | Palette, virtualized grids | Same | Same |

**Key read:** the ERP's existing **mono, token-based, financial-table-first** discipline aligns almost 1:1 with **shadcn/ui's** CSS-variable + neutral philosophy. TailAdmin/Flowbite/MatDash are *full visual templates* — faster to stand up, but their colorful, dashboard-centric opinions actively conflict with the ERP's deliberate mono policy and would have to be stripped (you'd fight the template and own less code).

---

## 3 recommended theme directions

### Direction A — **shadcn/ui as the design-system foundation** (recommended)
Own the components; map the existing `--theme-*` tokens to shadcn CSS variables; borrow the **shell/IA** (collapsible sidebar, Cmd+K, responsive nav) from **shadcn-admin** as a *reference*, not a dependency.
- **Pros:** closest philosophical + technical match to today's system; preserves mono + token discipline (and its regression tests' intent); no template lock-in; cleanest FastAPI/React target; tokens migrate directly.
- **Cons:** more assembly than a batteries-included template; you build the dashboard widgets yourself (mitigated by reusing the ERP's existing KPI/table grammar).

### Direction B — **TailAdmin React (batteries-included)**
Adopt TailAdmin as the React shell + widget library.
- **Pros:** fastest to a rich dashboard; MIT free; React 19 + Tailwind v4; large component count.
- **Cons:** opinionated, colorful visuals fight the mono policy → significant stripping; you inherit a template's structure and own less; risk of design drift from the established token system.

### Direction C — **Flowbite / MatDash (component-library route)**
Use Flowbite (or MatDash's finance widgets + ApexCharts) as the component layer.
- **Pros:** broad finance-oriented components and charts out of the box; MIT; middle ground on speed vs control.
- **Cons:** Flowbite's visual identity and heavier component opinions; weaker alignment with the token/mono system; chart library lock-in (ApexCharts) vs the ERP's current Altair/native charts.

---

## Best fit for our ERP

**Direction A (shadcn/ui foundation), with shadcn-admin as the layout reference and TailAdmin/MatDash as pattern libraries to borrow from — not adopt wholesale.**

Why: the ERP is not starting from zero. It already enforces tokens, mono, light/dark, and financial-table readability with tests. shadcn/ui is the only candidate whose *defaults* match that discipline, so the migration becomes "map tokens + rebuild shells" rather than "strip a template's opinions." It also gives the strongest long-term position: the team owns every component (no template upgrade treadmill), and the existing `--theme-*` variables become shadcn theme variables almost directly. Borrow the **command palette (Cmd+K)** and **collapsible/responsive shell** ideas from shadcn-admin; borrow **finance KPI/table layouts** as inspiration from MatDash/TailAdmin without importing their chrome.

---

## Mobile design system proposal (extends today's tokens)

- **Tokens:** keep the existing `--theme-*` set as the source of truth; formalize a **spacing scale** (4/8/12/16/24) and **radius scale** (8 control / 10–12 card) to match shadcn conventions.
- **Color:** one accent (`--theme-info`); semantic success/danger/warning only for signed amounts, status pills, and destructive actions (already policy). No gradient KPI cards.
- **Touch targets:** 44px min, 48–56px for hero/primary mobile actions (already in the style guide).
- **Navigation:** bottom-nav + center FAB (exists); add a **command/search affordance** as the mobile analog of Cmd+K; full-screen grouped "More" (per MOBILE-UX-01).
- **Lists over tables on mobile:** card-list rows with right-aligned amounts and a 3–4 action foot (exists for transactions) — generalize to banking queue, AR/AP, reports drilldowns.
- **Sheets/drawers:** standardize the hub-sheet + detail slide-over grammar (used by P1.3 queue) as the mobile disclosure pattern.
- **Density modes:** compact/comfortable as a **user preference** (B), per MOBILE-UX-01/P2.3.
- **Financial readability:** keep the HTML financial-table path (tabular nums, no ellipsis, wrap names) — this is an ERP differentiator the dashboard templates don't prioritize.
- **Dark mode:** mono parity (existing policy) — same grammar, no metric tinting.

---

## Streamlit MVP styling changes (approximable now)

- Normalize the **spacing/radius scale** to shadcn-like values across `ui/*.css` (token-level, low risk).
- Generalize the **mobile list-card** pattern beyond transactions (banking queue, AR/AP, report rows).
- Add a **lightweight command/search entry** on mobile (search field that routes) — a Streamlit-feasible stand-in for Cmd+K (not the full palette).
- Tighten **KPI grid + financial table** usage to the documented helpers everywhere (kill any residual `st.metric`/Glide display tables).
- Keep everything **token-driven** so the same variables transfer to shadcn later.
- **Do not** chase template visuals (gradients, colorful KPI cards) — they violate the mono policy and would be undone in React anyway.

## What should wait for React

- True **Cmd+K command palette** with fuzzy routing.
- **Virtualized data grids** (large GL/ledger) and column-level interactions.
- **Route-based IA** + deep links + transitions (replaces `mobile_hub_open` session-state).
- **Drag/drop** and keyboard-driven reconciliation queue.
- **Client-side form validation**, optimistic UI, offline/PWA.
- Rich **chart interactivity** (decide Altair-equivalent vs a React chart lib at that point).

---

## React future target design (direction)

- **Foundation:** shadcn/ui components + Tailwind; **map current `--theme-*` tokens to shadcn theme variables**; preserve the mono policy as the theme default.
- **Shell:** collapsible sidebar (desktop) + bottom-nav (mobile) from a **single declarative route table** (reuse the role/industry config from P2.3 + MOBILE-UX-01 IA) — Cmd+K palette over those routes.
- **Data:** TanStack Table for ledgers/queues (virtualized); keep the ERP's financial-table readability rules as a styled table variant.
- **Reuse, don't import:** take shell/IA patterns from shadcn-admin and finance widget layouts from TailAdmin/MatDash as inspiration; the codebase stays owned (no template dependency).
- **Outcome:** the design language is continuous from Streamlit → React because both are driven by the same tokens and the same mono/financial-readability rules.

---

## Risks

- **Template lock-in / visual drift** if a colorful template (TailAdmin/Flowbite/MatDash) is adopted wholesale — fights the mono policy and the tested design grammar.
- **Chasing dashboard aesthetics** over accounting readability (gradient KPIs, chart-heavy reports) — the ERP's edge is dense, readable financial data.
- **Two design languages** if Streamlit styling diverges from the React target — mitigated by token continuity.
- **Over-investing in Streamlit chrome** for things that belong in React (palette, virtualized grids).

---

*Research + recommendation only. No code, no implementation, no theme copying. Bottom line: the ERP already lives a shadcn-like discipline (tokens, mono, light/dark, financial-table-first). Recommend **Direction A — shadcn/ui as the foundation**, borrowing shell/IA patterns from shadcn-admin and finance layouts from TailAdmin/MatDash, rather than adopting any colorful template wholesale. Now: normalize spacing/radius, generalize mobile list-cards, add a search-as-command affordance, all token-driven. Later (React): shadcn/ui + route-based IA + Cmd+K + virtualized grids, with the current tokens carried straight across.*

---

Sources:
- [TailAdmin — Free React Tailwind Admin Dashboard (GitHub)](https://github.com/TailAdmin/free-react-tailwind-admin-dashboard)
- [TailAdmin React](https://tailadmin.com/react)
- [28 Best Free Shadcn Admin Dashboard Templates (2026) — AdminLTE.IO](https://adminlte.io/blog/shadcn-admin-dashboard-templates/)
- [18 Best shadcn/ui Templates & Starter Kits for 2026 — AdminLTE.IO](https://adminlte.io/blog/shadcn-ui-templates/)
- [Flowbite Admin Dashboard (GitHub)](https://github.com/themesberg/flowbite-admin-dashboard)
- [Flowbite React Admin Dashboard (GitHub)](https://github.com/themesberg/flowbite-react-admin-dashboard)
- [MatDash React Tailwind Free (GitHub)](https://github.com/adminmart/matdash-react-tailwind-free)
