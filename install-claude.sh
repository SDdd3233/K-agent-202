#!/usr/bin/env bash
# Install the lsdyna-kfile Claude Code plugin and initialize its academic-search MCP.
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
  echo "[ERROR] academic-search MCP setup or verification failed; installation is incomplete." >&2
  exit 1
}

if ! command -v claude >/dev/null 2>&1; then
  echo "[ERROR] Claude Code CLI not found. Install Claude Code, then rerun this script." >&2
  exit 1
fi

echo "Registering the local Claude marketplace ..."
claude plugin marketplace add "$PLUGIN_ROOT"

echo "Installing lsdyna-kagent from the local marketplace ..."
claude plugin install "lsdyna-kagent@lsdyna-kagent-marketplace"

echo "[OK] Claude Code plugin and academic-search MCP installed."
echo "Restart Claude Code before using lsdyna-kagent."
