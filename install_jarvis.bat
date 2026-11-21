@echo off
setlocal
title J.A.R.V.I.S. Mark-LVI Setup & Installation Wizard
color 0B

echo ======================================================================
echo  J.A.R.V.I.S. MARK-LVI CORE -- FIRST-RUN INSTALLATION & SETUP WIZARD
echo ======================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHON_EXE="
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%..\.venv-jarvis\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%..\.venv-jarvis\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%..\..\.venv-jarvis\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%..\..\.venv-jarvis\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" "%SCRIPT_DIR%installer\setup_wizard.py"
pause
