"""WO-C B1 — honest search scope, Transaction History filters, empty states."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = MagicMock()
sys.modules["streamlit"].session_state = {}

import app as erp

ROOT = Path(__file__).resolve().parents[1]


def test_header_search_only_on_table_pages():
    assert erp._header_search_active("💳 Expenses")
    assert erp._header_search_active("💼 Sales")
    assert erp._header_search_active("📄 Receivables")
    assert not erp._header_search_active("🏠 Home")
    assert not erp._header_search_active("📊 Reports")
    assert not erp._header_search_active("🏢 Vendors")


def test_header_search_conditionally_rendered():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "_header_search_active(page_key)" in src
    assert 'key="hdr_search_panel"' in src
    assert "st.caption(_t(_header_search_scope_key(page_key)))" in src


def test_txh_matches_keyword_fields():
    assert erp._txh_matches_keyword("", party="Acme")
    assert erp._txh_matches_keyword("acme", party="Acme Corp")
    assert erp._txh_matches_keyword("lunch", description="Team lunch")
    assert erp._txh_matches_keyword("cash", txn_type="Cash Sale", method="Cash")
    assert erp._txh_matches_keyword("150", amount=150.0)
    assert erp._txh_matches_keyword("inv-42", reference="INV-42")
    assert not erp._txh_matches_keyword("missing", party="Acme", description="widgets")


def test_txh_date_filters_from_to_only():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'key="txh_date_from"' in src
    assert 'key="txh_date_to"' in src
    assert "txh_date_preset" not in src
    assert "_TXH_DATE_PRESETS" not in src


def test_txh_inline_search_and_date_filters_wired():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'key="txh_search"' in src
    assert "_txh_search_keyword()" in src
    assert "_render_txh_date_filters" in src
    assert 'st.info(_t("search.no_results_table"))' in src


def test_local_table_search_labels():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '_t("search.table_label")' in src
    assert '_t("search.table_ph")' in src
    assert 'key="vendor_search"' in src
    assert 'key="payables_search"' in src
    assert 'key="inv_search"' in src


def test_search_scope_i18n():
    from registry.i18n import t

    assert t("search.no_results_table", "en") == "No results found in this table."
    assert t("search.scope.txn_history", "en") == "Searching Transaction Ledger only"
    assert t("search.date.today", "en") == "Today"
    assert t("search.date.this_month", "en") == "This Month"
    assert t("search.date.custom", "en") == "Custom Range"
