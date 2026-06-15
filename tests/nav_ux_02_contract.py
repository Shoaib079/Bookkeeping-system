"""NAV-UX-02 — shared navigation contract helpers and constants."""

from __future__ import annotations

import ast
import inspect
from collections import defaultdict

import app as erp
from registry.nav_keys import (
    ALL_NAV_PAGE_KEYS,
    LEGACY_NAV_ALIASES,
    NAV_BANKING,
    NAV_EXPENSES,
    NAV_HOME,
    NAV_INVENTORY,
    NAV_MEMBERS,
    NAV_MY_ACCOUNT,
    NAV_NEW_TRANSACTION,
    NAV_PAYABLES,
    NAV_PROFIT_LOSS,
    NAV_RECEIVABLES,
    NAV_REPORTS,
    NAV_SALES,
    NAV_TXN_LEDGER,
)

# Documented hidden/orphan routes (audit §5) — empty after NAV-UX-02-S2 retirement.
KNOWN_HIDDEN: frozenset[str] = frozenset()

# Intentional multi-surface entry points (audit §3 duplicate_workflow).
DOCUMENTED_DUPLICATE_WORKFLOWS: dict[str, frozenset[str]] = {
    "banking": frozenset({NAV_BANKING}),
    "statements": frozenset(
        {erp.NAV_PROFIT_LOSS, erp.NAV_BALANCE_SHEET, erp.NAV_CASH_FLOW}
    ),
    "txn_ledger": frozenset({NAV_TXN_LEDGER}),
    "ar": frozenset({NAV_RECEIVABLES}),
    "ap": frozenset({NAV_PAYABLES}),
    "new_txn": frozenset({NAV_NEW_TRANSACTION}),
    "members": frozenset({NAV_MEMBERS}),
    "reports_shortcuts": frozenset({NAV_SALES, NAV_EXPENSES}),
}

DOCUMENTED_MULTI_SURFACE_PAGES = frozenset().union(*DOCUMENTED_DUPLICATE_WORKFLOWS.values())

# Desktop/mobile chrome parity — not duplicate workflows (audit §3).
NAV_SURFACE_PARITY_OK = frozenset({NAV_HOME})

# Dashboard/header programmatic navigation (not in sidebar tree).
DOCUMENTED_PROGRAMMATIC_NAV = frozenset(
    {
        NAV_RECEIVABLES,
        NAV_PAYABLES,
        NAV_INVENTORY,
        NAV_MY_ACCOUNT,
        NAV_TXN_LEDGER,
    }
)

# Documented role/purpose review flags (audit §5) — behavior not changed in S1.
DOCUMENTED_ROLE_PURPOSE_REVIEW = frozenset({erp.NAV_STAFF_EXPENSE_CAPTURE})

# Mobile hub non-page entry kinds → expected route targets.
MOBILE_HUB_ENTRY_TARGETS: dict[str, str] = {
    "banking_import": NAV_BANKING,
    "report_sales": NAV_REPORTS,
    "report_expenses": NAV_REPORTS,
}

DIALOG_FUNCTION_NAMES = frozenset(
    {
        "_vendor_add_dialog",
        "_vendor_manage_dialog",
        "_cat_add_dialog",
        "_cat_manage_dialog",
        "_subcat_add_dialog",
        "_subcat_manage_dialog",
    }
)


def page_dispatch_from_main() -> dict[str, str]:
    """Parse _PAGE_DISPATCH inside main() — keys and handler names."""
    source = inspect.getsource(erp.main)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_PAGE_DISPATCH":
                if not isinstance(node.value, ast.Dict):
                    continue
                out: dict[str, str] = {}
                for key_node, value_node in zip(node.value.keys, node.value.values):
                    key = None
                    if isinstance(key_node, ast.Constant):
                        key = key_node.value
                    elif isinstance(key_node, ast.Name):
                        key = getattr(erp, key_node.id, key_node.id)
                    if key is None:
                        continue
                    if isinstance(value_node, ast.Name):
                        out[key] = value_node.id
                    elif isinstance(value_node, ast.Attribute):
                        out[key] = value_node.attr
                    elif isinstance(value_node, ast.Lambda):
                        out[key] = "<lambda>"
                return out
    raise AssertionError("Could not find _PAGE_DISPATCH in main()")


def resolve_dispatch_handler(handler_name: str):
    """Return callable for a dispatch handler name."""
    if handler_name == "<lambda>":
        return erp.render_backup_restore
    return getattr(erp, handler_name)


def accordion_page_keys() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for group_key, _label, pages in erp._NAV_ACCORDION:
        for _icon, page_key in pages:
            rows.append((group_key, page_key))
    return rows


def mobile_hub_page_keys_flat() -> list[str]:
    keys: list[str] = []
    for _hub, entries in erp._MOBILE_HUB_CONFIG.items():
        for kind, payload, *_rest in entries:
            if kind == "page" and payload:
                keys.append(payload)
    return keys


def mobile_bottom_hub_targets() -> list[str]:
    return [
        payload
        for kind, payload, *_rest in erp._MOBILE_BOTTOM_NAV
        if kind == "hub"
    ]


def mobile_bottom_page_keys() -> frozenset[str]:
    return frozenset(
        payload
        for kind, payload, *_rest in erp._MOBILE_BOTTOM_NAV
        if kind in {"home", "new", "page"}
    )


def mobile_resolved_page_keys() -> set[str]:
    """Pages reachable via mobile hubs (includes accordion expansion)."""
    keys: set[str] = set()
    for hub_key in erp._MOBILE_HUB_CONFIG:
        keys.update(erp._mobile_hub_page_keys(hub_key, erp._NAV_ACCORDION_BY_KEY))
    keys.update(mobile_bottom_page_keys())
    return keys


def page_surface_map() -> dict[str, list[str]]:
    """Map each page key to named surfaces that expose it."""
    surfaces: dict[str, list[str]] = defaultdict(list)

    for page_key in erp._NAV_DIRECT_PAGES:
        surfaces[page_key].append("sidebar_direct")

    for group_key, page_key in accordion_page_keys():
        surfaces[page_key].append(f"accordion:{group_key}")

    for page_key in mobile_hub_page_keys_flat():
        surfaces[page_key].append("mobile_hub_page")

    for hub_key in erp._MOBILE_HUB_CONFIG:
        for page_key in erp._mobile_hub_page_keys(hub_key, erp._NAV_ACCORDION_BY_KEY):
            if page_key not in mobile_hub_page_keys_flat():
                surfaces[page_key].append(f"mobile_hub:{hub_key}")

    for page_key in mobile_bottom_page_keys():
        surfaces[page_key].append("mobile_bottom")

    for page_key in DOCUMENTED_PROGRAMMATIC_NAV:
        surfaces[page_key].append("programmatic")

    for role, pages in erp._NAV_ROLE_PAGES.items():
        for page_key in pages:
            tag = f"role:{role}"
            if tag not in surfaces[page_key]:
                surfaces[page_key].append(tag)

    return dict(surfaces)


def handler_has_meaningful_body(fn) -> bool:
    """Heuristic: render handler is not an empty stub."""
    try:
        source = inspect.getsource(fn)
    except (OSError, TypeError):
        return False
    stripped = source.strip()
    if len(stripped) < 80:
        return False
    body = stripped.split("\n", 1)[-1] if "\n" in stripped else ""
    normalized = body.replace(" ", "").replace("\n", "")
    return normalized not in {"pass", "...", "returnNone", "return"}
