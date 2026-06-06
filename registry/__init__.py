"""Phase 14D-B2a — Settings and module registry foundation."""

from registry.loader import (
    get_module_def,
    get_setting_def,
    list_modules,
    list_settings,
    validate_registry,
)
from registry.service import (
    SettingLockError,
    get_company_milestones,
    get_effective_config,
    get_module_state,
    get_setting,
    save_company_settings_batch,
    set_setting,
)

__all__ = [
    "get_setting_def",
    "get_module_def",
    "list_settings",
    "list_modules",
    "validate_registry",
    "get_setting",
    "set_setting",
    "get_company_milestones",
    "save_company_settings_batch",
    "SettingLockError",
    "get_effective_config",
    "get_module_state",
]
