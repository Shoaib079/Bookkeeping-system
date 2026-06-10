"""P0-6 — SETUP-01 create failures map to catalog keys only."""

from __future__ import annotations

import inspect

import app as erp
from registry.i18n import t


def test_map_setup01_create_error_name_required():
    assert erp._map_setup01_create_error(ValueError("Company name is required.")) == "picker.name_required"


def test_map_setup01_create_error_unknown_value_error():
    assert erp._map_setup01_create_error(ValueError("database unavailable")) == "picker.create_failed"


def test_map_setup01_create_error_generic_exception_path():
    assert erp._map_setup01_create_error(RuntimeError("boom")) == "picker.create_failed"


def test_setup01_error_keys_resolve_tr():
    for key in ("picker.name_required", "picker.create_failed", "setup01.settings_failed"):
        assert t(key, "tr") != key


def test_wizard_error_display_always_uses_tw():
    from ui import setup01_wizard

    src = inspect.getsource(setup01_wizard.render_setup01_wizard)
    assert '_tw(t, str(err_key), str(err_key))' in src
    assert 'if "." in str(err_key)' not in src
