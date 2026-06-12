"""RC-P1 service tests for Recipe Costing."""

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
from services import recipe_costing as svc


SERVICE_PATH = pathlib.Path(svc.__file__)


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


def _ingredient(
    session,
    company_id,
    user_id,
    *,
    name="Flour",
    dimension="weight",
    unit="g",
    cost=0.002,
):
    result = svc.create_ingredient(
        session,
        company_id,
        name,
        dimension,
        unit,
        cost,
        user_id,
    )
    assert result.ok
    return result.record_id


def _line(**kwargs):
    defaults = {"quantity": 1.0, "unit": "g", "waste_percent": 0.0, "sort_order": 0}
    defaults.update(kwargs)
    return svc.RecipeLineInput(**defaults)


def _save_recipe(session, company_id, user_id, name, lines, **kwargs):
    return svc.save_recipe(
        session,
        company_id,
        name,
        kwargs.get("yield_quantity", 1.0),
        kwargs.get("yield_unit", "each"),
        lines,
        user_id,
        recipe_id=kwargs.get("recipe_id"),
    )


# ── Unit conversion ───────────────────────────────────────────────────────────


class TestUnitConversion:
    def test_to_base_units_weight(self):
        qty, dim = svc.to_base_units(1.5, "kg")
        assert dim == "weight"
        assert qty == 1500.0

    def test_to_base_units_volume(self):
        qty, dim = svc.to_base_units(2.0, "L")
        assert dim == "volume"
        assert qty == 2000.0

    def test_to_base_units_count(self):
        qty, dim = svc.to_base_units(2.0, "dozen")
        assert dim == "count"
        assert qty == 24.0

    def test_from_base_units_round_trip(self):
        base_qty, dim = svc.to_base_units(500, "g")
        back = svc.from_base_units(base_qty, dim, "kg")
        assert back == 0.5

    def test_cross_dimension_rejection(self):
        with pytest.raises(ValueError, match="Cannot convert"):
            svc.from_base_units(100.0, "weight", "ml")


# ── Ingredient validation ─────────────────────────────────────────────────────


class TestValidateIngredient:
    def test_valid_weight_ingredient(self):
        result = svc.validate_ingredient(
            name="Sugar",
            base_dimension="weight",
            base_unit="g",
            cost_per_base_unit=0.001,
        )
        assert result.ok

    def test_rejects_non_canonical_base_unit(self):
        result = svc.validate_ingredient(
            name="Sugar",
            base_dimension="weight",
            base_unit="kg",
            cost_per_base_unit=1.0,
        )
        assert not result.ok

    def test_rejects_negative_cost(self):
        result = svc.validate_ingredient(
            name="Sugar",
            base_dimension="weight",
            base_unit="g",
            cost_per_base_unit=-1.0,
        )
        assert not result.ok


# ── Recipe line validation ────────────────────────────────────────────────────


class TestValidateRecipeLines:
    def test_xor_ingredient_or_sub_recipe(self):
        result = svc.validate_recipe_lines(
            [_line(ingredient_id=1, sub_recipe_id=2)]
        )
        assert not result.ok
        assert "exactly one" in result.errors[0]

    def test_requires_at_least_one_line(self):
        result = svc.validate_recipe_lines([])
        assert not result.ok

    def test_self_sub_recipe_rejected(self):
        result = svc.validate_recipe_lines(
            [_line(sub_recipe_id=5, unit="each")],
            recipe_id=5,
        )
        assert not result.ok


# ── Pure cost computation ─────────────────────────────────────────────────────


