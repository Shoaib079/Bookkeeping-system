# PY313-CLEANUP-01 — UTC datetime migration

## Goal

Replace deprecated `datetime.datetime.utcnow()` (removed in Python 3.12+ deprecation path toward 3.13) with future-safe UTC handling without changing runtime behavior.

## Helper

`utc_datetime.utc_now_naive()` → `datetime.datetime.now(datetime.UTC).replace(tzinfo=None)`

Used wherever values must remain **naive** for SQLite and SQLAlchemy `DateTime` columns without `timezone=True`.

## SQLAlchemy DateTime audit

| Setting | Count | Notes |
|---------|-------|-------|
| `DateTime` (default, `timezone=False`) | All columns in `models.py` | SQLite stores naive timestamps |
| `DateTime(timezone=True)` | **0** | None in codebase |

All ORM timestamp columns expect naive datetimes. No schema migration required.

## Usage inventory (32 sites)

| File | Line(s) | Context | Class |
|------|---------|---------|-------|
| `app.py` | 2179 | Raw SQL `INSERT INTO companies … created_at` | **B** |
| `app.py` | 2281 | Raw SQL `INSERT INTO company_users … created_at` | **B** |
| `tests/test_banking_ux02_p2.py` | 78, 180, 196 | `Company.created_at` fixture | **B** |
| `tests/test_banking_ux02_p3.py` | 93 | `Company.created_at` fixture | **B** |
| `tests/test_phase14b2_registry.py` | 56 | `Company.created_at` fixture | **B** |
| `tests/test_phase14b2_registry.py` | 158 | `evaluate_lock` milestone dict | **B** |
| `tests/test_cc_expense_form.py` | 56 | `Company.created_at` fixture | **B** |
| `tests/test_phase18_mvp1.py` | 43 | `Company.created_at` fixture | **B** |
| `tests/test_phase18_mvp2.py` | 52 | `Company.created_at` fixture | **B** |
| `tests/test_phase18_mvp3.py` | 66, 105, 121 | `Company` / entity `created_at` | **B** |
| `tests/test_phase18_mvp4.py` | 74, 113, 129 | `Company` / entity `created_at` | **B** |
| `tests/test_phase18_mvp5.py` | 68, 110, 126, 291 | `Company` / entity `created_at` | **B** |
| `tests/test_cc_subledger_sync.py` | 64, 135, 151 | `Company` / entity `created_at` | **B** |
| `tests/test_company_cc_safety.py` | 70 | `Company.created_at` fixture | **B** |
| `tests/test_cc_recon_health.py` | 65, 127, 143 | `Company` / entity `created_at` | **B** |
| `tests/test_cc_bill_payment_void.py` | 61, 101, 117 | `Company` / entity `created_at` | **B** |
| `tests/test_workers.py` | 56 | `Company.created_at` fixture | **B** |

**Class A (timezone-aware):** 0 sites — no `DateTime(timezone=True)` columns and no aware-datetime consumers of these values.

**Class B (naive UTC):** 32 sites — all converted via `utc_now_naive()`.

## Risk assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Behavior change vs `utcnow()` | **Low** | `utc_now_naive()` returns the same naive UTC wall-clock value `utcnow()` did |
| Aware datetime in naive SQLite column | **None** | All conversions use `.replace(tzinfo=None)` |
| Accounting / posting logic | **None** | No changes to journal, void, or posting paths |
| Schema / migrations | **None** | No DDL or migration edits |
| Class A misclassification | **None** | No Class A conversions applied |

## Out of scope

- `datetime.datetime.now()` (local naive) usages elsewhere in `app.py` and tests — separate cleanup; not deprecated in 3.13
- `datetime.timezone.utc` timestamp calls in auth rate-limiting — already timezone-aware; unchanged

## Tests

- `tests/test_utc_datetime.py` — contract that helper returns naive UTC
- Full suite must remain green (no test logic changes beyond `utcnow` replacement)
