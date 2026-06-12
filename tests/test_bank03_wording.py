"""BANK-03 — Banking page naming and POS Settlement wording verification."""
from __future__ import annotations

import inspect
import re

import app as erp
from registry.i18n import t
from registry.locales.messages import MESSAGES
from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR
from registry.nav_keys import NAV_BANKING

_BANKING_KEY_PREFIXES = (
    "bank.",
    "banking.",
    "settings.banking.",
    "nav.bottom.banking",
    "nav.mobile.banking",
    "nav.mobile.hub.banking",
    "nav.banking",
)

_CANONICAL_EN = {
    "banking.pos_entry.title": "POS / Card Settlement",
    "banking.pos_entry.open": "Open POS / Card Settlement",
    "banking.pos_preview.section_title": "Settlement preview",
    "banking.match_failure.section_title": "Match check",
    "banking.import.match.kind.card_clearing": "Card sales deposit",
    "banking.clearing_visibility.section_title": "Card Sales Clearing (1150)",
    "bank.settings.card_settlement.section": "POS Settlement",
}

_CANONICAL_TR = {
    "banking.pos_entry.title": "POS / Kart Mutabakatı",
    "banking.pos_preview.section_title": "Mutabakat önizlemesi",
    "banking.match_failure.section_title": "Eşleşme kontrolü",
    "banking.clearing_visibility.section_title": "Kart Satış Takası (1150)",
    "bank.settings.card_settlement.section": "POS Mutabakatı",
}

_BANNED_USER_PATTERNS = (
    re.compile(r"\bBSI\b"),
    re.compile(r"deposit clearing", re.I),
    re.compile(r"(?<!Sales )card clearing", re.I),
    re.compile(r"\bclearing sales\b", re.I),
    re.compile(r"\btakas satış", re.I),
)

_GL_ACCOUNT_OK_PREFIXES = (
    "settings.banking.card_settlement_help",
    "settings.banking.backfill.",
    "settings.banking.backfill_done",
    "bank.settings.card_settlement.caption",
    "banking.import.match.pos_settlement_explainer",
    "banking.pos_preview.",
    "banking.pos_entry.",
    "banking.clearing_visibility.",
    "banking.unsettled_card_sales.",
    "banking.match_failure.",
)


def _banking_keys(catalog: dict[str, str]) -> list[str]:
    return sorted(
        k
        for k in catalog
        if any(k.startswith(p) for p in _BANKING_KEY_PREFIXES)
    )


def _offenders(catalog: dict[str, str]) -> list[str]:
    bad: list[str] = []
    for key, text in catalog.items():
        if not any(key.startswith(p) for p in _BANKING_KEY_PREFIXES):
            continue
        if any(key.startswith(p) for p in _GL_ACCOUNT_OK_PREFIXES):
            if not any(pat.search(text) for pat in _BANNED_USER_PATTERNS):
                continue
        if any(pat.search(text) for pat in _BANNED_USER_PATTERNS):
            bad.append(key)
    return bad


class TestCanonicalWording:
    def test_canonical_en_labels(self):
        for key, expected in _CANONICAL_EN.items():
            assert TRANSACTIONAL_EN[key] == expected
            assert t(key, "en") == expected

    def test_canonical_tr_labels(self):
        for key, expected in _CANONICAL_TR.items():
            assert TRANSACTIONAL_TR[key] == expected
            assert t(key, "tr") == expected


class TestNoStaleWorkflowTerms:
    def test_no_banned_terms_in_en_banking_locales(self):
        assert not _offenders(TRANSACTIONAL_EN), (
            f"Stale EN banking wording: {', '.join(_offenders(TRANSACTIONAL_EN))}"
        )

    def test_no_banned_terms_in_tr_banking_locales(self):
        assert not _offenders(TRANSACTIONAL_TR), (
            f"Stale TR banking wording: {', '.join(_offenders(TRANSACTIONAL_TR))}"
        )


class TestLocaleCoverage:
    def test_all_banking_keys_resolve_en(self):
        for key in _banking_keys(TRANSACTIONAL_EN):
            text = t(key, "en")
            assert text != key, f"unresolved EN key: {key}"
            assert not text.startswith("banking."), f"raw EN key: {key}"

    def test_all_banking_keys_resolve_tr(self):
        for key in _banking_keys(TRANSACTIONAL_TR):
            text = t(key, "tr")
            assert text != key, f"unresolved TR key: {key}"
            assert not text.startswith("banking."), f"raw TR key: {key}"

    def test_messages_duplicates_match_transactional_en(self):
        for key in _banking_keys(MESSAGES["en"]):
            if key in TRANSACTIONAL_EN:
                assert MESSAGES["en"][key] == TRANSACTIONAL_EN[key], key

    def test_messages_duplicates_match_transactional_tr(self):
        for key in _banking_keys(MESSAGES["tr"]):
            if key in TRANSACTIONAL_TR:
                assert MESSAGES["tr"][key] == TRANSACTIONAL_TR[key], key


class TestBankingPageHeaders:
    def test_render_banking_uses_localized_nav_title(self):
        src = inspect.getsource(erp.render_banking)
        assert "_st_page_title(NAV_BANKING)" in src
        assert '_st_page_title("Banking")' not in src

    def test_banking_chips_use_locale_keys(self):
        src = inspect.getsource(erp.render_banking)
        assert '("import", "bank.section.import")' in src
        assert '("settings", "bank.section.settings")' in src
        assert '("pos_settlement", "banking.pos_entry.title")' in src

    def test_statement_import_uses_banking_import_title(self):
        src = inspect.getsource(erp.render_bank_statement_import)
        assert "banking.import.title" in src
        assert "banking.import.nav." in src