class TestComputeRecipeCostPure:
    def _ing(self, iid=1, cost=0.01, active=True):
        return svc._IngredientCostData(
            id=iid,
            name="Item",
            base_dimension="weight",
            base_unit="g",
            cost_per_base_unit=cost,
            is_active=active,
        )

    def _recipe(self, lines, *, rid=1, yield_qty=1.0, yield_unit="each"):
        return svc._RecipeCostData(
            id=rid,
            name="Main",
            yield_quantity=yield_qty,
            yield_unit=yield_unit,
            yield_dimension="count",
            lines=tuple(lines),
        )

    def test_single_level_recipe_cost(self):
        recipe = self._recipe(
            [
                svc._RecipeLineData(
                    line_id=1,
                    ingredient_id=1,
                    sub_recipe_id=None,
                    quantity=100.0,
                    unit="g",
                    waste_percent=0.0,
                    name="Flour",
                )
            ]
        )
        breakdown = svc.compute_recipe_cost(recipe, {1: self._ing()}, {})
        assert breakdown.total_cost == 1.0
        assert breakdown.line_costs[0].line_cost == 1.0

    def test_waste_percentage(self):
        recipe = self._recipe(
            [
                svc._RecipeLineData(
                    line_id=1,
                    ingredient_id=1,
                    sub_recipe_id=None,
                    quantity=100.0,
                    unit="g",
                    waste_percent=10.0,
                    name="Flour",
                )
            ]
        )
        breakdown = svc.compute_recipe_cost(recipe, {1: self._ing(cost=0.01)}, {})
        assert breakdown.line_costs[0].line_cost == 1.1

    def test_sub_recipe_costing(self):
        sub = self._recipe(
            [
                svc._RecipeLineData(
                    line_id=1,
                    ingredient_id=1,
                    sub_recipe_id=None,
                    quantity=1000.0,
                    unit="g",
                    waste_percent=0.0,
                    name="Flour",
                )
            ],
            rid=2,
            yield_qty=1.0,
            yield_unit="kg",
        )
        main = self._recipe(
            [
                svc._RecipeLineData(
                    line_id=2,
                    ingredient_id=None,
                    sub_recipe_id=2,
                    quantity=500.0,
                    unit="g",
                    waste_percent=0.0,
                    name="Dough base",
                )
            ],
            rid=1,
        )
        ingredients = {1: self._ing(cost=0.001)}
        breakdown = svc.compute_recipe_cost(main, ingredients, {2: sub})
        assert breakdown.total_cost == 0.5

    def test_cycle_rejection(self):
        a = svc._RecipeCostData(
            id=1,
            name="A",
            yield_quantity=1.0,
            yield_unit="each",
            yield_dimension="count",
            lines=(
                svc._RecipeLineData(
                    line_id=1,
                    ingredient_id=None,
                    sub_recipe_id=2,
                    quantity=1.0,
                    unit="each",
                    waste_percent=0.0,
                    name="B",
                ),
            ),
        )
        b = svc._RecipeCostData(
            id=2,
            name="B",
            yield_quantity=1.0,
            yield_unit="each",
            yield_dimension="count",
            lines=(
                svc._RecipeLineData(
                    line_id=2,
                    ingredient_id=None,
                    sub_recipe_id=1,
                    quantity=1.0,
                    unit="each",
                    waste_percent=0.0,
                    name="A",
                ),
            ),
        )
        with pytest.raises(ValueError, match="cycle"):
            svc.compute_recipe_cost(a, {}, {1: a, 2: b})

    def test_recursion_depth_rejection(self):
        ingredients = {99: svc._IngredientCostData(
            id=99, name="Salt", base_dimension="weight", base_unit="g",
            cost_per_base_unit=0.001, is_active=True,
        )}
        sub_recipes = {}
        prev_id = 10
        for i in range(11, 15):
            sub_recipes[prev_id] = svc._RecipeCostData(
                id=prev_id,
                name=f"R{prev_id}",
                yield_quantity=1.0,
                yield_unit="each",
                yield_dimension="count",
                lines=(
                    svc._RecipeLineData(
                        line_id=prev_id,
                        ingredient_id=None,
                        sub_recipe_id=i,
                        quantity=1.0,
                        unit="each",
                        waste_percent=0.0,
                        name=f"R{i}",
                    ),
                ),
            )
            prev_id = i
        sub_recipes[14] = svc._RecipeCostData(
            id=14,
            name="R14",
            yield_quantity=1.0,
            yield_unit="each",
            yield_dimension="count",
            lines=(
                svc._RecipeLineData(
                    line_id=14,
                    ingredient_id=99,
                    sub_recipe_id=None,
                    quantity=1.0,
                    unit="g",
                    waste_percent=0.0,
                    name="Salt",
                ),
            ),
        )
        root = svc._RecipeCostData(
            id=10,
            name="Root",
            yield_quantity=1.0,
            yield_unit="each",
            yield_dimension="count",
            lines=sub_recipes[10].lines,
        )
        with pytest.raises(ValueError, match="recursion depth"):
            svc.compute_recipe_cost(root, ingredients, sub_recipes)

    def test_deactivated_ingredient_warning(self):
        recipe = self._recipe(
            [
                svc._RecipeLineData(
                    line_id=1,
                    ingredient_id=1,
                    sub_recipe_id=None,
                    quantity=10.0,
                    unit="g",
                    waste_percent=0.0,
                    name="Old stock",
                )
            ]
        )
        breakdown = svc.compute_recipe_cost(
            recipe, {1: self._ing(active=False)}, {}
        )
        assert breakdown.total_cost == 0.1
        assert "deactivated" in breakdown.warnings[0].lower()


# ── Service mutations & isolation ─────────────────────────────────────────────


