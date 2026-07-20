#!/bin/bash
# Launch an MCP server module from the irene_mcp or laraq_mcp package.
# Usage: run.sh <module>   e.g. run.sh irene_mcp.hpc_server, run.sh laraq_mcp.server
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE="$1"
shift || true

if command -v uv >/dev/null 2>&1; then
    exec uv run --quiet --directory "$DIR" python -m "$MODULE" "$@"
fi

VENV="$DIR/.venv"
if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV" >&2
    "$VENV/bin/pip" install --quiet --upgrade pip >&2
fi
# (Re)install if the package or its deps are missing.
if ! "$VENV/bin/python" -c "import irene_mcp, laraq_mcp, mcp, hpc_agent_core" >/dev/null 2>&1; then
    "$VENV/bin/pip" install --quiet -e "$DIR" >&2
fi

exec "$VENV/bin/python" -m "$MODULE" "$@"
