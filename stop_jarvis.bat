@echo off
title Stop J.A.R.V.I.S. Host
color 0C
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH.
    pause
    exit /b 1
)

python "%SCRIPT_DIR%installer\stop_jarvis.py"
pause
