# ERP-DS-04 — Master Design System

**Phase:** DS-4  
**Status:** Implementation-grade specification  
**Theme:** Direction A (shadcn Foundation)  
**Date:** 2026-06-05  
**Authority:** This document governs DS-6 React build. Streamlit follows `docs/UI_STYLE_GUIDE.md` until parity.

---

## 1. Branding

### Logo

| Asset | Spec |
|-------|------|
| Wordmark | Company name from settings — no baked-in product logo in v1 |
| App icon | 32×32 SVG — ledger grid motif, mono `--theme-info` on transparent |
| Favicon | Same icon 16/32/180px PNG |

### Icon style

- **Source:** `registry/icon_svg.py` — inline SVG, currentColor, no emoji in nav
- **Sizes:** `nav` 20px · `header` 18px · `inline` 14px · `row` 16px
- **Stroke:** 1.5px consistent; rounded caps
- **Color:** `currentColor` — inherits `--theme-text` or `--theme-muted`

### Headers

| Level | Component | Spec |
|-------|-----------|------|
| Page | `PageHeader` | Title 20px/600 + optional subtitle 13px muted + actions right |
| Section | `SectionLabel` | 10px uppercase, 700 weight, 0.07em tracking, `--theme-muted` |
| Financial | `FinSectionHeader` | Left 4px accent bar + section name + right-aligned total |
| Mobile screen | `ScreenTitle` | 13px/600 muted, ellipsis |

---

## 2. Colors

### Core palette (light)

| Token | CSS variable | Hex | Usage |
|-------|--------------|-----|-------|
| Background | `--background` / `--theme-bg` | `#F8FAFC` | Page |
| Card | `--card` / `--theme-card` | `#FFFFFF` | Surfaces |
| Text | `--foreground` / `--theme-text` | `#0F172A` | Body |
| Muted | `--muted-foreground` / `--theme-muted` | `#475569` | Labels |
| Border | `--border` / `--theme-border` | `#E6E9EE` | All borders |
| Primary | `--primary` / `--theme-info` | `#2563EB` | CTAs, active nav, chips |
| On-primary | `--primary-foreground` / `--erp-on-primary` | `#FFFFFF` | Text on solid primary |

### Semantic (restricted use)

| Token | Hex (light) | Allowed on |
|-------|-------------|------------|
| Success | `#16A34A` | Positive amounts, Paid pill, profit banner |
| Danger | `#DC2626` | Negative amounts, void, overdue, destructive |
| Warning | `#D97706` | Open/pending, backdated date indicator |
| Info | `#2563EB` | Partial status, links (same as primary) |

### Mono policy (non-negotiable)

1. **One accent:** `--primary` for chrome, chips, CTAs
2. **No gradient KPI cards**
3. **No per-metric background colors** except semantic signed amounts and status pills
4. **Dark mode:** same rules; adjust hex only

### shadcn mapping

```css
:root {
  --background: 210 40% 98%;      /* #F8FAFC */
  --foreground: 222 47% 11%;      /* #0F172A */
  --card: 0 0% 100%;
  --card-foreground: 222 47% 11%;
  --primary: 221 83% 53%;         /* #2563EB */
  --primary-foreground: 0 0% 100%;
  --muted: 215 16% 47%;
  --muted-foreground: 215 16% 47%;
  --border: 220 13% 91%;
  --radius: 0.5rem;               /* 8px */
  --destructive: 0 72% 51%;
  --success: 142 71% 45%;
  --warning: 32 95% 44%;
}
```

---

## 3. Typography

### Font stack

```css
--font-sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
--font-mono: ui-monospace, "SF Mono", Menlo, monospace; /* codes, JE# only */
```

### Scale

| Name | Size | Weight | Line | Use |
|------|------|--------|------|-----|
| `text-2xs` | 9px | 700 | 1.2 | KPI labels, micro badges |
| `text-xs` | 10px | 500–700 | 1.3 | Meta, pills, table headers |
| `text-sm` | 12px | 400–600 | 1.35 | Body small, list subtitles |
| `text-base` | 14px | 400 | 1.5 | Default body |
| `text-lg` | 16px | 600 | 1.25 | List titles mobile |
| `text-xl` | 18px | 700 | 1.15 | Ledger amount mobile |
| `text-2xl` | 22px | 800 | 1.1 | Banner values |
| `text-hero` | 72px | 800 | 1.0 | Mobile AT amount only |

### Financial numbers

- `font-variant-numeric: tabular-nums` on all amounts
- Right-align in tables and list rows
- Currency prefix: `USD 1,234.56` (company setting)
- Sign prefix: `+` inflow / `−` outflow

---

## 4. Layout

### Spacing scale

