# Mobile UI System — Design Blueprint

**Status:** Vision document — approved for phased implementation  
**Scope:** Mobile experience across all pages  
**Accounting/posting logic:** Not affected by this document  
**Last updated:** 2026-06-09

---

## 1. Core Design Principle

**The app should feel like a tool, not software.**

A restaurant owner using this application fifty times a day is not sitting at a desk. They are behind a counter, in a kitchen, on a phone call, standing up. Their hands may be wet. The light may be dim. They have three seconds of attention.

The design principle is: **immediate action, minimal thinking**.

Every screen should answer one question the moment it opens: *what do I do right now?* The answer must be visible without scrolling, without reading, without hunting. If the user has to look for anything, the design has failed.

This is not minimalism for aesthetic reasons. It is minimalism for operational reasons. The product is accounting software disguised as something fast enough to use in real life.

---

## 2. What Should This Feel Like?

A restaurant owner opens Add Transaction to log a cash sale. The experience should feel like:

- Tapping a number on a register
- Confirming the type in one tap if it was wrong
- Saving in one tap

Three interactions. Under five seconds. No error. Done before the next customer speaks.

The emotional quality of the app is **confident calm**. Dark background, large numbers, clear text. It does not feel nervous or cluttered. The numbers are large because numbers are what matter. The buttons are large because thumbs are the input device. The sheet pickers are deliberate — they appear when called, they close when done, they do not linger.

On the Home page, the owner glances and sees: today's sales, today's expenses, net position. Not a list. Not a table. A number they can hold in their head. The rest of the day's detail is one tap away, not immediately in the way.

The app should feel like a well-designed point-of-sale terminal that also happens to know accounting.

---

## 3. What Should Be Visible Immediately?

### Home
- Today's net position (one large number, coloured positive/negative)
- Today's sales total
- Today's expense total
- The Add Transaction button (always)

### Add Transaction (open state)
- The current transaction type (Sale by default)
- The current payment method
- The current date (today)
- The current currency
- The amount (0 until typed)
- The Save button
- The keypad

Nothing else. Every other field is a detail that belongs in a picker.

### Banking
- Account balances — one row per account
- Today's movement (deposit / withdrawal net)

### Reports / Cashflow
- The date range selector
- The primary metric for the selected report

---

## 4. What Should Stay Hidden Until Needed?

- Category and subcategory — hidden until the transaction type is set, revealed as a single row below Row 1
- Vendor — hidden unless the type is Purchase or Supplier Payment
- Invoice / Payable — hidden unless a vendor with open payables is selected
- Bank account — hidden unless the payment method is Bank
- Company credit card — hidden unless the payment method is Credit Card (company)
- FX rate row — hidden unless the currency differs from the company default
- Subcategory — hidden unless a category with subcategories exists
- Customer / invoice link — hidden unless the type is Customer Payment

The rule: **a field appears only when the user's prior choice makes it meaningful.** Fields that appear because they might be needed are noise. Fields that appear because the user just made them relevant are signal.

---

## 5. What Should Never Appear Unless Required?

- Error messages before the user has attempted anything
- Empty state illustrations on transactional screens
- Confirmation dialogs for reversible actions (category selection, type selection)
- Decimal keyboard for amounts — the keypad handles this
- Multiple save buttons on one screen
- Labels on icon-only bottom nav items when the icon is self-evident (but labels should remain until the UX is proven without them)
- The FX rate field when using the company's default currency
- Sub-navigation tabs inside a page when there is only one sub-section

---

## 6. Mobile Navigation Structure

### Bottom Navigation (five items, always visible)

| Position | Label | Icon | Content |
|---|---|---|---|
| 1 | Home | House | Today's snapshot — net, sales, expenses, recent activity |
| 2 | Banking | Bank building | Account balances, recent transactions per account |
| 3 | + (centre) | Large circle button | Add Transaction — opens the AT panel immediately |
| 4 | Reports | Bar chart | Cashflow, P&L, period summary |
| 5 | More | Three lines | Everything else |

The centre button is always the Add Transaction trigger. It is larger than the other nav items, elevated, accented in the primary blue. Tapping it anywhere on the app opens the AT panel. This is the most-used action and earns the most prominent position.

### Movement Between Pages

Users move by tapping bottom nav items. There are no back buttons except inside sheet pickers. There is no sidebar on mobile. The sidebar is a desktop pattern and does not belong on small screens.

