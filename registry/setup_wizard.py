"""Company setup wizard — Phase 14D-G (registry defaults, no policy enforcement)."""

from __future__ import annotations

from typing import Any

from registry.accounting_mode_bundles import ACCOUNTING_MODE_BUNDLES
from registry.loader import get_module_def, list_modules
from registry.service import (
    get_company_setting,
    get_setting,
    set_company_setting,
    set_setting,
)

WIZARD_SETTING_COMPLETED = "setup.wizard_completed"
WIZARD_SETTING_VERTICAL = "setup.vertical_template"
WIZARD_SETTING_ACCOUNTING_MODE = "policy.accounting_mode"

BUSINESS_TYPES: tuple[tuple[str, str, str], ...] = (
    ("general", "General business", "Default modules for most small companies."),
    ("services", "Services", "Consulting, agencies, freelancers — light inventory."),
    ("retail", "Retail / shop", "Stock and sales focus; inventory recommended."),
    ("restaurant", "Restaurant / café", "Food service; inventory and daily close emphasis."),
    ("tourism", "Tourism / hospitality", "Seasonal operations; partners and reporting."),
)

ACCOUNTING_MODES: tuple[tuple[str, str], ...] = (
    ("flexible", "Flexible — few mandatory controls; good while learning the system."),
    ("standard", "Standard — recommended daily close and reconciliation."),
    ("strict", "Strict — strongest controls; best when audit trail matters."),
)

# Optional modules offered in the wizard (shipped toggleable + planned prefs).
WIZARD_MODULE_IDS: tuple[str, ...] = (
    "inventory",
    "partner_accounts",
    "budget",
    "foreign_currency",
    "vat_tax",
)

_VERTICAL_MODULE_DEFAULTS: dict[str, dict[str, bool]] = {
    "general": {
        "inventory": False,
        "partner_accounts": True,
        "budget": True,
        "foreign_currency": False,
        "vat_tax": False,
    },
    "services": {
        "inventory": False,
        "partner_accounts": True,
        "budget": True,
        "foreign_currency": False,
        "vat_tax": False,
    },
    "retail": {
        "inventory": True,
        "partner_accounts": False,
        "budget": True,
        "foreign_currency": False,
        "vat_tax": True,
    },
    "restaurant": {
        "inventory": True,
        "partner_accounts": True,
        "budget": True,
        "foreign_currency": False,
        "vat_tax": True,
    },
    "tourism": {
        "inventory": False,
        "partner_accounts": True,
        "budget": True,
        "foreign_currency": True,
        "vat_tax": True,
    },
}


def module_setting_key(module_id: str) -> str:
    return f"module.{module_id}.enabled"


def default_modules_for_vertical(vertical: str) -> dict[str, bool]:
    base = {mid: False for mid in WIZARD_MODULE_IDS}
    base.update(_VERTICAL_MODULE_DEFAULTS.get(vertical, _VERTICAL_MODULE_DEFAULTS["general"]))
    return base


def is_wizard_complete(session, company_id: int) -> bool:
    return bool(get_setting(session, WIZARD_SETTING_COMPLETED, company_id=company_id))


def read_module_preferences(session, company_id: int) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for mid in WIZARD_MODULE_IDS:
        raw = get_company_setting(session, company_id, module_setting_key(mid))
        if raw is None or raw == "":
            continue
        out[mid] = bool(raw) if isinstance(raw, bool) else str(raw).lower() in (
            "1", "true", "yes", "on"
        )
    return out


def apply_accounting_mode_bundle(session, company_id: int, mode: str) -> None:
    if mode not in ACCOUNTING_MODE_BUNDLES:
        raise ValueError(f"Unknown accounting mode: {mode}")
    set_setting(session, WIZARD_SETTING_ACCOUNTING_MODE, mode, company_id=company_id)
    for policy_key, value in ACCOUNTING_MODE_BUNDLES[mode].items():
        set_company_setting(session, company_id, policy_key, value)


def apply_wizard_choices(
    session,
    company_id: int,
    *,
    vertical: str,
    accounting_mode: str,
    module_flags: dict[str, bool],
) -> None:
    valid_verticals = {v[0] for v in BUSINESS_TYPES}
    if vertical not in valid_verticals:
        raise ValueError(f"Unknown business type: {vertical}")
    if accounting_mode not in ACCOUNTING_MODE_BUNDLES:
        raise ValueError(f"Unknown accounting mode: {accounting_mode}")

    set_setting(session, WIZARD_SETTING_VERTICAL, vertical, company_id=company_id)
    apply_accounting_mode_bundle(session, company_id, accounting_mode)

    for mid in WIZARD_MODULE_IDS:
        enabled = bool(module_flags.get(mid, False))
        set_company_setting(
            session,
            company_id,
            module_setting_key(mid),
            enabled,
        )

    set_setting(session, WIZARD_SETTING_COMPLETED, True, company_id=company_id)


def get_wizard_summary(session, company_id: int) -> dict[str, Any]:
    return {
        "completed": is_wizard_complete(session, company_id),
        "vertical": get_setting(session, WIZARD_SETTING_VERTICAL, company_id=company_id),
        "accounting_mode": get_setting(
            session, WIZARD_SETTING_ACCOUNTING_MODE, company_id=company_id
        ),
        "modules": read_module_preferences(session, company_id),
    }


def wizard_module_labels() -> list[tuple[str, str, bool]]:
    """Return (id, label, is_planned) for wizard checkboxes."""
    labels = []
    for mid in WIZARD_MODULE_IDS:
        mod = get_module_def(mid)
        name = mid.replace("_", " ").title()
        if mod and mod.nav_page:
            name = mod.nav_page.split(" ", 1)[-1] if " " in mod.nav_page else mod.nav_page
        labels.append((mid, name, bool(mod.planned) if mod else True))
    return labels
