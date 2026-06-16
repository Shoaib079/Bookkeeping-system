"""MONEY-DECIMAL-03 — contract tests for services/money.py helpers.

Pure-module guard: no SQLAlchemy, no posting integration, no ORM.
"""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

import pytest

from services import money

ROOT = Path(__file__).resolve().parents[1]
MONEY_MODULE_PATH = ROOT / "services" / "money.py"


class TestParseMoney:
    def test_float_100_01_uses_string_path(self):
        direct = Decimal(100.01)
        parsed = money.parse_money(100.01)
        assert parsed == Decimal("100.01")
        assert parsed != direct

    def test_string_input(self):
        assert money.parse_money("100.01") == Decimal("100.01")
        assert money.parse_money("  -42.50  ") == Decimal("-42.50")

    def test_decimal_input_passthrough(self):
        d = Decimal("99.99")
        assert money.parse_money(d) is d

    def test_int_input(self):
        assert money.parse_money(100) == Decimal("100")

    def test_float_binary_trap_avoided(self):
        assert money.parse_money(0.1) == Decimal("0.1")
        assert money.parse_money(0.1) != Decimal(0.1)

    def test_empty_string_rejected(self):
        with pytest.raises(ValueError, match="empty string"):
            money.parse_money("   ")

    def test_bool_rejected(self):
        with pytest.raises(TypeError, match="bool"):
            money.parse_money(True)


class TestQuantizeMoney:
    def test_two_decimal_places(self):
        assert money.quantize_money("100.019") == Decimal("100.02")
        assert money.quantize_money("100.011") == Decimal("100.01")

    def test_round_half_up_positive(self):
        assert money.quantize_money("2.675") == Decimal("2.68")
        assert money.quantize_money("2.674") == Decimal("2.67")

    def test_round_half_up_negative(self):
        assert money.quantize_money("-2.675") == Decimal("-2.68")
        assert money.quantize_money("-2.674") == Decimal("-2.67")

    def test_float_input_100_01(self):
        assert money.quantize_money(100.01) == Decimal("100.01")


class TestQuantizeFx:
    def test_four_decimal_places(self):
        assert money.quantize_fx("34.56789") == Decimal("34.5679")
        assert money.quantize_fx("34.56784") == Decimal("34.5678")

    def test_negative_fx_amount(self):
        assert money.quantize_fx("-0.00005") == Decimal("-0.0001")


class TestQuantizeRate:
    def test_eight_decimal_places(self):
        assert money.quantize_rate("34.567891234") == Decimal("34.56789123")
        assert money.quantize_rate("34.567891235") == Decimal("34.56789124")


class TestMoneyToFloat:
    def test_converts_after_quantization(self):
        assert money.money_to_float("100.019") == 100.02
        assert isinstance(money.money_to_float(100.01), float)

    def test_negative_value(self):
        assert money.money_to_float("-10.005") == -10.01


class TestDecimalEqual:
    def test_equal_after_quantization(self):
        assert money.decimal_equal("100.01", Decimal("100.010"))
        assert money.decimal_equal(100.01, "100.010")

    def test_not_equal_after_quantization(self):
        assert not money.decimal_equal("100.01", "100.02")

    def test_half_up_makes_equal(self):
        assert money.decimal_equal("2.674", "2.6744")


class TestConstants:
    def test_precision_constants(self):
        assert money.MONEY_PRECISION == Decimal("0.01")
        assert money.FX_PRECISION == Decimal("0.0001")
        assert money.RATE_PRECISION == Decimal("0.00000001")


class TestPureModule:
    def test_no_sqlalchemy_imports(self):
        source = MONEY_MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "sqlalchemy" not in alias.name
            elif isinstance(node, ast.ImportFrom):
                assert node.module is None or "sqlalchemy" not in node.module

    def test_module_docstring(self):
        assert money.__doc__ is not None
        assert "MONEY-DECIMAL-03" in money.__doc__

    def test_public_api_surface(self):
        names = {
            "parse_money",
            "quantize_money",
            "quantize_fx",
            "quantize_rate",
            "money_to_float",
            "decimal_equal",
            "MONEY_PRECISION",
            "FX_PRECISION",
            "RATE_PRECISION",
        }
        assert names <= set(dir(money))

    def test_no_posting_or_models_imports(self):
        tree = ast.parse(MONEY_MODULE_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in ("models", "services.posting", "posting")
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module not in ("models", "services.posting", "posting")
                assert not node.module.startswith("sqlalchemy")
