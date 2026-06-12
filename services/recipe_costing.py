"""RC-P1 — Recipe Costing service layer.

FastAPI-ready: explicit company_id, serializable DTOs, no Streamlit or app.py imports.
Verification/costing only — no inventory, posting, or menu linkage in RC-P1.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from typing import Any

from models import AuditLog, Ingredient, Recipe, RecipeLine
from sqlalchemy.orm import Session

MAX_RECURSION_DEPTH = 3
MAX_NAME_LEN = 200

DIMENSIONS = frozenset({"weight", "volume", "count"})
CANONICAL_BASE_UNIT = {
    "weight": "g",
    "volume": "ml",
    "count": "each",
}

# unit (normalized) -> (dimension, multiplier to canonical base)
_UNIT_FACTORS: dict[str, tuple[str, float]] = {
    "g": ("weight", 1.0),
    "gram": ("weight", 1.0),
    "grams": ("weight", 1.0),
    "kg": ("weight", 1000.0),
    "kilogram": ("weight", 1000.0),
    "kilograms": ("weight", 1000.0),
    "lb": ("weight", 453.592),
    "lbs": ("weight", 453.592),
    "pound": ("weight", 453.592),
    "oz": ("weight", 28.3495),
    "ounce": ("weight", 28.3495),
    "ml": ("volume", 1.0),
    "milliliter": ("volume", 1.0),
    "millilitre": ("volume", 1.0),
    "l": ("volume", 1000.0),
    "liter": ("volume", 1000.0),
    "litre": ("volume", 1000.0),
    "liters": ("volume", 1000.0),
    "cl": ("volume", 10.0),
    "each": ("count", 1.0),
    "ea": ("count", 1.0),
    "pc": ("count", 1.0),
    "piece": ("count", 1.0),
    "pieces": ("count", 1.0),
    "dozen": ("count", 12.0),
}


# ── Serializable DTOs ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class IngredientView:
    id: int
    company_id: int
    name: str
    base_dimension: str
    base_unit: str
    cost_per_base_unit: float
    is_active: bool
    notes: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "company_id": self.company_id,
            "name": self.name,
            "base_dimension": self.base_dimension,
            "base_unit": self.base_unit,
            "cost_per_base_unit": self.cost_per_base_unit,
            "is_active": self.is_active,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass(frozen=True)
class RecipeLineCost:
    line_id: int | None
    ingredient_id: int | None
    sub_recipe_id: int | None
    name: str
    quantity: float
    unit: str
    waste_percent: float
    line_cost: float
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_id": self.line_id,
            "ingredient_id": self.ingredient_id,
            "sub_recipe_id": self.sub_recipe_id,
            "name": self.name,
            "quantity": self.quantity,
            "unit": self.unit,
            "waste_percent": self.waste_percent,
            "line_cost": self.line_cost,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class RecipeCostBreakdown:
    recipe_id: int
    recipe_name: str
    total_cost: float
    cost_per_yield_unit: float
    yield_quantity: float
    yield_unit: str
    yield_dimension: str
    line_costs: tuple[RecipeLineCost, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "recipe_name": self.recipe_name,
            "total_cost": self.total_cost,
            "cost_per_yield_unit": self.cost_per_yield_unit,
            "yield_quantity": self.yield_quantity,
            "yield_unit": self.yield_unit,
            "yield_dimension": self.yield_dimension,
            "line_costs": [lc.to_dict() for lc in self.line_costs],
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class WhereUsedEntry:
    recipe_id: int
    recipe_name: str
    usage_type: str  # direct | transitive
    depth: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "recipe_name": self.recipe_name,
            "usage_type": self.usage_type,
            "depth": self.depth,
        }


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "errors": list(self.errors)}


@dataclass(frozen=True)
class MutationResult:
    record_id: int | None
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.record_id is not None and not self.error

    def to_dict(self) -> dict[str, Any]:
        return {"record_id": self.record_id, "error": self.error, "ok": self.ok}


@dataclass(frozen=True)
class RecipeLineInput:
    """Input row for save_recipe — not persisted as-is."""

    quantity: float
    unit: str
    ingredient_id: int | None = None
    sub_recipe_id: int | None = None
    waste_percent: float = 0.0
    sort_order: int = 0
    notes: str | None = None


@dataclass(frozen=True)
class _IngredientCostData:
    id: int
    name: str
    base_dimension: str
    base_unit: str
    cost_per_base_unit: float
    is_active: bool


@dataclass(frozen=True)
class _RecipeLineData:
    line_id: int | None
    ingredient_id: int | None
    sub_recipe_id: int | None
    quantity: float
    unit: str
    waste_percent: float
    name: str


@dataclass(frozen=True)
class _RecipeCostData:
    id: int
    name: str
    yield_quantity: float
    yield_unit: str
    yield_dimension: str
    lines: tuple[_RecipeLineData, ...]


# ── Unit conversion (pure) ────────────────────────────────────────────────────


def _normalize_unit(unit: str) -> str:
    return (unit or "").strip().lower()


def _unit_dimension_and_factor(unit: str) -> tuple[str, float]:
    key = _normalize_unit(unit)
    if key not in _UNIT_FACTORS:
        raise ValueError(f"Unknown unit: {unit}")
    return _UNIT_FACTORS[key]


def to_base_units(quantity: float, unit: str) -> tuple[float, str]:
    """Convert quantity to canonical base units. Returns (base_qty, dimension)."""
    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")
    dimension, factor = _unit_dimension_and_factor(unit)
    return round(quantity * factor, 8), dimension


def from_base_units(base_quantity: float, dimension: str, target_unit: str) -> float:
    """Convert from canonical base units to target unit within the same dimension."""
    if dimension not in DIMENSIONS:
        raise ValueError(f"Invalid dimension: {dimension}")
    target_dim, factor = _unit_dimension_and_factor(target_unit)
    if target_dim != dimension:
        raise ValueError(
            f"Cannot convert {dimension} base units to {target_unit} ({target_dim})."
        )
    if factor == 0:
        raise ValueError("Invalid unit conversion factor.")
    return round(base_quantity / factor, 8)


# ── Pure validation ───────────────────────────────────────────────────────────


def validate_ingredient(
    *,
    name: str,
    base_dimension: str,
    base_unit: str,
    cost_per_base_unit: float,
) -> ValidationResult:
    errors: list[str] = []
    trimmed = (name or "").strip()
    if not trimmed:
        errors.append("Ingredient name is required.")
    elif len(trimmed) > MAX_NAME_LEN:
        errors.append(f"Ingredient name must be at most {MAX_NAME_LEN} characters.")

    dim = (base_dimension or "").strip().lower()
    if dim not in DIMENSIONS:
        errors.append(f"base_dimension must be one of: {', '.join(sorted(DIMENSIONS))}.")

    unit = _normalize_unit(base_unit)
    canonical = CANONICAL_BASE_UNIT.get(dim, "")
    if dim in DIMENSIONS and unit != canonical:
        errors.append(
            f"base_unit must be the canonical unit '{canonical}' for dimension '{dim}'."
        )

    if cost_per_base_unit < 0:
        errors.append("cost_per_base_unit cannot be negative.")

    return ValidationResult(ok=not errors, errors=tuple(errors))


def validate_recipe_lines(
    lines: list[RecipeLineInput],
    *,
    recipe_id: int | None = None,
) -> ValidationResult:
    errors: list[str] = []
    if not lines:
        errors.append("At least one recipe line is required.")

    for idx, line in enumerate(lines, start=1):
        has_ing = line.ingredient_id is not None
        has_sub = line.sub_recipe_id is not None
        if has_ing == has_sub:
            errors.append(
                f"Line {idx}: exactly one of ingredient_id or sub_recipe_id is required."
            )
        if recipe_id is not None and line.sub_recipe_id == recipe_id:
            errors.append(f"Line {idx}: recipe cannot reference itself as a sub-recipe.")
        if line.quantity <= 0:
            errors.append(f"Line {idx}: quantity must be positive.")
        if line.waste_percent < 0 or line.waste_percent > 100:
            errors.append(f"Line {idx}: waste_percent must be between 0 and 100.")
        try:
            _unit_dimension_and_factor(line.unit)
        except ValueError:
            errors.append(f"Line {idx}: unknown unit '{line.unit}'.")

    return ValidationResult(ok=not errors, errors=tuple(errors))


def _compute_recipe_cost_pure(
    recipe: _RecipeCostData,
    ingredients: dict[int, _IngredientCostData],
    sub_recipes: dict[int, _RecipeCostData],
    *,
    depth: int = 0,
    visiting: frozenset[int] | None = None,
) -> RecipeCostBreakdown:
    """Pure recursive cost rollup — never persists computed totals."""
    if depth > MAX_RECURSION_DEPTH:
        raise ValueError(
            f"Recipe recursion depth exceeds maximum of {MAX_RECURSION_DEPTH}."
        )

    active_visiting = visiting or frozenset()
    if recipe.id in active_visiting:
        raise ValueError("Sub-recipe cycle detected.")

    next_visiting = active_visiting | {recipe.id}
    line_costs: list[RecipeLineCost] = []
    breakdown_warnings: list[str] = []
    total = 0.0

    for line in recipe.lines:
        line_warnings: list[str] = []
        if line.ingredient_id is not None:
            ing = ingredients.get(line.ingredient_id)
            if ing is None:
                raise ValueError(f"Ingredient {line.ingredient_id} not found in cost map.")
            try:
                base_qty, line_dim = to_base_units(line.quantity, line.unit)
            except ValueError as exc:
                raise ValueError(f"Line '{line.name}': {exc}") from exc
            if line_dim != ing.base_dimension:
                raise ValueError(
                    f"Line '{line.name}': unit dimension '{line_dim}' does not match "
                    f"ingredient dimension '{ing.base_dimension}'."
                )
            effective_qty = base_qty * (1.0 + line.waste_percent / 100.0)
            line_cost = round(effective_qty * ing.cost_per_base_unit, 4)
            if not ing.is_active:
                line_warnings.append(f"Ingredient '{ing.name}' is deactivated.")
            line_costs.append(
                RecipeLineCost(
                    line_id=line.line_id,
                    ingredient_id=line.ingredient_id,
                    sub_recipe_id=None,
                    name=line.name,
                    quantity=line.quantity,
                    unit=line.unit,
                    waste_percent=line.waste_percent,
                    line_cost=line_cost,
                    warnings=tuple(line_warnings),
                )
            )
            total += line_cost
            breakdown_warnings.extend(line_warnings)
        else:
            assert line.sub_recipe_id is not None
            sub = sub_recipes.get(line.sub_recipe_id)
            if sub is None:
                raise ValueError(f"Sub-recipe {line.sub_recipe_id} not found in cost map.")
            sub_breakdown = _compute_recipe_cost_pure(
                sub,
                ingredients,
                sub_recipes,
                depth=depth + 1,
                visiting=next_visiting,
            )
            try:
                line_base, line_dim = to_base_units(line.quantity, line.unit)
                yield_base, yield_dim = to_base_units(sub.yield_quantity, sub.yield_unit)
            except ValueError as exc:
                raise ValueError(f"Line '{line.name}': {exc}") from exc
            if line_dim != yield_dim:
                raise ValueError(
                    f"Line '{line.name}': unit dimension '{line_dim}' does not match "
                    f"sub-recipe yield dimension '{yield_dim}'."
                )
            if yield_base <= 0:
                raise ValueError(f"Sub-recipe '{sub.name}' yield quantity must be positive.")
            scale = line_base / yield_base
            line_cost = round(sub_breakdown.total_cost * scale, 4)
            line_warnings.extend(sub_breakdown.warnings)
            line_costs.append(
                RecipeLineCost(
                    line_id=line.line_id,
                    ingredient_id=None,
                    sub_recipe_id=line.sub_recipe_id,
                    name=line.name,
                    quantity=line.quantity,
                    unit=line.unit,
                    waste_percent=line.waste_percent,
                    line_cost=line_cost,
                    warnings=tuple(line_warnings),
                )
            )
            total += line_cost
            breakdown_warnings.extend(sub_breakdown.warnings)

    total = round(total, 4)
    yield_base, _ = to_base_units(recipe.yield_quantity, recipe.yield_unit)
    cost_per_yield = round(total / yield_base, 4) if yield_base > 0 else 0.0

    return RecipeCostBreakdown(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        total_cost=total,
        cost_per_yield_unit=cost_per_yield,
        yield_quantity=recipe.yield_quantity,
        yield_unit=recipe.yield_unit,
        yield_dimension=recipe.yield_dimension,
        line_costs=tuple(line_costs),
        warnings=tuple(dict.fromkeys(breakdown_warnings)),
    )


# ── DB helpers ────────────────────────────────────────────────────────────────


def _ingredient_view(row: Ingredient) -> IngredientView:
    return IngredientView(
        id=row.id,
        company_id=row.company_id,
        name=row.name,
        base_dimension=row.base_dimension,
        base_unit=row.base_unit,
        cost_per_base_unit=row.cost_per_base_unit,
        is_active=row.is_active,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _write_audit(
    session: Session,
    *,
    company_id: int,
    action: str,
    entity_type: str,
    entity_id: int,
    description: str,
    performed_by: str | None,
) -> None:
    session.add(
        AuditLog(
            timestamp=datetime.datetime.now(),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            performed_by=performed_by,
            company_id=company_id,
        )
    )


def _get_ingredient_row(
    session: Session, company_id: int, ingredient_id: int
) -> Ingredient | None:
    return (
        session.query(Ingredient)
        .filter(Ingredient.id == ingredient_id, Ingredient.company_id == company_id)
        .first()
    )


def _get_recipe_row(session: Session, company_id: int, recipe_id: int) -> Recipe | None:
    return (
        session.query(Recipe)
        .filter(Recipe.id == recipe_id, Recipe.company_id == company_id)
        .first()
    )


def _load_recipe_cost_data(
    session: Session, company_id: int, recipe_id: int
) -> _RecipeCostData | None:
    recipe = _get_recipe_row(session, company_id, recipe_id)
    if recipe is None:
        return None
    lines = (
        session.query(RecipeLine)
        .filter(RecipeLine.recipe_id == recipe_id)
        .order_by(RecipeLine.sort_order, RecipeLine.id)
        .all()
    )
    line_data: list[_RecipeLineData] = []
    for line in lines:
        if line.ingredient_id is not None:
            ing = _get_ingredient_row(session, company_id, line.ingredient_id)
            name = ing.name if ing else f"Ingredient #{line.ingredient_id}"
        else:
            sub = _get_recipe_row(session, company_id, line.sub_recipe_id)
            name = sub.name if sub else f"Recipe #{line.sub_recipe_id}"
        line_data.append(
            _RecipeLineData(
                line_id=line.id,
                ingredient_id=line.ingredient_id,
                sub_recipe_id=line.sub_recipe_id,
                quantity=line.quantity,
                unit=line.unit,
                waste_percent=line.waste_percent,
                name=name,
            )
        )
    return _RecipeCostData(
        id=recipe.id,
        name=recipe.name,
        yield_quantity=recipe.yield_quantity,
        yield_unit=recipe.yield_unit,
        yield_dimension=recipe.yield_dimension,
        lines=tuple(line_data),
    )


def _collect_sub_recipe_ids(
    session: Session, company_id: int, recipe_id: int, collected: set[int] | None = None
) -> set[int]:
    seen = collected or set()
    if recipe_id in seen:
        return seen
    seen.add(recipe_id)
    lines = (
        session.query(RecipeLine.sub_recipe_id)
        .join(Recipe, Recipe.id == RecipeLine.recipe_id)
        .filter(
            Recipe.company_id == company_id,
            RecipeLine.recipe_id == recipe_id,
            RecipeLine.sub_recipe_id.isnot(None),
        )
        .all()
    )
    for (sub_id,) in lines:
        if sub_id is not None:
            _collect_sub_recipe_ids(session, company_id, sub_id, seen)
    return seen


def _would_create_cycle(
    session: Session, company_id: int, parent_recipe_id: int, sub_recipe_id: int
) -> bool:
    if sub_recipe_id == parent_recipe_id:
        return True
    descendants = _collect_sub_recipe_ids(session, company_id, sub_recipe_id)
    return parent_recipe_id in descendants


def _build_cost_maps(
    session: Session, company_id: int, root_recipe_id: int
) -> tuple[dict[int, _IngredientCostData], dict[int, _RecipeCostData]]:
    recipe_ids = _collect_sub_recipe_ids(session, company_id, root_recipe_id)
    sub_recipes: dict[int, _RecipeCostData] = {}
    for rid in recipe_ids:
        data = _load_recipe_cost_data(session, company_id, rid)
        if data is not None:
            sub_recipes[rid] = data

    ingredient_ids: set[int] = set()
    for data in sub_recipes.values():
        for line in data.lines:
            if line.ingredient_id is not None:
                ingredient_ids.add(line.ingredient_id)

    ingredients: dict[int, _IngredientCostData] = {}
    if ingredient_ids:
        rows = (
            session.query(Ingredient)
            .filter(
                Ingredient.company_id == company_id,
                Ingredient.id.in_(ingredient_ids),
            )
            .all()
        )
        for row in rows:
            ingredients[row.id] = _IngredientCostData(
                id=row.id,
                name=row.name,
                base_dimension=row.base_dimension,
                base_unit=row.base_unit,
                cost_per_base_unit=row.cost_per_base_unit,
                is_active=row.is_active,
            )
    return ingredients, sub_recipes


def _yield_dimension_from_unit(yield_unit: str) -> str:
    dimension, _ = _unit_dimension_and_factor(yield_unit)
    return dimension


# ── Service API ───────────────────────────────────────────────────────────────


def create_ingredient(
    session: Session,
    company_id: int,
    name: str,
    base_dimension: str,
    base_unit: str,
    cost_per_base_unit: float,
    user_id: int,
    *,
    notes: str | None = None,
    performed_by: str | None = None,
) -> MutationResult:
    validation = validate_ingredient(
        name=name,
        base_dimension=base_dimension,
        base_unit=base_unit,
        cost_per_base_unit=cost_per_base_unit,
    )
    if not validation.ok:
        return MutationResult(record_id=None, error=validation.errors[0])

    trimmed = name.strip()
    existing = (
        session.query(Ingredient.id)
        .filter(Ingredient.company_id == company_id, Ingredient.name == trimmed)
        .first()
    )
    if existing:
        return MutationResult(record_id=None, error="An ingredient with this name already exists.")

    now = datetime.datetime.now()
    row = Ingredient(
        company_id=company_id,
        name=trimmed,
        base_dimension=base_dimension.strip().lower(),
        base_unit=_normalize_unit(base_unit),
        cost_per_base_unit=round(cost_per_base_unit, 6),
        is_active=True,
        notes=notes,
        created_by_id=user_id,
        created_at=now,
    )
    session.add(row)
    session.flush()
    _write_audit(
        session,
        company_id=company_id,
        action="create_ingredient",
        entity_type="Ingredient",
        entity_id=row.id,
        description=f"Created ingredient '{trimmed}'",
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=row.id)


def update_ingredient_cost(
    session: Session,
    company_id: int,
    ingredient_id: int,
    cost_per_base_unit: float,
    user_id: int,
    *,
    performed_by: str | None = None,
) -> MutationResult:
    if cost_per_base_unit < 0:
        return MutationResult(record_id=None, error="cost_per_base_unit cannot be negative.")

    row = _get_ingredient_row(session, company_id, ingredient_id)
    if row is None:
        return MutationResult(record_id=None, error="Ingredient not found.")

    row.cost_per_base_unit = round(cost_per_base_unit, 6)
    row.updated_at = datetime.datetime.now()
    _write_audit(
        session,
        company_id=company_id,
        action="update_ingredient_cost",
        entity_type="Ingredient",
        entity_id=row.id,
        description=json.dumps({"cost_per_base_unit": row.cost_per_base_unit}),
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=row.id)


def bulk_update_costs(
    session: Session,
    company_id: int,
    updates: list[tuple[int, float]],
    user_id: int,
    *,
    performed_by: str | None = None,
) -> MutationResult:
    if not updates:
        return MutationResult(record_id=None, error="At least one cost update is required.")

    try:
        now = datetime.datetime.now()
        touched: list[int] = []
        for ingredient_id, cost in updates:
            if cost < 0:
                raise ValueError("cost_per_base_unit cannot be negative.")
            row = _get_ingredient_row(session, company_id, ingredient_id)
            if row is None:
                raise ValueError(f"Ingredient {ingredient_id} not found.")
            row.cost_per_base_unit = round(cost, 6)
            row.updated_at = now
            touched.append(row.id)

        _write_audit(
            session,
            company_id=company_id,
            action="bulk_update_ingredient_costs",
            entity_type="Ingredient",
            entity_id=touched[0],
            description=json.dumps({"ingredient_ids": touched, "count": len(touched)}),
            performed_by=performed_by,
        )
        session.commit()
        return MutationResult(record_id=touched[0])
    except ValueError as exc:
        session.rollback()
        return MutationResult(record_id=None, error=str(exc))


def deactivate_ingredient(
    session: Session,
    company_id: int,
    ingredient_id: int,
    user_id: int,
    *,
    performed_by: str | None = None,
) -> MutationResult:
    row = _get_ingredient_row(session, company_id, ingredient_id)
    if row is None:
        return MutationResult(record_id=None, error="Ingredient not found.")
    if not row.is_active:
        return MutationResult(record_id=row.id)

    row.is_active = False
    row.updated_at = datetime.datetime.now()
    _write_audit(
        session,
        company_id=company_id,
        action="deactivate_ingredient",
        entity_type="Ingredient",
        entity_id=row.id,
        description=f"Deactivated ingredient '{row.name}'",
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=row.id)


def save_recipe(
    session: Session,
    company_id: int,
    name: str,
    yield_quantity: float,
    yield_unit: str,
    lines: list[RecipeLineInput],
    user_id: int,
    *,
    recipe_id: int | None = None,
    description: str | None = None,
    performed_by: str | None = None,
) -> MutationResult:
    trimmed = (name or "").strip()
    if not trimmed:
        return MutationResult(record_id=None, error="Recipe name is required.")
    if yield_quantity <= 0:
        return MutationResult(record_id=None, error="yield_quantity must be positive.")

    try:
        yield_dimension = _yield_dimension_from_unit(yield_unit)
    except ValueError as exc:
        return MutationResult(record_id=None, error=str(exc))

    line_validation = validate_recipe_lines(lines, recipe_id=recipe_id)
    if not line_validation.ok:
        return MutationResult(record_id=None, error=line_validation.errors[0])

    for line in lines:
        if line.ingredient_id is not None:
            if _get_ingredient_row(session, company_id, line.ingredient_id) is None:
                return MutationResult(
                    record_id=None,
                    error=f"Ingredient {line.ingredient_id} not found.",
                )
        if line.sub_recipe_id is not None:
            if _get_recipe_row(session, company_id, line.sub_recipe_id) is None:
                return MutationResult(
                    record_id=None,
                    error=f"Sub-recipe {line.sub_recipe_id} not found.",
                )

    now = datetime.datetime.now()
    if recipe_id is None:
        dup = (
            session.query(Recipe.id)
            .filter(Recipe.company_id == company_id, Recipe.name == trimmed)
            .first()
        )
        if dup:
            return MutationResult(record_id=None, error="A recipe with this name already exists.")
        recipe = Recipe(
            company_id=company_id,
            name=trimmed,
            description=description,
            yield_quantity=yield_quantity,
            yield_unit=_normalize_unit(yield_unit),
            yield_dimension=yield_dimension,
            is_active=True,
            created_by_id=user_id,
            created_at=now,
        )
        session.add(recipe)
        session.flush()
        action = "create_recipe"
    else:
        recipe = _get_recipe_row(session, company_id, recipe_id)
        if recipe is None:
            return MutationResult(record_id=None, error="Recipe not found.")
        dup = (
            session.query(Recipe.id)
            .filter(
                Recipe.company_id == company_id,
                Recipe.name == trimmed,
                Recipe.id != recipe_id,
            )
            .first()
        )
        if dup:
            return MutationResult(record_id=None, error="A recipe with this name already exists.")
        for line in lines:
            if line.sub_recipe_id is not None and _would_create_cycle(
                session, company_id, recipe_id, line.sub_recipe_id
            ):
                return MutationResult(
                    record_id=None,
                    error="Sub-recipe reference would create a cycle.",
                )
        recipe.name = trimmed
        recipe.description = description
        recipe.yield_quantity = yield_quantity
        recipe.yield_unit = _normalize_unit(yield_unit)
        recipe.yield_dimension = yield_dimension
        recipe.updated_at = now
        session.query(RecipeLine).filter(RecipeLine.recipe_id == recipe_id).delete()
        action = "update_recipe"

    for line in lines:
        if line.sub_recipe_id is not None and _would_create_cycle(
            session, company_id, recipe.id, line.sub_recipe_id
        ):
            session.rollback()
            return MutationResult(
                record_id=None,
                error="Sub-recipe reference would create a cycle.",
            )
        session.add(
            RecipeLine(
                recipe_id=recipe.id,
                sort_order=line.sort_order,
                ingredient_id=line.ingredient_id,
                sub_recipe_id=line.sub_recipe_id,
                quantity=line.quantity,
                unit=_normalize_unit(line.unit),
                waste_percent=line.waste_percent,
                notes=line.notes,
            )
        )

    _write_audit(
        session,
        company_id=company_id,
        action=action,
        entity_type="Recipe",
        entity_id=recipe.id,
        description=f"Saved recipe '{trimmed}' with {len(lines)} line(s)",
        performed_by=performed_by,
    )
    session.commit()
    return MutationResult(record_id=recipe.id)


def compute_recipe_cost(
    recipe_or_session: _RecipeCostData | Session,
    ingredients_or_company_id: dict[int, _IngredientCostData] | int,
    sub_recipes_or_recipe_id: dict[int, _RecipeCostData] | int | None = None,
    *,
    depth: int = 0,
    visiting: frozenset[int] | None = None,
) -> RecipeCostBreakdown | None:
    """Pure graph rollup or DB-backed breakdown (Session as first argument)."""
    if isinstance(recipe_or_session, Session):
        session = recipe_or_session
        company_id = int(ingredients_or_company_id)  # type: ignore[arg-type]
        recipe_id = int(sub_recipes_or_recipe_id)  # type: ignore[arg-type]
        root = _load_recipe_cost_data(session, company_id, recipe_id)
        if root is None:
            return None
        ingredients, sub_recipes = _build_cost_maps(session, company_id, recipe_id)
        return _compute_recipe_cost_pure(root, ingredients, sub_recipes)
    return _compute_recipe_cost_pure(
        recipe_or_session,
        ingredients_or_company_id,  # type: ignore[arg-type]
        sub_recipes_or_recipe_id,  # type: ignore[arg-type]
        depth=depth,
        visiting=visiting,
    )


def _compute_recipe_cost_from_db(
    session: Session,
    company_id: int,
    recipe_id: int,
) -> RecipeCostBreakdown | None:
    return compute_recipe_cost(session, company_id, recipe_id)


def where_used(
    session: Session,
    company_id: int,
    *,
    ingredient_id: int | None = None,
    recipe_id: int | None = None,
) -> list[WhereUsedEntry]:
    """Direct and transitive parent recipes for an ingredient or sub-recipe."""
    if (ingredient_id is None) == (recipe_id is None):
        raise ValueError("Provide exactly one of ingredient_id or recipe_id.")

    seed: dict[int, tuple[str, str, int]] = {}

    if ingredient_id is not None:
        if _get_ingredient_row(session, company_id, ingredient_id) is None:
            return []
        rows = (
            session.query(Recipe.id, Recipe.name)
            .join(RecipeLine, RecipeLine.recipe_id == Recipe.id)
            .filter(
                Recipe.company_id == company_id,
                RecipeLine.ingredient_id == ingredient_id,
            )
            .all()
        )
        for rid, rname in rows:
            seed[rid] = (rname, "direct", 0)
    else:
        assert recipe_id is not None
        if _get_recipe_row(session, company_id, recipe_id) is None:
            return []
        rows = (
            session.query(Recipe.id, Recipe.name)
            .join(RecipeLine, RecipeLine.recipe_id == Recipe.id)
            .filter(
                Recipe.company_id == company_id,
                RecipeLine.sub_recipe_id == recipe_id,
            )
            .all()
        )
        for rid, rname in rows:
            seed[rid] = (rname, "direct", 0)

    results: dict[int, WhereUsedEntry] = {}
    frontier = list(seed.keys())
    while frontier:
        current_id = frontier.pop(0)
        if current_id in results:
            continue
        rname, usage_type, depth = seed[current_id]
        results[current_id] = WhereUsedEntry(
            recipe_id=current_id,
            recipe_name=rname,
            usage_type=usage_type,
            depth=depth,
        )
        parents = (
            session.query(Recipe.id, Recipe.name)
            .join(RecipeLine, RecipeLine.recipe_id == Recipe.id)
            .filter(
                Recipe.company_id == company_id,
                RecipeLine.sub_recipe_id == current_id,
            )
            .all()
        )
        for pid, pname in parents:
            if pid not in seed and pid not in results:
                seed[pid] = (pname, "transitive", depth + 1)
                frontier.append(pid)

    return sorted(results.values(), key=lambda e: (e.depth, e.recipe_name.lower()))
