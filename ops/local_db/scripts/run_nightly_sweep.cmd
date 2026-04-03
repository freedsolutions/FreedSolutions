@echo off
REM Post-Email Sweep — nightly launcher for Windows Task Scheduler
REM Schedule: 9:30 PM ET daily (1 hour before Notion Agent's 10:30 PM nightly)
REM Working directory: repo root
REM Logs: ops\local_db\logs\nightly_sweep_YYYY-MM-DD.log

setlocal

set REPO_ROOT=C:\Users\adamj\Code\FreedSolutions
set PYTHON=C:\Python313\python.exe
set SCRIPT=%REPO_ROOT%\ops\local_db\post_email_sweep.py
set LOG_DIR=%REPO_ROOT%\ops\local_db\logs

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

set DATESTAMP=%date:~-4%-%date:~4,2%-%date:~7,2%
set LOG_FILE=%LOG_DIR%\nightly_sweep_%DATESTAMP%.log

echo [%date% %time%] Starting nightly sweep >> "%LOG_FILE%"

cd /d "%REPO_ROOT%"
"%PYTHON%" "%SCRIPT%" --verbose >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] SWEEP FAILED with exit code %ERRORLEVEL% >> "%LOG_FILE%"
) else (
    echo [%date% %time%] Sweep completed successfully >> "%LOG_FILE%"
)

endlocal
