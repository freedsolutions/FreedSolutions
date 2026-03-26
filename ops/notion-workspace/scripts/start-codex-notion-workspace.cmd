@echo off
setlocal

set "DEFAULT_PROFILE=ops_notion_workspace_quiet"
set "FALLBACK_PROFILE=ops_notion_workspace"
set "CODEX_CONFIG=%USERPROFILE%\.codex\config.toml"
set "SELECTED_PROFILE=%DEFAULT_PROFILE%"

if not exist "%CODEX_CONFIG%" (
  echo [ops-notion-workspace] Codex config not found at "%CODEX_CONFIG%".
  echo [ops-notion-workspace] Remediation: restore ~/.codex/config.toml with the Notion-workspace profiles, then retry or use codex.cmd manually after setup.
  exit /b 1
) else (
  findstr /R /C:"^\[profiles\.ops_notion_workspace_quiet\]" "%CODEX_CONFIG%" >nul
  if errorlevel 1 (
    findstr /R /C:"^\[profiles\.ops_notion_workspace\]" "%CODEX_CONFIG%" >nul
    if errorlevel 1 (
      echo [ops-notion-workspace] Neither %DEFAULT_PROFILE% nor %FALLBACK_PROFILE% is configured in "%CODEX_CONFIG%".
      echo [ops-notion-workspace] Remediation: add one of the Notion-workspace profiles to ~/.codex/config.toml, then retry or use codex.cmd manually after setup.
      exit /b 1
    ) else (
      echo [ops-notion-workspace] Quiet profile not configured in "%CODEX_CONFIG%"; falling back to %FALLBACK_PROFILE%.
      echo [ops-notion-workspace] Remediation: add [profiles.ops_notion_workspace_quiet] or use start-codex-notion-workspace-safe.cmd explicitly.
      set "SELECTED_PROFILE=%FALLBACK_PROFILE%"
    )
  )
)

call "%~dp0start-codex-notion-workspace-common.cmd" %SELECTED_PROFILE% %*
exit /b %ERRORLEVEL%
