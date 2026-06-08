"""SETUP-01 wizard — all UI strings resolve in EN and TR (no raw keys)."""

from __future__ import annotations

from registry.i18n import t
from registry.locales.messages import MESSAGES
from registry.setup01_wizard import SETUP01_I18N_KEYS


def test_setup01_keys_exist_en_and_tr():
    for key in SETUP01_I18N_KEYS:
        assert key in MESSAGES["en"], f"missing EN: {key}"
        assert key in MESSAGES["tr"], f"missing TR: {key}"


def test_setup01_translate_never_returns_key():
    for key in SETUP01_I18N_KEYS:
        for loc in ("en", "tr"):
            text = t(key, loc, n=3, option="Example")
            assert text != key, f"unresolved {loc} key: {key}"
