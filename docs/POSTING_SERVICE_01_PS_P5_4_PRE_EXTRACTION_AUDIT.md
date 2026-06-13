# POSTING-SERVICE-01 — PS-P5-4 Pre-Extraction Audit (flag-only close voids)

**Phase:** PS-P5-4 (audit only — no code changes)
**Predecessors:** PS-P0…PS-P4, PS-P5-1 (receivables), PS-P5-2 (inventory), PS-P5-3 (simple equity) — complete
**State at audit:** suite green; working tree clean; PS-P4/PS-P5 audit docs committed
**Scope:** `void_reconciliation`, `void_eod_close`, `void_year_end_close`
**Verdict:** **GO** — extract as **one wave** (flag-only pair first, then `void_reconciliation`). No YEC-guard entanglement; these are safely in PS-P5.

---

## 1. Dependency graph

```
void_reconciliation (app.py:6229) → str
  ├─ session.get(DailyCashReconciliation) ... guards: not-found / is_void / status=="draft"
  ├─ if journal_entry_id:
  │     ├─ session.get(JournalEntry, journal_entry_id)
  │     ├─ reverse_journal_entries_for("CashReconciliation", reconciliation_id, reason) ... shim → service [commit per JE]
  │     └─ cq(JournalEntry).filter(Reversal, reference_id==original_je.id).order_by(id desc).first()
  │           → reconciliation.reversed_je_id = reversal.id
  ├─ is_void / voided_by_id(=owner_id) / voided_at / void_reason = …
  ├─ session.commit()
  └─ log_audit("Void","DailyCashReconciliation", id, "Voided by user {owner_id}, reason: {reason}")

void_eod_close (app.py:6448) → str          NO GL
  ├─ session.get(EndOfDayClose) ... guards: not-found / is_void
  ├─ is_void / voided_by_id(=owner_id) / voided_at / void_reason / status="voided" = …
  ├─ session.commit()
  └─ log_audit("Void","EndOfDayClose", id, "Day {eod.date} close voided by user {owner_id}: {reason}")

void_year_end_close (app.py:8150) → str      NO GL
  ├─ session.get(YearEndClose) ... guards: not-found / is_void / **empty-reason**
  ├─ is_void / status="voided" / voided_by_id(=voider_id) / voided_at / void_reason = …
  ├─ session.commit()
  └─ log_audit("VoidYearEndClose","YearEndClose", id, "Voided year-end close for {yec.fiscal_year} — {reason}")
```

Only `void_reconciliation` touches the GL (reverses the `CashReconciliation` variance JE) and uses `cq`. The other two are pure flag/status updates.

---

## 2. Return-contract table

| Function | Type | Success | Failure values |
|----------|------|---------|----------------|
| `void_reconciliation` | `str` | `""` | `"Reconciliation not found."` · `"Reconciliation already voided."` · `"Cannot void a draft reconciliation; delete it instead."` |
| `void_eod_close` | `str` | `""` | `"End-of-day close record not found."` · `"This close has already been voided."` |
| `void_year_end_close` | `str` | `""` | `"Year-end close record not found."` · `"Year-end close is already voided."` · `"Void reason is required."` |

**Contract quirk to preserve:** `void_year_end_close` **validates empty reason**; `void_reconciliation` and `void_eod_close` **do not** (empty reason still succeeds). Do not "normalize" this during extraction.

All three return an error `str` (not `bool`) — so the app shim's success check is `if not err:` (empty string = success), unlike the PS-P3 `bool` voids.

---

## 3. Commit & audit map

| Function | Commits | Audit | Actor model |
|----------|---------|-------|-------------|
| `void_reconciliation` | reverse JE (kernel) **if** `journal_entry_id` set + 1 explicit `commit()` + `log_audit` → **3** (posted-JE) / **2** (no JE) | `log_audit` after commit | `voided_by_id = owner_id` (explicit); `log_audit.performed_by = ambient _current_user` |
| `void_eod_close` | 1 explicit + `log_audit` → **2** | after commit | `voided_by_id = owner_id`; audit performed_by ambient |
| `void_year_end_close` | 1 explicit + `log_audit` → **2** | after commit | `voided_by_id = voider_id`; audit performed_by ambient |

**Dual-user note:** the actor is captured **twice** with different sources — `voided_by_id` from the explicit `owner_id`/`voider_id` param (FastAPI-friendly) and `log_audit.performed_by` from the ambient `_current_user` (Streamlit). Preserve both; flag for the eventual API user-context unification.

**Audit-description record-field dependency:** the `log_audit` text embeds fields of the voided record — `eod.date` (eod) and `yec.fiscal_year` (year-end). `void_reconciliation`'s text uses only `owner_id`/`reason` (both available to the shim). So when `log_audit` stays in the app shim (per the PS-P3/P4 pattern), the shim for `void_eod_close`/`void_year_end_close` must **re-read the record** (still readable post-void) to rebuild the description. Minor but real extraction wrinkle.

---

## 4. Company-scoping / `cq`

| Function | `cq` | company_id need |
|----------|------|-----------------|
| `void_reconciliation` | **yes** — `cq(JournalEntry)` reversal lookup; `reverse_journal_entries_for` (shim uses `current_company_required()`) | service needs explicit `company_id` |
| `void_eod_close` | none (`session.get`) | none |
| `void_year_end_close` | none (`session.get`) | none |

