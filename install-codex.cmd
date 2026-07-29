@echo off
rem Install the lsdyna-kfile skill into OpenAI Codex CLI (Windows).
setlocal
set "SRC=%~dp0skills\lsdyna-kfile"
if not defined CODEX_HOME set "CODEX_HOME=%USERPROFILE%\.codex"
set "DST=%CODEX_HOME%\skills\lsdyna-kfile"
set "ACADEMIC_MCP=%DST%\vendor\nature-academic-search\mcp-server"
set "ACADEMIC_REQ=%ACADEMIC_MCP%\requirements.txt"
set "ACADEMIC_PREFLIGHT=%DST%\vendor\nature-academic-search\scripts\preflight.py"

if not exist "%SRC%\SKILL.md" (
  echo [ERROR] skill source not found: %SRC%
  exit /b 1
)

echo Copying skill to %DST% ...
robocopy "%SRC%" "%DST%" /E /NFL /NDL /NJH /NJS /XD __pycache__ /XF *.pyc
if errorlevel 8 (
  echo [ERROR] copy failed.
  exit /b 1
)

if not exist "%ACADEMIC_MCP%\academic_search_server.py" (
  echo [ERROR] bundled academic-search MCP server not found: %ACADEMIC_MCP%
  exit /b 1
)

echo Registering academic-search MCP for Codex ...
where codex >nul 2>nul
if errorlevel 1 (
  echo [WARN] codex command not found; skill copied, but MCP was not registered.
  goto preflight
)

where uv >nul 2>nul
if errorlevel 1 (
  echo [WARN] uv command not found; install uv before using the academic-search MCP.
  goto preflight
)

call codex mcp get academic-search >nul 2>nul
if not errorlevel 1 (
  echo [OK] academic-search MCP already exists; preserving existing Codex MCP config.
) else (
  call codex mcp add academic-search -- uv run --no-project --directory "%ACADEMIC_MCP%" --with-requirements "%ACADEMIC_REQ%" python academic_search_server.py
  if errorlevel 1 (
    echo [ERROR] failed to register academic-search MCP.
    exit /b 1
  )
)

:preflight
echo Running academic-search endpoint preflight ...
where python >nul 2>nul
if not errorlevel 1 (
  python "%ACADEMIC_PREFLIGHT%"
  if errorlevel 1 echo [WARN] academic-search preflight reported unreachable endpoints; check network/proxy/API access.
) else (
  echo [WARN] python command not found; skipped academic-search preflight.
)

echo.
echo [OK] Installed. In Codex CLI:
echo   - invoke explicitly:  $lsdyna-kfile  (or let it auto-activate on LS-DYNA requests)
echo   - literature parameters: academic-search MCP handles paper discovery/verification
echo   - browse skills:      /skills
echo.
echo Notes:
echo   1. Manuals: if knowledge\manuals\*.pdf are missing, run:
echo        python "%DST%\scripts\fetch_manuals.py"
echo   2. Codex sandbox blocks the solver by default. Run Codex with approvals enabled
echo      (e.g. codex --ask-for-approval untrusted) or allow the LS-DYNA bin directory.
echo   3. Solver path defaults to ANSYS v242; override with env LSDYNA_BIN if needed.
echo   4. PubMed email/API keys are read from environment/config; never store secrets in this skill.
exit /b 0
