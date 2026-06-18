"""FASTAPI-REACT-50 — read-only recipe costing lists and breakdowns."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from services import recipe_costing as rc_svc


@dataclass(frozen=True, slots=True)
class RecipeIngredientsListPage:
    rows: tuple[rc_svc.IngredientView, ...]
    row_count: int
    company_id: int


@dataclass(frozen=True, slots=True)
class RecipesListPage:
    rows: tuple[rc_svc.RecipeSummary, ...]
    row_count: int
    company_id: int


@dataclass(frozen=True, slots=True)
class MenuProfitabilityListPage:
    rows: tuple[rc_svc.MenuProfitabilityView, ...]
    row_count: int
    company_id: int
    target_food_cost_pct: float


def compute_recipe_ingredients_list(
    session: Session,
    *,
    company_id: int,
    active_only: bool | None = True,
) -> RecipeIngredientsListPage:
    rows = tuple(
        rc_svc.list_ingredients(session, company_id, active_only=active_only)
    )
    return RecipeIngredientsListPage(
        rows=rows,
        row_count=len(rows),
        company_id=company_id,
    )


def compute_recipes_list(
    session: Session,
    *,
    company_id: int,
    active_only: bool | None = True,
) -> RecipesListPage:
    rows = tuple(rc_svc.list_recipes(session, company_id, active_only=active_only))
    return RecipesListPage(
        rows=rows,
        row_count=len(rows),
        company_id=company_id,
    )


def compute_recipe_cost_breakdown(
    session: Session,
    *,
    company_id: int,
    recipe_id: int,
) -> rc_svc.RecipeCostBreakdown | None:
    return rc_svc.compute_recipe_cost(session, company_id, recipe_id)


def compute_menu_profitability_list(
    session: Session,
    *,
    company_id: int,
    active_only: bool = True,
    target_food_cost_pct: float = rc_svc.DEFAULT_TARGET_FOOD_COST_PCT,
) -> MenuProfitabilityListPage:
    rows = tuple(
        rc_svc.list_menu_profitability(
            session,
            company_id,
            active_only=active_only,
            target_food_cost_pct=target_food_cost_pct,
        )
    )
    return MenuProfitabilityListPage(
        rows=rows,
        row_count=len(rows),
        company_id=company_id,
        target_food_cost_pct=target_food_cost_pct,
    )
