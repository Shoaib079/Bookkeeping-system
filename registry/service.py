"""Registry read/write helpers — Phase 14D-B2a reads; 14D-B2b guarded writes."""

from __future__ import annotations

import datetime
from typing import Any

from models import AppSetting, Company, CompanySetting, JournalEntry
from registry.loader import get_module_def, get_setting_def, list_modules, list_settings
from sqlalchemy import func


class SettingLockError(Exception):
    """Raised when a setting change is blocked or needs explicit confirmation."""

    def __init__(
        self,
        key: str,
        *,
        level: str,
        reason: str | None,
        message: str,
    ) -> None:
        self.key = key
        self.level = level
        self.reason = reason
        self.message = message
        super().__init__(message)


def _coerce_value(defn, raw: Any) -> Any:
    if raw is None:
        return defn.default
    if defn.type in ("int",):
        try:
            return int(raw)
        except (TypeError, ValueError):
            return defn.default
    if defn.type in ("float", "percent"):
        try:
            return float(raw)
        except (TypeError, ValueError):
            return defn.default
    if defn.type == "bool":
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in ("1", "true", "yes", "on")
    return raw


def _read_company_setting_row(session, company_id: int, storage_key: str) -> str | None:
    row = (
        session.query(CompanySetting)
        .filter_by(company_id=company_id, key=storage_key)
        .first()
    )
    return row.value if row else None


def _setting_storage_key(defn) -> str:
    return defn.legacy_key or defn.key


def get_company_milestones(session, company_id: int) -> dict[str, datetime.datetime | None]:
    """Detect company lifecycle milestones used by setting lock rules."""
    min_entry_date = (
        session.query(func.min(JournalEntry.entry_date))
        .filter(JournalEntry.company_id == company_id)
        .scalar()
    )
    first_posted_at: datetime.datetime | None = None
    if min_entry_date is not None:
        if isinstance(min_entry_date, datetime.datetime):
            first_posted_at = min_entry_date
        else:
            first_posted_at = datetime.datetime.combine(
                min_entry_date, datetime.time.min
            )
    return {
        "first_posted_at": first_posted_at,
        "first_fx_transaction_at": None,
        "first_tax_invoice_at": None,
    }


def lock_user_message(key: str, result: dict, locale: str | None = None) -> str:
    """Plain-language lock message for UI (EN/TR via registry.i18n)."""
    from registry.i18n import t

    defn = get_setting_def(key)
    setting_label = t(defn.label_key, locale) if defn else key
    level = result.get("level") or "block"
    reason = result.get("reason") or "locked"
    msg_key = f"registry.lock.{level}.{reason}"
    text = t(msg_key, locale)
    if text == msg_key:
        text = t("registry.lock.generic", locale, setting=setting_label, level=level)
    elif "{setting}" in text:
        text = text.format(setting=setting_label)
    return text


def set_company_setting(session, company_id: int, key: str, value: Any) -> None:
    """Upsert a CompanySetting row by key (registry key or legacy key)."""
    if isinstance(value, bool):
        str_val = "true" if value else "false"
    elif value is None:
        str_val = ""
    else:
        str_val = str(value)
    row = (
        session.query(CompanySetting)
        .filter_by(company_id=company_id, key=key)
        .first()
    )
    if row:
        row.value = str_val
    else:
        session.add(CompanySetting(company_id=company_id, key=key, value=str_val))


def _evaluate_change_lock(key: str, *, milestones: dict) -> dict | None:
    """Return lock result only when change must be blocked; warn is advisory only."""
    result = evaluate_lock(key, milestones=milestones)
    if result["allowed"]:
        return None
    return result


