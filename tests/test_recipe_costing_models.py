"""RC-P1 model tests for Ingredient, Recipe, RecipeLine."""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
import models
from services.recipe_costing import RecipeLineInput, create_ingredient, save_recipe


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


def test_ingredient_model_unique_per_company(session):
    db, company_id, user_id = session
    create_ingredient(db, company_id, "Butter", "weight", "g", 0.01, user_id)
    dup = create_ingredient(db, company_id, "Butter", "weight", "g", 0.02, user_id)
    assert not dup.ok


def test_recipe_line_xor_constraint_via_service(session):
    db, company_id, user_id = session
    ing = create_ingredient(db, company_id, "Milk", "volume", "ml", 0.001, user_id)
    assert ing.ok
    bad = save_recipe(
        db,
        company_id,
        "Bad",
        1.0,
        "each",
        [
            RecipeLineInput(
                quantity=1.0,
                unit="ml",
                ingredient_id=ing.record_id,
                sub_recipe_id=99,
            )
        ],
        user_id,
    )
    assert not bad.ok


def test_recipe_model_does_not_store_computed_cost(session):
    db, company_id, user_id = session
    ing = create_ingredient(db, company_id, "Sugar", "weight", "g", 0.005, user_id)
    saved = save_recipe(
        db,
        company_id,
        "Cake",
        1.0,
        "each",
        [RecipeLineInput(quantity=200, unit="g", ingredient_id=ing.record_id)],
        user_id,
    )
    recipe = db.get(models.Recipe, saved.record_id)
    assert recipe is not None
    assert not hasattr(recipe, "total_cost")
    cols = {c.name for c in models.Recipe.__table__.columns}
    assert "total_cost" not in cols
    assert "stored_cost" not in cols
