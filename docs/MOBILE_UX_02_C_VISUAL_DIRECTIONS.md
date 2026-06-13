# MOBILE-UX-02-C — Visual Directions (mockup summary)

**Mode:** Visual direction / mockups + commentary. No code, no implementation.
Companion to `MOBILE_UX_02_THEME_DESIGN_AUDIT.md`. Mockups were rendered as interactive light/dark boards (Dashboard, Money, Reports, More, Reconcile, Financial statement, with bottom nav) for three directions.

## The three directions

### Option A — Accounting-first shadcn (recommended)
Mono, one accent, generous whitespace, tabular financial rows, quiet confidence pills.
- **Pros:** matches the existing token/mono system ~1:1; least noise during fast daily work; figures are the hero; scales to 500+ rows; cleanest shadcn/React migration.
- **Cons:** less flashy; build dashboard widgets yourself; less hand-holding for non-finance users.
- **Fits:** daily operators, bookkeepers, clarity-over-decoration users.

### Option B — TailAdmin-inspired
Colorful KPI cards, dashboard chart, vibrant icon tiles, % confidence badges, rounded chrome.
- **Pros:** instantly legible KPIs for non-accountants; modern, motivating; fastest "wow" dashboard.
- **Cons:** color fights the mono policy + financial-table discipline; decoration over density; more to strip for React.
- **Fits:** owner-facing dashboards where glanceable KPIs beat dense entry.

### Option C — Traditional accounting ERP (QuickBooks / Xero / Zoho)
Brand top-bar, labeled bottom tabs, dense list/table rows, classic statement tables, status pills.
- **Pros:** immediate familiarity; dense, table-first; great for high-volume scanning.
- **Cons:** busier chrome; least distinctive; brand bar partially breaks mono; can feel legacy on mobile.
- **Fits:** power bookkeepers and trading firms who live in tables.

## Best fit by industry

| Industry | Best fit | Why |
|---|---|---|
| Restaurants | A (richer dashboard optional) | Fast daily cash/EOD capture; calm > colorful in rushes; still glanceable |
| Service businesses | A | Low volume, AR/invoice focus; clarity wins |
| Trading companies | A + dense-table variant (C acceptable) | High volume + inventory + payables; dense scannable tables |
| Bookkeeping firms | A (Cmd+K, density) | Power users; palette + tabular density + defensible statements; some prefer C familiarity |
| Partners | A / B | Read-mostly (P&L, partner statement); A clean, B's KPI color helps non-finance partners |

## Recommendation

Make **Option A the spine** — the only direction that extends the existing design system rather than fighting it, and the cleanest path to shadcn/ui. Treat **B and C as configurable flavors, not separate products**:
- a "richer dashboard" toggle (B-style KPI color/charts) as a **user/company preference**;
- a "dense table" **density mode** (C-style) for power users.

Both fit the configurable-ERP model (P2.3). One design language serves restaurants (calm but glanceable), bookkeepers/traders (density), and partners (clean read).

*Mockups only. No code, no implementation, no theme copying.*
