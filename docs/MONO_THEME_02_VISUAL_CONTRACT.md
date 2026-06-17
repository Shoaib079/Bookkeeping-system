# MONO-THEME-02-S0 — Option A+ Visual Contract (Desktop + Mobile Shell)

**Status:** ✅ **Frozen (audit only)**  
**Mode:** Visual contract / audit only — **no CSS changes, no runtime changes, no route/nav/posting/accounting changes.**  
**Depends on:** MONO-THEME-01 complete (`docs/MONO_THEME_01_AUDIT.md`, shared grammar tokens in `ui/design_tokens.py`)  
**Tests:** `tests/test_mono_theme_02_visual_contract.py`  
**Source of truth:** User-approved screenshots + existing token SSOT (`ui/design_tokens.py` → `ui/theme.py` → `ui/theme.css`)

## Purpose

MONO-THEME-01 delivered the **token and grammar foundation**. Real screenshots show the live app is still **too spacious** and not yet as refined as the approved Option A+ direction. MONO-THEME-02 freezes **what “done” looks like** before any CSS work begins.

This document is the implementation contract for slices **S1–S5**. All implementation must use **existing MONO-THEME tokens only** — no new palette, no parallel CSS system.

---

## 1. Design philosophy

| Principle | Rule |
|-----------|------|
| **Accounting-first ERP** | Dense tables, readable money, operational clarity over marketing chrome |
| **Mono surfaces** | Neutral `--theme-bg` / `--theme-card` / `--theme-border` dominate every screen |
| **Single blue accent** | `#2563EB` (`--erp-primary-fill`, `--theme-info`, `--theme-focus`) for primary, active, focus only |
| **Dense but readable** | Tighter vertical rhythm; never sacrifice ledger legibility |
| **One app** | Desktop and mobile must feel **identical in grammar**, not like two products |
| **No rainbow dashboards** | Decorative hue per section/card is forbidden |
| **Color = meaning** | Tint only when data carries semantics (P&L, status, recon, void) |

**Inspired by (reference only — do not copy templates):**

- Stripe Dashboard — calm density, neutral cards, accent for action/active
- QuickBooks Accountant — accounting-first hierarchy, money-forward tables
- shadcn/ui — token scales, subtle borders, restrained shadows
- Linear navigation — quiet sidebar, accent bar + tint for active, not filled buttons

**Explicitly NOT:**

- TailAdmin / colorful admin templates
- Rainbow SaaS dashboards
- Per-section decorative card tints
- New accent colors or gradients for chrome

**Token authority:** `ui/design_tokens.py` is SSOT. `COMPONENT_GRAMMAR_TOKENS` (`--erp-nav-*`, `--erp-card-*`, `--erp-chip-*`, `--erp-table-*`) is the shared component layer. React export: `react_token_bundle()` grammar keys (MONO-THEME-01-S7).

---

## 2. Sidebar contract

### Current state (screenshot observation)

- Registry-driven nav structure is **good** — keep `registry/navigation.py` and `app.py` nav renderers unchanged
- MONO-THEME-01-S3 wired `--erp-nav-*` tokens into desktop sidebar CSS
- Active item can still **read as a filled Streamlit primary button** (heavy border box, bold fill) rather than a quiet nav row
- Section spacing is functional but not yet rhythmically tight

### Target

| Element | Visual rule |
|---------|-------------|
| **Active item** | Subtle blue tint (`--erp-nav-active-bg`) + **3px left bar** (`--erp-nav-active-bar`) + blue label/icon (`--erp-nav-active-fg`) |
| **Idle item** | Transparent/neutral background; text `--theme-text` |
| **Hover** | Light neutral wash (`--erp-nav-hover-bg`) — no blue fill on hover |
| **Section headers** | Muted uppercase (`--erp-nav-section-fg`); tighter vertical rhythm between groups |
| **Folder accordion** | Open group: faint left rail tint; active folder header matches nav active grammar — **not** a solid button pill |

### Never

- Giant blue filled buttons for active nav
- Rainbow or per-role icon colors
- Route / registry / `react_route` changes
- New nav tokens or accent hues

**CSS owners (implementation S1):** `ui/theme.css`, `ui/icons.css` — sidebar scoping only.

---

## 3. Top bar contract

### Current state (screenshot observation)

- Fixed header shell (`--hdr-h`) works; company + page context present
- Controls are usable but can feel **slightly tall/spacious** relative to accounting density target
- Search exists but could be more visually prominent in the hierarchy

### Target

