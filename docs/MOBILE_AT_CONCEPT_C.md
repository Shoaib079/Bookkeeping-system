# Mobile Add Transaction — Concept C "Full Pad" Design Reference

**Status:** Approved 2026-06-09  
**Scope:** Mobile AT panel only (`_render_add_transaction_mobile()`). Desktop AT unchanged.  
**Accounting/posting logic:** Unchanged. `_at_save()` is not modified.

---

## Colour tokens

| Token | Hex | Usage |
|-------|-----|-------|
| `--mob-navy` | `#0f1629` | Panel background, Row 1 background |
| `--mob-surface` | `#1a2540` | Card/row surfaces inside panel |
| `--mob-surface-2` | `#243050` | Hover/pressed state for surface elements |
| `--mob-border` | `#2a3a5c` | Dividers, button borders |
| `--mob-primary` | `#3b82f6` | Primary action buttons (Save) |
| `--mob-primary-hover` | `#2563eb` | Save button hover |
| `--mob-text` | `#e2e8f0` | Primary text on dark background |
| `--mob-text-muted` | `#94a3b8` | Secondary/placeholder text |
| `--mob-sale` | `#10b981` | Sale transaction dot / accent |
| `--mob-expense` | `#f59e0b` | Expense transaction dot / accent |
| `--mob-purchase` | `#8b5cf6` | Purchase transaction dot / accent |
| `--mob-supplier` | `#ec4899` | Supplier Payment accent |
| `--mob-customer` | `#06b6d4` | Customer Payment accent |
| `--mob-bank` | `#64748b` | Bank Transaction accent |
| `--mob-salary` | `#f97316` | Salary accent |
| `--mob-amount` | `#ffffff` | Amount display text |
| `--mob-keypad-bg` | `#1e2d4a` | Keypad button background |
| `--mob-keypad-hover` | `#2a3a5c` | Keypad button hover |

---

## Layout rules — mobile AT panel

```
┌─────────────────────────────────────────┐  ← panel bg: --mob-navy
│ ── drag handle ──                       │
├──────────┬──────────┬────────┬──────────┤  ← Row 1 (4 cols)
│  TYPE ▼  │  PAYMENT │ DATE ▼ │  TRY ▼  │
│  Sale    │  Cash    │ 09 Jun │         │
├──────────┴──────────┴────────┴──────────┤
│  ● Food & Bev            Category ▼    │  ← Cat row (dot + name or placeholder)
├─────────────────────────────────────────┤
│  [Bank/Card account trigger if needed] │  ← Conditional sub-row
├─────────────────────────────────────────┤
│              1,250.00                  │  ← Amount display (large, centred)
├─────────────────────────────────────────┤
│              ✓  SAVE                   │  ← Save button (full width, primary)
├─────────────────────────────────────────┤
│    7     │    8     │    9             │
│    4     │    5     │    6             │
│    1     │    2     │    3             │  ← 3×4 keypad
│    .     │    0     │    ⌫            │
└─────────────────────────────────────────┘
```

---

## Row 1 — column mapping

| Col | Width | Content | Picker opened | Session key read |
|-----|-------|---------|---------------|------------------|
| Type | flex 2.2 | Current type name (e.g. "Sale") | `"txn_type"` picker | `at_type_idx` |
| Payment | flex 2.0 | Current PM (e.g. "Cash") | `"payment"` picker | `at_pm` |
| Date | flex 1.5 | Formatted date (e.g. "09 Jun") | `"date"` picker | `at_date` |
| Currency | flex 0.9 | Currency code (e.g. "TRY") | `"currency"` picker | `at_currency` |

Row 1 uses `st.columns([2.2, 2.0, 1.5, 0.9])`.  
Each button is `type="secondary"`, `use_container_width=True`.  
CSS container key: `mob_at_row1`.

---

## Category row

- Full-width secondary button showing type-coloured dot + category name
- Dot colour taken from `transaction_type` field of `TransactionCategory` (no `color` column)
- Placeholder text when no category selected: `"Category ▼"`
- Picker opened: existing `"sale_cat"` / `"expense_cat"` / `"purchase_cat"` (unchanged)
- CSS container key: `mob_at_c_cat_row`
- Hidden for: Salary, Bank Transaction, Customer Payment, Supplier Payment (these use vendor/payable/invoice pickers instead or have no category)

---

## Amount + Save + Keypad (fragment)

All three live inside `@st.fragment _mob_at_render_amount_keypad_fragment()`.

```
mob_at_amount_row    → amount display (full width, large text)
mob_at_save_row      → Save button (full width, primary, use_container_width=True)
mob_at_keypad        → 3×4 button grid
```

Save button: `st.button("✓ Save", key="mob_at_save", type="primary", use_container_width=True)`  
On click: sets `st.session_state["mob_at_save_clicked"] = True` then `st.rerun(scope="app")`.

---

## New picker modes

| `mob_at_picker` value | Sheet renders | Sets |
|-----------------------|---------------|------|
| `"txn_type"` | Grid of all 7 types with coloured dots | `at_type_idx`, `mob_at_tab`, `mob_at_more_idx` |
| `"payment"` | List of PM options for current type | `at_pm` |
| `"date"` | `st.date_input` widget | `at_date` |
| `"currency"` | 4-chip grid (TRY/USD/EUR/GBP) | `at_currency` |

---

## What is NOT changed

- `_at_save()` and all posting functions
- Database schema — no new columns or tables
- Desktop AT form (`render_add_transaction`)
- Bottom nav, header, Banking, Reports, More Hub
- Existing picker sheets (vendor, bank, payable, category, subcat) — only new branches added to dispatcher
- `mob_at_tabs` CSS class (kept for backward compat; new layout does not use it)

---

## Implementation files

| File | Change |
|------|--------|
| `app.py` | Add `"at_picker_mode"` to `_COMPANY_SCOPED_AT_KEYS`; add default in `_mob_at_ensure_defaults()`; add picker branches; add `_mob_at_render_c_row1()`, `_mob_at_render_c_cat_row()`, type/PM/date/currency picker functions; rewrite AT panel section of `_render_add_transaction_mobile()`; restructure `_mob_at_render_amount_keypad_fragment()` |
| `ui/mobile_txn.css` | Add `mob_at_row1`, `mob_at_c_cat_row`, `mob_at_save_row` container styles; colour token variables |
