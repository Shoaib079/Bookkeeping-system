"""FASTAPI-REACT-40 — read-only permission overview DTOs and compute."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from services import user_access as ua_svc


@dataclass(frozen=True, slots=True)
class PermissionMemberRow:
    user_id: int
    username: str
    display_name: str
    role: str
    company_id: int


@dataclass(frozen=True, slots=True)
class PermissionMembersPage:
    rows: tuple[PermissionMemberRow, ...]
    row_count: int
    company_id: int


@dataclass(frozen=True, slots=True)
class PermissionProvenanceRow:
    permission_key: str
    in_template: bool
    is_grant: bool
    is_deny: bool
    is_effective: bool


@dataclass(frozen=True, slots=True)
class EffectivePermissionsPage:
    user_id: int
    role: str | None
    template_count: int
    grant_count: int
    deny_count: int
    effective_count: int
    rows: tuple[PermissionProvenanceRow, ...]
    company_id: int


def compute_permission_members_page(
    session: Session,
    *,
    company_id: int,
) -> PermissionMembersPage:
    members = ua_svc.list_active_members(session, company_id)
    rows = tuple(
        PermissionMemberRow(
            user_id=member.user_id,
            username=member.username,
            display_name=member.display_name,
            role=member.role,
            company_id=company_id,
        )
        for member in members
    )
    return PermissionMembersPage(
        rows=rows,
        row_count=len(rows),
        company_id=company_id,
    )


def compute_effective_permissions_page(
    session: Session,
    *,
    company_id: int,
    user_id: int,
) -> EffectivePermissionsPage:
    view = ua_svc.effective_permissions(session, company_id, user_id)
    keys = sorted(
        view.template_keys | view.grants | view.denies | view.effective_keys
    )
    rows = tuple(
        PermissionProvenanceRow(
            permission_key=key,
            in_template=key in view.template_keys,
            is_grant=key in view.grants,
            is_deny=key in view.denies,
            is_effective=key in view.effective_keys,
        )
        for key in keys
    )
    return EffectivePermissionsPage(
        user_id=user_id,
        role=view.role,
        template_count=len(view.template_keys),
        grant_count=len(view.grants),
        deny_count=len(view.denies),
        effective_count=len(view.effective_keys),
        rows=rows,
        company_id=company_id,
    )
