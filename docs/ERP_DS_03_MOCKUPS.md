# ERP-DS-03 — Visual Mockups

**Phase:** DS-3  
**Mode:** Wireframe specification — no implementation  
**Theme:** Direction A (shadcn Foundation)  
**Date:** 2026-06-05  
**Formats:** ASCII wireframes + layout notes. Replace with Figma frames before DS-6.

---

## Global chrome

### Light mode tokens (summary)

| Role | Value |
|------|-------|
| Background | `#F8FAFC` (`--theme-bg`) |
| Card | `#FFFFFF` (`--theme-card`) |
| Text | `#0F172A` |
| Muted | `#475569` |
| Primary | `#2563EB` (`--theme-info`) |
| Border | `#E6E9EE` |

### Dark mode tokens (summary)

| Role | Value |
|------|-------|
| Background | `#0B1220` |
| Card | `#111827` |
| Text | `#F1F5F9` |
| Muted | `#94A3B8` |
| Primary | `#3B82F6` |
| Border | `#1E293B` |

**Dark mode rule:** Same layout and component grammar. No metric tinting beyond semantic signed amounts.

---

## Desktop mockups

### 1. Dashboard

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [≡]  Acme Bistro Ltd ▾                              [🔍] [🔔] [Avatar ▾]   │
├──────────┬──────────────────────────────────────────────────────────────────┤
│ Home ●   │  HOME                                                            │
│ + New    │  ┌─────────────┬─────────────┬─────────────┬─────────────┐      │
│ Ledger   │  │ TODAY SALES │ TODAY EXP   │ NET TODAY   │ CASH BAL    │      │
│ Banking  │  │ $4,280.00   │ $1,120.50   │ +$3,159.50  │ $8,420.00   │      │
│ Reports  │  └─────────────┴─────────────┴─────────────┴─────────────┘      │
│ ─────    │                                                                  │
│ ▾ Trans  │  RECENT ACTIVITY                              [View ledger →]    │
│ ▾ People │  ┌──────────────────────────────────────────────────────────┐   │
│ ▾ Close  │  │ 🧾 Walk-in      Sale · CS-1042          +$45.00   14:32 │   │
│ ▾ Books  │  │ 💳 Sysco        Purchase · PUR-88       −$320.00  11:05 │   │
│ ▾ Team   │  │ 🧾 Catering Co  Credit Sale · INV-12  +$890.00  09:15 │   │
│ Settings │  └──────────────────────────────────────────────────────────┘   │
│          │                                                                  │
│          │  QUICK ACTIONS                                                   │
│          │  [Cash Recon]  [EOD Close]  [Add Transaction]                   │
└──────────┴──────────────────────────────────────────────────────────────────┘
```

**Notes:**
- KPI chips: flat card, 9px uppercase label, 12–14px value, semantic color on signed amounts only
- No gradient hero cards
- Sidebar: collapsible to icon rail at `<1200px`

---

### 2. Banking

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ BANKING — Operating Account (****4821)                    [Import] [Settings] │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Queue (240px) ────────┐ ┌─ Detail ─────────────────────────────────────┐ │
│ │ UNMATCHED (12)         │ │ Statement line                              │ │
│ │ ┌────────────────────┐ │ │ 04 Jun  SYSCO FOODS        −$320.00       │ │
│ │ │ −$320 SYSCO  ● high│ │ │ Status: [Open]  Confidence: 92%           │ │
│ │ └────────────────────┘ │ │                                             │ │
│ │ ┌────────────────────┐ │ │ Suggested matches                           │ │
│ │ │ +$1,200 DEPOSIT    │ │ │ ○ PUR-88  Sysco Invoice    −$320.00  [Match]│ │
│ │ └────────────────────┘ │ │ ○ Create expense            −$320.00  [Create]│ │
│ │ ...                    │ │                                             │ │
│ └────────────────────────┘ │ [Skip]  [Match]  [Split]                     │ │
│                            └─────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│ Readiness: 94% tied · 3 exceptions · Last import 2h ago                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- Queue cards use `erp-mob-list-row` grammar at desktop width
- Status pills: shared `erp-mob-status-pill` variants
- Readiness panel: info accent strip (not success green wash)

---

### 3. Reconciliation (Cash Recon / EOD)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CASH RECONCILIATION — 04 Jun 2026                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌──────────────┬──────────────┬──────────────┐                            │
│ │ EXPECTED     │ COUNTED      │ VARIANCE     │                            │
│ │ $1,842.50    │ $1,840.00    │ −$2.50       │                            │
│ └──────────────┴──────────────┴──────────────┘                            │
│                                                                             │
│ DENOMINATION COUNT                                                          │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ $100 × 10 = $1,000    $20 × 20 = $400    $10 × 40 = $400   ...        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ VARIANCE NOTES (required if ≠ 0)                                            │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Short $2.50 — till #2                                                      │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                        [Save draft] [Close] │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 4. Reports (P&L)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PROFIT & LOSS                     01 Apr 2026 — 30 Apr 2026    [Export ▾]  │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─ Date bar ──────────────────────────────────────────────────────────────┐ │
│ │ From [01/04/2026]    To [30/04/2026]                                    │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ INCOME                                              USD 24,500.00           │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 4100  Food Sales                                    18,200.00           │ │
│ │ 4200  Beverage Sales                                 6,300.00           │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│ EXPENSES                                            USD 16,800.00           │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ 5100  COGS                                          10,200.00           │ │
│ │ 6200  Payroll                                        6,600.00           │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│ ┌─ NET PROFIT BANNER ────────────────────────────────────────────────────┐ │
│ │ Net Profit · Margin 31.4%                              USD 7,700.00     │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Notes:**
- Financial tables: `financial_statement_table_html` grammar — tabular nums, wrap account names
- Section headers: left accent bar, uppercase muted label

---

### 5. Settings

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ COMPANY SETTINGS                                                            │
├──────────────┬──────────────────────────────────────────────────────────────┤
│ General ●    │  GENERAL                                      [Save]        │
│ Accounting   │  ┌────────────────────────────────────────────────────────┐  │
│ Banking      │  │ Company name    [Acme Bistro Ltd          ]            │  │
│ Members      │  │ Currency        [USD ▾]                               │  │
│ Permissions  │  │ Fiscal year     [Jan 1 ▾]                             │  │
│ Backup       │  └────────────────────────────────────────────────────────┘  │
│              │                                                              │
│              │  MODULES                                                     │
│              │  [●] Inventory  [●] Partners  [○] Budget                     │
└──────────────┴──────────────────────────────────────────────────────────────┘
```

