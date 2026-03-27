@echo off
setlocal

for %%I in ("%~f0") do set "SCRIPT_DIR=%%~dpI"

set "PROFILE_NAME=%~1"
if "%PROFILE_NAME%"=="" (
  echo ERROR: Missing Codex profile name.
  echo Usage: start-codex-notion-workspace-common.cmd ^<profile^> [codex args...]
  exit /b 1
)
shift

set "BASELINE_VALIDATOR=%SCRIPT_DIR%test-approval-baseline.ps1"
if not exist "%BASELINE_VALIDATOR%" (
  echo ERROR: Missing approval baseline validator at "%BASELINE_VALIDATOR%".
  echo Remediation: restore ops/notion-workspace/scripts/test-approval-baseline.ps1 and retry.
  exit /b 1
)

powershell.exe -ExecutionPolicy Bypass -File "%BASELINE_VALIDATOR%" -CodexProfileName "%PROFILE_NAME%"
if errorlevel 1 (
  echo [ops-notion-workspace] Selected Codex profile failed validation: %PROFILE_NAME%
  exit /b 1
)

set "CODEX_CMD=%APPDATA%\npm\codex.cmd"
if not exist "%CODEX_CMD%" (
  for /f "usebackq delims=" %%I in (`where codex.cmd 2^>nul`) do (
    set "CODEX_CMD=%%I"
    goto codex_found
  )
  echo ERROR: Could not find codex.cmd.
  echo Looked for "%APPDATA%\npm\codex.cmd" and for codex.cmd on PATH.
  echo Remediation: reinstall Codex or add its npm bin directory to PATH.
  exit /b 1
)

:codex_found
set "REPO_ROOT=%SCRIPT_DIR%..\..\.."
for %%I in ("%REPO_ROOT%") do set "REPO_ROOT=%%~fI"

echo [ops-notion-workspace] Codex profile: %PROFILE_NAME%
echo [ops-notion-workspace] Repo root: %REPO_ROOT%

call "%CODEX_CMD%" -p "%PROFILE_NAME%" -C "%REPO_ROOT%" %*
exit /b %ERRORLEVEL%
