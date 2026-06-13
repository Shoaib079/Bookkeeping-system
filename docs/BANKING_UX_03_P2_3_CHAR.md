# BANKING-UX-03 P2.3 — Banking Configuration Surface Characterization

**Mode:** Characterization only — no code, no implementation, no DB changes, no posting changes.
**Inputs read:** BANKING_UX_01_AUDIT, _02_DESIGN, _03_ROADMAP, _03_P2_1_CHAR, _03_P2_2_CHAR, _03_P2_2_B_CHAR.
**Governing principle:** *Automation suggests. User approves. System posts only what it can explain.* Ladder: **Manual → Suggested → Trusted → Automated**. **Never Unknown → Automated.**

**Grounding fact (infrastructure already exists):** the registry (`registry/service.py`) supports settings at **`scope="company"`** and **`scope="user"`**, with a per-definition **default** and a **lock** mechanism (`check_locks`) and `get_effective_config` merging both. So the A/B/C model maps directly with **no schema change**:
- **A = system default** (the setting definition's default value)
- **B = user preference** (`scope="user"`)
- **C = company setting** (`scope="company"`); a **locked** company setting = a **policy** users cannot override.

Existing banking settings (all **C**, feature gates): `banking.reconciliation_enabled`, `banking.card_settlement_enabled`, `banking.company_card_enabled`, `banking.bank_charges_enabled`, `banking.transfer_fee_threshold`.

---

## 1. Current hard-coded decisions

| Behavior | Today | Verdict |
|----------|-------|---------|
| Default banking landing = **Accounts** form | hard-coded | **Candidate for config** (should be Cockpit/Queue/Classic per design §3) |
| Match queue sort/filter/density | hard-coded (P1.3) | **Candidate (B)** |
| Confidence chip display | always on (P1.2) | **Candidate (B)** |
| Confidence bands (High/Med/Low) | hard-coded heuristic | **Good hard-coded** (presentation); thresholds = candidate **C** with bounds |
| Batch eligibility = **`bank_fee` only**, fee-token-gated | hard-coded (P2.2/P2.2-B) | **Good hard-coded — keep as a safety invariant**; may only be *narrowed* by config, never widened |
| Review requirements | none today | **Candidate (C/policy)** |
| Match workflow (queue → detail → post) | hard-coded | **Good hard-coded** (the core flow shouldn't be a setting) |
| Per-row posting kinds + GL routing | hard-coded in services | **Good hard-coded — must stay fixed** (accounting) |
| Import header-row detection (auto + override) | hard-coded default | **Candidate (C per-bank, B per-user)** |
| Statement-row status lifecycle | hard-coded | **Good hard-coded** (accounting/state integrity) |
| Feature gates (reconciliation/card/charges) | **C settings already** | already configurable |
| Transfer-fee keyword recognition (P2.2-B) | hard-coded heuristic | **Good hard-coded default (A)**; per-tenant tuning = future **C** |
| Audit on post (`log_audit`) | always | **Good hard-coded — never optional** |

**Principle for the table:** anything that changes *what posts* or *what is reviewed* or *the GL* is **fixed or company-policy**, never user-level. Anything cosmetic/workflow is a safe user preference.

---

## 2. Configuration ownership model

| Setting | Owner | Why |
|---------|-------|-----|
| Default landing view (Cockpit/Queue/Classic) | **C default + B override** | Tenant sets a sensible default (firms→ledger); individual users may prefer another |
| Queue sort / density / default import tab | **B** | Pure personal workflow; zero financial impact |
| Show confidence chips / accounting previews | **B** | Presentation only |
| Confidence thresholds (band cutoffs) | **C (bounded)** | Affects which rows *look* trusted; must be a tenant decision within system floors, not per-user |
| Enable batch posting | **C (policy)** | Changes automation posture for the company |
| Batch-eligible kinds (within the safe set) | **C, narrowing-only** | A company may restrict; the *safe set* itself is a **system invariant (A)** |
| Require confirmation before batch | **C** | Risk control |
| Review-required kinds | **C (policy, lockable)** | Financial control; must be uniform per company |
| Trusted-pattern / learned automation enablement | **C (policy)** | Never a personal toggle — it changes what posts unattended |
| Feature gates (reconciliation/card/charges/transfer-threshold) | **C** | Already so |
| Audit on post | **A, fixed** | Compliance; never configurable |
| Per-row GL routing / posting rules | **A, fixed** | Accounting integrity |

Rule of thumb: **B = looks/feels; C = what posts / what's reviewed / what's automated; A = safety + accounting invariants.**

---

## 3. Banking workspace preferences

| Preference | Recommend |
|------------|-----------|
| Default landing (Cockpit / Queue / Classic) | **C default, B override** (A default = Cockpit) |
| Default import tab (Upload/Review/Match/History) | **B** (A default = Match when postable rows exist, else Upload) |
| Queue sorting (date/amount/confidence) | **B** |
| Queue density (compact/comfortable) | **B** |
| Show confidence chips | **B** (A default = on) |
| Show accounting previews (the JE that will post) | **B** (A default = on) — *visibility only; never gates posting* |

All of §3 is **safe to be user-level** because none changes what posts. Accounting previews are read-only explanations (supports the "post only what it can explain" principle).

---

## 4. Automation controls

| Control | Owner | Notes / safeguard |
|---------|-------|-------------------|
| Enable batch posting | **C (policy)** | Off by default (A) until a company opts in |
| Eligible posting kinds | **A invariant + C narrowing** | Safe set = `bank_fee` only (fee-token-gated, P2.2-B); company may further restrict; **never widen** to vendor/card_clearing/worker/principal kinds |
| Confidence threshold | **C, bounded** | System floor prevents "post everything"; threshold never lets an **unsafe kind** or **principal-routing** row automate |
| Require confirmation | **C** | A default = confirmation required; companies may relax only for the safe set |
| Trusted-pattern automation | **C (policy)** | Per the ladder (§7); off by default; never user-level |
| Future learned automation | **C (policy)** | Same; advancement gated + audited |

**Hard invariant (challenges any "make it configurable" pressure):** confidence and company settings may decide *whether* the **already-safe** set automates — they may **never** route an input-incomplete or principal-bearing kind into automation. Unsafe-kind automation is not a setting; it does not exist.

---

## 5. Review & approval controls

| Control | Owner | Notes |
|---------|-------|-------|
| Always require review (all rows) | **C** | Strictest posture; firms may default this on |
| Review low-confidence only | **C** | A sensible default for opted-in automation |
| Review all financial charges | **C** | |
| Review **transfer charges** | **C** | Ties to P2.2-B; until recognition is tightened, transfer-fee rows should default to review |
| Review payroll-related rows | **C** | Companies with staff may require it |
| Review vendor-related rows | **C** | |

All review controls are **company-level policy** (lockable) — review is a financial control, never a personal preference. A user must not be able to *lower* their own review burden.

---

## 6. Industry differences

**Universal (never vary by type):** posting safety/GL routing, the batch safe-set invariant, audit, review of principal-routing kinds, the Manual→…→Automated ladder.

**Vary by company type (via C defaults / templates):**

| Type | Likely defaults |
|------|-----------------|
| Restaurant / Retail | card settlement + POS commission on; bank charges on; cockpit landing; payroll review if staff |
| Trading | card/POS off; transfer/EFT-heavy → transfer-charge review on; vendor review likely |
| Service business | minimal card; vendor + bank-fee focus |
| Partnership | equity/partner-movement review on; cockpit/ledger landing |
| Bookkeeping firm | stricter review defaults; **ledger/classic** landing preference; settings **locked** as policy; (future) multi-client cockpit |

Avoid restaurant-specific assumptions: the **POS/card tiles already gate on company settings** (P2.1), so a trading or service tenant simply never sees them. Company-type only seeds **defaults**; every tenant can override within policy.

---

## 7. Learned-transaction framework (characterization only — no design)

Ladder semantics:

| Stage | Meaning | Advance requires | Safeguard |
|-------|---------|------------------|-----------|
| **Manual** | Operator chooses kind + inputs | — | Default state for any new pattern |
| **Suggested** | System proposes kind + confidence (today's heuristics) | nothing — suggestion only | Never posts; human picks |
| **Trusted** | Repeatedly-confirmed pattern is pre-filled / pre-selected | **N explicit human confirmations** of the same pattern, logged | Still **requires a human click to post**; per-company; reversible |
| **Automated** | Pattern posts without per-row click (batch/unattended) | **Explicit company opt-in (C policy)** + pattern already Trusted | **Only for input-complete, non-principal kinds** (today: `bank_fee`); audited; never Unknown→Automated |

Required confirmations before advancing: explicit, counted, human, and **kind-restricted** — a pattern can only reach Automated for a kind that is *input-complete from the row* (so the system can fully explain the posting). A vendor/worker/card_clearing pattern can reach **Trusted** (pre-fill) but **never Automated** (it still needs human input).

Safeguards: per-company (never per-user) enablement; reversible at any stage; confidence floor; principal-routing kinds barred from Automated; transfer-fee rows barred until P2.2-B recognition is tightened.

Audit requirements: every automated/trusted post audited with the pattern id, the stage, and the actor (the enabling policy + the system); advancement events (Suggested→Trusted→Automated) themselves audited. (Note: reconciliation audit policy is a PS-P7 item — automation must not ship before reconciliation posting is auditable.)

---

## 8. FastAPI / React readiness

Conceptual separation (maps to the existing registry scopes):

- **User preferences (B)** → `GET/PUT /me/preferences` (landing, density, sort, chips, previews). Per-user, low-risk, no policy implication.
- **Company settings (C)** → `GET/PUT /company/settings` (feature gates, default landing, thresholds, batch enable). Tenant-scoped.
- **Policy settings (locked C)** → a **distinct concept**: company settings that are **locked** (the registry already supports locks) — review requirements, automation enablement, eligible kinds. In an API these should be **separately permissioned** (owner/admin only) and surfaced as "policy", not "preference".

The three-way split (preference / setting / policy) should be **explicit in the API**, not collapsed into one settings bag — so a React client can render personal prefs freely but gate policy behind admin permissions. `get_effective_config` already models the merge; the API layer adds the permission boundary.

---

## 9. Risks

**Dangerous settings (guard heavily or disallow):**
- "Auto-post all suggested rows" — violates the ladder; **must not exist**.
- "Confidence threshold = 0 / post everything" — system floor must forbid.
- "Disable review for financial charges" beyond the safe set — risk of bulk mis-posting.
- "Enable batch for vendor/card_clearing/worker/principal kinds" — **must not exist** (P2.2-B: principal→Bank Charges hazard).

**Confusing settings:**
- Too many overlapping review toggles (collapse into a small, clear policy set).
- Per-user automation toggles (automation is company policy; per-user is confusing *and* unsafe).
- Thresholds expressed as opaque numbers without a "what this means" preview.

**Settings that should never exist:** unsafe-kind batch; Unknown→Automated; disabling audit; user-level control over what posts or what's reviewed.

**Should never be user-level (must be C/policy):** batch enablement, eligible kinds, confidence thresholds, review requirements, feature gates, automation advancement.

---

## 10. Recommended MVP (small, safe P2.3)

**Must-have — Company (C), reusing the existing registry (no DB change):**
- Default landing view (Cockpit/Queue/Classic), A default = Cockpit.
- Batch posting **enable** (off by default) + **eligible-kind narrowing** within the safe set.
- Review-required kinds (at least: transfer charges + a global "review low-confidence only" default).
- Confidence threshold **within system bounds**.

**Must-have — User (B):**
- Show confidence chips (on); show accounting previews (on); queue sort + density; default import tab.

**Nice-to-have:**
- Per-bank default header row (C); remembered queue filters (B).

**Defer to P3:**
- Trusted-pattern / learned automation (§7) — needs the ladder + reconciliation audit (PS-P7) first.
- Multi-client firm policy locks + cross-tenant cockpit.
- Per-company transfer/keyword tuning (from P2.2-B).

**MVP guardrails (non-negotiable):** the batch safe-set invariant (A) is not user-configurable and may only be narrowed; audit stays on; no setting can route a principal/unsafe-kind row into automation; previews are read-only.

---

*Characterization only. No code, no implementation, no DB or posting change. The registry already provides company/user scopes + locks, so A/B/C/policy needs no schema work. Core stance: configure presentation and posture freely; keep what-posts / what's-reviewed / accounting / audit as fixed invariants or locked company policy; never let configuration cross Unknown → Automated.*