| Token | px | Use |
|-------|-----|-----|
| `--space-1` / `--mob-space-1` | 4 | Pill gaps, tight meta |
| `--space-2` / `--mob-space-2` | 8 | Chip gaps, field gaps |
| `--space-3` / `--mob-space-3` | 12 | Card padding mobile |
| `--space-4` / `--mob-space-4` | 16 | Card padding desktop, section gaps |
| `--space-5` / `--mob-space-5` | 24 | Section margins |
| `--space-6` / `--mob-space-6` | 32 | Page sections |

### Radius scale

| Token | px | Use |
|-------|-----|-----|
| `--radius-sm` | 6 | Pills, small chips |
| `--radius-md` / `--erp-field-radius` | 8 | Buttons, inputs, chips |
| `--radius-lg` | 10–12 | Cards, list rows |
| `--radius-xl` | 16 | Hub sheet top, modals |
| `--radius-full` | 999 | Status pills, FAB |

### Shadows

| Level | Value | Use |
|-------|-------|-----|
| None | — | Default cards (border only) |
| `shadow-sm` | `0 1px 3px color-mix(shadow 65%, transparent)` | AT amount card |
| `shadow-md` | `0 2px 6px color-mix(shadow 45%, transparent)` | Ledger cards mobile |
| `shadow-fab` | `0 4px 12px color-mix(primary 35%, transparent)` | FAB only |

### Borders

- Default: `1px solid var(--border)`
- Focus: `2px solid var(--primary)` + `outline-offset: 2px`
- Section accent: `4px left bar var(--primary)` (financial headers)

### Breakpoints

| Name | px | Layout |
|------|-----|--------|
| `mobile` | ≤968 | Bottom nav, hub sheets |
| `tablet` | 969–1200 | Collapsed sidebar |
| `desktop` | >1200 | Full sidebar |

---

## 5. Components

### 5.1 KPI cards

**Classes:** `.erp-mob-kpi-chip` / React `<KpiChip>`

| Property | Value |
|----------|-------|
| Background | `--card` |
| Border | 1px `--border` |
| Radius | 10px |
| Padding | 8px 12px |
| Label | 9px uppercase muted |
| Value | 12–14px bold tabular-nums |
| Variants | `success` `danger` `warning` `info` `neutral` `amt-pos` `amt-neg` `amt-zero` |

**Grid:** 3-col equal `minmax(0,1fr)`, gap 8px.

**Forbidden:** gradients, icon backgrounds, colored card fills (except highlight banner).

### 5.2 Tables

**Desktop ledger:** TanStack Table + shadcn Table

| Property | Value |
|----------|-------|
| Header | 10px uppercase muted |
| Row height | 40px comfortable / 32px compact |
| Numeric cols | right-align, tabular-nums |
| Name cols | wrap, no ellipsis on financial statements |
| Actions | icon buttons 32px, secondary style |
| Virtualization | Required for GL >500 rows (React only) |

**Mobile:** Card list — not a table. See List Row.

**Financial statements:** `FinTable` — code | name | amount columns; section subtotals.

### 5.3 Forms

| Element | Spec |
|---------|------|
| Label | 11px muted above field |
| Input height | 36px desktop / 44px mobile |
| Radius | 8px |
| Border | `--border`; focus `--primary` |
| Error | `--destructive` text + border |
| Section | Card wrap, 16px padding |
| Submit | Primary button, bottom-right or full-width mobile |

**Amount input:** Text field with locale parse (US/EU) — not `type=number`.

### 5.4 Buttons

| Variant | Fill | Text | Border | Min height |
|---------|------|------|--------|------------|
| Primary | `--primary` | white | none | 36px / 48px mobile hero |
| Secondary | `--card` | `--text` | `--border` | 36px |
| Danger | danger 8% mix | `--danger` | danger mix | 36px |
| Ghost | transparent | `--text` | none | 36px |

**Chip selected:** chip-active tokens — NOT solid primary fill.

### 5.5 Chips

| State | Tokens |
|-------|--------|
| Idle | `--erp-chip-idle-*` |
| Active | `--erp-chip-active-*` |

Height: 30–36px. Font: 11px/700. Use for tabs, filters, payment methods, report pickers.

### 5.6 Alerts

| Variant | Background | Border | Icon |
|---------|------------|--------|------|
| Info | info 8% mix | info 24% mix | optional |
| Success | success 8% mix | success 24% mix | ✓ |
| Warning | warning 8% mix | warning 24% mix | ⚠ |
| Danger | danger 8% mix | danger 24% mix | ✕ |

Streamlit `st.info/success/warning/error` maps to these in React.

### 5.7 Status pills

**Classes:** `.erp-mob-status-pill--{variant}`

| Variant | Use |
|---------|-----|
| success | Paid |
| warning | Open |
| danger | Overdue |
| info | Partial, Recorded |
| neutral | Active |
| void | VOID (strikethrough) |
| corrected | ✱ Corrected |

