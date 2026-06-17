# BANKING-UX-04-S4 — React Banking Workflow Contract

**Status:** ✅ **Frozen (BANKING-UX-04-S4)**  
**Source of truth:** `registry/banking_workflow_contract.py` + `registry/banking_config.py`  
**Streamlit consumers:** `ui/banking.py`, `render_banking`, `render_add_transaction`  
**React consumers:** Future `/banking/*` and `/transactions/new` surfaces (not implemented in this slice)  
**Tests:** `tests/test_banking_ux_04_s4_react_workflow_contract.py`, `tests/test_banking_ux_04_epic_matrix.py`

## Purpose

Freeze the **company-scoped `banking.workflow_mode` presentation contract** so the React port reads the same setting value and applies the same UI routing rules as Streamlit — without duplicating posting, reconciliation, or GL logic.

## Contract rules

1. **UI-only** — `banking.workflow_mode` affects section order, default landing, Advanced grouping, and Add Transaction type placement only. **`services/posting.py` and `reconciliation/match_post.py` never read this setting.**
2. **Company-scoped** — stored as `company_setting`; API shape: `GET/PATCH /api/v1/companies/{id}/settings` key `banking.workflow_mode`.
3. **Enum** — `statement_first` | `hybrid` | `manual_first`; default `statement_first`; invalid values normalize to `statement_first`.
4. **No workflow removed** — every banking section and manual bank entry path stays reachable in all modes (visibility/order varies).
5. **Permission gates unchanged** — mode does not bypass `manage_banking`, `view_bank_statement_import`, or feature toggles (`banking.reconciliation_enabled`, `banking.pos_settlement_enabled`, `banking.company_card_enabled`).
6. **Change policy** — any contract edit requires updating `registry/banking_workflow_contract.py`, this doc, `ui/banking.py` helpers (if behavior changes), and S4/epic tests.

## Setting contract

| Field | Value |
|-------|-------|
| Key | `banking.workflow_mode` |
| Scope | `company` |
| Type | `enum` |
| Options | `statement_first`, `hybrid`, `manual_first` |
| Default | `statement_first` |
| Catalog | `registry/settings_catalog.py` |
| Getter | `banking_workflow_mode(session, company_id)` |

## Frozen mode map

| Mode | EN label key | Banking default section | React default sub-route | Add Transaction bank type |
|------|----------------|-------------------------|-------------------------|---------------------------|
| `statement_first` | `settings.banking.workflow_mode.statement_first` | `cockpit` (else `import`) | `/banking/recon` | Under **Advanced**; statement callout prominent |
| `hybrid` | `settings.banking.workflow_mode.hybrid` | Registry landing (`banking.default_landing`) | `/banking/recon` | Primary type chips; no callout |
| `manual_first` | `settings.banking.workflow_mode.manual_first` | `accounts` | `/banking/accounts` | First primary type; statement link as caption |

## Banking section → React sub-route

| `banking_section` | React path | Streamlit section |
|-------------------|------------|-------------------|
| `cockpit` | `/banking/recon` | Reconciliation cockpit |
| `import` | `/banking/import` | Statement import |
| `accounts` | `/banking/accounts` | Accounts & manual transactions |
| `pos_settlement` | `/banking/pos-settlement` | POS / Card Settlement |
| `settings` | `/banking/settings` | Banking page settings |

**Statement-first Advanced:** `accounts` is valid in session but hidden from chips; surfaced via Advanced expander → `/banking/accounts`.

## Add Transaction contract

| Streamlit state | React equivalent |
|-----------------|------------------|
| `at_workflow_mode` | Company setting `banking.workflow_mode` on page load |
| `at_type_idx` (Bank = 5) | Transaction type param / tab index 5 |
| Statement callout button | Navigate to `/banking/import` |
| Advanced manual bank gate | Sheet/expander → select Bank Transaction type |

Path: `ADD_TRANSACTION_REACT_PATH` = `/transactions/new` (frozen in `registry/navigation.py`).

## Streamlit helper map (presentation SSOT)

| Helper | Role |
|--------|------|
| `banking_build_section_options` | Chip order + gated sections |
| `banking_section_extra_valid` | Hidden-but-valid sections (`accounts` in statement-first) |
| `banking_workflow_default_section` | Mode default landing |
| `banking_show_manual_advanced_panel` | Banking Advanced expander visibility |
| `at_primary_type_indices` | Add Transaction desktop type order |
| `at_mobile_type_picker_split` | Add Transaction mobile type picker split |
| `at_render_statement_workflow_callout` | Statement import CTA |
| `at_render_manual_bank_advanced_gate` | Manual bank type under Advanced |

## React implementation notes

- Fetch `banking.workflow_mode` once per company context (React Query key: `['settings', companyId, 'banking.workflow_mode']`).
- Compose visible tabs from mode spec **after** applying the same permission/toggle gates as Streamlit.
- Do **not** embed match/post algorithms in the React layer — call FastAPI endpoints that delegate to existing services unchanged.
- Duplicate-post safeguard remains in `reconciliation/match_post.py` only.

## No-change statement (BANKING-UX-04-S4)

- **No posting, reconciliation, GL, schema, or duplicate-post logic changes.** Contract freeze + extended tests only.
- **BANKING-UX-04 epic S1–S4 complete** after this slice.
