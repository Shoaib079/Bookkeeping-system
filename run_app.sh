#!/usr/bin/env bash
# Run Streamlit from the project root so `registry` imports resolve correctly.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
find registry -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
exec "$ROOT/.venv/bin/streamlit" run app.py --server.port 8501 "$@"