def set_setting(
    session,
    key: str,
    value: Any,
    *,
    company_id: int | None = None,
    user_id: int | None = None,
    check_locks: bool = True,
    locale: str | None = None,
) -> None:
    """Write one registry-backed setting (company or user scope)."""
    defn = get_setting_def(key)
    if defn is None:
        raise KeyError(f"Unknown registry setting key: {key}")

    if check_locks and defn.scope == "company" and company_id is not None:
        current = get_setting(session, key, company_id=company_id, user_id=user_id)
        new_val = _coerce_value(defn, value)
        if new_val != current:
            milestones = get_company_milestones(session, company_id)
            lock = _evaluate_change_lock(key, milestones=milestones)
            if lock is not None:
                raise SettingLockError(
                    key,
                    level=lock["level"],
                    reason=lock.get("reason"),
                    message=lock_user_message(key, lock, locale),
                )

    if defn.scope == "company":
        if company_id is None:
            raise ValueError(f"company_id required for company setting {key}")
        if defn.storage == "company_column" and defn.company_column:
            company = session.get(Company, company_id)
            if company is None:
                raise ValueError(f"Company {company_id} not found")
            setattr(company, defn.company_column, value)
            return
        set_company_setting(session, company_id, _setting_storage_key(defn), value)
        return

    if defn.scope == "user":
        if user_id is None:
            raise ValueError(f"user_id required for user setting {key}")
        if defn.storage == "app_setting" and defn.legacy_key:
            pref_key = f"user_pref_{user_id}_{defn.legacy_key}"
            row = session.get(AppSetting, pref_key)
            str_val = str(value)
            if row:
                row.value = str_val
            else:
                session.add(AppSetting(key=pref_key, value=str_val))
        return

    raise ValueError(f"Cannot set setting {key} with scope {defn.scope}")


def save_company_settings_batch(
    session,
    company_id: int,
    changes: dict[str, Any],
    *,
    locale: str | None = None,
) -> None:
    """Validate locks for all changes, then write via set_setting (14D-B2b)."""
    milestones = get_company_milestones(session, company_id)

    for key, value in changes.items():
        defn = get_setting_def(key)
        if defn is None:
            raise KeyError(f"Unknown registry setting key: {key}")
        current = get_setting(session, key, company_id=company_id)
        if _coerce_value(defn, value) == current:
            continue
        lock = _evaluate_change_lock(key, milestones=milestones)
        if lock is not None:
            raise SettingLockError(
                key,
                level=lock["level"],
                reason=lock.get("reason"),
                message=lock_user_message(key, lock, locale),
            )

    for key, value in changes.items():
        set_setting(
            session,
            key,
            value,
            company_id=company_id,
            check_locks=False,
        )


def get_setting(
    session,
    key: str,
    *,
    company_id: int | None = None,
    user_id: int | None = None,
) -> Any:
    """Read one setting value using registry metadata.

    Falls back to registry default when storage is virtual/planned or row missing.
    Does not call load_settings() — reads ORM directly to avoid Streamlit coupling.
    """
    defn = get_setting_def(key)
    if defn is None:
        raise KeyError(f"Unknown registry setting key: {key}")

    if defn.scope == "company":
        if company_id is None:
            raise ValueError(f"company_id required for company setting {key}")
        company = session.get(Company, company_id)
        if defn.storage == "company_column" and defn.company_column and company:
            raw = getattr(company, defn.company_column, None)
            return _coerce_value(defn, raw if raw is not None else defn.default)
        if defn.storage == "company_setting":
            raw = _read_company_setting_row(
                session, company_id, _setting_storage_key(defn)
            )
            if raw is None:
                return defn.default
            return _coerce_value(defn, raw)
        raw = _read_company_setting_row(session, company_id, defn.key)
        if raw is not None:
            return _coerce_value(defn, raw)
        return defn.default

    if defn.scope == "user":
        if user_id is None:
            raise ValueError(f"user_id required for user setting {key}")
        if defn.storage == "app_setting" and defn.legacy_key:
            pref_key = f"user_pref_{user_id}_{defn.legacy_key}"
            row = session.get(AppSetting, pref_key)
            if row and row.value is not None:
                return _coerce_value(defn, row.value)
        return defn.default

    return defn.default


