# Accounting Decisions — Frozen Rules

Persistent decisions for this ERP. **Do not reverse without explicit architecture approval.**  
New sessions should treat these as constraints before changing posting or payment flows.

**Last updated:** 2026-06-09 (CC expense save fix)

## Documentation maintenance (required)

When accounting behavior changes, update **this file** and follow the full checklist in [BANKING_RECON_CC_STATUS.md](./BANKING_RECON_CC_STATUS.md#documentation-maintenance-required). Append **AUDIT_HISTORY.md** for every completed change.

**When making future accounting changes, either reference an existing AD number or create a new AD entry** (update this index and add or amend the detailed section below).

---

## Decision Log Index

Quick reference — full rationale in sections below.

| Decision ID | Date | Topic | Status | Source / Notes |
|---------------|------|-------|--------|----------------|
| **AD-001** | 2026-06-05 | Card Sales Clearing uses account **1150** | Frozen | [Account numbers](#account-numbers-phase-18); `banking.card_settlement_enabled` |
| **AD-002** | 2026-06-05 | Credit Card Payable uses account **2110** | Frozen | [Account numbers](#account-numbers-phase-18); pooled company CC liability |
| **AD-003** | 2026-06-05 | Customer Card Sale and Company Credit Card are **separate systems** | Frozen | [Card sales vs company credit card](#card-sales-vs-company-credit-card-separate-systems) |
| **AD-004** | 2026-06-05 | Company Credit Card **hidden unless enabled** | Frozen | [Company credit card enablement](#company-credit-card-enablement); `banking.company_card_enabled` |
| **AD-005** | 2026-06-05 | **No silent Cash/Bank fallback** for Company Credit Card | Frozen | [Company credit card enablement](#company-credit-card-enablement); `_resolve_payment_credit_account` |
| **AD-006** | 2026-06-05 | `CardPurchase` uses `reference_type` **CardPurchase** | Shipped | [Purchase reference types](#purchase-reference-types-_purchase_ref_type); void/edit fix |
| **AD-007** | 2026-06-05 | Purchase payable lifecycle follows **`purchase_type` Credit only** | Shipped | [Purchase payable lifecycle](#purchase-payable-lifecycle-credit-only) |
| **AD-008** | 2026-06-05 | **GL 2110** is source of truth for company credit card liability | Frozen | [Ledger authority](#ledger-authority-gl-2110-vs-card-sub-ledger) |
| **AD-009** | 2026-06-05 | `credit_card` `BankAccount.balance` is **secondary sub-ledger** until synced | Frozen | [Ledger authority](#ledger-authority-gl-2110-vs-card-sub-ledger); drift risk documented |
| **AD-010** | 2026-06-05 | **Do not build** credit card issuer statement import yet | Deferred | [Explicitly out of scope](#explicitly-out-of-scope-unless-new-phase-approved) |
| **AD-011** | 2026-06-08 | Company CC charges **sync GL 2110 and card sub-ledger** | Shipped | [AD-011 sub-ledger sync](#ad-011--company-cc-sub-ledger-sync-shipped-2026-06-08) |
| **AD-012** | 2026-06-08 | CC sub-ledger linkage via `credit_card_account_id` + `ccc:{type}:{id}` | Shipped | [AD-011 sub-ledger sync](#ad-011--company-cc-sub-ledger-sync-shipped-2026-06-08) |
| **AD-013** | 2026-06-09 | Recon Health compares **2110 GL** vs **sum(active card balances)** | Shipped | [AD-013 Recon Health](#ad-013--credit-card-payable-recon-health-shipped-2026-06-09) |
| **AD-014** | 2026-06-09 | Void/unpost **BankStmtCCBillPay** atomically from reconciliation | Shipped | [AD-014 void bill pay](#ad-014--voidunpost-bankstmtccbillpay-shipped-2026-06-09) |
| **AD-015** | 2026-06-09 | Company CC **opening balance** DR OBE / CR 2110 (not bank asset) | Shipped | [AD-015 opening balance](#ad-015--company-cc-opening-balance-shipped-2026-06-09) |

---

## Card sales vs company credit card (separate systems)

| Concept | Stored value | Posting | GL |
|---------|--------------|---------|-----|
| **Customer card sale** | `sale_type = "Card"` | `post_card_sale` | `CardSale` → Bank or 1150 Clearing |
| **Company credit card charge** | `payment_method` / `purchase_type = "Credit Card"` | `post_expense`, `post_purchase`, `post_payable_payment` | Credits **2110** |

- `_resolve_payment_credit_account` must **never** treat customer `"Card"` as company CC.
- Customer card bank picker (`at_card_bank_acct`) is **not** company CC.

---

## Account numbers (Phase 18)

| Account | Code | Type | Decision |
|---------|------|------|----------|
| **Card Sales Clearing** | **1150** | Asset | Used when `banking.card_settlement_enabled` is ON. Design doc once suggested 5100; **code uses 1150** — do not rename without migration. |
| **Credit Card Payable** | **2110** | Liability | Single pooled company CC liability. All company CC charges credit this account. |
| **Bank Charges** | **5800** | Expense | Bank fees, interest heuristics, POS commission — not CC Payable accrual. |

---

## Company credit card enablement

- Controlled by `banking.company_card_enabled` (default **OFF**).
- When OFF: Company CC hidden from payment method lists; `_resolve_payment_credit_account("Credit Card")` raises `ValueError`.
- **No silent fallback** to Cash or Bank when CC is disabled or mis-typed.
- Mobile and desktop use the **same helpers** (`_at_expense_pay_methods`, etc.) — no separate mobile accounting rules.

---

## Purchase reference types (`_purchase_ref_type`)

| `purchase_type` | GL `reference_type` |
|-----------------|---------------------|
| Cash | `CashPurchase` |
| Bank | `BankPurchase` |
| Credit Card | **`CardPurchase`** |
| Credit (vendor AP) | `Purchase` |

- `void_purchase` and `edit_purchase` must reverse using the **original** type’s reference type.
- **Fix shipped 2026-06-05** — previously Credit Card reversed as `Purchase` (bug).

---

## Purchase payable lifecycle (Credit only)

- Only `purchase_type == "Credit"` creates/maintains a linked `Payable` (no `PayableCreation` GL — AP from `Purchase` JE).
- **Credit → Credit:** update linked payable fields.
- **Credit → Cash/Bank/Credit Card:** void linked payable (reverse `PayablePayment` if paid).
- **Non-Credit → Credit:** create linked payable.
- **Non-Credit → Non-Credit:** no payable side effects.
- Tier-2 edit blocked when linked payable is already paid.

**Fix shipped 2026-06-05.**

---

## Ledger authority: GL 2110 vs card sub-ledger

| Layer | Source of truth | Notes |
|-------|-----------------|-------|
| **GL `Credit Card Payable` (2110)** | **Primary** — `JournalEntryLine` via `calculate_account_balance()` | Legal/books liability |
| **`BankAccount.balance` (`kind=credit_card`)** | **Synced sub-ledger** on company CC charges (AD-011) | Updated on charge, bill pay, void/edit reversal |

**Decision (2026-06-05, superseded for charges by AD-011):** **2110 remains primary** for books; per-card balance should match attributed charges after AD-011.

---

## AD-011 — Company CC sub-ledger sync (shipped 2026-06-08)

When `payment_method` / `purchase_type` is **Company Credit Card**:

1. **GL unchanged:** DR expense/inventory/AP, CR **2110** via existing posting.
2. **Sub-ledger:** `post_cc_subledger_charge` creates `BankTransaction` type `withdrawal` on selected `kind=credit_card` account; `apply_account_balance_delta` increases card balance. **No extra JE.**
3. **Card selection:** One active card → auto; multiple → require `credit_card_account_id`; none → block with clear error.
4. **Linkage:** `credit_card_account_id` on `ExpenseRecord`, `Purchase`, `Payable`; `statement_ref` = `ccc:{reference_type}:{reference_id}` (`PayablePayment` uses journal entry id).
5. **Void/edit:** `reverse_cc_subledgers_for_gl_reference` before/after GL reversal per existing void/edit paths.
6. **Bill pay:** `post_credit_card_bill_payment` unchanged; after synced charge, bill pay zeros both 2110 and selected card.
7. **Out of scope:** Customer `CardSale`, 1150 clearing, issuer statement import, per-card GL accounts.
8. **Form visibility (2026-06-09):** Show Company CC on expense/purchase/payable forms only when `_company_cc_charge_ready` (toggle on + active card). Use `_save_and_post_expense_record` for desktop New Transaction and Expenses — sets `company_id`, posts GL + sub-ledger, surfaces errors without silent rerun.

---

## AD-013 — Credit Card Payable Recon Health (shipped 2026-06-09)

Read-only integrity check on **Recon Health** page when `banking.company_card_enabled`:

| Measure | Source |
|---------|--------|
| **Credit Card Payable GL** | `calculate_account_balance` on account **2110** |
| **Credit Card Sub-ledger Total** | Sum of `BankAccount.balance` for active `kind=credit_card` rows |
| **Difference** | GL − sub-ledger total |

- **OK** when `abs(difference) < 0.01` (same tolerance as AR/AP Recon Health).
- **Warning** otherwise — e.g. manual CC withdrawal without GL, legacy drift.
- **Card breakdown:** name, balance, last non-void `BankTransaction.date`.
- Does **not** modify posting, import, or 2110 structure. Customer `CardSale` excluded by design (AD-003).

---

## Bill payment from bank statement

- Match kind `cc_bill`: DR 2110 / CR Bank (`BankStmtCCBillPay`).
- User must select which `BankAccount` (`kind=credit_card`) the payment applies to.
- Partial payments allowed (statement line amount).
- Does **not** import card issuer charge lines — only bank-side payment.

---

## AD-014 — Void/unpost BankStmtCCBillPay (shipped 2026-06-09)

**Problem:** Voiding only the bank `BankTransaction` (`statement_ref=bsr:{row_id}`) left GL 2110, bank GL, and CC sub-ledger (`bsr:{row_id}:cc`) out of sync.

**Rule:**

- Use `void_credit_card_bill_payment(session, row_id, company_id, void_reason)` — **only** for `BankStatementRow` with `status=posted` and `match_type=cc_bill_payment`.
- Atomically: reverse `BankStmtCCBillPay` JE → void bank txn → void CC txn by `bsr:{row_id}:cc` → reverse both sub-ledgers → `row.status=voided`.
- **Block** direct `void_bank_transaction` when `statement_ref` starts with `bsr:` — message: *Statement-linked transactions must be unposted from Bank Reconciliation.*
- UI: minimal unpost control on Banking → Statement import → **Review** for posted bill-payment rows.
- Does **not** change happy-path `post_credit_card_bill_payment`, CardSale, 2110 structure, or issuer import.

---

## AD-015 — Company CC opening balance (shipped 2026-06-09)

**Problem:** Opening Balances page treated all `BankAccount` rows as bank assets (DR Bank/Cash, CR OBE, deposit txn). Company `credit_card` accounts require liability treatment.

**Rule:**

- `kind=credit_card` opening balance on **Opening Balances** page (and Banking add-account initial balance via shared `_post_opening_balance_bank_account`):
  - **JE:** DR Opening Balance Equity / CR Credit Card Payable (**2110**), `reference_type=OBBank`, `reference_id=bank_account.id`
  - **Sub-ledger:** `BankTransaction` `type=withdrawal`, `description=Opening Balance`; `apply_account_balance_delta` increases card `balance` (amount owed)
- `kind=bank` unchanged: DR Bank or Cash / CR OBE, `type=deposit`
- **One-time guard:** reject second `OBBank` JE for same account id
- **Gating:** CC opening requires `banking.company_card_enabled`; UI labels amount as *Amount owed on card*
- Does **not** change CC charge posting, CardSale, bill payment, or 2110 structure

---

## Posting guardrails (Phase 18)

- All GL via `create_journal_entry` (period lock, balance check).
- Statement import: **zero auto-post** — user confirms each line.
- Duplicate file detection: soft warning, not hard block.
- `BankTransaction.statement_ref` links posted txns to `bsr:{row_id}`.

---

## Explicitly out of scope (unless new phase approved)

- Credit card **issuer** statement import
- Splitting 2110 into per-card GL sub-accounts (future option; not required for minimal sub-ledger sync)
- Changing customer `CardSale` posting
- Booking CC interest to 2110 (currently Bank Charges from bank stmt)

---

## NEXT APPROVED ACCOUNTING TASK

> **None mandated** after AD-014. See [BANKING_RECON_CC_STATUS.md](./BANKING_RECON_CC_STATUS.md) for optional follow-ups.
