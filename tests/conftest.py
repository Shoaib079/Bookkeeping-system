"""Ensure project root is on sys.path so `import models` works without PYTHONPATH=."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TESTS = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_TESTS) not in sys.path:
    sys.path.insert(0, str(_TESTS))
