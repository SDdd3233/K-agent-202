#!/usr/bin/env bash
# Initialize the academic-search MCP used by the lsdyna-kfile Claude plugin.
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")" && pwd)"
ACADEMIC_MCP="$PLUGIN_ROOT/skills/lsdyna-kfile/vendor/academic-search-mcp"
ACADEMIC_SETUP="$PLUGIN_ROOT/skills/lsdyna-kfile/scripts/setup_academic_mcp.py"

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "[ERROR] python/python3 not found; cannot initialize the academic-search MCP."
  exit 1
fi

echo "Detecting an existing academic-search MCP before registration ..."
"$PYTHON_BIN" "$ACADEMIC_SETUP" ensure --client claude --server-dir "$ACADEMIC_MCP" || {
  echo "[WARN] academic-search MCP was not changed; review the message above."
  exit 1
}

echo "[OK] Claude MCP initialization complete. Existing registrations were preserved."
echo "Restart Claude Code before using literature search."
