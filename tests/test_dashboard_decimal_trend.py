"""Regression: dashboard trend money math with PG Numeric (Decimal) aggregates."""

from __future__ import annotations

from decimal import Decimal

import pytest

from services.money import money_to_float


def _trend_net(sales, expenses) -> float:
    """Mirror render_dashboard 7-day trend Net column (display-only)."""
    return round(money_to_float(sales) - money_to_float(expenses), 2)


class TestDashboardTrendNet:
    def test_decimal_sales_float_expenses(self):
        assert _trend_net(Decimal("150.50"), 40.25) == 110.25

    def test_float_sales_decimal_expenses(self):
        assert _trend_net(200.0, Decimal("75.10")) == 124.90

    def test_both_decimal(self):
        assert _trend_net(Decimal("100.00"), Decimal("25.00")) == 75.0

    def test_both_float_sqlite_shape(self):
        assert _trend_net(100.0, 25.0) == 75.0

    def test_none_treated_as_zero(self):
        assert _trend_net(None, Decimal("10.00")) == -10.0


class TestDashboardTrendSourceContract:
    def test_render_dashboard_uses_dash_money(self):
        from pathlib import Path

        src = Path(__file__).resolve().parents[1] / "app.py"
        text = src.read_text(encoding="utf-8")
        start = text.index("def render_dashboard")
        end = text.index("\ndef ", start + 1)
        block = text[start:end]
        assert "def _dash_money" in block
        assert "money_to_float" in block
        assert "_trend_sales[d] - _trend_exp[d]" in block


@pytest.mark.optional_postgres
def test_pg_sale_sum_is_float_compatible():
    import os

    from sqlalchemy import create_engine, func, select

    import models
    from postgres_utils import get_test_postgres_url, require_test_postgres_url

    if get_test_postgres_url() is None:
        pytest.skip("ERP_TEST_POSTGRES_URL not set")

    url = require_test_postgres_url()
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            raw = conn.execute(select(func.sum(models.Sale.amount))).scalar()
        if raw is None:
            pytest.skip("No sales in PG test DB")
        net = _trend_net(raw, 0.0)
        assert isinstance(net, float)
    finally:
        engine.dispose()
