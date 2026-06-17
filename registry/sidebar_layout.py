"""UI-SYSTEM-02-S3 — desktop sidebar presentation layout (frozen render order).

Routes and dispatch are unchanged. This module owns **visual render sequence only** —
which direct pages and accordion groups appear, and under which section headers.
Order intentionally differs from ``build_nav_direct_pages()`` sidebar_direct_order
(e.g. Banking sits in Daily work, not after Inventory).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from registry.nav_keys import (
    NAV_BANKING,
    NAV_HOME,
    NAV_INVENTORY,
    NAV_NEW_TRANSACTION,
    NAV_REPORTS,
    NAV_TXN_LEDGER,
)
from registry.nav_group_hints import NAV_GROUP_HINTS
from registry.navigation import NAV_ACCORDION_GROUPS

SidebarItemKind = Literal["direct", "accordion"]


@dataclass(frozen=True)
class SidebarLayoutItem:
    kind: SidebarItemKind
    key: str
    hint_i18n: str | None = None


@dataclass(frozen=True)
class SidebarLayoutSection:
    section_i18n: str | None
    items: tuple[SidebarLayoutItem, ...]


# Frozen desktop sidebar sequence (UI-SYSTEM-02-S3). Do not reorder without contract test update.
SIDEBAR_LAYOUT: tuple[SidebarLayoutSection, ...] = (
    SidebarLayoutSection(
        None,
        (
            SidebarLayoutItem("direct", NAV_HOME),
            SidebarLayoutItem("direct", NAV_NEW_TRANSACTION),
            SidebarLayoutItem("direct", NAV_TXN_LEDGER),
        ),
    ),
    SidebarLayoutSection(
        "nav.sidebar.section_work",
        (
            SidebarLayoutItem("accordion", "transactions"),
            SidebarLayoutItem("direct", NAV_BANKING),
            SidebarLayoutItem("accordion", "people"),
            SidebarLayoutItem("direct", NAV_INVENTORY),
            SidebarLayoutItem("accordion", "recipe_costing"),
        ),
    ),
    SidebarLayoutSection(
        "nav.sidebar.section_reports",
        (
            SidebarLayoutItem("accordion", "statements"),
            SidebarLayoutItem("direct", NAV_REPORTS),
            SidebarLayoutItem("accordion", "close_day", hint_i18n=NAV_GROUP_HINTS["close_day"]),
        ),
    ),
    SidebarLayoutSection(
        "nav.sidebar.section_advanced",
        (
            SidebarLayoutItem("accordion", "accounting", hint_i18n=NAV_GROUP_HINTS["accounting"]),
            SidebarLayoutItem("accordion", "team"),
            SidebarLayoutItem("accordion", "settings"),
        ),
    ),
)


def build_nav_group_keys() -> dict[str, str]:
    """Derive accordion group i18n keys from ``NAV_ACCORDION_GROUPS``."""
    return {g.group_key: g.label_i18n for g in NAV_ACCORDION_GROUPS}


def flatten_sidebar_layout_keys() -> list[tuple[str, str]]:
    """Flatten layout to (kind, key) pairs for parity tests."""
    rows: list[tuple[str, str]] = []
    for section in SIDEBAR_LAYOUT:
        if section.section_i18n:
            rows.append(("section", section.section_i18n))
        for item in section.items:
            rows.append((item.kind, item.key))
    return rows


def validate_sidebar_layout() -> None:
    """Guardrail: layout references only known accordion groups."""
    group_keys = {g.group_key for g in NAV_ACCORDION_GROUPS}
    for section in SIDEBAR_LAYOUT:
        for item in section.items:
            if item.kind == "accordion" and item.key not in group_keys:
                raise ValueError(f"Unknown accordion group in sidebar layout: {item.key!r}")
            if item.hint_i18n and item.kind == "accordion":
                if item.key not in NAV_GROUP_HINTS and item.hint_i18n not in NAV_GROUP_HINTS.values():
                    pass  # hint may be inline for close_day/accounting


__all__ = (
    "SIDEBAR_LAYOUT",
    "SidebarLayoutItem",
    "SidebarLayoutSection",
    "build_nav_group_keys",
    "flatten_sidebar_layout_keys",
    "validate_sidebar_layout",
)
