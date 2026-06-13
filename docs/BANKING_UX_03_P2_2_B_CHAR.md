# BANKING-UX-03 P2.2-B — Transfer-Charge Classification Characterization

**Mode:** Characterization only — no code, no implementation. Classification analysis.
**Scope:** `reconciliation/match_post.py` bank-fee subtype recognition, focused on **Turkish transfer-related charges** (`havale` / `EFT` / `SWIFT`).
**Why now:** P2.2 batch targets `bank_fee` rows. The reliability of transfer-charge recognition is therefore a **batch-safety question**, not just a labeling one.

---

## 1. Current recognition inventory

**Keyword sets (ASCII-folded via `_fold_tr`):**
- `_TRANSFER_FEE_KEYWORDS` = `havale`, `eft`, `wire`, `transfer fee`, `swift`, `islem ucret`, `banka masraf`, `eft masraf`, `havale masraf`, `havale ucret`
- `_COMMISSION_KEYWORDS` = `komisyon`, `commission`, `bsmv`, `pos ucret`, `kart komisyon`, `tahsilat komisyon`, `kart tahsilat`, `uye isyeri`, `isyeri ucret`, `merchant fee`, `merchant`, `sanal pos`, `vpos`, `taksit komisyon`, `kk tahsilat`
- `_INTEREST_KEYWORDS` = `faiz`, `gecikme…`, `late interest/fee/payment`, …
- `_CREDIT_CARD_ACCOUNT_FEE_KEYWORDS` = `yillik ucret/aidat`, `kart aidat`, `annual fee`, …
- `_CREDIT_CARD_BILL_PAYMENT_KEYWORDS` = `kk odeme`, `kart odeme`, …

**Classifiers & precedence (exclusions):**
- `looks_like_interest` — any interest kw.
- `looks_like_credit_card_account_fee` — **not** interest, **not** cc-bill, then cc-account-fee kw.
- `looks_like_commission` — **not** interest, **not** cc-account-fee, then commission kw.
- `looks_like_transfer_fee` — **not** commission, **not** interest, **not** cc-account-fee, then transfer kw.
- `looks_like_statement_bank_fee` = commission **OR** interest **OR** cc-account-fee **OR** transfer-fee.

**Subtype inference (`infer_bank_charge_subtype`) — ordered:**
1. interest → `interest`
2. cc-account-fee → `credit_card_fee`
3. commission → `card_settlement_fee`
4. **else → `transfer_fee`** ← catch-all default

**Label (`bank_charge_fee_label`):** transfer_fee → "transfer fee", card_settlement_fee → "POS commission", credit_card_fee → "credit card fee", interest → "interest".

**Routing into bank_fee (`suggest_withdrawal_match_kind`) — ordered:**
`cc_bill` (if company-card on) → **`bank_fee` (if bank-charges on & `looks_like_statement_bank_fee`)** → `worker_payroll` (if workers) → `vendor`.

---

## 2. The transfer-keyword hazard (core finding)

`_TRANSFER_FEE_KEYWORDS` includes **bare transfer-rail tokens** — `havale`, `eft`, `wire`, `swift` — which name the **mechanism of moving money**, not a **fee**. On Turkish statements:
- A real **payment** line typically reads `HAVALE …` / `EFT GİDEN …` / `SWIFT …` (the principal moving).
- A real **fee** line reads `HAVALE ÜCRETİ`, `EFT MASRAFI`, `İŞLEM ÜCRETİ`, `SWIFT MASRAFI`.

Because bare rail tokens match `looks_like_transfer_fee`, **a genuine transfer/payment is classified as a bank fee.** Two concrete misclassifications:

| Statement line (folded) | Today's suggestion | Should be |
|--------------------------|--------------------|-----------|
| `EFT GIDEN — ACME LTD 5,000.00` | **bank_fee** (matches `eft`) | vendor payment |
| `HAVALE — kira 12,000.00` | **bank_fee** (matches `havale`) | vendor / rent / equity |
| `EFT MAAS ODEME 8,000.00` | **bank_fee** (matches `eft`, and bank_fee precedes worker_payroll) | worker_payroll |
| `HAVALE UCRETI 6.50` | bank_fee → transfer_fee | ✓ correct |

The first three steer the operator to post **principal** to **Bank Charges (5800)**. The fourth is the only correct one.

Precedence makes it worse: in `suggest_withdrawal_match_kind`, **bank_fee is checked before worker_payroll and vendor** — so `EFT MAAS` (salary) and `EFT/HAVALE` vendor payments lose to the bank_fee default.

---

## 3. Accounting vs reporting consequence (crucial distinction)

- **Among the four fee subtypes** (interest / credit_card_fee / card_settlement_fee / transfer_fee), misclassification is **reporting-only**: `post_bank_charge_outflow` always posts **Dr Bank Charges / Cr Bank** regardless of subtype. The subtype is stored on `BankTransaction.charge_subtype` for labeling/reporting. So "commission vs transfer fee" being wrong does **not** corrupt the GL.
- **The accounting-consequential error** is classifying a **non-fee** row (a transfer *principal*) as `bank_fee` **at all** — that would post the full principal to Bank Charges instead of to a vendor/worker/equity account. *This* is the real risk, and it is exactly what the bare rail tokens enable.

So the transfer-keyword problem is **not** a subtype-taxonomy nicety — it is a **mis-routing** risk into the wrong posting kind.

---

## 4. Why this matters for P2.2 (batch)

