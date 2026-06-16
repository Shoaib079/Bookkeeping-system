"""MD-05-IMPL-3 — quantization boundary + cache re-sync contract tests."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from money_numeric_columns import NUMERIC_19_4, scale_for

ROOT = Path(__file__).resolve().parents[1]
MATCH_POST_PATH = ROOT / "reconciliation" / "match_post.py"
REVISION_0002_PATH = ROOT / "alembic" / "versions" / "0002_money_numeric.py"
APP_PATH = ROOT / "app.py"
MODELS_PATH = ROOT / "models.py"
BANKING_BALANCE_PATH = ROOT / "services" / "banking_balance.py"
POSTING_PATH = ROOT / "services" / "posting.py"


@pytest.fixture(scope="module")
def match_post_source() -> str:
    return MATCH_POST_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def revision_source() -> str:
    return REVISION_0002_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def app_source() -> str:
    return APP_PATH.read_text(encoding="utf-8")


class TestMatchPostQuantizationBoundary:
    def test_no_business_critical_round_float(self, match_post_source: str):
        assert 'round(float(' not in match_post_source

    def test_uses_money_helpers(self, match_post_source: str):
        assert "from services.money import" in match_post_source
        assert "money_to_float" in match_post_source
        assert "persist_money" in match_post_source


class TestAlembicRoundHalfUpUsing:
    def test_pg_using_explicit_round(self, revision_source: str):
        assert re.search(r'postgresql_using=f"ROUND\(\{column\}::numeric, \{scale\}\)"', revision_source)


class TestIngredientsFxTier:
    def test_classification_is_19_4(self):
        assert ("ingredients", "cost_per_base_unit") in NUMERIC_19_4
        assert scale_for("ingredients", "cost_per_base_unit") == 4

    def test_model_uses_numeric_fx(self):
        models = MODELS_PATH.read_text(encoding="utf-8")
        assert "cost_per_base_unit = Column(NUMERIC_FX" in models


class TestCacheResync:
    def test_sync_account_balances_uses_persist_money(self, app_source: str):
        start = app_source.index("def sync_account_balances")
        end = app_source.index("\n\n", start)
        block = app_source[start:end]
        assert "persist_money" in block
        assert "calculate_account_balance" in block

    def test_sync_bank_account_balances_defined(self):
        src = BANKING_BALANCE_PATH.read_text(encoding="utf-8")
        assert "def sync_bank_account_balances(" in src
        assert "def derive_bank_account_balance(" in src

    def test_startup_calls_bank_sync(self, app_source: str):
        assert "sync_bank_account_balances(_boot_session)" in app_source


class TestPostingJeLineMoneyPreserved:
    def test_je_line_money_documented_and_present(self):
        src = POSTING_PATH.read_text(encoding="utf-8")
        assert "def _je_line_money(" in src
        assert "MD-02" in src or "golden" in src.lower() or "characterization" in src.lower()
        assert "_normalize_money_amount" not in src
        assert "_allocation_share_float" not in src
