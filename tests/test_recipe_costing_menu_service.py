"""RC-P2A service tests — menu items and profitability."""

from __future__ import annotations

import datetime
import inspect

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from services import recipe_costing as svc


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
        user = models.User(
            username="chef",
            display_name="Chef",
            password_hash="x",
            role="manager",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add_all([co_a, co_b, user])
        s.commit()
        yield s, co_a.id, co_b.id, user.id


def _ingredient(session, company_id, user_id, *, name="Flour", cost=0.002):
    result = svc.create_ingredient(
        session, company_id, name, "weight", "g", cost, user_id
    )
    assert result.ok, result.error
    return result.record_id


def _recipe(session, company_id, user_id, name="Bread", *, cost_ingredient=None):
    if cost_ingredient is None:
        ing_name = f"Ing-{name}"
        ing = _ingredient(session, company_id, user_id, name=ing_name)
    else:
        ing = cost_ingredient
    saved = svc.save_recipe(
        session,
        company_id,
        name,
        1.0,
        "each",
        [svc.RecipeLineInput(quantity=500, unit="g", ingredient_id=ing)],
        user_id,
    )
    assert saved.ok
    return saved.record_id


def _menu_item(session, company_id, user_id, name="Toast", recipe_id=None):
    rid = recipe_id or _recipe(session, company_id, user_id, name=f"Recipe-{name}")
    result = svc.create_menu_item(session, company_id, name, rid, user_id)
    assert result.ok
    return result.record_id


def _set_tax_rate(session, company_id, rate_pct: float):
    session.add(
        models.CompanySetting(company_id=company_id, key="tax_rate", value=str(rate_pct))
    )
    session.commit()


# ── Pure profitability math ───────────────────────────────────────────────────


class TestProfitabilityMath:
    def test_gross_to_net_with_tax(self):
        assert svc.gross_to_net_price(118.0, 18.0) == pytest.approx(100.0, rel=1e-3)

    def test_gross_to_net_zero_tax(self):
        assert svc.gross_to_net_price(50.0, 0.0) == 50.0

    def test_net_to_gross_round_trip(self):
        net = svc.gross_to_net_price(118.0, 18.0)
        gross = svc.net_to_gross_price(net, 18.0)
        assert gross == pytest.approx(118.0, rel=1e-3)

    def test_food_cost_and_markup(self):
        assert svc.compute_food_cost_pct(30.0, 100.0) == 30.0
        assert svc.compute_markup_pct(30.0, 100.0) == pytest.approx(233.33, rel=1e-2)

    def test_suggested_gross_for_target_food_cost(self):
        # cost 30, target 30% => net 100, tax 18% => gross 118
        suggested = svc.compute_suggested_gross_price(30.0, 30.0, 18.0)
        assert suggested == pytest.approx(118.0, rel=1e-3)

    def test_metrics_without_price_warns(self):
        view = svc.compute_menu_profitability_metrics(
            recipe_cost=10.0,
            selling_price_gross=None,
            tax_rate_pct=0.0,
        )
        assert "No selling price set." in view.warnings
        assert view.gross_profit is None


# ── Price history ─────────────────────────────────────────────────────────────


class TestMenuPriceHistory:
    def test_current_price_latest_effective(self, session):
        db, company_id, _, user_id = session
        menu_id = _menu_item(db, company_id, user_id)
        t0 = datetime.datetime(2026, 1, 1, 10, 0, 0)
        t1 = datetime.datetime(2026, 2, 1, 10, 0, 0)
        svc.set_menu_price(
            db, company_id, menu_id, 80.0, user_id, effective_at=t0
        )
        svc.set_menu_price(
            db, company_id, menu_id, 95.0, user_id, effective_at=t1
        )
        current = svc.get_current_menu_price(db, company_id, menu_id)
        assert current is not None
        assert current.price_gross == 95.0

    def test_current_price_as_of_past_date(self, session):
        db, company_id, _, user_id = session
        menu_id = _menu_item(db, company_id, user_id)
        t0 = datetime.datetime(2026, 1, 1, 10, 0, 0)
        t1 = datetime.datetime(2026, 3, 1, 10, 0, 0)
        svc.set_menu_price(
            db, company_id, menu_id, 80.0, user_id, effective_at=t0
        )
        svc.set_menu_price(
            db, company_id, menu_id, 95.0, user_id, effective_at=t1
        )
        as_of = datetime.datetime(2026, 2, 15, 12, 0, 0)
        current = svc.get_current_menu_price(
            db, company_id, menu_id, as_of=as_of
        )
        assert current is not None
        assert current.price_gross == 80.0


# ── Tax / net from company settings ───────────────────────────────────────────


class TestTaxNetCalculation:
    def test_compute_menu_profitability_uses_company_tax(self, session):
        db, company_id, _, user_id = session
        _set_tax_rate(db, company_id, 20.0)
        recipe_id = _recipe(db, company_id, user_id)
        menu_id = _menu_item(db, company_id, user_id, recipe_id=recipe_id)
        svc.set_menu_price(db, company_id, menu_id, 120.0, user_id)
        view = svc.compute_menu_profitability(db, company_id, menu_id)
        assert view is not None
        assert view.tax_rate_pct == 20.0
        assert view.selling_price_net == pytest.approx(100.0, rel=1e-3)
        assert view.recipe_cost == pytest.approx(1.0, rel=1e-3)
        assert view.gross_profit == pytest.approx(99.0, rel=1e-2)


# ── CRUD & isolation ──────────────────────────────────────────────────────────


class TestMenuItemService:
    def test_company_isolation(self, session):
        db, company_a, company_b, user_id = session
        recipe_a = _recipe(db, company_a, user_id, name="A Dish")
        menu_a = _menu_item(db, company_a, user_id, "Only A", recipe_a)
        assert svc.compute_menu_profitability(db, company_b, menu_a) is None
        assert svc.get_current_menu_price(db, company_b, menu_a) is None

    def test_inactive_item_still_computes_with_warning(self, session):
        db, company_id, _, user_id = session
        menu_id = _menu_item(db, company_id, user_id)
        svc.set_menu_price(db, company_id, menu_id, 50.0, user_id)
        svc.deactivate_menu_item(db, company_id, menu_id, user_id)
        view = svc.compute_menu_profitability(db, company_id, menu_id)
        assert view is not None
        assert view.is_active is False
        assert "Menu item is deactivated." in view.warnings

    def test_list_menu_profitability_active_only_default(self, session):
        db, company_id, _, user_id = session
        active = _menu_item(db, company_id, user_id, "Active")
        inactive = _menu_item(db, company_id, user_id, "Inactive")
        svc.deactivate_menu_item(db, company_id, inactive, user_id)
        rows = svc.list_menu_profitability(db, company_id)
        names = {r.menu_item_name for r in rows}
        assert "Active" in names
        assert "Inactive" not in names

    def test_update_menu_item_links_recipe(self, session):
        db, company_id, _, user_id = session
        r1 = _recipe(db, company_id, user_id, "R1")
        r2 = _recipe(db, company_id, user_id, "R2")
        menu_id = _menu_item(db, company_id, user_id, "Item", r1)
        res = svc.update_menu_item(
            db, company_id, menu_id, "Item Renamed", r2, user_id
        )
        assert res.ok
        items = svc.list_menu_items(db, company_id)
        row = next(i for i in items if i.id == menu_id)
        assert row.name == "Item Renamed"
        assert row.recipe_id == r2

    def test_dto_to_dict_json_safe(self):
        now = datetime.datetime.now()
        view = svc.MenuProfitabilityView(
            menu_item_id=1,
            menu_item_name="Burger",
            recipe_id=2,
            recipe_name="Patty",
            is_active=True,
            recipe_cost=5.0,
            selling_price_gross=15.0,
            selling_price_net=12.0,
            tax_rate_pct=20.0,
            gross_profit=7.0,
            food_cost_pct=41.67,
            markup_pct=140.0,
            target_food_cost_pct=30.0,
            suggested_price_gross=18.0,
            warnings=("note",),
        )
        payload = view.to_dict()
        assert payload["menu_item_name"] == "Burger"
        assert payload["warnings"] == ["note"]


class TestMenuMigrationReadiness:
    MENU_DB_FUNCS = (
        svc.create_menu_item,
        svc.update_menu_item,
        svc.deactivate_menu_item,
        svc.set_menu_price,
        svc.get_current_menu_price,
        svc.compute_menu_profitability,
        svc.list_menu_profitability,
        svc.list_menu_items,
    )

    def test_public_api_uses_explicit_company_id(self):
        for fn in self.MENU_DB_FUNCS:
            params = list(inspect.signature(fn).parameters)
            assert params[1] == "company_id", f"{fn.__name__} must take company_id"
