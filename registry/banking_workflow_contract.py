"""BANKING-UX-04-S4 — frozen banking workflow mode React migration contract.

Machine-readable mirror of ``docs/BANKING_UX_04_REACT_WORKFLOW_CONTRACT.md``.
UI-only: ``banking.workflow_mode`` governs presentation routing in Streamlit and
the future React Banking + Add Transaction surfaces. Posting/recon/GL never read
this setting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from registry.banking_config import (
    BANKING_WORKFLOW_MODE_DEFAULT,
    BANKING_WORKFLOW_MODE_IDS,
    banking_normalize_workflow_mode,
)

CONTRACT_DOC = "docs/BANKING_UX_04_REACT_WORKFLOW_CONTRACT.md"

SETTING_KEY: Final[str] = "banking.workflow_mode"
SETTING_SCOPE: Final[str] = "company"

# banking_section chip id → React sub-route (under /banking)
BANKING_SECTION_REACT_ROUTES: dict[str, str] = {
    "cockpit": "/banking/recon",
    "import": "/banking/import",
    "accounts": "/banking/accounts",
    "pos_settlement": "/banking/pos-settlement",
    "settings": "/banking/settings",
}

ADD_TRANSACTION_REACT_PATH: Final[str] = "/transactions/new"
AT_BANK_TXN_TYPE_IDX: Final[int] = 5


@dataclass(frozen=True)
class BankingWorkflowModeSpec:
    mode_id: str
    label_key: str
    banking_section_order: tuple[str, ...]
    banking_advanced_sections: frozenset[str]
    banking_default_section: str
    react_default_subroute: str
    add_txn_bank_type_in_primary: bool
    add_txn_statement_callout: str  # "prominent" | "caption" | "none"
    add_txn_manual_bank_advanced: bool


WORKFLOW_MODE_SPECS: tuple[BankingWorkflowModeSpec, ...] = (
    BankingWorkflowModeSpec(
        mode_id="statement_first",
        label_key="settings.banking.workflow_mode.statement_first",
        banking_section_order=("cockpit", "import", "pos_settlement", "settings"),
        banking_advanced_sections=frozenset({"accounts"}),
        banking_default_section="cockpit",
        react_default_subroute="/banking/recon",
        add_txn_bank_type_in_primary=False,
        add_txn_statement_callout="prominent",
        add_txn_manual_bank_advanced=True,
    ),
    BankingWorkflowModeSpec(
        mode_id="hybrid",
        label_key="settings.banking.workflow_mode.hybrid",
        banking_section_order=("cockpit", "accounts", "import", "pos_settlement", "settings"),
        banking_advanced_sections=frozenset(),
        banking_default_section="cockpit",
        react_default_subroute="/banking/recon",
        add_txn_bank_type_in_primary=True,
        add_txn_statement_callout="none",
        add_txn_manual_bank_advanced=False,
    ),
    BankingWorkflowModeSpec(
        mode_id="manual_first",
        label_key="settings.banking.workflow_mode.manual_first",
        banking_section_order=("accounts", "cockpit", "import", "pos_settlement", "settings"),
        banking_advanced_sections=frozenset(),
        banking_default_section="accounts",
        react_default_subroute="/banking/accounts",
        add_txn_bank_type_in_primary=True,
        add_txn_statement_callout="caption",
        add_txn_manual_bank_advanced=False,
    ),
)

_WORKFLOW_SPEC_BY_ID = {spec.mode_id: spec for spec in WORKFLOW_MODE_SPECS}


def workflow_mode_spec(mode_id: str) -> BankingWorkflowModeSpec:
    return _WORKFLOW_SPEC_BY_ID[banking_normalize_workflow_mode(mode_id)]


def workflow_contract_rows() -> list[tuple[str, str, str]]:
    """``(mode_id, label_key, react_default_subroute)`` for docs and tooling."""
    validate_banking_workflow_contract()
    return [(s.mode_id, s.label_key, s.react_default_subroute) for s in WORKFLOW_MODE_SPECS]


def banking_section_react_route(section_id: str) -> str | None:
    return BANKING_SECTION_REACT_ROUTES.get(section_id)


def validate_banking_workflow_contract() -> None:
    spec_ids = {s.mode_id for s in WORKFLOW_MODE_SPECS}
    if spec_ids != set(BANKING_WORKFLOW_MODE_IDS):
        raise ValueError(
            f"WORKFLOW_MODE_SPECS ids {spec_ids!r} must match "
            f"BANKING_WORKFLOW_MODE_IDS {set(BANKING_WORKFLOW_MODE_IDS)!r}"
        )
    if BANKING_WORKFLOW_MODE_DEFAULT not in spec_ids:
        raise ValueError("BANKING_WORKFLOW_MODE_DEFAULT must have a spec")

    routes = list(BANKING_SECTION_REACT_ROUTES.values())
    if len(routes) != len(set(routes)):
        raise ValueError("Duplicate react sub-route in BANKING_SECTION_REACT_ROUTES")

    for spec in WORKFLOW_MODE_SPECS:
        for section in spec.banking_section_order:
            if section not in BANKING_SECTION_REACT_ROUTES:
                raise ValueError(f"Unknown banking_section {section!r} in {spec.mode_id}")
        for section in spec.banking_advanced_sections:
            if section not in BANKING_SECTION_REACT_ROUTES:
                raise ValueError(f"Unknown advanced section {section!r} in {spec.mode_id}")
        if spec.banking_default_section not in (
            spec.banking_section_order + tuple(spec.banking_advanced_sections)
        ):
            raise ValueError(
                f"default_section {spec.banking_default_section!r} not reachable "
                f"for mode {spec.mode_id!r}"
            )
        if not spec.react_default_subroute.startswith("/banking/"):
            raise ValueError(f"react_default_subroute must be under /banking for {spec.mode_id}")
        if spec.add_txn_statement_callout not in ("prominent", "caption", "none"):
            raise ValueError(f"Invalid add_txn_statement_callout for {spec.mode_id}")
        # Manual bank accounts always reachable: accounts in chips or advanced
        if "accounts" not in spec.banking_section_order and "accounts" not in spec.banking_advanced_sections:
            raise ValueError(f"accounts must stay reachable in mode {spec.mode_id}")
        # Manual bank txn always reachable
        if not spec.add_txn_bank_type_in_primary and not spec.add_txn_manual_bank_advanced:
            raise ValueError(f"Bank Transaction type must stay reachable in mode {spec.mode_id}")
