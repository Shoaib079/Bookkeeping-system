"""ICON-SWEEP-01 / LOGO-BUG-01 — canonical cross-platform emoji nav + action icons.

Text-presentation-default emoji (Emoji_Presentation=No) must carry U+FE0F (VS16)
so browsers use the OS colour-emoji font instead of the text font stack (tofu).
"""

from __future__ import annotations

VS16 = "\ufe0f"


def with_vs16(base: str) -> str:
    """Return *base* with VS16 appended when missing."""
    return base if base.endswith(VS16) else base + VS16


# ── Nav page keys (must match app.py _PAGE_DISPATCH + nav_labels NAV_PAGE_I18N) ─
NAV_TXN_LEDGER = with_vs16("\U0001F4D2") + " Transaction Ledger"
NAV_GENERAL_LEDGER = with_vs16("\U0001F5C2") + " General Ledger"
NAV_FISCAL_PERIODS = with_vs16("\U0001F5D3") + " Fiscal Periods"
NAV_JOURNAL_ENTRIES = with_vs16("\U0001F4D3") + " Journal Entries"
NAV_CHART_OF_ACCOUNTS = with_vs16("\U0001F50D") + " Chart of Accounts"
NAV_RECURRING_EXPENSES = "\U0001F501 Recurring Expenses"  # 🔁 — emoji-presentation OK for nav

# ── Transaction History action bar (emoji-only Streamlit buttons) ─────────────
TXH_VIEW = with_vs16("\U0001F441")  # 👁️
TXH_EDIT = with_vs16("\u270f")  # ✏️
# 🔄 replaces 🔁 — broader OS emoji-font coverage for compact action buttons
TXH_REPEAT = "\U0001F504"
TXH_DUPLICATE = "\U0001F4CB"  # 📋
TXH_VOID = "\U0001F6AB"  # 🚫
