"""My Account page — source contracts (crash guards, role badge)."""

from __future__ import annotations

import inspect
import re

import app as erp


def _render_my_account_source() -> str:
    return inspect.getsource(erp.render_my_account)


def test_render_my_account_role_badge_no_undefined_rc():
    src = _render_my_account_source()
    assert "{_rc}" not in src
    assert "mono_role_pill_html" in src
    assert "_role_badge = mono_role_pill_html" in src


def test_render_my_account_no_undefined_short_css_vars():
    """Short inline CSS placeholders must be defined in function scope."""
    src = _render_my_account_source()
    undefined_patterns = ("{_rc}", "{_bg}", "{_fg}", "{_pill}")
    for pattern in undefined_patterns:
        assert pattern not in src, f"undefined CSS placeholder in render_my_account: {pattern}"

    # f-string style tokens like background:{_rc} without a prior assignment
    for name in ("_rc", "_bg", "_fg", "_pill"):
        uses = [m.start() for m in re.finditer(rf"\{{{name}\}}", src)]
        if not uses:
            continue
        before = src[: uses[0]]
        assert f"{name} =" in before or f"{name}=" in before, (
            f"{name} used in HTML but not assigned in render_my_account"
        )
