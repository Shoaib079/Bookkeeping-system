"""LOGO-BUG-01 / ICON-SWEEP-01 — icon glyph rendering contracts.

Root cause of the broken-square icons: text-presentation-default Unicode emoji
(Emoji_Presentation=No per UTS#51) used WITHOUT the VS16 variation selector
(U+FE0F). Without VS16 the browser renders them from the text font stack, which
lacks those glyphs on many desktop platforms (tofu boxes). With VS16 they render
from the OS colour-emoji font, present on macOS, Windows, iOS and Android.

These contracts ban the bare forms so the bug cannot return.
"""

from __future__ import annotations

import re
from pathlib import Path

import app as erp
from registry.icon_glyphs import (
    NAV_CHART_OF_ACCOUNTS,
    NAV_FISCAL_PERIODS,
    NAV_GENERAL_LEDGER,
    NAV_JOURNAL_ENTRIES,
    NAV_TXN_LEDGER,
    TXH_DUPLICATE,
    TXH_EDIT,
    TXH_REPEAT,
    TXH_VIEW,
    TXH_VOID,
    VS16,
)
from registry.modules_catalog import MODULES, NAV_PAGES_IN_APP
from registry.nav_labels import NAV_PAGE_I18N

ROOT = Path(__file__).resolve().parents[1]

# Text-presentation-default glyphs used in this codebase — must always carry VS16.
FRAGILE_GLYPHS = (
    "\U0001F3DB",  # classical building (Owner Equity / Balance Sheet)
    "\U0001F5C2",  # card index dividers (General Ledger / Account Activity)
    "\U0001F5D3",  # spiral calendar (Fiscal Periods / Close Month)
    "\U0001F575",  # sleuth (Audit Log)
    "\U0001F5D1",  # wastebasket (delete actions)
    "\U0001F441",  # eye (view actions)
    "\U0001F5D2",  # spiral note pad
    "\U0001F4D3",  # notebook (Journal Entries)
    "\U0001F50D",  # magnifying glass (Chart of Accounts / audit expander)
    "\U0001F4D2",  # ledger (Transaction Ledger)
    "✏",      # pencil (edit actions)
    "☀",      # sun (theme toggle)
    "⚙",      # gear (settings)
    "⚠",      # warning sign
    "⚖",      # scales (Trial Balance)
    "⏸",      # pause (recurring)
    "⏭",      # skip (recurring)
    "⬇",      # down arrow
)

# Glyphs with no emoji presentation and poor desktop font coverage — banned outright.
BANNED_GLYPHS = (
    "⏻",  # power symbol (was sign-out icon; replaced with 🚪)
    "①", "②", "③", "④", "⑤", "⑥", "⑦",  # ①–⑦
)

UI_SOURCE_FILES = (
    ROOT / "app.py",
    ROOT / "registry" / "modules_catalog.py",
    ROOT / "registry" / "nav_labels.py",
    *sorted((ROOT / "registry" / "locales").glob("*.py")),
)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_fragile_emoji_always_carry_vs16():
    violations: list[str] = []
    for path in UI_SOURCE_FILES:
        text = _read(path)
        for ch in FRAGILE_GLYPHS:
            for m in re.finditer(re.escape(ch) + f"(?!{VS16})", text):
                line = text.count("\n", 0, m.start()) + 1
                violations.append(f"{path.name}:{line} bare U+{ord(ch):04X}")
    assert not violations, (
        "text-presentation emoji without VS16 render as broken squares on "
        "desktop — append \\ufe0f: " + "; ".join(violations[:10])
    )


def test_banned_glyphs_absent():
    violations: list[str] = []
    for path in UI_SOURCE_FILES:
        text = _read(path)
        for ch in BANNED_GLYPHS:
            n = text.count(ch)
            if n:
                violations.append(f"{path.name}: U+{ord(ch):04X} ×{n}")
    assert not violations, (
        "glyphs with no reliable cross-platform rendering: " + "; ".join(violations)
    )


def test_nav_dispatch_keys_consistent_with_vs16():
    """Nav keys with fragile icons must not use bare emoji literals in app.py."""
    src = _read(ROOT / "app.py")
    # Bare fragile prefixes must not appear outside VS16-qualified forms.
    for cp, label in (
        ("\U0001F5C2", "General"),
        ("\U0001F5D3", "Fiscal"),
        ("\U0001F4D3", "Journal"),
        ("\U0001F50D", "Chart"),
        ("\U0001F4D2", "Transaction"),
    ):
        assert cp + " " + label not in src.replace(cp + VS16, "")
    for const in (
        "NAV_GENERAL_LEDGER",
        "NAV_FISCAL_PERIODS",
        "NAV_JOURNAL_ENTRIES",
        "NAV_CHART_OF_ACCOUNTS",
        "NAV_TXN_LEDGER",
    ):
        assert const in src
    assert erp.NAV_GENERAL_LEDGER == NAV_GENERAL_LEDGER
    assert erp._TXN_LEDGER_PAGE_KEY == NAV_TXN_LEDGER


def test_modules_catalog_nav_pages_use_icon_glyphs():
    """Registry nav_page values must match canonical icon_glyphs constants."""
    mapped = {m.nav_page for m in MODULES if m.nav_page and not m.planned}
    for key in (
        NAV_TXN_LEDGER,
        NAV_GENERAL_LEDGER,
        NAV_FISCAL_PERIODS,
        NAV_JOURNAL_ENTRIES,
        NAV_CHART_OF_ACCOUNTS,
    ):
        assert key in mapped, f"missing module nav_page for {key!r}"
        assert key in NAV_PAGES_IN_APP
        assert key in NAV_PAGE_I18N


def test_icon_glyphs_nav_constants_carry_vs16():
    """Canonical nav keys in icon_glyphs.py must use VS16 on fragile prefixes."""
    fragile_nav = (
        NAV_TXN_LEDGER,
        NAV_GENERAL_LEDGER,
        NAV_FISCAL_PERIODS,
        NAV_JOURNAL_ENTRIES,
        NAV_CHART_OF_ACCOUNTS,
    )
    for key in fragile_nav:
        emoji = key.split(" ", 1)[0]
        assert emoji.endswith(VS16), f"{key!r} missing VS16 on nav emoji"


def test_txh_action_icons_use_icon_glyphs_module():
    """TXH action bar must wire shared icon constants (no inline fragile emoji)."""
    src = _read(ROOT / "app.py")
    bind = src[src.index("def _txh_bind_action_buttons"): src.index("def _txh_render_mobile_actions")]
    assert "button(TXH_VIEW" in bind
    assert "TXH_EDIT" in bind
    assert "TXH_REPEAT" in bind
    assert "TXH_DUPLICATE" in bind
    assert "TXH_VOID" in bind
    assert '"🔁"' not in bind
    assert erp.TXH_REPEAT == TXH_REPEAT
    assert erp.TXH_VIEW == TXH_VIEW
