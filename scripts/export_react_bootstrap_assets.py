#!/usr/bin/env python3
"""FASTAPI-REACT-05 — export design tokens + route map for the React SPA bootstrap."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "frontend" / "src" / "generated"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module {name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_navigation_registry():
    """Load ``registry.navigation`` without ``registry.__init__`` (no DB)."""
    import types

    _load_module("registry.nav_keys", ROOT / "registry" / "nav_keys.py")
    _load_module("registry.nav_group_hints", ROOT / "registry" / "nav_group_hints.py")
    _load_module("registry.nav_labels", ROOT / "registry" / "nav_labels.py")
    _load_module("registry.icon_svg", ROOT / "registry" / "icon_svg.py")
    pkg = types.ModuleType("registry")
    pkg.nav_keys = sys.modules["registry.nav_keys"]
    pkg.nav_group_hints = sys.modules["registry.nav_group_hints"]
    pkg.nav_labels = sys.modules["registry.nav_labels"]
    pkg.icon_svg = sys.modules["registry.icon_svg"]
    sys.modules["registry"] = pkg
    return _load_module("registry.navigation", ROOT / "registry" / "navigation.py")


def export_assets() -> None:
    sys.path.insert(0, str(ROOT))
    from ui.react_design_contract import react_token_bundle

    navigation = _load_navigation_registry()
    rows = navigation.react_route_contract_rows()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    tokens_path = OUT_DIR / "design-tokens.json"
    tokens_path.write_text(
        json.dumps(react_token_bundle(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    routes_payload = {
        "version": "NAV-ARCH-S4",
        "routes": [
            {"routeKey": key, "path": path} for key, path in rows
        ],
    }
    routes_path = OUT_DIR / "routes.json"
    routes_path.write_text(
        json.dumps(routes_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {tokens_path.relative_to(ROOT)} ({len(rows)} routes)")


def main() -> None:
    export_assets()


if __name__ == "__main__":
    main()
