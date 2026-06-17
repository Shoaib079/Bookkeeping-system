"""Smoke regression — DSC + Recipe Costing (no browser, no UI layout)."""

from __future__ import annotations

import ast
import datetime
import inspect

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app as erp
from db import Base
import models
from registry.nav_keys import (
    NAV_EXTERNAL_SALES_VERIFICATION,
    NAV_RC_COST_BREAKDOWN,
    NAV_RC_INGREDIENTS,
    NAV_RC_MENU_ITEMS,
    NAV_RC_RECIPES,
)
from services import daily_sales_close as dsc
from services import recipe_costing as rc
from tests.nav_ux_02_contract import page_dispatch_from_main

_DSC_RC_PAGES = (
    NAV_EXTERNAL_SALES_VERIFICATION,
    NAV_RC_INGREDIENTS,
    NAV_RC_RECIPES,
    NAV_RC_MENU_ITEMS,
    NAV_RC_COST_BREAKDOWN,
)

_DSC_RC_HANDLERS = {
    NAV_EXTERNAL_SALES_VERIFICATION: "render_external_sales_verification",
    NAV_RC_INGREDIENTS: "render_recipe_ingredients",
    NAV_RC_RECIPES: "render_recipe_recipes",
    NAV_RC_MENU_ITEMS: "render_recipe_menu_items",
    NAV_RC_COST_BREAKDOWN: "render_recipe_cost_breakdown",
}

_VALID_DSC_SOURCE_TYPES = (None, "POS", "ERP", "MANUAL")


def _accordion_pages(group_key: str) -> list[str]:
    return [page for _, page in erp._NAV_ACCORDION_BY_KEY[group_key][1]]


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        co = models.Company(
            name="Smoke Co",
            slug="smoke_co",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        user = models.User(
            username="owner",
            display_name="Owner",
            password_hash="x",
            role="owner",
            is_active=True,
            created_at=datetime.datetime.now(),
        )
        s.add(co)
        s.add(user)
        s.commit()
        yield s, co.id, user.id


class TestDscRcNavSmoke:
    def test_nav_constants_are_canonical_strings(self):
        for key in _DSC_RC_PAGES:
            assert isinstance(key, str)
            assert key.strip() == key
            assert key

    def test_dsc_rc_pages_in_page_dispatch(self):
        dispatch = page_dispatch_from_main()
        missing = [key for key in _DSC_RC_PAGES if key not in dispatch]
        assert missing == []

    def test_dsc_rc_dispatch_handlers(self):
        dispatch = page_dispatch_from_main()
        for key, handler in _DSC_RC_HANDLERS.items():
            assert dispatch[key] == handler

    def test_closings_accordion_includes_external_sales_verification(self):
        assert NAV_EXTERNAL_SALES_VERIFICATION in _accordion_pages("close_day")

    def test_recipe_costing_accordion_includes_all_rc_pages(self):
        pages = _accordion_pages("recipe_costing")
        for key in (
            NAV_RC_INGREDIENTS,
            NAV_RC_RECIPES,
            NAV_RC_COST_BREAKDOWN,
            NAV_RC_MENU_ITEMS,
        ):
            assert key in pages

    def test_manager_role_can_access_dsc_and_menu_items(self):
        manager_pages = set(erp._NAV_ROLE_PAGES.get("manager", []))
        assert NAV_EXTERNAL_SALES_VERIFICATION in manager_pages
        assert NAV_RC_MENU_ITEMS in manager_pages


class TestDscDraftWorkflowSmoke:
    @pytest.mark.parametrize("source_type", _VALID_DSC_SOURCE_TYPES)
    def test_save_draft_with_valid_source_types(self, session, source_type):
        db, company_id, user_id = session
        source = dsc.ExternalSalesSource(
            source_name="Terminal A",
            source_type=source_type,
            branch_location=None,
        )
        external = dsc.ExternalSalesTotals(
            external_total=150.0,
            cash=100.0,
            card=50.0,
        )
        result = dsc.save_draft(
            db,
            company_id,
            datetime.date.today(),
            source,
            external,
            user_id,
        )
        assert result.ok, result.error
        record = dsc.get_active_verification(db, company_id, datetime.date.today())
        assert record is not None
        assert record.status == "draft"
        assert record.source_name == "Terminal A"
        assert record.source_type == source_type


class TestRecipeCostingWorkflowSmoke:
    def test_ingredient_to_profitability_chain(self, session):
        db, company_id, user_id = session

        ing = rc.create_ingredient(
            db, company_id, "Flour", "weight", "g", 0.002, user_id
        )
        assert ing.ok, ing.error

        saved = rc.save_recipe(
            db,
            company_id,
            "Bread",
            1.0,
            "each",
            [
                rc.RecipeLineInput(
                    quantity=500,
                    unit="g",
                    ingredient_id=ing.record_id,
                )
            ],
            user_id,
        )
        assert saved.ok, saved.error

        breakdown = rc.compute_recipe_cost(db, company_id, saved.record_id)
        assert breakdown is not None
        assert breakdown.total_cost > 0
        assert breakdown.line_costs

        menu = rc.create_menu_item(
            db,
            company_id,
            "Toast",
            saved.record_id,
            user_id,
        )
        assert menu.ok, menu.error

        price = rc.set_menu_price(db, company_id, menu.record_id, 25.0, user_id)
        assert price.ok, price.error

        current = rc.get_current_menu_price(db, company_id, menu.record_id)
        assert current is not None
        assert current.price_gross == 25.0

        prof = rc.compute_menu_profitability(db, company_id, menu.record_id)
        assert prof is not None
        assert prof.recipe_cost is not None
        assert prof.selling_price_gross == 25.0
        assert prof.gross_profit is not None

        listed = rc.list_menu_profitability(db, company_id)
        assert any(row.menu_item_id == menu.record_id for row in listed)
