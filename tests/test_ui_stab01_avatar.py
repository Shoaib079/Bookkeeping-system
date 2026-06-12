"""UI-STAB-01 — shared initials avatar renderer."""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import app as erp
from ui.avatar import render_user_avatar, user_initials

ROOT = Path(__file__).resolve().parents[1]
APP_SRC = (ROOT / "app.py").read_text(encoding="utf-8")
THEME_CSS = (ROOT / "ui" / "theme.css").read_text(encoding="utf-8")


class TestAvatarHelper:
    def test_initials_two_words(self):
        assert user_initials(display_name="Jane Doe") == "JD"

    def test_initials_single_word(self):
        assert user_initials(display_name="Admin") == "A"

    def test_initials_fallback(self):
        assert user_initials(display_name="", username="") == "U"

    def test_render_sizes(self):
        user = {"display_name": "Sam Lee", "username": "sam"}
        for size in ("sm", "md", "lg"):
            html = render_user_avatar(user, size=size)
            assert f"erp-user-avatar--{size}" in html
            assert "SL" in html

    def test_html_escapes_initials(self):
        html = render_user_avatar({"display_name": "Sam <tag>"}, size="md")
        assert "S&lt;" in html
        assert "<tag>" not in html


class TestSharedRendererWiring:
    def test_header_profile_panel_uses_shared_renderer(self):
        src = inspect.getsource(erp._render_hdr_profile_panel_content)
        assert "render_user_avatar" in src
        assert "erp-hdr-profile-avatar" not in src
        assert "w[0].upper" not in src

    def test_header_toolbar_popover_uses_user_initials(self):
        src = inspect.getsource(erp._render_hdr_toolbar)
        assert "user_initials" in src
        assert "w[0].upper" not in src

    def test_mobile_profile_uses_shared_panel(self):
        src = inspect.getsource(erp._render_mobile_profile_sheet)
        assert "_render_hdr_profile_panel_content" in src

    def test_my_account_uses_shared_renderer(self):
        src = inspect.getsource(erp.render_my_account)
        assert "render_user_avatar" in src
        assert 'erp-mono-avatar' not in src
        assert "w[0].upper" not in src

    def test_login_tiles_use_shared_renderer(self):
        src = inspect.getsource(erp.render_login)
        assert "render_user_avatar" in src
        assert "erp-user-avatar--md" in src or 'size="md"' in src
        assert "w[0].upper" not in src


class TestNoDuplicateGenerators:
    def test_app_has_no_inline_initials_avatar_markup(self):
        assert not re.search(r'w\[0\]\.upper', APP_SRC)
        assert "erp-hdr-profile-avatar" not in APP_SRC
        assert 'class="erp-mono-avatar"' not in APP_SRC

    def test_avatar_css_contract(self):
        assert ".erp-user-avatar--sm" in THEME_CSS
        assert ".erp-user-avatar--md" in THEME_CSS
        assert ".erp-user-avatar--lg" in THEME_CSS
