# MONEY-DECIMAL-03 — Money Helper Module

**Mode:** Pure helpers only (2026-06-16). No posting, model, schema, or Alembic changes.

**Goal:** Centralize `Decimal` parse/quantize rules before MD-04 posting-kernel migration.

**Module:** `services/money.py`  
**Contract:** `tests/test_money_decimal_03_money_helpers.py`  
**Prerequisites:** [MONEY_DECIMAL_01_AUDIT.md](./MONEY_DECIMAL_01_AUDIT.md) · [MONEY_DECIMAL_02_GOLDEN_VECTORS.md](./MONEY_DECIMAL_02_GOLDEN_VECTORS.md)

---

## Executive summary

| Function | Purpose |
|----------|---------|
| `parse_money(value)` | Boundary parse → `Decimal`; float via `str()` for safety |
| `quantize_money(value)` | 2 dp, `ROUND_HALF_UP` |
| `quantize_fx(value)` | 4 dp, `ROUND_HALF_UP` |
| `quantize_rate(value)` | 8 dp, `ROUND_HALF_UP` |
| `money_to_float(value)` | Float seam after money quantize (not wired yet) |
| `decimal_equal(a, b)` | Equality after money quantize |

**Constants:** `MONEY_PRECISION`, `FX_PRECISION`, `RATE_PRECISION`

---

## Design rules

1. **Pure module** — stdlib `decimal` only; no SQLAlchemy, models, or posting imports.
2. **Not wired** — no production caller until MD-04; golden vectors (MD-02) remain Float baseline.
3. **Float safety** — `parse_money(100.01)` → `Decimal('100.01')`, not binary `Decimal(100.01)`.
4. **Rounding** — all quantize helpers use `ROUND_HALF_UP` (documented policy from MD-01 audit).
5. **Bool rejected** — `parse_money(True)` raises `TypeError` (bool is an `int` subclass).

---

## API reference

### `parse_money(value)`

| Input | Result |
|-------|--------|
| `Decimal` | Passthrough (same object) |
| `int` | `Decimal(int)` |
| `float` | `Decimal(str(float))` |
| `str` | `Decimal(strip)` |
| `bool` | `TypeError` |
| empty `str` | `ValueError` |

### `quantize_money` / `quantize_fx` / `quantize_rate`

Apply `parse_money` then quantize to the matching precision constant.

Examples:

| Input | Helper | Output |
|-------|--------|--------|
| `"2.675"` | `quantize_money` | `2.68` |
| `"34.56789"` | `quantize_fx` | `34.5679` |
| `"34.567891235"` | `quantize_rate` | `34.56789124` |

### `money_to_float(value)`

`float(quantize_money(value))` — explicit compatibility seam for future posting bridge.

### `decimal_equal(a, b)`

`quantize_money(a) == quantize_money(b)` — use in tests and future parity checks.

---

## Next slice

**MONEY-DECIMAL-04** — posting kernel internal Decimal math (SQLite Float columns unchanged). Re-run MD-02 golden vectors after any kernel change.
