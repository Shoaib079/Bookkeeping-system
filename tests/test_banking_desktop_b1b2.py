"""BANKING-DESKTOP-01 B1+B2 — Banking chip switchers + POS Settlement wording."""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import app as erp
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from ui.theme import load_theme_css

ROOT = Path(__file__).resolve().parents[1]
BANKING_CSS = ROOT / "ui" / "banking.css"
THEME_PY = ROOT / "ui" / "theme.py"

# Workflow labels retired by BANK-03 (GL account name "Card Sales Clearing" is allowed).
_STALE_WORKFLOW_PATTERNS = (
    re.compile(r"card[\s-]sales[\s-]clearing", re.I),
    re.compile(r"card[\s-]settlement", re.I),
    re.compile(r"card sales → bank", re.I),
    re.compile(r"kart satışı → banka", re.I),
    re.compile(r"(?<!Sales )card clearing", re.I),
    re.compile(r"\bclearing sales\b", re.I),
    re.compile(r"deposit clearing", re.I),
    re.compile(r"\bBSI\b"),
    re.compile(r"\btakas satış", re.I),
)

# Keys that may still mention Card Sales Clearing as the GL account name.
_GL_ACCOUNT_OK_PREFIXES = (
    "settings.banking.card_settlement_help",
    "settings.banking.backfill.",
    "settings.banking.backfill_done",
    "bank.settings.card_settlement.caption",
    "banking.import.section.",
    "banking.import.match.",
    "banking.pos_preview.",
    "banking.pos_entry.",
    "banking.clearing_visibility.",
    "banking.unsettled_card_sales.",
    "banking.match_failure.",
)


def _read(name: str) -> str:
    return (ROOT / "ui" / name).read_text(encoding="utf-8")


def test_banking_css_registered_in_theme_loader():
    assert BANKING_CSS.is_file()
    theme_py = THEME_PY.read_text(encoding="utf-8")
    assert "banking.css" in theme_py
    assert "_BANKING_CSS_PATH" in theme_py
    bundled = load_theme_css()
    assert BANKING_CSS.read_text(encoding="utf-8") in bundled


def test_banking_chip_layout_in_banking_css():
    css = _read("banking.css")
    assert "MONO-THEME-01-S6" in css or "BANKING-DESKTOP-01" in css
    assert "erp-bank-sel-chip-host" in css
    assert "st-key-bank_sec_sel_" in css
    assert "grid-template-columns: repeat(2" in css


def test_banking_css_not_in_mobile_viewport_owner_list():
    theme_py = THEME_PY.read_text(encoding="utf-8")
    block = theme_py.split("MOBILE_VIEWPORT_CSS_OWNER_FILES")[1].split(")")[0]
    assert "banking.css" not in block


def test_banking_section_select_chips_not_radio():
    src = inspect.getsource(erp._banking_section_select)
    assert "bank_sec_sel_" in src
    assert "erp-bank-sel-chip-host" in src
    assert "st.radio" not in src
    assert "return st.session_state[widget_key]" in src


def test_render_banking_uses_chips_and_banking_section_key():
    src = inspect.getsource(erp.render_banking)
    assert "st.radio" not in src
    assert '_banking_section_select(\n        "banking_section"' in src or '_banking_section_select("banking_section"' in src
    assert '"banking_section"' in src
    assert 'section == "import"' in src
    assert 'section == "settings"' in src
    assert "_render_banking_statement_import" in src
    assert "_render_banking_page_settings" in src


def test_render_bank_statement_import_uses_chips_and_bsi_section_key():
    src = inspect.getsource(erp.render_bank_statement_import)
    nav_block = src.split("st.divider()", 1)[0]
    assert "st.radio" not in nav_block
    assert '_banking_section_select("bsi_section"' in src
    assert 'section == "upload"' in src
    assert 'section == "review"' in src
    assert 'section == "match"' in src
    assert 'section == "history"' in src


def test_bsi_staged_upload_state_not_cleared_on_section_switch():
    """Chip navigation only updates bsi_section — staged file bytes survive tab hops."""
    chip_src = inspect.getsource(erp._banking_section_select)
    assert "bsi_file_bytes" not in chip_src
    assert "bsi_file_name" not in chip_src
    assert "pop(" not in chip_src
    nav_block = inspect.getsource(erp.render_bank_statement_import).split("st.divider()", 1)[0]
    assert "bsi_file_bytes" not in nav_block
    assert "bsi_file_name" not in nav_block


def test_no_stale_card_settlement_workflow_wording_en():
    offenders = []
    for key, text in TRANSACTIONAL_EN.items():
        if any(key.startswith(p) for p in _GL_ACCOUNT_OK_PREFIXES):
            continue
        if any(pat.search(text) for pat in _STALE_WORKFLOW_PATTERNS):
            offenders.append(key)
    assert not offenders, f"Stale EN workflow wording: {', '.join(offenders)}"


def test_no_stale_card_settlement_workflow_wording_tr():
    offenders = []
    for key, text in TRANSACTIONAL_TR.items():
        if any(key.startswith(p) for p in _GL_ACCOUNT_OK_PREFIXES):
            continue
        if any(pat.search(text) for pat in _STALE_WORKFLOW_PATTERNS):
            offenders.append(key)
    assert not offenders, f"Stale TR workflow wording: {', '.join(offenders)}"


def test_pos_settlement_wording_present_en():
    assert TRANSACTIONAL_EN["bank.settings.card_settlement.section"] == "POS Settlement"
    assert "POS Settlement" in TRANSACTIONAL_EN["settings.banking.card_settlement_enabled"]
    assert "POS Settlement" in TRANSACTIONAL_EN["banking.import.match.needs_settlement"]


def test_pos_settlement_wording_present_tr():
    assert TRANSACTIONAL_TR["bank.settings.card_settlement.section"] == "POS Mutabakatı"
    assert "POS Mutabakat" in TRANSACTIONAL_TR["settings.banking.card_settlement_enabled"]
    assert "POS Mutabakat" in TRANSACTIONAL_TR["banking.import.match.needs_settlement"]