P2.2's safe batch set is **`bank_fee` only**. If bare `havale`/`eft`/`wire`/`swift` keep classifying transfer *principals* as `bank_fee`, then:
- Those principal rows enter the **bank_fee batch candidate set**, and a "Post N bank charges" action could post **vendor/salary principal to Bank Charges** in bulk.
- This converts a recoverable wrong *suggestion* (today: operator can override in the queue) into a **bulk accounting error** (batch: many rows posted at once).

**Therefore: tightening transfer-charge recognition is a precondition for trusting the `bank_fee` batch.** Until then, the bank_fee batch should be gated to subtypes that cannot be a principal (commission/interest/cc-fee), or transfer-fee rows excluded from batch.

**Mitigating context (honest):** (a) the whole bank_fee path only fires when `bank_charges_on` (company setting **C**); tenants without it default to vendor. (b) In the manual P1.3 queue it is a *suggestion*, human-overridable. The danger sharpens specifically at **batch + bank-charges-on**.

---

## 5. How Turkish transfer charges *should* be classified (target taxonomy — framing only)

- **Transfer fee** = a charge *for executing* a transfer. Reliable signal = a **fee token** (`ucret`, `masraf`, `komisyon`, `fee`) — optionally co-occurring with a transfer token. Examples: `havale ucreti`, `havale masrafi`, `eft ucreti/masrafi`, `islem ucret`, `swift masrafi`, `transfer fee`. → GL **Bank Charges (5800)**, subtype `transfer_fee` (reporting).
- **Transfer principal** = the money moved (`HAVALE`, `EFT`, `WIRE`, `SWIFT` *without* a fee token). → **not** a bank charge; routes to vendor / worker / equity / loan per the operator. Must **not** default to `bank_fee`.
- **BSMV** (banking transaction tax) currently sits in commission keywords → `card_settlement_fee`. It is a tax that rides many charge types (incl. transfers); its placement is a **reporting choice**, GL-neutral. Worth a deliberate decision but not a mis-routing risk.

**Recommendation framing (no implementation):**
1. Treat bare rail tokens (`havale`, `eft`, `wire`, `swift`) as **transfer-principal indicators**, *not* transfer-fee indicators — recognize a transfer *fee* only when a **fee token** is present.
2. Keep `charge_subtype` as **reporting metadata** (GL unchanged).
3. Reconsider the **`transfer_fee` catch-all default** in `infer_bank_charge_subtype`: an unrecognized bank charge defaulting to "transfer fee" mislabels reporting; an explicit "other/uncategorized" subtype would be more honest (label-only).
4. Until (1) lands, **exclude transfer-fee-classified rows from the P2.2 batch** (or require an explicit fee token to batch them).

**Classification of the changes themselves:**
- Heuristic keyword behavior = **A** (default) — improving the default recognition for everyone.
- Per-tenant keyword tuning / extra bank dialects = **C** (company setting), if ever exposed.
- No **B** (user-level) dimension and **no accounting/posting change** — GL routing for genuine fees is unchanged; the fix is *which rows are called fees*.

---

## 6. Open questions (for product decision, not resolved here)

- Should bare `havale`/`eft` ever suggest `bank_fee`, or always default to vendor with bank_fee only on a fee token? (Recommended: fee-token-gated.)
- Should the bank_fee **batch** be restricted to `commission` + `interest` + `credit_card_fee` subtypes (which can't be a principal), leaving `transfer_fee` to manual review until recognition is tightened?
- Is `BSMV` better reported as its own subtype than folded into commission?
- Should `transfer_fee` remain the inference catch-all, or become an explicit "uncategorized bank charge" for cleaner reporting?

---

## 7. Validation / tests needed before any classification change

1. **Principal-not-fee corpus** — `EFT GIDEN`, `HAVALE <payee>`, `SWIFT <ref>`, `EFT MAAS` must **not** classify as `bank_fee`; assert they route to vendor/worker.
2. **Fee corpus** — `HAVALE UCRETI`, `EFT MASRAFI`, `ISLEM UCRET`, `SWIFT MASRAFI`, `TRANSFER FEE` **must** classify as `bank_fee` / subtype `transfer_fee`.
3. **Precedence pins** — `EFT MAAS` resolves to `worker_payroll` (not bank_fee); `KART KOMISYON` stays `card_settlement_fee`; interest/cc-fee precedence unchanged.
4. **GL-neutrality** — subtype changes do **not** alter the JE (always Dr Bank Charges / Cr Bank); only `charge_subtype`/label differ.
5. **Batch-safety** — with the principal corpus present, the bank_fee batch candidate set excludes all principal rows (no principal can be bulk-posted to Bank Charges).
6. **No-service-change guard** — `post_bank_charge_outflow` and `services.posting` unchanged; only recognition heuristics are in scope.
7. **Regression** — existing commission/interest/cc-fee classifications and `infer_bank_charge_subtype` outputs unchanged except the deliberately-targeted transfer cases.

---

*Characterization only. No code, no implementation. Key conclusion: bare `havale`/`eft`/`wire`/`swift` conflate transfer **mechanism** with transfer **fee**, mis-routing transfer **principals** into `bank_fee` — a recoverable wrong suggestion today, but a bulk accounting risk under the P2.2 batch. Subtype confusion among fee types is reporting-only (GL always Dr Bank Charges / Cr Bank); the real hazard is non-fee rows entering the bank_fee path. Tightening transfer recognition (fee-token-gated) is a precondition for a trustworthy bank_fee batch.*
