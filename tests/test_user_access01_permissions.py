"""UA-P1 tests — user access effective permissions."""

from __future__ import annotations

import datetime
import inspect
import json
import pathlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from services import user_access as ua

SERVICE_PATH = pathlib.Path(ua.__file__)


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        co_a = models.Company(
            name="Co A",
            slug="co_a",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        co_b = models.Company(
            name="Co B",
            slug="co_b",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        owner = models.User(
            username="owner",
            display_name="Owner",
            password_hash="x",
            role="owner",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        manager = models.User(
            username="mgr",
            display_name="Mgr",
            password_hash="x",
            role="manager",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add_all([co_a, co_b, owner, manager])
        s.commit()
        yield s, co_a.id, co_b.id, owner.id, manager.id


def _membership(session, company_id, user_id, role, *, is_active=True):
    session.add(
        models.CompanyUser(
            company_id=company_id,
            user_id=user_id,
            role=role,
            is_active=is_active,
            created_at=datetime.datetime.now(),
        )
    )
    session.commit()


class TestPureResolution:
    def test_template_only(self):
        effective = ua.resolve_effective_permissions(
            frozenset({"a", "b"}),
            frozenset(),
            frozenset(),
            role="manager",
        )
        assert effective == frozenset({"a", "b"})

    def test_grant_adds(self):
        effective = ua.resolve_effective_permissions(
            frozenset({"a"}),
            frozenset({"b"}),
            frozenset(),
            role="manager",
        )
        assert effective == frozenset({"a", "b"})

    def test_deny_removes(self):
        effective = ua.resolve_effective_permissions(
            frozenset({"a", "b"}),
            frozenset(),
            frozenset({"b"}),
            role="manager",
        )
        assert effective == frozenset({"a"})

    def test_deny_beats_grant(self):
        effective = ua.resolve_effective_permissions(
            frozenset({"a"}),
            frozenset({"b"}),
            frozenset({"b"}),
            role="manager",
        )
        assert "b" not in effective

    def test_owner_locked_grant_ignored_for_non_owner(self):
        effective = ua.resolve_effective_permissions(
            frozenset(),
            frozenset({ua.MANAGE_PERMISSIONS_KEY}),
            frozenset(),
            role="manager",
        )
        assert ua.MANAGE_PERMISSIONS_KEY not in effective


class TestHasPermission:
    def test_unknown_key_false(self, session):
        db, company_id, _, owner_id, _ = session
        _membership(db, company_id, owner_id, "owner")
        assert ua.has_permission(db, company_id, owner_id, "not_a_real_permission") is False

    def test_template_only_manager(self, session):
        db, company_id, _, _, manager_id = session
        _membership(db, company_id, manager_id, "manager")
        assert ua.has_permission(db, company_id, manager_id, "create_transaction")
        assert not ua.has_permission(db, company_id, manager_id, "manage_users")

    def test_grant_adds_permission(self, session):
        db, company_id, _, _, manager_id = session
        _membership(db, company_id, manager_id, "manager")
        ua.set_override(
            db,
            company_id,
            manager_id,
            "manage_budget",
            "grant",
            manager_id,
        )
        assert ua.has_permission(db, company_id, manager_id, "manage_budget")

    def test_owner_locked_grant_ignored(self, session):
        db, company_id, _, _, manager_id = session
        _membership(db, company_id, manager_id, "manager")
        ua.set_override(
            db,
            company_id,
            manager_id,
            "manage_users",
            "grant",
            manager_id,
        )
        assert not ua.has_permission(db, company_id, manager_id, "manage_users")

    def test_deny_removes_permission(self, session):
        db, company_id, _, owner_id, manager_id = session
        _membership(db, company_id, manager_id, "manager")
        ua.set_override(
            db,
            company_id,
            manager_id,
            "create_transaction",
            "deny",
            owner_id,
        )
        assert not ua.has_permission(db, company_id, manager_id, "create_transaction")

    def test_company_isolation(self, session):
        db, company_a, company_b, owner_id, _ = session
        _membership(db, company_a, owner_id, "owner")
        _membership(db, company_b, owner_id, "manager")
        ua.set_override(
            db,
            company_a,
            owner_id,
            "create_transaction",
            "deny",
            owner_id,
        )
        assert not ua.has_permission(db, company_a, owner_id, "create_transaction")
        assert ua.has_permission(db, company_b, owner_id, "create_transaction")


class TestOwnerLockoutGuard:
    def test_reject_deny_manage_permissions_last_owner(self, session):
        db, company_id, _, owner_id, _ = session
        _membership(db, company_id, owner_id, "owner")
        result = ua.set_override(
            db,
            company_id,
            owner_id,
            ua.MANAGE_PERMISSIONS_KEY,
            "deny",
            owner_id,
        )
        assert not result.ok
        assert "manage_permissions" in result.error

    def test_allow_deny_manage_permissions_when_second_owner(self, session):
        db, company_id, _, owner_id, manager_id = session
        _membership(db, company_id, owner_id, "owner")
        _membership(db, company_id, manager_id, "owner")
        result = ua.set_override(
            db,
            company_id,
            owner_id,
            ua.MANAGE_PERMISSIONS_KEY,
            "deny",
            manager_id,
        )
        assert result.ok
        assert ua.has_permission(db, company_id, manager_id, ua.MANAGE_PERMISSIONS_KEY)


class TestOverrideLifecycle:
    def test_set_flip_clear_reset(self, session):
        db, company_id, _, owner_id, manager_id = session
        _membership(db, company_id, manager_id, "manager")

        created = ua.set_override(
            db, company_id, manager_id, "manage_budget", "grant", owner_id
        )
        assert created.ok
        assert ua.has_permission(db, company_id, manager_id, "manage_budget")

        flipped = ua.set_override(
            db, company_id, manager_id, "manage_budget", "deny", owner_id
        )
        assert flipped.ok
        assert not ua.has_permission(db, company_id, manager_id, "manage_budget")

        cleared = ua.clear_override(
            db, company_id, manager_id, "manage_budget", owner_id
        )
        assert cleared.ok
        assert ua.has_permission(db, company_id, manager_id, "manage_budget")

        ua.set_override(db, company_id, manager_id, "close_day", "deny", owner_id)
        reset = ua.reset_to_template(db, company_id, manager_id, owner_id)
        assert reset.ok
        assert ua.has_permission(db, company_id, manager_id, "close_day")

    def test_audit_log_on_set(self, session):
        db, company_id, _, owner_id, manager_id = session
        _membership(db, company_id, manager_id, "manager")
        ua.set_override(
            db, company_id, manager_id, "manage_budget", "grant", owner_id
        )
        row = (
            db.query(models.AuditLog)
            .filter(
                models.AuditLog.company_id == company_id,
                models.AuditLog.entity_type == "UserPermissionOverride",
            )
            .first()
        )
        assert row is not None
        assert row.action == "set_permission_override"


class TestBackwardCompatibility:
    def test_legacy_matrix_matches_has_permission(self, session):
        db, company_id, _, owner_id, manager_id = session
        cashier = models.User(
            username="cash",
            display_name="Cash",
            password_hash="x",
            role="cashier",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        partner = models.User(
            username="part",
            display_name="Part",
            password_hash="x",
            role="partner",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        db.add(cashier)
        db.add(partner)
        db.commit()
        _membership(db, company_id, owner_id, "owner")
        _membership(db, company_id, manager_id, "manager")
        _membership(db, company_id, cashier.id, "cashier")
        _membership(db, company_id, partner.id, "partner")
        users = {
            "owner": owner_id,
            "manager": manager_id,
            "cashier": cashier.id,
            "partner": partner.id,
        }
        for key, roles in ua.LEGACY_PERMISSION_MATRIX.items():
            for role in ("owner", "manager", "cashier", "partner"):
                uid = users[role]
                expected = role in roles
                actual = ua.has_permission(db, company_id, uid, key)
                assert actual == expected, f"{key}/{role}"

    def test_app_permissions_dict_matches_legacy_matrix(self):
        import app

        for key, roles in ua.LEGACY_PERMISSION_MATRIX.items():
            assert app._PERMISSIONS[key] == set(roles)


class TestRegistryAndTemplates:
    def test_list_registry_contains_legacy_keys(self):
        keys = {entry.key for entry in ua.list_registry()}
        assert "create_transaction" in keys
        assert ua.MANAGE_PERMISSIONS_KEY in keys

    def test_owner_template_has_manage_permissions(self):
        assert ua.MANAGE_PERMISSIONS_KEY in ua.template_definition("owner")

    def test_no_dotted_keys(self):
        for key in ua.PERMISSION_REGISTRY:
            assert "." not in key


class TestMigrationReadiness:
    FORBIDDEN_IMPORT_TOKENS = (
        "import streamlit",
        "from streamlit",
        "import app",
        "from app",
    )

    def test_service_imports_no_streamlit_or_app(self):
        source = SERVICE_PATH.read_text(encoding="utf-8")
        for token in self.FORBIDDEN_IMPORT_TOKENS:
            assert token not in source

    def test_public_api_explicit_company_id(self):
        db_funcs = (
            ua.effective_permissions,
            ua.has_permission,
            ua.set_override,
            ua.clear_override,
            ua.reset_to_template,
        )
        for fn in db_funcs:
            params = list(inspect.signature(fn).parameters)
            assert params[1] == "company_id", fn.__name__

    def test_dto_to_dict_json_safe(self):
        view = ua.EffectivePermissionsView(
            company_id=1,
            user_id=2,
            role="manager",
            template_keys=frozenset({"a"}),
            grants=frozenset(),
            denies=frozenset(),
            effective_keys=frozenset({"a"}),
        )
        json.dumps(view.to_dict())
        assert ua.MutationResult(record_id=1).to_dict()["ok"] is True
