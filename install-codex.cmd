@echo off
rem Install the lsdyna-kfile skill into OpenAI Codex CLI (Windows).
setlocal
set "SRC=%~dp0skills\lsdyna-kfile"
if not defined CODEX_HOME set "CODEX_HOME=%USERPROFILE%\.codex"
set "DST=%CODEX_HOME%\skills\lsdyna-kfile"
set "ACADEMIC_MCP=%DST%\vendor\academic-search-mcp"
set "ACADEMIC_SETUP=%DST%\scripts\setup_academic_mcp.py"

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

where python >nul 2>nul
if errorlevel 1 (
  echo [WARN] python command not found; skill copied, but academic-search MCP setup was skipped.
  goto installed
)

echo Detecting an existing academic-search MCP before registration ...
python "%ACADEMIC_SETUP%" ensure --client codex --server-dir "%ACADEMIC_MCP%"
if errorlevel 1 echo [WARN] academic-search MCP was not changed; review the message above.

:installed
echo.
echo [OK] Installed. In Codex CLI:
echo   - invoke explicitly:  $lsdyna-kfile  (or let it auto-activate on LS-DYNA requests)
echo   - literature inputs: academic-search MCP handles paper search and metadata
echo   - browse skills:      /skills
echo.
echo Notes:
echo   1. Manuals: if knowledge\manuals\*.pdf are missing, run:
echo        python "%DST%\scripts\fetch_manuals.py"
echo   2. Codex sandbox blocks the solver by default. Run Codex with approvals enabled
echo      (e.g. codex --ask-for-approval untrusted) or allow the LS-DYNA bin directory.
echo   3. Solver path defaults to ANSYS v242; override with env LSDYNA_BIN if needed.
echo   4. Existing academic-search MCP registrations are reused and never overwritten.
echo   5. PubMed email/API keys are read from environment/config; never store secrets in this skill.
exit /b 0
