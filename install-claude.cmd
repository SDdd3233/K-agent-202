@echo off
rem Initialize the academic-search MCP used by the lsdyna-kfile Claude plugin.
setlocal
set "PLUGIN_ROOT=%~dp0"
set "ACADEMIC_MCP=%PLUGIN_ROOT%skills\lsdyna-kfile\vendor\academic-search-mcp"
set "ACADEMIC_SETUP=%PLUGIN_ROOT%skills\lsdyna-kfile\scripts\setup_academic_mcp.py"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python command not found; cannot initialize the academic-search MCP.
  exit /b 1
)

echo Detecting an existing academic-search MCP before registration ...
python "%ACADEMIC_SETUP%" ensure --client claude --server-dir "%ACADEMIC_MCP%"
if errorlevel 1 (
  echo [WARN] academic-search MCP was not changed; review the message above.
  exit /b 1
)

echo [OK] Claude MCP initialization complete. Existing registrations were preserved.
echo Restart Claude Code before using literature search.
exit /b 0
