#!/usr/bin/env bash
# Install the lsdyna-kfile skill into OpenAI Codex CLI (macOS/Linux/Git-Bash).
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/skills/lsdyna-kfile"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DST="$CODEX_HOME/skills/lsdyna-kfile"
ACADEMIC_MCP="$DST/vendor/academic-search-mcp"
ACADEMIC_SETUP="$DST/scripts/setup_academic_mcp.py"

[ -f "$SRC/SKILL.md" ] || { echo "[ERROR] skill source not found: $SRC"; exit 1; }

mkdir -p "$DST"
cp -R "$SRC/." "$DST/"
find "$DST" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$DST" -type f -name "*.pyc" -delete 2>/dev/null || true

if [ ! -f "$ACADEMIC_MCP/academic_search_server.py" ]; then
  echo "[ERROR] bundled academic-search MCP server not found: $ACADEMIC_MCP"
  exit 1
fi

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

if [ -n "$PYTHON_BIN" ]; then
  echo "Detecting an existing academic-search MCP before registration ..."
  "$PYTHON_BIN" "$ACADEMIC_SETUP" ensure --client codex --server-dir "$ACADEMIC_MCP" || \
    echo "[WARN] academic-search MCP was not changed; review the message above."
else
  echo "[WARN] python/python3 not found; skill copied, but academic-search MCP setup was skipped."
fi

cat <<EOF
[OK] Installed to $DST
In Codex CLI:
  - invoke explicitly:  \$lsdyna-kfile   (or let it auto-activate on LS-DYNA requests)
  - literature inputs: academic-search MCP handles paper search and metadata
  - browse skills:      /skills
Notes:
  1. Manuals: if knowledge/manuals/*.pdf are missing, run:
       python "$DST/scripts/fetch_manuals.py"
  2. Codex sandbox blocks the solver by default; run Codex with approvals enabled.
  3. Solver path defaults to ANSYS v242; override with env LSDYNA_BIN.
  4. Existing academic-search MCP registrations are reused and never overwritten.
  5. PubMed email/API keys are read from environment/config; never store secrets in this skill.
EOF
