"""P0-2 — mobile Add Transaction type selection uses Concept C Row 1 picker.

Concept C (MOB-AT-C1) replaced the 4-tab row with a compact Row 1 type picker.
_MOB_AT_TABS constants are kept for backward-compat / legacy reference; the active
type picker uses _MOB_AT_C_TYPE_ROWS with named labels and colour keys.
"""

from __future__ import annotations

import inspect

import app as erp
from registry.i18n import t


def test_mob_at_tab_i18n_keys_resolve_tr():
    """_MOB_AT_TABS constants still resolve to localized strings (legacy reference)."""
    for _idx, key, _fallback in erp._MOB_AT_TABS:
        assert t(key, "tr") != key


def test_mob_at_c_type_rows_defined():
    """Concept C type picker must have all 7 type entries including Salary."""
    type_keys = [row[2] for row in erp._MOB_AT_C_TYPE_ROWS]
    assert "sale" in type_keys
    assert "expense" in type_keys
    assert "purchase" in type_keys
    assert "salary" in type_keys
    assert len(type_keys) == 7


def test_render_mobile_at_uses_concept_c_row1():
    """Concept C panel must call Row 1 helper and not use old tab-chip loop."""
    src = inspect.getsource(erp._render_add_transaction_mobile)
    # Concept C Row 1 must be called from the panel
    assert "_mob_at_render_c_row1" in src
    # Old individual tab buttons must not be present
    assert 'key=f"mob_at_tab_{' not in src
