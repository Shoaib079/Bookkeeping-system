"""i18n helpers — Phase 15 (EN / TR)."""

from __future__ import annotations

from registry.locales.messages import DEFAULT_LOCALE, MESSAGES, SUPPORTED_LOCALES
from registry.nav_labels import NAV_PAGE_I18N


def normalize_locale(code: str | None) -> str:
    if not code:
        return DEFAULT_LOCALE
    base = str(code).strip().lower().replace("_", "-").split("-")[0]
    return base if base in SUPPORTED_LOCALES else DEFAULT_LOCALE


def translate(key: str, locale: str | None = None, **kwargs) -> str:
    loc = normalize_locale(locale)
    from registry.locales.transactional import TRANSACTIONAL_EN, TRANSACTIONAL_TR

    _live = TRANSACTIONAL_TR if loc == "tr" else TRANSACTIONAL_EN
    # Prefer live transactional catalog — reloads reliably under Streamlit hot-reload.
    text = _live.get(key)
    if text is None:
        text = MESSAGES.get(loc, {}).get(key)
    if text is None and loc != DEFAULT_LOCALE:
        text = MESSAGES.get(DEFAULT_LOCALE, {}).get(key)
    if text is None:
        text = TRANSACTIONAL_EN.get(key)
    if text is None:
        text = TRANSACTIONAL_TR.get(key)
    if text is None:
        text = key
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text
    return text


def t(key: str, locale: str | None = None, **kwargs) -> str:
    """Translate a UI string for the interface locale."""
    return translate(key, locale, **kwargs)


def td(key: str, document_locale: str | None = None, **kwargs) -> str:
    """Translate for company documents (may differ from UI language)."""
    return translate(key, document_locale, **kwargs)


def registry_label(label_key: str, locale: str | None = None) -> str:
    """Resolve a registry label_key to localized text if mapped."""
    return translate(label_key, locale)


def page_title(nav_page_key: str, locale: str | None = None) -> str:
    """Localized page title (no emoji) from a canonical nav page key."""
    msg_key = NAV_PAGE_I18N.get(nav_page_key)
    if msg_key:
        return translate(msg_key, locale)
    if " " in nav_page_key:
        return nav_page_key.split(" ", 1)[1]
    return nav_page_key


def nav_display(page_key: str, locale: str | None = None) -> str:
    """Localized sidebar label for a canonical text-only nav page key."""
    msg_key = NAV_PAGE_I18N.get(page_key)
    if msg_key:
        return translate(msg_key, locale)
    return page_key