---

## Mobile mockups

### 1. Home

```
┌─────────────────────────┐
│ Acme Bistro    [Avatar] │
├─────────────────────────┤
│ ┌─────┬─────┬─────┐     │
│ │SALES│ EXP │ NET │     │
│ │4.2k │1.1k │+3.1k│     │
│ └─────┴─────┴─────┘     │
│                         │
│ TODAY                   │
│ ┌─────────────────────┐ │
│ │🧾 Walk-in    +$45  │ │
│ │💳 Sysco     −$320  │ │
│ └─────────────────────┘ │
│                         │
│ [Cash Recon] [EOD]      │
├─────────────────────────┤
│ Home Money [+] Rpt More │
└─────────────────────────┘
```

---

### 2. Money hub (sheet)

```
┌─────────────────────────┐
│ ─── (grab handle)       │
│ Money                   │
│                         │
│ CLOSE                   │
│ [Cash Reconciliation]   │
│ [External Sales Verif.] │
│ [End-of-Day Close]      │
│                         │
│ BANK                    │
│ [Banking]               │
│ [Recon Health]          │
│ [Import Statements]     │
├─────────────────────────┤
│ Home Money [+] Rpt More │
└─────────────────────────┘
```

---

### 3. Reports hub

```
┌─────────────────────────┐
│ Reports                 │
│                         │
│ STATEMENTS              │
│ [P&L] [Balance Sheet]   │
│ [Cash Flow]             │
│                         │
│ LEDGER                  │
│ [Transaction Ledger]    │
│                         │
│ SUMMARIES               │
│ [Sales Report]          │
│ [Expenses Report]       │
├─────────────────────────┤
│ Home Money [+] Rpt More │
└─────────────────────────┘
```

