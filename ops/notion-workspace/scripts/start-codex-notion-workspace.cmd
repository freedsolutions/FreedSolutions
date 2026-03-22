@echo off
setlocal

set "CODEX_CMD=%APPDATA%\npm\codex.cmd"
if not exist "%CODEX_CMD%" set "CODEX_CMD=codex"

set "REPO_ROOT=%~dp0..\..\.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"

call "%CODEX_CMD%" -p ops_notion_workspace -C "%REPO_ROOT%" %*