Padding: 2px 8px. Radius: full. Font: 10px/700.

### 5.8 List rows

**Classes:** `.erp-mob-list-row`

| Zone | Content |
|------|---------|
| Icon (optional) | 30–40px rounded square, semantic tint bg |
| Main | Title 12px/600 + subtitle 10px muted |
| Amount | Right-aligned 13px/700, semantic color |

Gap: 12px. Padding: 8px 12px. Margin-bottom: 8px.

### 5.9 Empty states

Centered 12px muted text. Padding: 12px 0. No illustration v1.

### 5.10 Drawers / sheets (mobile)

| Type | Behavior |
|------|----------|
| Hub sheet | Bottom sheet, grab handle, lists nav targets |
| Picker sheet | Full modal scrim, 72dvh max, internal scroll |
| Profile sheet | Header avatar + settings links |
| Detail sheet | Transaction/bank line expand |

Radix Sheet. Z-index: sheet 99980, scrim 99979, header 99990.

### 5.11 Dialogs

Desktop modals for: void confirm, period close, destructive actions.

| Property | Value |
|----------|-------|
| Max width | 480px |
| Padding | 24px |
| Actions | Secondary cancel + Primary/Danger confirm |

### 5.12 Highlight banner

Net P&L / cash-flow totals.

| Property | Value |
|----------|-------|
| Layout | Flex space-between |
| Padding | 16px 20px |
| Radius | 10px |
| Variants | success / danger / neutral |
| Value | 22px/800 tabular-nums |

---

## 6. Navigation components

### Desktop sidebar

- Width: 240px expanded / 64px collapsed
- Groups: accordion with 8 groups (see DS-5)
- Active item: chip-active tokens
- Section captions: Work · Reports · Advanced

### Mobile bottom bar

- Height: 56px + safe-area
- 5 slots: Home · Money · FAB · Reports · More
- Active: primary text; idle: muted
- FAB: 56px circle, primary fill, card ring

### Command palette (React only)

- Trigger: `Cmd+K` / header search icon
- shadcn Command component
- Routes + recent pages + actions

---

## 7. Domain-specific patterns

### Accounting

- Double-entry lines: debit | credit columns, balanced indicator
- JE expand: grid `1fr 4.5rem 4.5rem` on mobile
- Period closed: warning banner, block posting
- Statement tables: never DataFrame display — always `FinTable`

### Banking

- Queue card: amount prominent, confidence badge, party/sub ref
- Match actions: primary Match, secondary Skip
- Import history: list rows with status pill
- Readiness: info panel, not success wash

### Partners

- Mono role pills (no per-role colors)
- Equity movement: highlight banner
- Aging buckets: neutral card + semantic amounts only

### Reports

- Date bar: 2-col grid mobile, inline desktop
- Export: popover with Excel + PDF
- Tab strip: horizontal scroll mobile

---

## 8. Accessibility

- Touch targets: 44px minimum (WCAG 2.5.5)
- Focus visible on all interactive elements
- Radix primitives for keyboard nav in sheets/dialogs
- Status not conveyed by color alone (pill text + icon)
- `aria-label` on icon-only buttons

---

## 9. Streamlit ↔ React parity matrix

| Component | Streamlit | React | Parity test |
|-----------|-----------|-------|-------------|
| KPI chip | `mobile_kpi_chip_html` | `<KpiChip>` | Token snapshot |
| List row | `mobile_list_row_html` | `<ListRow>` | Visual regression |
| Status pill | `mobile_status_pill_html` | `<StatusPill>` | Variant enum |
| Fin table | `financial_statement_table_html` | `<FinTable>` | Column alignment |
| Section label | `mobile_section_label_html` | `<SectionLabel>` | CSS contract |
| Highlight banner | `mobile_highlight_banner_html` | `<SummaryBanner>` | Variant colors |

---

## 10. File conventions (React DS-6)

```
src/
  components/
    ui/          # shadcn primitives (owned)
    erp/         # domain components (KpiChip, ListRow, FinTable)
  styles/
    tokens.css   # maps --theme-* to shadcn
  layouts/
    DesktopShell.tsx
    MobileShell.tsx
```

---

## 11. Regression guards

Until React ships, maintain:

- `tests/test_ui1_design_language.py`
- `tests/test_mobile_ux02_a.py`
- `docs/ui_style_guide_preview.html` (update when tokens change)

Add when React ships:

- `tests/visual/` Playwright screenshots per DS-03 frames
- Storybook with all §5 components in light + dark

---

## Approval

| Role | Sign-off |
|------|----------|
| Product owner | |
| Engineering | |
| Design | |

**Approved theme direction:** Direction A  
**Next:** [ERP_DS_05_REACT_ARCHITECTURE.md](./ERP_DS_05_REACT_ARCHITECTURE.md) → DS-6 implementation