Pages do not slide in from the right. They cross-fade or replace. The AT panel slides up from the bottom. Sheet pickers slide up from the bottom. These are the only directional transitions. Everything else is a direct replace.

### Home Page

Home is a **glance page**, not a list page. It shows:
- Net position for today (large, top)
- Sales / Expenses / Purchases as a three-cell summary row
- A short list of today's recent transactions (maximum five, tap to expand)
- Quick links to Banking and Reports if relevant balances are notable

Home does not show pagination. Home does not show filters. Home does not show settings. Home is read-only.

### Add Transaction

The AT panel is a bottom sheet permanently anchored at the bottom of every page. It is always one tap (the centre button) away. It does not navigate away from the current page — it overlays.

### More Hub

More contains: Settings, Workers/HR, Chart of Accounts, Fiscal Periods, Company Profile, Ledger / Transaction History, Import/Export, About. These are low-frequency operations. They belong in More, not in bottom nav.

**What belongs in More:**
- Anything used less than once a day
- Administrative functions
- Data management (import/export, chart of accounts)
- Company and user settings

**What never belongs in bottom nav:**
- Settings
- Ledger (transaction history is accessed from Home or More, not primary nav)
- Any function used less than once per day
- Nested sub-navigation pages

---

## 7. Pickers and Sheets

All picker interactions follow one pattern: **a sheet slides up from the bottom, presents one focused choice, closes when a selection is made or the X is tapped.** There is no in-page navigation, no multi-step wizard inside a picker, no nested pickers.

### The Sheet Pattern

Every picker sheet has:
1. A grab handle at the top (visual affordance for swipe-to-close, even if swipe is not implemented)
2. A title (what the user is choosing) and a close X button on the right
3. A scrollable list of options or an input control
4. No footer buttons — selection closes the sheet immediately

### Type Picker

Opens when the user taps the transaction type label in Row 1. Shows all seven transaction types as a vertical list. Each row has a coloured dot (type accent colour) and the type name. The current type is visually distinguished (primary button style). Tapping a type applies it and closes the sheet immediately — no confirm button. The dot communicates type at a glance.

### Payment Method Picker

Opens when the user taps the payment method label. Shows only the valid payment methods for the current transaction type — invalid options are **hidden entirely**, not disabled. If only one method exists, the picker should not open; the method is set automatically and the button is non-interactive. The current method is visually distinguished.

**Unavailable options are hidden.** Disabled options are confusing — the user sees something they cannot tap and wonders why. Hiding removes the confusion.

### Category Picker

Opens via the category row below Row 1. Shows categories that are valid for the current transaction type. Organised alphabetically or by frequency if usage data is available. Search field at the top for long lists. Selecting a category applies it and closes. If subcategories exist, the subcategory row appears below the category row immediately after selection.

### Subcategory Picker

Same pattern as Category Picker. Opens via the subcategory row (which appears only after a category with subcategories is selected). Selecting closes the sheet.

### Vendor Picker

Same pattern. Filtered to active vendors. Search always visible. If no vendors exist, the picker does not open — an inline message explains how to add one (and links to the vendor setup page in More).

### Date Picker

Opens via the date label in Row 1. Shows the system date input. Selecting a date does not close the picker automatically — the user taps Confirm Date. This is intentional because date input on mobile browsers has inconsistent behaviour (the native date picker may need an explicit confirm). After confirmation, the sheet closes and the Row 1 date label updates.

For today's date: show "Today" as the label in Row 1, not the full date, to reduce visual clutter. Show the full date only when a non-today date is selected.

### Currency Picker

Opens via the currency label in Row 1. Shows available currencies as a short horizontal chip row or a short vertical list. Selecting applies immediately and closes. If only one currency is configured, the currency button is non-interactive and the picker never opens.

### Company Switcher

Opens from the header company name tap. Shows all companies the user has access to. Selecting switches the active company — the panel reloads. The current company has a checkmark or accent indicator.

### Profile / Account Sheet

Opens from the profile icon in the header. Shows: logged-in user name, role, logout button, and optionally a dark/light mode toggle. It is a bottom sheet like all others. It is not a separate page.

### Empty States

Empty states appear **only when the user reaches a screen that requires data that does not yet exist.** They appear in the picker sheet if a list is empty (e.g., no categories, no vendors). They include: a brief explanation of why the list is empty, and a single action link to create the missing item. They do not appear with illustrations or decorative elements — this is an operational tool.