def get_effective_config(session, company_id: int, *, user_id: int | None = None) -> dict:
    """Resolved company settings + module catalog snapshot for support/debug."""
    settings_out: dict[str, Any] = {}
    for defn in list_settings(scope="company"):
        try:
            settings_out[defn.key] = get_setting(
                session, defn.key, company_id=company_id, user_id=user_id
            )
        except ValueError:
            settings_out[defn.key] = defn.default

    if user_id is not None:
        for defn in list_settings(scope="user"):
            settings_out[defn.key] = get_setting(
                session, defn.key, company_id=company_id, user_id=user_id
            )

    modules_out = []
    for mod in list_modules(planned=False):
        modules_out.append(
            get_module_state(
                mod.id, company_id=company_id, user_id=user_id, session=session
            )
        )

    milestones = get_company_milestones(session, company_id)
    return {
        "company_id": company_id,
        "user_id": user_id,
        "settings": settings_out,
        "modules": modules_out,
        "milestones": milestones,
    }


def get_company_setting(session, company_id: int, key: str, default: Any = None) -> Any:
    raw = _read_company_setting_row(session, company_id, key)
    if raw is None:
        return default
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    return raw


def get_module_state(
    module_id: str,
    *,
    company_id: int,
    user_id: int | None = None,
    session=None,
) -> dict:
    """Return module visibility state concepts (defaults only in 14D-B2a).

    Hidden / disabled / locked enforcement and DB tables come in later phases.
    """
    mod = get_module_def(module_id)
    if mod is None:
        raise KeyError(f"Unknown module id: {module_id}")

    entitled = True
    company_enabled = not mod.planned
    locked_disabled = mod.planned
    disabled_reason = "planned" if mod.planned else None

    pref_key = f"module.{module_id}.enabled"
    raw = (
        _read_company_setting_row(session, company_id, pref_key)
        if session is not None
        else None
    )
    if raw is not None:
        company_enabled = str(raw).lower() in ("1", "true", "yes", "on")
        locked_disabled = mod.planned
        if mod.planned and company_enabled:
            disabled_reason = "planned"
        elif not company_enabled:
            disabled_reason = "disabled_by_company"
            locked_disabled = True
        else:
            disabled_reason = None
            locked_disabled = False

    return {
        "module_id": mod.id,
        "label_key": mod.label_key,
        "group": mod.group,
        "nav_page": mod.nav_page,
        "entitled": entitled,
        "company_enabled": company_enabled,
        "company_nav_visible": company_enabled,
        "user_nav_hidden": False,
        "locked_disabled": locked_disabled,
        "disabled_reason": disabled_reason,
        "company_toggleable": mod.company_toggleable,
        "user_hideable": mod.user_hideable,
        "planned": mod.planned,
        "company_id": company_id,
        "user_id": user_id,
    }


def evaluate_lock(
    key: str,
    *,
    milestones: dict | None = None,
) -> dict:
    """Return lock evaluation metadata for a proposed setting change."""
    defn = get_setting_def(key)
    if defn is None:
        raise KeyError(key)
    milestones = milestones or {}
    result = {
        "key": key,
        "allowed": True,
        "level": "allow",
        "reason": None,
    }
    lock = defn.lock
    if milestones.get("first_posted_at") and lock.after_first_post != "allow":
        result["level"] = lock.after_first_post
        result["reason"] = "first_posted_at"
        if lock.after_first_post == "block":
            result["allowed"] = False
        elif lock.after_first_post == "warn":
            result["allowed"] = True
    if milestones.get("first_fx_transaction_at") and lock.after_first_fx_transaction == "block":
        result["allowed"] = False
        result["level"] = "block"
        result["reason"] = "first_fx_transaction_at"
    if milestones.get("first_tax_invoice_at") and lock.after_first_tax_invoice == "block":
        result["allowed"] = False
        result["level"] = "block"
        result["reason"] = "first_tax_invoice_at"
    return result
