#!/usr/bin/env bash
# Install the lsdyna-kfile skill into OpenAI Codex CLI (macOS/Linux/Git-Bash).
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/skills/lsdyna-kfile"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DST="$CODEX_HOME/skills/lsdyna-kfile"
ACADEMIC_MCP="$DST/vendor/nature-academic-search/mcp-server"
ACADEMIC_REQ="$ACADEMIC_MCP/requirements.txt"
ACADEMIC_PREFLIGHT="$DST/vendor/nature-academic-search/scripts/preflight.py"

[ -f "$SRC/SKILL.md" ] || { echo "[ERROR] skill source not found: $SRC"; exit 1; }

mkdir -p "$DST"
cp -R "$SRC/." "$DST/"
find "$DST" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$DST" -type f -name "*.pyc" -delete 2>/dev/null || true

if [ ! -f "$ACADEMIC_MCP/academic_search_server.py" ]; then
  echo "[ERROR] bundled academic-search MCP server not found: $ACADEMIC_MCP"
  exit 1
fi

echo "Registering academic-search MCP for Codex ..."
if ! command -v codex >/dev/null 2>&1; then
  echo "[WARN] codex command not found; skill copied, but MCP was not registered."
elif ! command -v uv >/dev/null 2>&1; then
  echo "[WARN] uv command not found; install uv before using the academic-search MCP."
elif codex mcp get academic-search >/dev/null 2>&1; then
  echo "[OK] academic-search MCP already exists; preserving existing Codex MCP config."
else
  codex mcp add academic-search -- \
    uv run --no-project --directory "$ACADEMIC_MCP" \
    --with-requirements "$ACADEMIC_REQ" \
    python academic_search_server.py
fi

echo "Running academic-search endpoint preflight ..."
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

if [ -n "$PYTHON_BIN" ]; then
  "$PYTHON_BIN" "$ACADEMIC_PREFLIGHT" || \
    echo "[WARN] academic-search preflight reported unreachable endpoints; check network/proxy/API access."
else
  echo "[WARN] python/python3 not found; skipped academic-search preflight."
fi

cat <<EOF
[OK] Installed to $DST
In Codex CLI:
  - invoke explicitly:  \$lsdyna-kfile   (or let it auto-activate on LS-DYNA requests)
  - literature parameters: academic-search MCP handles paper discovery/verification
  - browse skills:      /skills
Notes:
  1. Manuals: if knowledge/manuals/*.pdf are missing, run:
       python "$DST/scripts/fetch_manuals.py"
  2. Codex sandbox blocks the solver by default; run Codex with approvals enabled.
  3. Solver path defaults to ANSYS v242; override with env LSDYNA_BIN.
  4. PubMed email/API keys are read from environment/config; never store secrets in this skill.
EOF