class TestServiceMutations:
    def test_create_and_cost_single_recipe(self, session):
        db, company_id, _, user_id = session
        flour = _ingredient(db, company_id, user_id, cost=0.002)
        result = _save_recipe(
            db,
            company_id,
            user_id,
            "Bread",
            [_line(ingredient_id=flour, quantity=250, unit="g")],
            yield_quantity=1.0,
            yield_unit="each",
        )
        assert result.ok
        breakdown = svc.compute_recipe_cost(db, company_id, result.record_id)
        assert breakdown is not None
        assert breakdown.total_cost == 0.5

    def test_company_isolation(self, session):
        db, company_a, company_b, user_id = session
        flour_a = _ingredient(db, company_a, user_id, name="Flour A")
        result = _save_recipe(
            db,
            company_a,
            user_id,
            "Private",
            [_line(ingredient_id=flour_a, quantity=100, unit="g")],
        )
        assert result.ok
        assert svc.compute_recipe_cost(db, company_b, result.record_id) is None

    def test_bulk_update_atomicity(self, session):
        db, company_id, _, user_id = session
        a = _ingredient(db, company_id, user_id, name="A", cost=0.01)
        b = _ingredient(db, company_id, user_id, name="B", cost=0.02)
        before_a = db.get(models.Ingredient, a).cost_per_base_unit
        before_b = db.get(models.Ingredient, b).cost_per_base_unit
        result = svc.bulk_update_costs(
            db,
            company_id,
            [(a, 0.05), (99999, 0.10)],
            user_id,
        )
        assert not result.ok
        db.expire_all()
        assert db.get(models.Ingredient, a).cost_per_base_unit == before_a
        assert db.get(models.Ingredient, b).cost_per_base_unit == before_b

        ok = svc.bulk_update_costs(
            db, company_id, [(a, 0.05), (b, 0.06)], user_id
        )
        assert ok.ok
        db.expire_all()
        assert db.get(models.Ingredient, a).cost_per_base_unit == 0.05
        assert db.get(models.Ingredient, b).cost_per_base_unit == 0.06

    def test_deactivate_ingredient_still_costs_with_warning(self, session):
        db, company_id, _, user_id = session
        ing = _ingredient(db, company_id, user_id, cost=0.01)
        saved = _save_recipe(
            db,
            company_id,
            user_id,
            "Soup",
            [_line(ingredient_id=ing, quantity=10, unit="g")],
        )
        svc.deactivate_ingredient(db, company_id, ing, user_id)
        breakdown = svc.compute_recipe_cost(db, company_id, saved.record_id)
        assert "deactivated" in breakdown.warnings[0].lower()

    def test_save_recipe_cycle_rejected(self, session):
        db, company_id, _, user_id = session
        flour = _ingredient(db, company_id, user_id)
        sub = _save_recipe(
            db,
            company_id,
            user_id,
            "Sub",
            [_line(ingredient_id=flour, quantity=10, unit="g")],
        )
        main = _save_recipe(
            db,
            company_id,
            user_id,
            "Main",
            [_line(sub_recipe_id=sub.record_id, quantity=1, unit="each")],
        )
        assert main.ok
        cycle = _save_recipe(
            db,
            company_id,
            user_id,
            "Sub",
            [_line(sub_recipe_id=main.record_id, quantity=1, unit="each")],
            recipe_id=sub.record_id,
        )
        assert not cycle.ok
        assert "cycle" in cycle.error.lower()


class TestWhereUsed:
    def test_transitive_where_used_for_ingredient(self, session):
        db, company_id, _, user_id = session
        salt = _ingredient(db, company_id, user_id, name="Salt", cost=0.01)
        sub = _save_recipe(
            db,
            company_id,
            user_id,
            "Base",
            [_line(ingredient_id=salt, quantity=5, unit="g")],
        )
        main = _save_recipe(
            db,
            company_id,
            user_id,
            "Menu batch",
            [_line(sub_recipe_id=sub.record_id, quantity=1, unit="each")],
        )
        entries = svc.where_used(db, company_id, ingredient_id=salt)
        by_id = {e.recipe_id: e for e in entries}
        assert by_id[sub.record_id].usage_type == "direct"
        assert by_id[main.record_id].usage_type == "transitive"
        assert by_id[main.record_id].depth == 1

    def test_where_used_for_sub_recipe(self, session):
        db, company_id, _, user_id = session
        flour = _ingredient(db, company_id, user_id)
        sub = _save_recipe(
            db,
            company_id,
            user_id,
            "Dough",
            [_line(ingredient_id=flour, quantity=100, unit="g")],
        )
        top = _save_recipe(
            db,
            company_id,
            user_id,
            "Pizza",
            [_line(sub_recipe_id=sub.record_id, quantity=1, unit="each")],
        )
        entries = svc.where_used(db, company_id, recipe_id=sub.record_id)
        assert len(entries) == 1
        assert entries[0].recipe_id == top.record_id
        assert entries[0].usage_type == "direct"


# ── Contract / migration readiness ────────────────────────────────────────────


