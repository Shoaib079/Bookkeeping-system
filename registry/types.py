"""Registry type definitions — Phase 14D-B2a."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Scope = Literal["system", "company", "user"]
SettingType = Literal[
    "string",
    "text",
    "email",
    "phone",
    "int",
    "float",
    "percent",
    "bool",
    "enum",
    "policy_level",
    "accounting_mode",
    "currency_code",
    "timezone",
    "date_format",
    "number_format",
    "language_code",
    "module_ref",
]
SettingGroup = Literal[
    "setup",
    "company",
    "accounting",
    "banking",
    "policy",
    "preferences",
    "workspace",
    "system",
]
ModuleGroup = Literal[
    "operations",
    "crm",
    "accounting",
    "administration",
    "reporting",
    "planned",
]
StorageKind = Literal[
    "company_column",
    "company_setting",
    "app_setting",
    "virtual",
]
LockLevel = Literal["allow", "warn", "block"]


@dataclass(frozen=True)
class LockRules:
    after_first_post: LockLevel = "allow"
    after_year_end_close: LockLevel = "allow"
    after_first_fx_transaction: LockLevel = "allow"
    after_first_tax_invoice: LockLevel = "allow"


@dataclass(frozen=True)
class SettingDef:
    key: str
    scope: Scope
    type: SettingType
    group: SettingGroup
    label_key: str
    default: Any = None
    storage: StorageKind = "virtual"
    legacy_key: str | None = None
    company_column: str | None = None
    options: tuple[str, ...] = ()
    lock: LockRules = field(default_factory=LockRules)
    dangerous_after_transactions: bool = False
    audit: bool = True
    enforce_in: tuple[str, ...] = ()
    planned: bool = False
    description: str = ""


@dataclass(frozen=True)
class ModuleDef:
    id: str
    label_key: str
    group: ModuleGroup
    nav_page: str | None = None
    company_toggleable: bool = False
    user_hideable: bool = True
    entitlement: str = "core"
    planned: bool = False
    dependencies: tuple[str, ...] = ()
    description: str = ""
