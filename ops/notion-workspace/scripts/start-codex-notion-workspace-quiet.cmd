@echo off
setlocal

rem Compatibility alias for the default quiet lane.
call "%~dp0start-codex-notion-workspace-common.cmd" ops_notion_workspace_quiet %*
exit /b %ERRORLEVEL%