| Element | Visual rule |
|---------|-------------|
| **Height / density** | Compact bar aligned to `--hdr-h`; minimal vertical padding inside brand block |
| **Alignment** | Logo, company name, page title, search, toolbar on one calm row (desktop) |
| **Controls** | Softer secondary buttons; primary actions use `--erp-primary-fill` sparingly |
| **Search** | Visually prominent input (card surface, clear border); not buried |
| **Company identity** | Company name + subtitle readable at a glance |

### Never

- Large decorative hero banners in the header
- Extra accent colors or gradients in the chrome
- Header height changes that break sidebar `top: var(--hdr-h)` math without coordinated update

**CSS owners (implementation S2):** `ui/theme.css`, `ui/mobile_header.css`, header rules in `ui/widgets.css`.

---

## 4. Dashboard contract

### Current issue (screenshot observation — primary gap)

**Too much whitespace.** KPI grid, section gaps, and card padding leave the home screen feeling sparse rather than accounting-operational.

### Target

| Area | Visual rule |
|------|-------------|
| **KPI grid** | Denser grid (`kpi-grid` / `stMetric`): smaller gaps, tighter card padding, consistent `--erp-card-*` shells |
| **Hierarchy** | Section headers (`erp-section-hdr`) close to their content; welcome card compact, not hero-sized |
| **Recent activity** | List rows visually prominent — tight rows, clear party/amount/date, status pills with chip grammar |
| **Insights** | Insight rows as card surfaces (`--erp-card-*`), not floating text in empty space |
| **Banking / cash** | Cash position visible without a separate decorative panel |
| **Alerts** | Semantic left borders only (danger/warning/info) on neutral card bg |

### Keep

- Clean neutral cards — no decorative section tints
- Semantic deltas (up/down pct, positive/negative balances) using `--theme-success-text` / `--theme-danger-text`
- Tabular-nums on money

### Never

- Marketing-style hero gradients on dashboard
- Extra KPI accent colors per metric type (mono text for KPI values unless semantic delta)

**CSS owners (implementation S3):** `ui/theme.css` (`.erp-dash-*`, `.kpi-*`), `ui/widgets.css` (`stMetric`, `stVerticalBlockBorderWrapper`).

---

## 5. Card contract

**All neutral card shells** must resolve through:

```
--erp-card-bg
--erp-card-border
--erp-card-radius
--erp-card-shadow
--erp-card-muted-bg   (subtle inset panels only)
```

### Rules

- Same radius, border weight, and shadow on dashboard KPI, bordered Streamlit containers, mobile KPI chips, hub sheets, and list row cards
- **No decorative colors** on card backgrounds or borders
- Left accent borders (4px) allowed **only** when semantic (alert severity, section accent prop)

### Semantic colors (immutable — never flatten to mono)

| Meaning | Token family | Use |
|---------|--------------|-----|
| Profit / inflow | `--theme-success`, `--theme-success-text` | P&L positive, paid, matched |
| Loss / outflow | `--theme-danger`, `--theme-danger-text` | P&L negative, overdue, void |
| Caution | `--theme-warning`, `--theme-warning-text` | Review, partial, aging |
| Info / primary action | `--theme-info` | Links, active nav text, focus |
| Recon matched | success mix | Banking recon row/chip |
| Recon review | warning mix | Banking recon row/chip |
| Recon mismatch | danger mix | Banking recon row/chip |

---

## 6. Mobile contract

Mobile must feel like: **“Desktop compressed”** — not a separate design language.

| Grammar | Parity rule |
|---------|-------------|
| **Bottom nav active** | Same `--erp-nav-active-bg` tint + `--erp-nav-active-bar` accent + `--erp-nav-active-fg` text as desktop sidebar |
| **Hub sheets** | Card shells via `--erp-card-*` (via `--mob-surface-*` aliases) |
| **KPI chips** | Same card border/radius/shadow as desktop KPI cards |
| **Status pills / chips** | `--erp-chip-*` + extensions; semantic variants unchanged |
| **Tables / lists** | `--erp-table-*` row density aligned with desktop txn ledger |

### Never

- Mobile-only accent palette
- Emoji nav (SVG icons per MOBILE-NAV-ICON-01)
- Separate rainbow status colors

**CSS owners (implementation S4):** `ui/mobile_shell.css`, `ui/mobile_components.css`, `ui/mobile_header.css`, mobile overrides in `ui/widgets.css`.

---

## 7. Old vs new preview

Screenshots are the source of truth. Below describes **observed current** vs **contract target**. This is refinement, not redesign.

### Desktop Home (dashboard)