class TestServiceReadApis:
    def test_list_and_get_ingredient(self, session):
        db, company_id, _, user_id = session
        created = svc.create_ingredient(
            db, company_id, "Salt", "weight", "g", 0.01, user_id
        )
        rows = svc.list_ingredients(db, company_id, search="Sal")
        assert len(rows) == 1
        got = svc.get_ingredient(db, company_id, created.record_id)
        assert got is not None
        assert got.name == "Salt"

    def test_update_and_activate_ingredient(self, session):
        db, company_id, _, user_id = session
        created = svc.create_ingredient(
            db, company_id, "Cream", "volume", "ml", 0.02, user_id
        )
        svc.deactivate_ingredient(db, company_id, created.record_id, user_id)
        act = svc.activate_ingredient(db, company_id, created.record_id, user_id)
        assert act.ok
        upd = svc.update_ingredient(
            db, company_id, created.record_id, "Fresh Cream", user_id, notes="cold"
        )
        assert upd.ok
        got = svc.get_ingredient(db, company_id, created.record_id)
        assert got.name == "Fresh Cream"
        assert got.is_active is True

    def test_list_and_get_recipe(self, session):
        db, company_id, _, user_id = session
        ing = svc.create_ingredient(db, company_id, "Flour", "weight", "g", 0.002, user_id)
        saved = svc.save_recipe(
            db,
            company_id,
            "Dough",
            1.0,
            "kg",
            [svc.RecipeLineInput(quantity=500, unit="g", ingredient_id=ing.record_id)],
            user_id,
        )
        summaries = svc.list_recipes(db, company_id, search="Dou")
        assert len(summaries) == 1
        detail = svc.get_recipe(db, company_id, saved.record_id)
        assert detail is not None
        assert detail.lines[0].display_name == "Flour"


class TestMigrationReadinessContract:
    FORBIDDEN_IMPORT_TOKENS = (
        "import streamlit",
        "from streamlit",
        "import app",
        "from app",
    )
    FORBIDDEN_DOMAIN_TOKENS = (
        "create_journal_entry",
        "post_cash_sale",
        "post_purchase",
        "post_expense",
        "inventory_transactions",
    )

    def test_service_imports_no_streamlit_or_app(self):
        source = SERVICE_PATH.read_text(encoding="utf-8")
        for token in self.FORBIDDEN_IMPORT_TOKENS:
            assert token not in source

    def test_no_posting_or_inventory_imports(self):
        source = SERVICE_PATH.read_text(encoding="utf-8").lower()
        for token in self.FORBIDDEN_DOMAIN_TOKENS:
            assert token not in source

    def test_public_api_uses_explicit_company_id(self):
        db_funcs = (
            svc.create_ingredient,
            svc.update_ingredient_cost,
            svc.bulk_update_costs,
            svc.deactivate_ingredient,
            svc.save_recipe,
            svc.where_used,
            svc.list_ingredients,
            svc.get_ingredient,
            svc.update_ingredient,
            svc.activate_ingredient,
            svc.list_recipes,
            svc.get_recipe,
            svc.create_menu_item,
            svc.update_menu_item,
            svc.deactivate_menu_item,
            svc.set_menu_price,
            svc.get_current_menu_price,
            svc.compute_menu_profitability,
            svc.list_menu_profitability,
            svc.list_menu_items,
        )
        for fn in db_funcs:
            params = list(inspect.signature(fn).parameters)
            assert params[1] == "company_id", f"{fn.__name__} must take company_id"

    def test_compute_recipe_cost_db_entry_accepts_company_id(self, session):
        db, company_id, _, user_id = session
        ing = _ingredient(db, company_id, user_id)
        saved = _save_recipe(
            db,
            company_id,
            user_id,
            "Item",
            [_line(ingredient_id=ing, quantity=1, unit="g")],
        )
        breakdown = svc.compute_recipe_cost(db, company_id, saved.record_id)
        assert breakdown is not None

    def test_dto_to_dict_json_safe(self):
        now = datetime.datetime.now()
        view = svc.IngredientView(
            id=1,
            company_id=1,
            name="Flour",
            base_dimension="weight",
            base_unit="g",
            cost_per_base_unit=0.002,
            is_active=True,
            notes=None,
            created_at=now,
            updated_at=None,
        )
        payload = view.to_dict()
        json.dumps(payload)
        assert payload["created_at"] == now.isoformat()

        breakdown = svc.RecipeCostBreakdown(
            recipe_id=1,
            recipe_name="Bread",
            total_cost=1.0,
            cost_per_yield_unit=1.0,
            yield_quantity=1.0,
            yield_unit="each",
            yield_dimension="count",
            line_costs=(),
            warnings=("note",),
        )
        json.dumps(breakdown.to_dict())

        assert svc.MutationResult(record_id=1).to_dict()["ok"] is True
        assert svc.ValidationResult(ok=False, errors=("x",)).to_dict()["ok"] is False
