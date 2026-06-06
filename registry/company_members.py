"""Company membership helpers — Phase 14D-E member management."""

from __future__ import annotations

import datetime

from models import CompanyUser, User

COMPANY_ROLES = ("owner", "manager", "partner", "cashier", "viewer")


def count_active_owners(session, company_id: int) -> int:
    return (
        session.query(CompanyUser)
        .filter(
            CompanyUser.company_id == company_id,
            CompanyUser.role == "owner",
            CompanyUser.is_active == True,
        )
        .count()
    )


def would_violate_last_owner_guard(
    session,
    company_id: int,
    membership: CompanyUser,
    *,
    new_role: str | None = None,
    new_active: bool | None = None,
) -> bool:
    """True if the change would leave the company with no active owner."""
    if membership.role != "owner":
        return False
    role = new_role if new_role is not None else membership.role
    active = new_active if new_active is not None else membership.is_active
    if role == "owner" and active:
        return False
    return count_active_owners(session, company_id) <= 1


def would_block_remove(session, company_id: int, membership: CompanyUser) -> bool:
    """True if removing this membership would leave no active owner."""
    if membership.role != "owner" or not membership.is_active:
        return False
    return count_active_owners(session, company_id) <= 1


def get_membership(session, company_id: int, user_id: int) -> CompanyUser | None:
    return (
        session.query(CompanyUser)
        .filter_by(company_id=company_id, user_id=user_id)
        .first()
    )


def add_existing_user_to_company(
    session,
    *,
    company_id: int,
    user: User,
    role: str,
    invited_by_id: int | None,
) -> CompanyUser:
    """Add a user to a company, or reactivate an inactive membership."""
    if role not in COMPANY_ROLES:
        raise ValueError(f"Invalid role: {role}")
    existing = get_membership(session, company_id, user.id)
    if existing:
        if existing.is_active:
            raise ValueError(f"'{user.username}' is already a member of this company.")
        existing.role = role
        existing.is_active = True
        if invited_by_id is not None:
            existing.invited_by_id = invited_by_id
        return existing
    now = datetime.datetime.now(datetime.timezone.utc)
    membership = CompanyUser(
        company_id=company_id,
        user_id=user.id,
        role=role,
        is_active=True,
        created_at=now,
        invited_by_id=invited_by_id,
    )
    session.add(membership)
    return membership


def create_user_for_company(
    session,
    *,
    company_id: int,
    username: str,
    display_name: str,
    password_hash: str,
    role: str,
    invited_by_id: int | None,
) -> tuple[User, CompanyUser]:
    if role not in COMPANY_ROLES:
        raise ValueError(f"Invalid role: {role}")
    if session.query(User).filter_by(username=username).first():
        raise ValueError(f"Username '{username}' already exists.")
    user = User(
        username=username,
        display_name=display_name,
        password_hash=password_hash,
        role="viewer",
        is_active=True,
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    session.add(user)
    session.flush()
    membership = add_existing_user_to_company(
        session,
        company_id=company_id,
        user=user,
        role=role,
        invited_by_id=invited_by_id,
    )
    return user, membership


def update_membership(
    session,
    company_id: int,
    membership: CompanyUser,
    *,
    role: str,
    is_active: bool,
) -> None:
    if role not in COMPANY_ROLES:
        raise ValueError(f"Invalid role: {role}")
    if membership.company_id != company_id:
        raise ValueError("Membership does not belong to this company.")
    if would_violate_last_owner_guard(
        session, company_id, membership, new_role=role, new_active=is_active
    ):
        raise ValueError(
            "Cannot demote or deactivate the last active owner for this company."
        )
    membership.role = role
    membership.is_active = is_active


def remove_membership(session, company_id: int, membership: CompanyUser) -> None:
    if membership.company_id != company_id:
        raise ValueError("Membership does not belong to this company.")
    if would_block_remove(session, company_id, membership):
        raise ValueError("Cannot remove the last active owner for this company.")
    session.delete(membership)
