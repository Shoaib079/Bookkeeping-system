"""Ensure project root is on sys.path so `import models` works without PYTHONPATH=."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_TESTS = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_TESTS) not in sys.path:
    sys.path.insert(0, str(_TESTS))


@pytest.fixture(autouse=True)
def _ensure_streamlit_components_v1_shim():
    """Register components.v1 when tests replace streamlit with a non-package mock."""
    st = sys.modules.get("streamlit")
    if st is None or getattr(st, "__path__", None) is not None:
        yield
        return
    if "streamlit.components" not in sys.modules:
        sys.modules["streamlit.components"] = MagicMock()
    if "streamlit.components.v1" not in sys.modules:
        sys.modules["streamlit.components.v1"] = MagicMock()
    yield