**When there is no data in a list picker:** the picker sheet opens, the list is empty, and a short inline message explains how to add data. The user can close the sheet. The trigger button remains visible.

---

## 8. Category and Subcategory UX

All context-sensitive rows (Category, Subcategory, Vendor, Customer, Bank Account) follow one visual pattern: **a full-width trigger row with a coloured dot indicator and plain text label, tappable to open the corresponding picker sheet.**

### The Trigger Row Pattern

```
● [Label text]                                      ›
```

- Left: coloured dot (type accent colour, 10px circle)
- Centre: the current selection label (or a placeholder if nothing selected)
- Right: a chevron › indicating "opens a picker"
- Full-width tappable area
- Same height, same border radius, same background across all row types

The dot colour matches the transaction type accent colour. This visually connects the category/vendor/bank choice to the type it belongs to, reinforcing that these fields are context-dependent.

### Consistent Rules

- Category row: appears for Sale, Expense, Purchase
- Subcategory row: appears immediately below Category row if category has subcategories
- Vendor row: appears for Purchase, Supplier Payment
- Customer row / Invoice row: appears for Customer Payment
- Bank Account row: appears when payment method is Bank
- Company Credit Card row: appears when payment method is company CC

All rows disappear when they are not relevant. None are disabled in place. Irrelevant rows do not consume vertical space.

---

## 9. Add Transaction — Ideal User Journey

### Opening

The user taps the centre + button in the bottom nav. The AT panel slides up from the bottom of the screen. The panel is anchored — it does not cover the full screen. The main content (Home, Banking, Reports) remains partially visible above the panel, providing spatial context.

### First State (default: Sale, Cash, Today, default currency)

The user sees immediately:
- Row 1: [Sale] [Cash] [Today] [TRY] — four compact buttons
- Category row (if Sale has categories): ● Uncategorised ›
- Amount display: 0 (large, right-aligned)
- Save button (full width, primary blue)
- Keypad (3×4 grid)

### Type Change

If the transaction is not a Sale, the user taps [Sale] in Row 1. The type picker sheet slides up. They tap "Expense". The sheet closes. Row 1 now shows [Expense] [Cash] [Today] [TRY]. The category row changes to the expense category. The dot colour changes to amber. Everything happens without a page reload or visual flash.

### Amount Entry

The user taps keypad digits. The amount display updates on each tap (fragment scope — fast, no full page reload). The currency label is small in the top-right of the amount area. Backspace is always the bottom-right key.

### Category Selection

The user taps the category row. The category picker sheet slides up. They tap a category. The sheet closes. The category row updates to show the selected category name with the type accent dot.

If a subcategory is needed, the subcategory row appears immediately below. The user taps it, selects, sheet closes.

### Saving

The user taps Save. The panel collapses (or resets to 0). A brief success indicator appears (ideally a subtle green flash or the amount resets with animation). The transaction is saved. The user is back to the default state, ready for the next entry.

The user never leaves the Home page. The AT panel is always available. The keypad is always the fastest path.

### Why Concept C Is Structured This Way

The original mobile AT had tab chips for the transaction type and separate chip rows for payment method. Each chip row consumed vertical space and demanded visual attention even when the user knew exactly what they were entering. The type chips and PM chips were always visible regardless of context.

Concept C moves all meta-choices (type, payment, date, currency) into Row 1 — four compact buttons that take one line of vertical space. The selected values are shown as button labels. Changing them opens a focused picker sheet. The panel body is then entirely available for the amount entry (the number) and the keypad.

This is why the keypad is central and large. The keypad is the primary input device. Everything else is context that can be changed quickly if needed but does not need to be present at all times.

**Progressive disclosure in Concept C:**
1. Open: type, PM, date, currency visible in Row 1 (always)
2. Type-relevant fields appear below Row 1 (category, vendor, etc.) — progressive
3. Amount entry + Save + keypad always at bottom (always, unless picker is open)
4. Picker sheet slides up on demand, hides panel content — focused

---

## 10. Header

The header appears at the top of every page. On mobile it is compact — it must not consume more than one row of height.

### Company Name

Displayed in the header centre as a truncated text label. Tapping it opens the company switcher sheet. The company name is always visible — it is critical context, especially for multi-company users.

### Notifications Bell

