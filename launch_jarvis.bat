@echo off
setlocal EnableDelayedExpansion
title J.A.R.V.I.S. Mark-LVI Core Host Service
color 0B

echo ======================================================================
echo  J.A.R.V.I.S. MARK-LVI CORE -- ADVANCED ASSISTANT AND REELS HOST
echo  Root Directory : %~dp0
echo  Dashboard URL  : http://localhost:8000/
echo  OAuth Proxy    : http://127.0.0.1:8005
echo  To Stop Cleanly: Run stop_jarvis.bat or press Ctrl+C in this window
echo ======================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM ------------------------------------------------------------------
REM 1. Python Executable Discovery
REM ------------------------------------------------------------------
set "PYTHON_EXE="

if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%..\.venv-jarvis\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%..\.venv-jarvis\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%..\..\.venv-jarvis\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%..\..\.venv-jarvis\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%..\.venv\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%..\..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%..\..\.venv\Scripts\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) else if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
) else if exist "%ProgramFiles%\Python312\python.exe" (
    set "PYTHON_EXE=%ProgramFiles%\Python312\python.exe"
) else if exist "%ProgramFiles%\Python311\python.exe" (
    set "PYTHON_EXE=%ProgramFiles%\Python311\python.exe"
) else if exist "C:\Python312\python.exe" (
    set "PYTHON_EXE=C:\Python312\python.exe"
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
    echo Please install Python 64-bit from https://www.python.org/downloads/
    echo Ensure "Add python.exe to PATH" is checked during installation.
    echo.
    pause
    exit /b 1
)

echo [JARVIS] Using Python: %PYTHON_EXE%

REM ------------------------------------------------------------------
REM 2. Ollama Local AI Daemon Check / Startup
REM ------------------------------------------------------------------
echo [JARVIS] Checking local Ollama AI daemon on port 11434...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c = Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue; if ($c) { Write-Host '[JARVIS] Ollama server is already active on 127.0.0.1:11434.' } else { $scriptDir = '%SCRIPT_DIR%'; $paths = @((Join-Path $scriptDir '..\Ollama\ollama.exe'), (Join-Path $scriptDir 'Ollama\ollama.exe'), (Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'), (Join-Path $env:ProgramFiles 'Ollama\ollama.exe')); $exe = $paths | Where-Object { Test-Path $_ } | Select-Object -First 1; if (-not $exe) { $cmd = Get-Command 'ollama' -ErrorAction SilentlyContinue; if ($cmd) { $exe = $cmd.Source } }; if ($exe) { Write-Host \"[JARVIS] Starting Ollama serve ($exe)...\"; $env:OLLAMA_HOST='127.0.0.1:11434'; Start-Process -FilePath $exe -ArgumentList 'serve' -WindowStyle Hidden; Start-Sleep -Seconds 3 } else { Write-Host '[JARVIS] Ollama is not installed or not active (Optional). Continuing with cloud/offline fallback.' } }"

REM ------------------------------------------------------------------
REM 3. Launch J.A.R.V.I.S. Core & Auto-open Dashboard
REM ------------------------------------------------------------------
echo [JARVIS] Launching J.A.R.V.I.S. Mark-LVI Core...
echo [JARVIS] Opening Modern Companion dashboard in default browser...
start /b cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8000/app"
echo.
if "%PYTHON_EXE:~0,2%"=="py" (
    %PYTHON_EXE% "%SCRIPT_DIR%main.py"
) else (
    "%PYTHON_EXE%" "%SCRIPT_DIR%main.py"
)
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo ======================================================================
if "%EXIT_CODE%"=="0" (
    echo  [JARVIS] Host service stopped cleanly.
) else (
    echo  [ERROR] Host service exited with error code: %EXIT_CODE%
    echo  CMD window kept open for diagnostics.
)
echo ======================================================================
pause
