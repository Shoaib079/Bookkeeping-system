"""FASTAPI-REACT-38 — read-only product catalog DTOs and compute."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models import Product


@dataclass(frozen=True, slots=True)
class ProductListRow:
    id: int
    sku: str | None
    name: str
    category: str | None
    subcategory: str | None
    unit_of_measure: str | None
    quantity: float
    min_stock: float
    stock_status: str
    cost_price: float
    unit_price: float
    is_active: bool
    company_id: int


@dataclass(frozen=True, slots=True)
class ProductsListStats:
    total: int
    low_stock: int
    out_of_stock: int


@dataclass(frozen=True, slots=True)
class ProductsListPage:
    rows: tuple[ProductListRow, ...]
    row_count: int
    stats: ProductsListStats
    company_id: int


def _stock_status(quantity: float, min_stock: float) -> str:
    if quantity <= 0:
        return "out"
    if min_stock > 0 and quantity <= min_stock:
        return "low"
    return "ok"


def compute_products_list(
    session: Session,
    *,
    company_id: int,
    active_only: bool = True,
) -> ProductsListPage:
    query = (
        session.query(Product)
        .filter(Product.company_id == company_id)
        .order_by(Product.name, Product.id)
    )
    if active_only:
        query = query.filter(Product.is_active == True)  # noqa: E712
    products = query.all()
    rows: list[ProductListRow] = []
    low_stock = out_of_stock = 0
    for product in products:
        quantity = float(product.quantity or 0)
        min_stock = float(product.min_stock or 0)
        status = _stock_status(quantity, min_stock)
        if status == "low":
            low_stock += 1
        elif status == "out":
            out_of_stock += 1
        rows.append(
            ProductListRow(
                id=product.id,
                sku=product.sku,
                name=product.name,
                category=product.category,
                subcategory=product.subcategory,
                unit_of_measure=product.unit_of_measure,
                quantity=quantity,
                min_stock=min_stock,
                stock_status=status,
                cost_price=float(product.cost_price or 0),
                unit_price=float(product.unit_price or 0),
                is_active=bool(product.is_active),
                company_id=company_id,
            )
        )
    return ProductsListPage(
        rows=tuple(rows),
        row_count=len(rows),
        stats=ProductsListStats(
            total=len(rows),
            low_stock=low_stock,
            out_of_stock=out_of_stock,
        ),
        company_id=company_id,
    )
