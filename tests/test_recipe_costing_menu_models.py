"""RC-P2A model tests for MenuItem and MenuPriceHistory."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from services.recipe_costing import (
    RecipeLineInput,
    create_ingredient,
    create_menu_item,
    save_recipe,
    set_menu_price,
)


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as s:
        co = models.Company(
            name="Test Co",
            slug="test_co",
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
        s.add(co)
        s.add(user)
        s.commit()
        yield s, co.id, user.id


def _recipe(session, company_id, user_id, name="Soup"):
    ing = create_ingredient(session, company_id, "Stock", "volume", "ml", 0.001, user_id)
    saved = save_recipe(
        session,
        company_id,
        name,
        1.0,
        "each",
        [RecipeLineInput(quantity=200, unit="ml", ingredient_id=ing.record_id)],
        user_id,
    )
    assert saved.ok
    return saved.record_id


def test_menu_item_unique_name_per_company(session):
    db, company_id, user_id = session
    recipe_id = _recipe(db, company_id, user_id)
    first = create_menu_item(db, company_id, "Burger", recipe_id, user_id)
    assert first.ok
    dup = create_menu_item(db, company_id, "Burger", recipe_id, user_id)
    assert not dup.ok


def test_menu_item_model_does_not_store_computed_profitability(session):
    db, company_id, user_id = session
    recipe_id = _recipe(db, company_id, user_id)
    created = create_menu_item(db, company_id, "Salad", recipe_id, user_id)
    row = db.get(models.MenuItem, created.record_id)
    cols = {c.name for c in models.MenuItem.__table__.columns}
    assert row is not None
    assert "food_cost_pct" not in cols
    assert "gross_profit" not in cols
    assert "selling_price" not in cols


def test_menu_price_history_append_only(session):
    db, company_id, user_id = session
    recipe_id = _recipe(db, company_id, user_id)
    created = create_menu_item(db, company_id, "Pasta", recipe_id, user_id)
    p1 = set_menu_price(db, company_id, created.record_id, 100.0, user_id)
    p2 = set_menu_price(db, company_id, created.record_id, 120.0, user_id)
    assert p1.ok and p2.ok
    rows = (
        db.query(models.MenuPriceHistory)
        .filter(models.MenuPriceHistory.menu_item_id == created.record_id)
        .all()
    )
    assert len(rows) == 2
    prices = {r.price_gross for r in rows}
    assert prices == {100.0, 120.0}