---

### 4. More hub

```
┌─────────────────────────┐
│ More                    │
│                         │
│ [People →]              │
│                         │
│ BOOKS                   │
│ [GL] [Chart of Accounts]│
│ [Journal Entries] ...     │
│                         │
│ ADMIN                   │
│ [Company Settings]      │
│ [Backup] [Audit Log]    │
├─────────────────────────┤
│ Home Money [+] Rpt More │
└─────────────────────────┘
```

---

### 5. Reconciliation (mobile)

```
┌─────────────────────────┐
│ ← Cash Reconciliation   │
├─────────────────────────┤
│ ┌─────┬─────┬─────┐     │
│ │ EXP │ CNT │ VAR │     │
│ │1842 │1840 │ −2.5│     │
│ └─────┴─────┴─────┘     │
│                         │
│ COUNTED AMOUNT          │
│ ┌─────────────────────┐ │
│ │      $1,840.00      │ │
│ └─────────────────────┘ │
│ [Keypad 1][2][3]        │
│ [Keypad 4][5][6]        │
│ ...                     │
│                         │
│ [Save draft]            │
│ [CLOSE SHIFT]           │
├─────────────────────────┤
│ Home Money [+] Rpt More │
└─────────────────────────┘
```

---

## Light vs dark comparison

| Element | Light | Dark |
|---------|-------|------|
| Page bg | `#F8FAFC` | `#0B1220` |
| KPI chip | white card + border | `#111827` card + `#1E293B` border |
| List row | white + border | card + border (same structure) |
| Primary CTA | `#2563EB` fill | `#3B82F6` fill |
| Success amount | `#16A34A` text | `#4ADE80` text |
| Danger amount | `#DC2626` text | `#F87171` text |
| Sidebar | `#EEF2F7` | `#0F172A` |
| Hub sheet scrim | 42% text mix | 55% text mix |

**Invariant across modes:** layout, spacing, component names, touch targets, nav IA.

---

## Component mapping (mockup → implementation)

| Mockup element | Streamlit (today) | React (DS-6) |
|----------------|-------------------|--------------|
| KPI chip row | `mobile_kpi_grid_html` | `<KpiGrid>` shadcn Card |
| List row | `mobile_list_row_html` | `<ListRow>` |
| Status pill | `mobile_status_pill_html` | `<Badge variant>` |
| Highlight banner | `mobile_highlight_banner_html` | `<SummaryBanner>` |
| Financial table | `financial_statement_table_html` | `<FinTable>` TanStack |
| Hub sheet | `mobile_shell.css` | Radix Sheet |
| Bottom nav | `erp_mob_bottom_bar` | Fixed tab bar |
| Cmd+K | — (future) | shadcn Command |

---

## Figma frame list (for design handoff)

| Frame ID | Name | Viewport | Mode |
|----------|------|----------|------|
| D-01 | Dashboard | 1440×900 | Light |
| D-02 | Dashboard | 1440×900 | Dark |
| D-03 | Banking Cockpit | 1440×900 | Light |
| D-04 | Reconciliation | 1440×900 | Light |
| D-05 | P&L Report | 1440×900 | Light |
| D-06 | Settings | 1440×900 | Light |
| M-01 | Home | 390×844 | Light |
| M-02 | Home | 390×844 | Dark |
| M-03 | Money Hub | 390×844 | Light |
| M-04 | Reports Hub | 390×844 | Light |
| M-05 | More Hub | 390×844 | Light |
| M-06 | Cash Recon | 390×844 | Light |
| M-07 | Transaction Ledger | 390×844 | Light |
| T-01 | Dashboard | 1024×768 | Light |

---

## Approval checklist

- [ ] Stakeholder confirms Home KPI layout
- [ ] Banking queue + detail matches workflow
- [ ] P&L table readability accepted
- [ ] Mobile bottom nav IA matches MOBILE-UX-01
- [ ] Dark mode specimens reviewed
- [ ] Ready for DS-4 token formalization

**Next:** [ERP_DS_04_MASTER_DESIGN_SYSTEM.md](./ERP_DS_04_MASTER_DESIGN_SYSTEM.md)
