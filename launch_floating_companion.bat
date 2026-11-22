@echo off
setlocal EnableDelayedExpansion
title J.A.R.V.I.S. Floating Desktop Companion
color 0B

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
    where py >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=py -3"
    ) else (
        where python >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_EXE=python"
        )
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python 3.10+ was not found on this system.
    pause
    exit /b 1
)

echo [JARVIS] Launching Floating Desktop Companion...
"%PYTHON_EXE%" -m core.floating_companion