Right of the company name. Shows a badge count if there are unread notifications. Tapping opens a sheet or a popover listing recent alerts. Notifications that require action (e.g., overdue payables, failed sync) are visually prioritised. Informational notifications are muted.

### Profile Icon

Rightmost in the header. Tapping opens the profile/account sheet. Contains: user name, role label, dark/light mode toggle, logout button. It is minimal — the header icon communicates identity. The sheet provides action.

### Header Philosophy

The header is a navigation anchor, not a content area. It should not contain filters, date ranges, search bars, or secondary navigation. Those belong in the page body. The header contains only: company context, global alerts, and user identity.

The header height must remain fixed and minimal. A large header consumes vertical space that belongs to the content. On a 390px-wide phone, vertical space is the scarcest resource.

---

## 11. Design System Specification

### Colour Philosophy

The colour palette is intentionally dark-primary. Dark backgrounds reduce glare in restaurant environments (often bright ambient light), make large numbers legible, and communicate professionalism without visual noise.

**Base palette:**
- Panel / page background: `#0f1629` (navy)
- Surface (cards, rows): `#1a2540`
- Surface hover / pressed: `#243050`
- Border: `#2a3a5c`
- Text primary: `#e2e8f0`
- Text muted: `#94a3b8`
- Primary action (Save, confirm): `#3b82f6`

**Transaction type accents:**
Each transaction type has a single accent colour. This colour appears on the type dot, and optionally on the border of the active panel or the Row 1 type button. The accent colour communicates type at a glance without reading text.

| Type | Accent |
|---|---|
| Sale | `#10b981` (emerald) |
| Expense | `#f59e0b` (amber) |
| Purchase | `#8b5cf6` (violet) |
| Supplier Payment | `#ec4899` (pink) |
| Customer Payment | `#06b6d4` (cyan) |
| Bank Transaction | `#64748b` (slate) |
| Salary | `#f97316` (orange) |

**Colour rules:**
- Use accent colours only for dots, active state indicators, and panel top borders
- Never fill full-width elements with accent colours
- Never use more than two accent colours on one screen simultaneously (if both category and type are visible, only the type dot carries the accent)
- Status colours (success green, error red, warning yellow) are separate from type accent colours — they must not be the same hue

### Spacing Philosophy

Spacing is thumb-friendly and consistent. All interactive elements have a minimum tap target of 44px height. Row elements (category row, trigger rows) are 42–48px. The keypad keys are square, filling their column width, minimum 52px tall.

**Base spacing unit:** 8px  
**Common values:** 4 / 8 / 12 / 16 / 24px  
**Panel internal padding:** 12px left/right, 8px top, 12px bottom  
**Between rows:** 6–8px gap  
**Sheet internal padding:** 12px left/right  
**Between picker items:** 4px  

Do not use fractional spacing. Do not use values outside the base unit scale. Consistent spacing is what makes an interface feel calm and reliable.

### Picker Philosophy

Every picker follows the bottom sheet pattern without exception. No dropdown selects, no inline expand-collapse, no modal dialogs for data selection.

**Rules:**
1. One focused choice per sheet
2. Sheet slides up — never replaces the page
3. Selection closes the sheet immediately (except date, which requires explicit confirm due to browser input behaviour)
4. No nested sheets — a picker never opens another picker
5. A sheet that opens while another sheet is open must first close the previous one
6. The AT panel suppresses its keypad/save area while any picker is open — the sheet has full focus

### Progressive Disclosure Rules

1. **Show what the user needs now.** Do not show what they might need later.
2. **A field appears when the prior choice makes it meaningful.** Never before.
3. **A field disappears when it becomes irrelevant.** Do not leave it disabled.
4. **Default values are the most common values.** Sale / Cash / Today / company default currency.
5. **The user should never need to clear a field they didn't set.** Switching type clears type-specific fields silently.

### Component Reuse Rules

The following components must be identical across all pages and all transaction types:

| Component | Rule |
|---|---|
| Trigger row (category, vendor, bank, etc.) | Same height, same padding, same border, same dot, same chevron |
| Picker sheet | Same grab handle, same header layout (title + X), same list item height |
| Keypad | Only on Add Transaction. Never elsewhere. |
| Amount display | Only on Add Transaction. Specific typography. |
| Row 1 (type, PM, date, currency) | Only on Add Transaction. |
| Bottom nav | Identical across all pages. |
| Header | Identical across all pages. |

