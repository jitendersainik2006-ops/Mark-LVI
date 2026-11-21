@echo off
title Uninstall J.A.R.V.I.S. Mark LVI
color 0C
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ======================================================================
echo   J.A.R.V.I.S. MARK LVI — UNINSTALL CONFIRMATION
echo ======================================================================
echo.
echo This will remove Desktop and Start Menu shortcuts for J.A.R.V.I.S.
echo Your personal memory notes and content ledgers will be preserved.
echo.
set /p CONFIRM="Are you sure you want to uninstall J.A.R.V.I.S.? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo.
    echo Uninstallation cancelled. No changes were made.
    pause
    exit /b 0
)

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found in PATH.
    pause
    exit /b 1
)

python "%SCRIPT_DIR%installer\uninstall_jarvis.py"
pause
