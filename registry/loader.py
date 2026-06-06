"""Load and validate settings/module registry metadata."""

from __future__ import annotations

from registry.accounting_mode_bundles import ACCOUNTING_MODE_BUNDLES
from registry.modules_catalog import MODULES, NAV_PAGES_IN_APP
from registry.settings_catalog import (
    LEGACY_COMPANY_DIRECT_KEYS,
    LEGACY_COMPANY_SETTING_KEYS,
    SETTINGS,
)
from registry.types import ModuleDef, SettingDef

_VALID_SCOPES = frozenset({"system", "company", "user"})
_VALID_SETTING_TYPES = frozenset(
    {
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
    }
)
_CRITICAL_LOCK_KEYS = frozenset(
    {
        "accounting.base_currency",
        "accounting.fiscal_year_start_month",
        "accounting.multi_currency_enabled",
        "policy.vat_enabled",
    }
)

_settings_by_key: dict[str, SettingDef] | None = None
_modules_by_id: dict[str, ModuleDef] | None = None
_validated: bool = False


def _build_indexes() -> None:
    global _settings_by_key, _modules_by_id
    _settings_by_key = {s.key: s for s in SETTINGS}
    _modules_by_id = {m.id: m for m in MODULES}


def validate_registry() -> None:
    """Validate registry metadata. Raises ValueError on problems."""
    global _validated
    _build_indexes()
    assert _settings_by_key is not None and _modules_by_id is not None

    if len(_settings_by_key) != len(SETTINGS):
        raise ValueError("Duplicate setting keys in settings catalog")

    if len(_modules_by_id) != len(MODULES):
        raise ValueError("Duplicate module ids in modules catalog")

    for s in SETTINGS:
        if s.scope not in _VALID_SCOPES:
            raise ValueError(f"Invalid scope for {s.key}: {s.scope}")
        if s.type not in _VALID_SETTING_TYPES:
            raise ValueError(f"Invalid type for {s.key}: {s.type}")
        if s.storage == "company_column" and not s.company_column:
            raise ValueError(f"{s.key} uses company_column storage but company_column is missing")
        if s.storage == "company_setting" and not s.legacy_key:
            raise ValueError(f"{s.key} uses company_setting storage but legacy_key is missing")

    mapped_legacy_settings = {
        s.legacy_key for s in SETTINGS if s.storage == "company_setting" and s.legacy_key
    }
    if mapped_legacy_settings != LEGACY_COMPANY_SETTING_KEYS:
        missing = LEGACY_COMPANY_SETTING_KEYS - mapped_legacy_settings
        extra = mapped_legacy_settings - LEGACY_COMPANY_SETTING_KEYS
        if missing or extra:
            raise ValueError(
                f"Legacy CompanySetting key map mismatch. missing={missing} extra={extra}"
            )

    mapped_direct = {
        s.legacy_key for s in SETTINGS if s.storage == "company_column" and s.legacy_key
    }
    if mapped_direct != LEGACY_COMPANY_DIRECT_KEYS:
        missing = LEGACY_COMPANY_DIRECT_KEYS - mapped_direct
        extra = mapped_direct - LEGACY_COMPANY_DIRECT_KEYS
        if missing or extra:
            raise ValueError(
                f"Legacy Company direct key map mismatch. missing={missing} extra={extra}"
            )

    for key in _CRITICAL_LOCK_KEYS:
        s = _settings_by_key.get(key)
        if s is None:
            raise ValueError(f"Critical setting missing from registry: {key}")
        lock = s.lock
        if key == "accounting.base_currency":
            if lock.after_first_post != "block":
                raise ValueError(f"{key} must block after first post")
        if key == "accounting.fiscal_year_start_month":
            if lock.after_first_post != "block":
                raise ValueError(f"{key} must block after first post")
        if key == "accounting.multi_currency_enabled":
            if lock.after_first_fx_transaction != "block":
                raise ValueError(f"{key} must block disable after first FX transaction")
        if key == "policy.vat_enabled":
            if lock.after_first_tax_invoice != "block":
                raise ValueError(f"{key} must block disable after first tax invoice")

    for mode, bundle in ACCOUNTING_MODE_BUNDLES.items():
        for policy_key in bundle:
            if policy_key not in _settings_by_key:
                raise ValueError(f"Bundle {mode} references unknown setting {policy_key}")

    nav_mapped = {m.nav_page for m in MODULES if m.nav_page and not m.planned}
    unmapped_nav = NAV_PAGES_IN_APP - nav_mapped - {"📅 Today's Summary"}
    if unmapped_nav:
        raise ValueError(f"Nav pages missing module registry entries: {sorted(unmapped_nav)}")

    _validated = True


def _ensure_validated() -> None:
    if not _validated:
        validate_registry()


def list_settings(*, group: str | None = None, scope: str | None = None) -> list[SettingDef]:
    _ensure_validated()
    out = list(SETTINGS)
    if group is not None:
        out = [s for s in out if s.group == group]
    if scope is not None:
        out = [s for s in out if s.scope == scope]
    return out


def list_modules(*, planned: bool | None = None) -> list[ModuleDef]:
    _ensure_validated()
    if planned is None:
        return list(MODULES)
    return [m for m in MODULES if m.planned is planned]


def get_setting_def(key: str) -> SettingDef | None:
    _ensure_validated()
    assert _settings_by_key is not None
    return _settings_by_key.get(key)


def get_module_def(module_id: str) -> ModuleDef | None:
    _ensure_validated()
    assert _modules_by_id is not None
    return _modules_by_id.get(module_id)


def validate_on_load() -> None:
    """Called at app import to fail fast on invalid registry metadata."""
    validate_registry()