A shared service signature can accept `company_id` used only by `void_reconciliation`; the flag-only pair can ignore it (or omit it).

---

## 5. Journal-reversal behavior

- **`void_reconciliation` → `CashReconciliation`:** when `journal_entry_id` is set, `reverse_journal_entries_for("CashReconciliation", reconciliation_id, reason)` posts the reversal, then the reversal JE is found (`Reversal`/`reference_id==original_je.id`) and its id stored in `reconciliation.reversed_je_id`. When no JE was posted (balanced recon), reversal is skipped and `reversed_je_id` stays `None`.
- **`void_eod_close`:** **no GL** — EOD close posts no journal entries; void is flag/status only.
- **`void_year_end_close`:** **no GL** — removes the year lock by setting `is_void`/`status="voided"`; no reversal. (The year *lock* is enforced elsewhere via `YearEndClose` rows; voiding reopens posting into that year.)

---

## 6. Existing test coverage

| Function | Tests (strong) |
|----------|----------------|
| `void_reconciliation` | `test_cash_reconciliation.py`: `test_void_creates_reversal_je` (posted-JE + `reversed_je_id` set), `test_void_balanced_reconciliation_no_reversal_je` (no-JE path → `None`), `test_double_void_returns_error` ("already voided") |
| `void_eod_close` | `test_end_of_day_close.py`: void, double-void, not-found (id 99999), **"must not create any journal entries"** (no-GL) |
| `void_year_end_close` | `test_year_end_close.py`: void, double-void, **empty-reason** (`reason=""`), lock-reopen (void used to re-test), owner-only permission |

Coverage is comprehensive — both JE branches of `void_reconciliation`, the no-GL assertion for `void_eod_close`, and the empty-reason guard for `void_year_end_close` are already pinned.

---

## 7. Missing characterization (small, add before extraction)

1. **`void_reconciliation` guard strings** — the `"not found"` and especially the `"Cannot void a draft …"` guard are not obviously pinned; add exact-string assertions.
2. **Empty-reason asymmetry** — pin that `void_reconciliation` and `void_eod_close` **succeed** with an empty reason (preserve the quirk vs `void_year_end_close`).
3. **Commit-count pins** — none of the three has a `mock_commit.call_count` pin (unlike PS-P3 voids). Add: `void_reconciliation` = 3 (posted-JE) / 2 (no JE); `void_eod_close` = 2; `void_year_end_close` = 2 — to lock the boundary before the shim refactor.
4. **Audit-description pin** — assert the exact `log_audit` description text (with `eod.date` / `yec.fiscal_year` / `owner_id`) so the shim re-read refactor preserves it.

---

## 8. One wave or separate?

**One wave (PS-P5-4).** All three share the `str` return contract, an explicit `owner_id`/`voider_id` actor param, the flag-set → `commit` → post-commit `log_audit` shape, and the close/period-end domain. They are small and benefit from a single shim pattern + one test module. The only asymmetry — `void_reconciliation`'s JE reversal + `cq` — is accommodated by a shared service signature that takes an optional `company_id` (used only there).

**They are correctly in PS-P5, not PS-P6:** none carries a duplicate inline YEC guard. `void_year_end_close` *removes* the lock; it does not *check* one, so it has no TD-POSTING-05 entanglement.

**Sub-sequence within the wave:**
1. `void_eod_close` + `void_year_end_close` (flag-only, no GL, no `cq`) — trivial; establish the `str`-return shim + audit-re-read pattern.
2. `void_reconciliation` (adds `reverse_journal_entries_for` + `cq` reversal lookup + `reversed_je_id`) — needs the §7.1–7.3 pins.

---

## 9. Risk map

| Item | Risk | Driver / mitigation |
|------|------|---------------------|
| `void_eod_close` | **Low** | flag-only, no GL/`cq`, `session.get`; strong coverage |
| `void_year_end_close` | **Low–Medium** | flag-only, but voiding **reopens the year lock** — high-impact semantics; lock-reopen already tested; has reason validation |
| `void_reconciliation` | **Medium** | JE reversal + `cq` reversal lookup + `reversed_je_id`; two branches (posted/no-JE); empty-reason quirk |
| `str` return contract | **Low** | shim success check = empty string (not `bool`) — note in shim |
| Audit-description record-field dependency | **Low–Medium** | shim must re-read `eod.date`/`yec.fiscal_year`; pin description first (§7.4) |
| Dual-user (`voided_by_id` explicit vs `performed_by` ambient) | **Low (debt)** | preserve verbatim; register for API user-context unification |
| YEC-guard entanglement | **None** | no duplicate inline guards in scope |

---

## 10. Go / No-Go

| Decision | Verdict |
|----------|---------|
| Extract all three as one PS-P5-4 wave (flag-only pair → `void_reconciliation`), after §7 pins | **GO** |
| Extract `void_reconciliation` before its guard-string + commit-count + branch pins (§7.1–7.3) land | **NO-GO** |
| "Fix" the empty-reason asymmetry or the dual-user model during extraction | **NO-GO** — verbatim move; register as debt |
| Fold in any YEC-guarded equity/period-end function | **NO-GO** — PS-P6 (gated on TD-POSTING-05) |

---

*Audit only. No code modified. Update `POSTING_SERVICE_01_CASCADE_MAP.md` and `AUDIT_HISTORY.md` when PS-P5-4 lands.*
