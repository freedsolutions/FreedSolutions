@echo off
setlocal

call "%~dp0start-codex-notion-workspace-common.cmd" ops_notion_workspace %*
exit /b %ERRORLEVEL%
