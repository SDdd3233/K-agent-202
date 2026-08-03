@echo off
rem Install the lsdyna-kfile Claude Code plugin and initialize its academic-search MCP.
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
  echo [ERROR] academic-search MCP setup or verification failed; installation is incomplete.
  exit /b 1
)

where claude >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Claude Code CLI not found. Install Claude Code, then rerun this script.
  exit /b 1
)

echo Registering the local Claude marketplace ...
claude plugin marketplace add "%PLUGIN_ROOT%"
if errorlevel 1 (
  echo [ERROR] Claude marketplace registration failed.
  exit /b 1
)

echo Installing lsdyna-kagent from the local marketplace ...
claude plugin install "lsdyna-kagent@lsdyna-kagent-marketplace"
if errorlevel 1 (
  echo [ERROR] Claude plugin installation failed.
  exit /b 1
)

echo.
echo [OK] Claude Code plugin and academic-search MCP installed.
echo Restart Claude Code before using lsdyna-kagent.
exit /b 0