```
CURRENT (screenshot):
- Spacious vertical gaps between KPI sections and bordered containers
- KPI cards clean but float with generous padding/margins
- Welcome card reads slightly hero-sized
- Recent activity present but competing with empty space
- Overall: minimal, clean, but not yet accounting-dense

TARGET (Option A+):
- Tighter KPI grid (smaller gap, lower min-height cards)
- Section headers closer to content blocks
- Activity list feels like the operational center of the page
- Insights and cash rows as compact card strips
- Overall: refined, denser, stronger hierarchy — same components, less air
```

### Sidebar active item

```
CURRENT (screenshot):
- Active nav uses grammar tokens but can still resemble a filled primary button
- Full border box + heavy weight on active/top-level items

TARGET (Option A+):
- Quiet row: light blue tint + 3px left bar + blue text/icon
- No full rectangular button border on active state
- Hover: neutral wash only
```

### Top bar

```
CURRENT: Functional fixed header; adequate branding; search could dominate more
TARGET: Compact, aligned, softer secondary controls, search prominence unchanged in layout
```

### Mobile dashboard

```
CURRENT: Mobile KPI scroll/grid works; bottom nav active tint partially overridden by widget rules
TARGET: Active tab matches desktop accent grammar; KPI chips use same --erp-card-* as desktop
```

### Light / dark

Both modes must pass contrast on tinted nav rows and dense table hover (`--erp-table-row-hover-bg`). No new dark palette — existing `DARK_COLOR_TOKENS` only.

**No redesign:** Same page structure, same nav tree, same Streamlit widget keys, same `erp-*` class names.

---

## 8. Visual scorecard

Scores reflect **live UI vs this contract** (screenshot review, 2026-06-05). Target after MONO-THEME-02-S1–S5 implementation: **10/10** on all axes.

| Surface | Current (est.) | Target | Gap |
|---------|----------------|--------|-----|
| **Sidebar** | 7/10 | 10/10 | Active state too button-like; spacing rhythm |
| **Top bar** | 8/10 | 10/10 | Compactness + search prominence |
| **Dashboard** | 6/10 | 10/10 | Whitespace / hierarchy — largest gap |
| **Desktop/mobile parity** | 7/10 | 10/10 | Bottom-nav active grammar drift in cascade |
| **Accounting feel** | 8/10 | 10/10 | Dense tables good; dashboard too airy |

**Pass criteria for epic closure:** All five axes ≥ 9/10 on desktop + mobile screenshot review; full pytest green; no new hex outside `design_tokens.py`.

---

## 9. Implementation slices

| Slice | Scope | Status |
|-------|--------|--------|
| **MONO-THEME-02-S0** | This visual contract (audit only) | ✅ **Complete** |
| **MONO-THEME-02-S1** | Sidebar polish — active tint + accent bar, spacing rhythm, no button fill | 📋 Planned |
| **MONO-THEME-02-S2** | Top bar — compact alignment, softer controls, search prominence | 📋 Planned |
| **MONO-THEME-02-S3** | Dashboard density — KPI grid, sections, activity, insights | 📋 Planned |
| **MONO-THEME-02-S4** | Mobile parity — bottom nav, KPI chips, hub sheets | 📋 Planned |
| **MONO-THEME-02-S5** | Final polish — tables/lists density, dark-mode pass, scorecard closure | 📋 Planned |

**Per-slice rules:**

- CSS/layout only in listed owner files
- Token-parity tests + existing UI/theme/dashboard/nav/mobile tests must pass
- Screenshot smoke: desktop Home, sidebar active, KPI area, activity list, mobile Home, dark mode quick check
- No accounting, PostgreSQL, nav route, or business-logic changes

---

## No-change statement (MONO-THEME-02-S0)

- **Audit / contract only** — no CSS edits, no Python runtime edits, no schema, no posting, no navigation registry changes
- **No new colors** — all implementation slices use existing `LIGHT_COLOR_TOKENS` / `DARK_COLOR_TOKENS` / `COMPONENT_GRAMMAR_TOKENS`
- **Semantic colors immutable** — success, danger, warning, recon states, void, P&L sign colors preserved
- **shadcn / Stripe / QuickBooks / Linear** — inspiration only; no template copying

---

## Related documents

| Doc | Role |
|-----|------|
| [MONO_THEME_01_AUDIT.md](./MONO_THEME_01_AUDIT.md) | Token + grammar foundation (S1–S7 complete) |
| [UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md](./UI_SYSTEM_02_REACT_DESIGN_CONTRACT.md) | React token + grammar export |
| [ROADMAP.md](../ROADMAP.md) | Epic tracking |

*Frozen 2026-06-05. MONO-THEME-02-S0 audit complete. Next: **MONO-THEME-02-S1** (sidebar polish).*