If you find yourself creating a one-off component that looks similar to an existing one but slightly different, that is a violation. Extend the existing component or use it as-is.

### Forbidden Patterns

The following patterns are explicitly forbidden on mobile:

- **HTML inside widget labels.** `st.button`, `st.selectbox`, `st.radio` labels must be plain text. Use `st.markdown(unsafe_allow_html=True)` for any decorative HTML element. The button is the click target; the markdown is the visual.
- **Disabled options in pickers.** If an option is not valid for the current context, hide it. Never disable it.
- **Confirmation dialogs for reversible selections.** Changing type, category, or date is always reversible. Confirm only for saves and destructive actions.
- **Multi-step wizards inside sheet pickers.** A picker resolves one choice. It is not a flow.
- **Scrollable content inside the AT panel.** The AT panel is fixed height. Its content must fit. If content overflows, the design is wrong.
- **Page navigation from inside the AT panel.** The panel overlays the current page. It never navigates away from it.
- **Showing the keypad when a picker is open.** Keypad is suppressed. The user cannot enter an amount while choosing a category.
- **Inline error text on every field.** Errors appear after the user attempts to save, not while they are filling in fields.
- **Desktop patterns on mobile.** No sidebars, no multi-column layouts (except Row 1), no hover-dependent interactions, no right-click menus.

---

## 12. Future Migration — Phased Approach

The design system should be applied gradually across pages. A full rewrite is not needed or desirable. Each page is migrated in one focused session.

### Migration Sequence and Approach

**Phase 1 — Add Transaction (complete)**  
Concept C is implemented. The AT panel, Row 1, picker sheets, keypad, and save are in the correct pattern. This is the reference implementation for all future components.

**Phase 2 — Home Page**  
Home migration is contained: replace any desktop-style tables or data frames with the mobile card pattern (navy surface, summary numbers, type accents for transaction rows). Add the quick metrics row (sales / expenses / net). The AT button is already in the bottom nav. Home does not need a new navigation structure — it needs visual refinement.

Migration rule: read the Home render function, identify any `st.dataframe`, `st.table`, or multi-column desktop layouts, and replace with mobile-pattern `st.markdown` cards within the existing structure.

**Phase 3 — Banking Page**  
Banking shows account balances and recent transactions. The mobile migration converts any data tables to card rows (account name, balance, last movement). The existing reconciliation and bank transaction logic is not touched. Only the visual rendering of the list changes.

**Phase 4 — Reports / Cashflow**  
Reports on mobile shows one report at a time. The report picker (which report to view) becomes a sheet. The date range filter becomes two Row 1-style compact buttons. The chart, if present, renders full-width below. The KPI summary row uses the same card pattern as Home.

**Phase 5 — More Hub**  
More is a list of links. The migration converts any desktop card grid to a mobile list — each item is a full-width tap target with icon, label, and chevron. Section headers separate groups. No visual complexity needed here — More is navigation, not content.

**Phase 6 — Transaction History / Ledger**  
This is the most complex migration because it involves data tables and filters. The approach: the filter row (date, type, search) becomes a compact filter bar with sheet pickers for each filter. The transaction list becomes a mobile-optimised row (amount right-aligned, type dot left, description centre, date small beneath). Pagination is replaced by lazy-load or a "show more" button.

### Migration Constraints (apply to all phases)

- Do not change accounting logic, session state keys, or database queries
- Do not change existing desktop rendering — all mobile changes are inside `html.erp-mobile` CSS guards or mobile-dispatch branches
- Do not create new pages — enhance existing ones
- Apply the design system components (trigger rows, sheet pickers, colour tokens) exactly as defined here — do not invent new patterns per page
- Test contracts must be updated alongside every migration to reflect the new component structure

---

## 13. Summary

The mobile ERP design is built on one idea: **the tool disappears and the work appears.**

A restaurant owner should feel that entering a transaction is as natural as pressing keys on a register. The app should be invisible in its complexity and obvious in its purpose. Every decision in Concept C — the Row 1 meta-strip, the full-pad keypad, the picker sheets, the type accent dots, the suppression of irrelevant fields — is in service of that principle.

The design system is not a set of aesthetic preferences. It is a set of operational decisions made on behalf of the user who has three seconds and no patience for software that thinks it knows better.

Build every future component against this document. When in doubt: make it faster, make it smaller, make it disappear until needed.
