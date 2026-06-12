"""UI-STAB-01 — shared initials avatar renderer (PROFILE-PHOTO-01 prep)."""

from __future__ import annotations

import html
from typing import Any

AVATAR_SIZES: frozenset[str] = frozenset({"sm", "md", "lg"})


def _resolve_user_names(user: Any) -> tuple[str, str | None]:
    if isinstance(user, dict):
        display = user.get("display_name") or user.get("username") or "User"
        username = user.get("username")
        return str(display), username
    display = (
        getattr(user, "display_name", None)
        or getattr(user, "username", None)
        or "User"
    )
    username = getattr(user, "username", None)
    return str(display), username


def user_initials(
    display_name: str | None = None,
    *,
    username: str | None = None,
    user: Any = None,
) -> str:
    """First letters of up to two name tokens; fallback U."""
    if user is not None:
        display_name, username = _resolve_user_names(user)
    label = (display_name or username or "User").strip()
    words = label.split()
    return "".join(w[0].upper() for w in words[:2]) or "U"


def user_avatar_html(
    user: Any,
    *,
    size: str = "md",
    element: str = "span",
) -> str:
    """Mono initials avatar markup — sm (header), md (login tiles), lg (My Account)."""
    sz = size if size in AVATAR_SIZES else "md"
    tag = element if element in ("span", "div") else "span"
    initials = user_initials(user=user)
    return (
        f'<{tag} class="erp-user-avatar erp-user-avatar--{sz}">'
        f"{html.escape(initials)}</{tag}>"
    )


def render_user_avatar(
    user: Any,
    *,
    size: str = "md",
    element: str = "span",
) -> str:
    """Return avatar HTML for ``st.markdown(..., unsafe_allow_html=True)``."""
    return user_avatar_html(user, size=size, element=element)
