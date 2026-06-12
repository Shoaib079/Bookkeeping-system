"""UA-P1 — User access / effective permissions service layer.

FastAPI-ready: explicit company_id and user_id, serializable DTOs, no Streamlit or app.py.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from typing import Any, Literal

from models import AuditLog, CompanyUser, UserPermissionOverride
from sqlalchemy.orm import Session

OverrideMode = Literal["grant", "deny"]

MANAGE_PERMISSIONS_KEY = "manage_permissions"

# Legacy role matrix — seed for PERMISSION_TEMPLATES (mirrors app.py _PERMISSIONS).
LEGACY_PERMISSION_MATRIX: dict[str, frozenset[str]] = {
    "create_transaction": frozenset({"owner", "manager", "cashier"}),
    "edit_transaction": frozenset({"owner", "manager"}),
    "void_transaction": frozenset({"owner", "manager"}),
    "create_customer_vendor": frozenset({"owner", "manager", "cashier"}),
    "edit_customer_vendor": frozenset({"owner", "manager"}),
    "manage_inventory": frozenset({"owner", "manager"}),
    "manage_banking": frozenset({"owner", "manager"}),
    "post_manual_journal": frozenset({"owner", "manager"}),
    "close_fiscal_period": frozenset({"owner", "manager"}),
    "manage_budget": frozenset({"owner", "manager"}),
    "manage_categories": frozenset({"owner", "manager", "cashier"}),
    "manage_users": frozenset({"owner"}),
    "manage_settings": frozenset({"owner"}),
    "manage_backup": frozenset({"owner"}),
    "post_equity_movement": frozenset({"owner"}),
    "manage_recurring_templates": frozenset({"owner", "manager"}),
    "post_recurring_draft": frozenset({"owner", "manager", "cashier"}),
    "create_reconciliation": frozenset({"owner", "manager", "cashier"}),
    "submit_reconciliation": frozenset({"owner", "manager", "cashier"}),
    "approve_reconciliation": frozenset({"owner", "manager"}),
    "reject_reconciliation": frozenset({"owner", "manager"}),
    "void_reconciliation": frozenset({"owner"}),
    "view_reconciliation": frozenset({"owner", "manager", "cashier", "partner"}),
    "close_day": frozenset({"owner", "manager"}),
    "void_eod": frozenset({"owner"}),
    "view_eod": frozenset({"owner", "manager", "cashier", "partner"}),
    "view_external_sales_verification": frozenset({"owner", "manager"}),
    "verify_external_sales": frozenset({"owner", "manager"}),
    "void_external_sales_verification": frozenset({"owner", "manager"}),
    "view_recipe_costing": frozenset({"owner", "manager"}),
    "manage_recipe_costing": frozenset({"owner", "manager"}),
    "view_management_reports": frozenset({"owner", "manager", "partner"}),
    "manage_partners": frozenset({"owner"}),
    "post_partner_movement": frozenset({"owner", "manager"}),
    "allocate_profit": frozenset({"owner"}),
    "void_partner_movement": frozenset({"owner"}),
    "void_profit_allocation": frozenset({"owner"}),
    "view_partner_accounts": frozenset({"owner", "manager", "partner"}),
    "manage_workers": frozenset({"owner", "manager"}),
    "post_worker_movement": frozenset({"owner", "manager"}),
    "void_worker_movement": frozenset({"owner"}),
    "view_workers": frozenset({"owner", "manager"}),
    "upload_attachment": frozenset({"owner", "manager", "cashier"}),
    "delete_attachment": frozenset({"owner", "manager"}),
    "view_attachment": frozenset({"owner", "manager", "cashier"}),
    "generate_document": frozenset({"owner", "manager", "cashier"}),
    "view_statement": frozenset({"owner", "manager", "partner"}),
    "import_bank_statement": frozenset({"owner", "manager"}),
    "view_bank_statement_import": frozenset({"owner", "manager", "cashier", "partner"}),
    "perform_year_end_close": frozenset({"owner"}),
    "void_year_end_close": frozenset({"owner"}),
    "view_year_end_close": frozenset({"owner", "manager", "partner"}),
}

OWNER_LOCKED_KEYS: frozenset[str] = frozenset(
    {
        MANAGE_PERMISSIONS_KEY,
        "manage_users",
        "manage_settings",
        "manage_backup",
        "post_equity_movement",
        "manage_partners",
        "allocate_profit",
        "void_partner_movement",
        "void_profit_allocation",
        "void_reconciliation",
        "void_eod",
        "void_worker_movement",
        "perform_year_end_close",
        "void_year_end_close",
    }
)

TEMPLATE_ROLES: tuple[str, ...] = (
    "owner",
    "manager",
    "accountant",
    "cashier",
    "staff",
    "viewer",
    "partner",
)


def _build_permission_templates() -> dict[str, frozenset[str]]:
    buckets: dict[str, set[str]] = {role: set() for role in TEMPLATE_ROLES}
    for key, roles in LEGACY_PERMISSION_MATRIX.items():
        for role in roles:
            if role in buckets:
                buckets[role].add(key)
    buckets["owner"].add(MANAGE_PERMISSIONS_KEY)
    return {role: frozenset(keys) for role, keys in buckets.items()}


PERMISSION_TEMPLATES: dict[str, frozenset[str]] = _build_permission_templates()


@dataclass(frozen=True)
class PermissionRegistryEntry:
    key: str
    category: str
    owner_locked: bool
    i18n_key: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "category": self.category,
            "owner_locked": self.owner_locked,
            "i18n_key": self.i18n_key,
        }


def _registry_category(key: str) -> str:
    if key.startswith("view_"):
        return "view"
    if key.startswith("manage_"):
        return "manage"
    if key.startswith("void_"):
        return "void"
    if key.startswith("approve_") or key.startswith("reject_"):
        return "approve"
    if key.startswith("post_") or key.startswith("create_") or key.startswith("submit_"):
        return "post"
    return "action"


def _build_permission_registry() -> dict[str, PermissionRegistryEntry]:
    keys = set(LEGACY_PERMISSION_MATRIX) | {MANAGE_PERMISSIONS_KEY}
    registry: dict[str, PermissionRegistryEntry] = {}
    for key in sorted(keys):
        registry[key] = PermissionRegistryEntry(
            key=key,
            category=_registry_category(key),
            owner_locked=key in OWNER_LOCKED_KEYS,
            i18n_key=f"perm.{key}",
        )
    return registry


PERMISSION_REGISTRY: dict[str, PermissionRegistryEntry] = _build_permission_registry()


@dataclass(frozen=True)
class PermissionOverrideView:
    id: int
    company_id: int
    user_id: int
    permission_key: str
    mode: str
    created_by_id: int | None
    created_at: datetime.datetime
    updated_at: datetime.datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "user_id": self.user_id,
            "permission_key": self.permission_key,
            "mode": self.mode,
            "created_by_id": self.created_by_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass(frozen=True)
class EffectivePermissionsView:
    company_id: int
    user_id: int
    role: str | None
    template_keys: frozenset[str]
    grants: frozenset[str]
    denies: frozenset[str]
    effective_keys: frozenset[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "user_id": self.user_id,
            "role": self.role,
            "template_keys": sorted(self.template_keys),
            "grants": sorted(self.grants),
            "denies": sorted(self.denies),
            "effective_keys": sorted(self.effective_keys),
        }


@dataclass(frozen=True)
class MutationResult:
    record_id: int | None
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.record_id is not None and not self.error

    def to_dict(self) -> dict[str, Any]:
        return {"record_id": self.record_id, "error": self.error, "ok": self.ok}


# ── Pure resolution ───────────────────────────────────────────────────────────


def resolve_effective_permissions(
    template_keys: frozenset[str],
    grants: frozenset[str],
    denies: frozenset[str],
    *,
    role: str | None,
) -> frozenset[str]:
    """template ∪ grants − denies; owner_locked grants stripped for non-owners."""
    effective = set(template_keys) | set(grants)
    effective -= set(denies)
    if role != "owner":
        effective -= set(OWNER_LOCKED_KEYS)
    return frozenset(effective)


def template_definition(role: str) -> frozenset[str]:
    return PERMISSION_TEMPLATES.get(role, frozenset())


def list_registry() -> list[PermissionRegistryEntry]:
    return [PERMISSION_REGISTRY[k] for k in sorted(PERMISSION_REGISTRY)]


# ── DB helpers ────────────────────────────────────────────────────────────────


def _membership_role(session: Session, company_id: int, user_id: int) -> str | None:
    row = (
        session.query(CompanyUser.role)
        .filter(
            CompanyUser.company_id == company_id,
            CompanyUser.user_id == user_id,
            CompanyUser.is_active.is_(True),
        )
        .first()
    )
    return row[0] if row else None


def _load_override_maps(
    session: Session,
    company_id: int,
    user_id: int,
) -> tuple[frozenset[str], frozenset[str]]:
    rows = (
        session.query(UserPermissionOverride)
        .filter(
            UserPermissionOverride.company_id == company_id,
            UserPermissionOverride.user_id == user_id,
        )
        .all()
    )
    grants: set[str] = set()
    denies: set[str] = set()
    for row in rows:
        if row.mode == "grant":
            grants.add(row.permission_key)
        elif row.mode == "deny":
            denies.add(row.permission_key)
    return frozenset(grants), frozenset(denies)


def _override_view(row: UserPermissionOverride) -> PermissionOverrideView:
    return PermissionOverrideView(
        id=row.id,
        company_id=row.company_id,
        user_id=row.user_id,
        permission_key=row.permission_key,
        mode=row.mode,
        created_by_id=row.created_by_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _write_audit(
    session: Session,
    *,
    company_id: int,
    action: str,
    entity_id: int,
    description: str,
    performed_by: str | None,
) -> None:
    session.add(
        AuditLog(
            timestamp=datetime.datetime.now(),
            action=action,
            entity_type="UserPermissionOverride",
            entity_id=entity_id,
            description=description,
            performed_by=performed_by,
            company_id=company_id,
        )
    )


def _active_owner_user_ids(session: Session, company_id: int) -> list[int]:
    rows = (
        session.query(CompanyUser.user_id)
        .filter(
            CompanyUser.company_id == company_id,
            CompanyUser.role == "owner",
            CompanyUser.is_active.is_(True),
        )
        .all()
    )
    return [r[0] for r in rows]


def _effective_with_adjustment(
    session: Session,
    company_id: int,
    user_id: int,
    *,
    adjust_key: str | None = None,
    adjust_mode: str | None = None,
    clear_all_overrides: bool = False,
) -> frozenset[str]:
    role = _membership_role(session, company_id, user_id)
    template = template_definition(role or "")
    if clear_all_overrides:
        grants: frozenset[str] = frozenset()
        denies: frozenset[str] = frozenset()
    else:
        grants, denies = _load_override_maps(session, company_id, user_id)
        if adjust_key is not None and adjust_mode is not None:
            g = set(grants)
            d = set(denies)
            g.discard(adjust_key)
            d.discard(adjust_key)
            if adjust_mode == "grant":
                g.add(adjust_key)
            elif adjust_mode == "deny":
                d.add(adjust_key)
            grants = frozenset(g)
            denies = frozenset(d)
    return resolve_effective_permissions(template, grants, denies, role=role)


def _would_violate_owner_lockout(
    session: Session,
    company_id: int,
    target_user_id: int,
    *,
    adjust_key: str | None = None,
    adjust_mode: str | None = None,
    clear_all_overrides: bool = False,
) -> bool:
    """Return True if the pending change leaves no active owner with manage_permissions."""
    owner_ids = _active_owner_user_ids(session, company_id)
    if not owner_ids:
        return False
    remaining = 0
    for owner_id in owner_ids:
        if owner_id == target_user_id:
            effective = _effective_with_adjustment(
                session,
                company_id,
                owner_id,
                adjust_key=adjust_key,
                adjust_mode=adjust_mode,
                clear_all_overrides=clear_all_overrides,
            )
        else:
            effective = effective_permissions(session, company_id, owner_id).effective_keys
        if MANAGE_PERMISSIONS_KEY in effective:
            remaining += 1
    return remaining == 0


def _validate_override_inputs(permission_key: str, mode: str) -> str | None:
    if permission_key not in PERMISSION_REGISTRY:
        return f"Unknown permission key: {permission_key}."
    if mode not in ("grant", "deny"):
        return "Override mode must be grant or deny."
    return None


# ── Public API ────────────────────────────────────────────────────────────────


def effective_permissions(
    session: Session,
    company_id: int,
    user_id: int,
    *,
    membership_role: str | None = None,
) -> EffectivePermissionsView:
    """Resolve template ∪ grants − denies for a user in a company.

    When *membership_role* is supplied (e.g. Streamlit session context), it is
    used for the template instead of re-querying CompanyUser — matching legacy
    _can() behaviour while still loading overrides from the database.
    """
    role = (
        membership_role
        if membership_role is not None
        else _membership_role(session, company_id, user_id)
    )
    template = template_definition(role or "")
    grants, denies = _load_override_maps(session, company_id, user_id)
    effective = resolve_effective_permissions(template, grants, denies, role=role)
    return EffectivePermissionsView(
        company_id=company_id,
        user_id=user_id,
        role=role,
        template_keys=template,
        grants=grants,
        denies=denies,
        effective_keys=effective,
    )


def has_permission(
    session: Session,
    company_id: int,
    user_id: int,
    permission_key: str,
) -> bool:
    if permission_key not in PERMISSION_REGISTRY:
        return False
    view = effective_permissions(session, company_id, user_id)
    return permission_key in view.effective_keys


def set_override(
    session: Session,
    company_id: int,
    target_user_id: int,
    permission_key: str,
    mode: OverrideMode,
    actor_user_id: int,
    *,
    performed_by: str | None = None,
) -> MutationResult:
    err = _validate_override_inputs(permission_key, mode)
    if err:
        return MutationResult(record_id=None, error=err)
    if _membership_role(session, company_id, target_user_id) is None:
        return MutationResult(record_id=None, error="User is not an active member of this company.")

    if permission_key == MANAGE_PERMISSIONS_KEY and mode == "deny":
        if _would_violate_owner_lockout(
            session,
            company_id,
            target_user_id,
            adjust_key=permission_key,
            adjust_mode=mode,
        ):
            return MutationResult(
                record_id=None,
                error="Cannot deny manage_permissions: no active owner would remain able to manage permissions.",
            )

    now = datetime.datetime.now()
    row = (
        session.query(UserPermissionOverride)
        .filter(
            UserPermissionOverride.company_id == company_id,
            UserPermissionOverride.user_id == target_user_id,
            UserPermissionOverride.permission_key == permission_key,
        )
        .first()
    )
    if row is None:
        row = UserPermissionOverride(
            company_id=company_id,
            user_id=target_user_id,
            permission_key=permission_key,
            mode=mode,
            created_by_id=actor_user_id,
            created_at=now,
            updated_at=None,
        )
        session.add(row)
    else:
        row.mode = mode
        row.updated_at = now

    session.flush()
    _write_audit(
        session,
        company_id=company_id,
        action="set_permission_override",
        entity_id=row.id,
        description=json.dumps(
            {
                "target_user_id": target_user_id,
                "permission_key": permission_key,
                "mode": mode,
            }
        ),
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=row.id)


def clear_override(
    session: Session,
    company_id: int,
    target_user_id: int,
    permission_key: str,
    actor_user_id: int,
    *,
    performed_by: str | None = None,
) -> MutationResult:
    if permission_key not in PERMISSION_REGISTRY:
        return MutationResult(record_id=None, error=f"Unknown permission key: {permission_key}.")

    row = (
        session.query(UserPermissionOverride)
        .filter(
            UserPermissionOverride.company_id == company_id,
            UserPermissionOverride.user_id == target_user_id,
            UserPermissionOverride.permission_key == permission_key,
        )
        .first()
    )
    if row is None:
        return MutationResult(record_id=0)

    row_id = row.id
    session.delete(row)
    session.flush()
    _write_audit(
        session,
        company_id=company_id,
        action="clear_permission_override",
        entity_id=row_id,
        description=json.dumps(
            {
                "target_user_id": target_user_id,
                "permission_key": permission_key,
            }
        ),
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=row_id)


def reset_to_template(
    session: Session,
    company_id: int,
    target_user_id: int,
    actor_user_id: int,
    *,
    performed_by: str | None = None,
) -> MutationResult:
    if _membership_role(session, company_id, target_user_id) is None:
        return MutationResult(record_id=None, error="User is not an active member of this company.")

    rows = (
        session.query(UserPermissionOverride)
        .filter(
            UserPermissionOverride.company_id == company_id,
            UserPermissionOverride.user_id == target_user_id,
        )
        .all()
    )
    count = len(rows)
    for row in rows:
        session.delete(row)
    session.flush()
    _write_audit(
        session,
        company_id=company_id,
        action="reset_permission_overrides",
        entity_id=target_user_id,
        description=json.dumps({"target_user_id": target_user_id, "cleared_count": count}),
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=target_user_id)
