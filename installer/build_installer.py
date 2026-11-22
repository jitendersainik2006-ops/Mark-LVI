"""
installer/build_installer.py — Standalone Windows Release Packaging Engine

Builds a complete, relocatable, self-contained Windows release package:
- Target Directory: D:\\JARVIS-AI\\release\\JARVIS_Mark_LVI_Windows_x64
- Relocatable Scripts: Uses %~dp0 (Zero hardcoded D: paths inside launcher scripts)
- Generates:
  1. install_jarvis.bat — One-click setup wizard
  2. launch_jarvis.bat  — Foreground host launcher
  3. stop_jarvis.bat    — Clean shutdown script
  4. uninstall.bat      — Clean uninstaller
  5. SHA256_MANIFEST.txt
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


BASE_DIR = Path(__file__).resolve().parent.parent
RELEASE_DIR = BASE_DIR.parent / "release" / "JARVIS_Mark_LVI_Windows_x64"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def build_release_package() -> dict:
    print("=" * 75)
    print("  J.A.R.V.I.S. MARK LVI — PUBLIC WINDOWS RELEASE BUILDER")
    print("=" * 75)
    print(f"• Source Directory : {BASE_DIR}")
    print(f"• Release Target   : {RELEASE_DIR}")

    def _handle_readonly(func, path, exc_info):
        import stat
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    if RELEASE_DIR.exists():
        print("• Cleaning previous build directory contents...")
        for item in RELEASE_DIR.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item, onerror=_handle_readonly)
                else:
                    item.unlink()
            except Exception as e:
                print(f"  Note cleaning {item.name}: {e}")
    else:
        RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Directories to copy
    copy_dirs = ["actions", "core", "dashboard", "installer", "memory", "providers", "tests", "tools", "docs"]
    for d in copy_dirs:
        src = BASE_DIR / d
        dst = RELEASE_DIR / d
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.bak*", ".git"))
            print(f"  ✓ Bundled {d}/")

    # Sanitize memory: ensure zero developer personal memories in release
    rel_mem_file = RELEASE_DIR / "memory" / "long_term.json"
    clean_empty_mem = {
        "identity": {},
        "preferences": {},
        "projects": {},
        "relationships": {},
        "wishes": {},
        "notes": {},
    }
    rel_mem_file.write_text(json.dumps(clean_empty_mem, indent=2), encoding="utf-8")
    print("  ✓ Sanitized memory/long_term.json (zero developer memories in release)")

    # 2. Config & template initialization
    dst_cfg = RELEASE_DIR / "config"
    dst_cfg.mkdir(parents=True, exist_ok=True)
    if (BASE_DIR / "config" / "jarvis.ico").exists():
        shutil.copy2(BASE_DIR / "config" / "jarvis.ico", dst_cfg / "jarvis.ico")
    if (BASE_DIR / "config" / "cloudflared_named_tunnel.yml").exists():
        shutil.copy2(BASE_DIR / "config" / "cloudflared_named_tunnel.yml", dst_cfg / "cloudflared_named_tunnel.yml")
    if (BASE_DIR / "config" / "pronunciation_rules.json").exists():
        shutil.copy2(BASE_DIR / "config" / "pronunciation_rules.json", dst_cfg / "pronunciation_rules.json")
        print("  ✓ Bundled config/pronunciation_rules.json")
    # Release version record
    ver_data = {
        "version": "56.1.0",
        "codename": "Stonic-AI-Companion-Master-Rebuild",
        "release_name": "J.A.R.V.I.S. Mark LVI Stonic AI Companion Master Release v56.1.0",
        "release_date": "2026-11-22",
    }
    (dst_cfg / "version.json").write_text(json.dumps(ver_data, indent=2), encoding="utf-8")
    print("  ✓ Created config/version.json (v56.1.0 Stonic-AI-Companion-Master-Rebuild)")

    # 3. Data folder skeleton
    dst_data = RELEASE_DIR / "data"
    dst_data.mkdir(parents=True, exist_ok=True)
    (dst_data / "knowledge" / "documents").mkdir(parents=True, exist_ok=True)
    (dst_data / "reels").mkdir(parents=True, exist_ok=True)
    (dst_data / "veo_output").mkdir(parents=True, exist_ok=True)

    # 4. Copy root entry files & continuity documentation
    root_files = [
        "main.py",
        "ui.py",
        "requirements.txt",
        "launch_floating_companion.bat",
        "README_INSTALL_FOR_SIR.md",
        "PROJECT_CONTEXT.md",
        "PROJECT_STATUS.md",
        "CHANGELOG.md",
        "NEXT_STEPS.md",
        "ARCHITECTURE.md",
        "SECURITY.md",
        "SESSION_HANDOFF.md",
        "FEATURE_REFERENCE_MATRIX.md",
        "LICENSES_AND_ATTRIBUTIONS.md",
    ]
    for rf in root_files:
        src = BASE_DIR / rf
        if src.exists():
            shutil.copy2(src, RELEASE_DIR / rf)
            print(f"  ✓ Bundled {rf}")

    # 5. Create Relocatable Bat Scripts (Zero Hardcoded Paths)
    # A. install_jarvis.bat
    install_bat = r"""@echo off
setlocal EnableDelayedExpansion
title J.A.R.V.I.S. Mark-LVI Installer
color 0B
echo ======================================================================
echo  J.A.R.V.I.S. MARK-LVI CORE -- WINDOWS ONE-CLICK INSTALLER
echo ======================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Discover Python executable across standard Windows installation paths
set "BASE_PYTHON="
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "BASE_PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe"
) else (
    where py >nul 2>&1
    if not errorlevel 1 (
        set "BASE_PYTHON=py -3"
    ) else (
        where python >nul 2>&1
        if not errorlevel 1 (
            set "BASE_PYTHON=python"
        ) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
            set "BASE_PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        ) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
            set "BASE_PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        ) else if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" (
            set "BASE_PYTHON=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        ) else if exist "%ProgramFiles%\Python312\python.exe" (
            set "BASE_PYTHON=%ProgramFiles%\Python312\python.exe"
        ) else if exist "%ProgramFiles%\Python311\python.exe" (
            set "BASE_PYTHON=%ProgramFiles%\Python311\python.exe"
        ) else if exist "C:\Python312\python.exe" (
            set "BASE_PYTHON=C:\Python312\python.exe"
        )
    )
)

if "%BASE_PYTHON%"=="" (
    echo [ERROR] Python 3.10+ (64-bit) was not found on this machine.
    echo.
    echo J.A.R.V.I.S. requires Python 3.10 or higher.
    echo Please install Python from: https://www.python.org/downloads/
    echo IMPORTANT: Make sure to check "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [JARVIS] Using Python: %BASE_PYTHON%

REM Setup local virtual environment if not present
if not exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    echo [JARVIS] Creating dedicated Python virtual environment (.venv)...
    %BASE_PYTHON% -m venv "%SCRIPT_DIR%.venv"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo   ✓ Virtual environment created successfully.
)

if exist "%SCRIPT_DIR%requirements.txt" (
    echo [JARVIS] Checking and installing Python dependencies into .venv...
    "%SCRIPT_DIR%.venv\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
    "%SCRIPT_DIR%.venv\Scripts\python.exe" -m pip install -r "%SCRIPT_DIR%requirements.txt"
    if errorlevel 1 (
        echo [WARNING] Some dependencies had warnings during install.
    ) else (
        echo   ✓ Dependencies verified.
    )
)

echo [JARVIS] Running First-Time Setup Wizard...
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    "%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%installer\setup_wizard.py"
) else (
    %BASE_PYTHON% "%SCRIPT_DIR%installer\setup_wizard.py"
)
if errorlevel 1 (
    echo [ERROR] Setup encountered an issue.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo  Installation completed! You may now launch J.A.R.V.I.S. from Desktop.
echo ======================================================================
pause
"""
    (RELEASE_DIR / "install_jarvis.bat").write_text(install_bat, encoding="utf-8")

    # B. launch_jarvis.bat (Relocatable)
    launch_bat = r"""@echo off
setlocal EnableDelayedExpansion
title J.A.R.V.I.S. Mark-LVI Core Host Service
color 0B
echo ======================================================================
echo  J.A.R.V.I.S. MARK-LVI CORE -- ASSISTANT AND LOCAL DASHBOARD
echo  Directory    : %~dp0
echo  Dashboard URL: http://localhost:8000/app
echo  OAuth Proxy  : http://127.0.0.1:8005
echo ======================================================================
echo.

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Discover Python executable across standard paths
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
    echo Please run install_jarvis.bat first to set up the environment,
    echo or install Python 64-bit from https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [JARVIS] Using Python: %PYTHON_EXE%

REM Check or start Ollama local daemon if installed
echo [JARVIS] Checking local Ollama AI daemon on port 11434...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c = Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue; if ($c) { Write-Host '[JARVIS] Ollama server is already active on 127.0.0.1:11434.' } else { $scriptDir = '%SCRIPT_DIR%'; $paths = @((Join-Path $scriptDir '..\Ollama\ollama.exe'), (Join-Path $scriptDir 'Ollama\ollama.exe'), (Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'), (Join-Path $env:ProgramFiles 'Ollama\ollama.exe')); $exe = $paths | Where-Object { Test-Path $_ } | Select-Object -First 1; if (-not $exe) { $cmd = Get-Command 'ollama' -ErrorAction SilentlyContinue; if ($cmd) { $exe = $cmd.Source } }; if ($exe) { Write-Host \"[JARVIS] Starting Ollama serve ($exe)...\"; $env:OLLAMA_HOST='127.0.0.1:11434'; Start-Process -FilePath $exe -ArgumentList 'serve' -WindowStyle Hidden; Start-Sleep -Seconds 3 } else { Write-Host '[JARVIS] Ollama is not installed or not active (Optional). Continuing with cloud/offline fallback.' } }"

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
"""
    (RELEASE_DIR / "launch_jarvis.bat").write_text(launch_bat, encoding="utf-8")

    # C. stop_jarvis.bat
    stop_bat = r"""@echo off
setlocal EnableDelayedExpansion
title Stop J.A.R.V.I.S. Host
color 0C
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

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
    echo [ERROR] Python was not found in PATH or .venv.
    pause
    exit /b 1
)

if "%PYTHON_EXE:~0,2%"=="py" (
    %PYTHON_EXE% "%SCRIPT_DIR%installer\stop_jarvis.py"
) else (
    "%PYTHON_EXE%" "%SCRIPT_DIR%installer\stop_jarvis.py"
)
pause
"""
    (RELEASE_DIR / "stop_jarvis.bat").write_text(stop_bat, encoding="utf-8")

    # D. uninstall_jarvis.bat
    uninstall_bat = r"""@echo off
setlocal EnableDelayedExpansion
title Uninstall J.A.R.V.I.S. Mark LVI
color 0C
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"
echo ======================================================================
echo   J.A.R.V.I.S. MARK LVI -- UNINSTALL CONFIRMATION
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

set "PYTHON_EXE="
if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%.venv\Scripts\python.exe"
) else if exist "%SCRIPT_DIR%..\.venv-jarvis\Scripts\python.exe" (
    set "PYTHON_EXE=%SCRIPT_DIR%..\.venv-jarvis\Scripts\python.exe"
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
    echo [ERROR] Python was not found in PATH or .venv.
    pause
    exit /b 1
)

%PYTHON_EXE% "%SCRIPT_DIR%installer\uninstall_jarvis.py"
pause
"""
    (RELEASE_DIR / "uninstall_jarvis.bat").write_text(uninstall_bat, encoding="utf-8")


    # D. README.txt
    readme_txt = """======================================================================
  J.A.R.V.I.S. MARK LVI CORE — PERSONAL AI DESKTOP COMPANION
======================================================================

SYSTEM REQUIREMENTS:
• Windows 10 or Windows 11 (64-bit)
• Python 3.10+ (64-bit)
• 8 GB RAM minimum (16 GB recommended for local neural models)
• Microphone and Speakers / Headset
• Optional: NVIDIA GPU (CUDA) or fast multi-core CPU for local STT/LLM

ONE-CLICK INSTALLATION:
1. Double-click 'install_jarvis.bat'.
2. The Setup Wizard will automatically verify requirements, configure audio
   devices, initialize databases, and generate Desktop & Start Menu shortcuts.
3. Launch J.A.R.V.I.S. via the Desktop shortcut or 'launch_jarvis.bat'.
4. Open your browser to http://127.0.0.1:8000/app for the local dashboard.

LOCAL AI / OLLAMA:
• Download Ollama from https://ollama.com.
• Run: ollama run qwen2.5:3b
• J.A.R.V.I.S. will automatically detect and connect to your local models.

SHUTDOWN & UNINSTALLATION:
• Run 'stop_jarvis.bat' to cleanly stop background services without removing shortcuts or data.
• Run 'uninstall_jarvis.bat' to remove Desktop and Start Menu shortcuts.
======================================================================
"""
    (RELEASE_DIR / "README.txt").write_text(readme_txt, encoding="utf-8")

    # 6. Generate SHA256 Manifest
    print("\n• Generating SHA256 Package Manifest...")
    manifest_lines = []
    total_files = 0
    total_bytes = 0
    for root, _, files in os.walk(RELEASE_DIR):
        for f in sorted(files):
            fp = Path(root) / f
            if fp.name == "SHA256_MANIFEST.txt":
                continue
            h = compute_sha256(fp)
            rel = fp.relative_to(RELEASE_DIR)
            manifest_lines.append(f"{h}  {rel}")
            total_files += 1
            total_bytes += fp.stat().st_size

    (RELEASE_DIR / "SHA256_MANIFEST.txt").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    shutil.copy2(RELEASE_DIR / "SHA256_MANIFEST.txt", RELEASE_DIR.parent / "SHA256_MANIFEST.txt")
    print(f"  ✓ Manifest generated for {total_files} files ({round(total_bytes / 1024 / 1024, 2)} MB).")

    # 7. Generate Portable ZIP Archive
    print("\n• Generating Portable ZIP Distribution Archive...")
    import zipfile
    zip_path = RELEASE_DIR.parent / "JARVIS_Mark_LVI_Windows_x64_Portable.zip"
    if zip_path.exists():
        try:
            zip_path.unlink()
        except Exception:
            pass
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(RELEASE_DIR):
            for f in sorted(files):
                fp = Path(root) / f
                arcname = fp.relative_to(RELEASE_DIR)
                zf.write(fp, arcname)
    zip_size_mb = round(zip_path.stat().st_size / (1024 * 1024), 2)
    print(f"  ✓ Portable ZIP generated: {zip_path} ({zip_size_mb} MB)")

    # 8. Compile Native Inno Setup Executable Installer
    print("\n• Checking for Inno Setup Compiler (iscc.exe)...")
    iscc_candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "iscc.exe",
        Path(r"C:\Program Files (x86)\Inno Setup 6\iscc.exe"),
        Path(r"C:\Program Files\Inno Setup 6\iscc.exe"),
    ]
    iscc_exe = next((p for p in iscc_candidates if p.exists()), None)
    installer_exe_path = None
    if iscc_exe:
        iss_script = BASE_DIR / "installer" / "jarvis_setup.iss"
        print(f"  ✓ Inno Setup Compiler found: {iscc_exe}")
        print(f"  ✓ Compiling Windows Installer executable via {iss_script}...")
        try:
            res = subprocess.run([str(iscc_exe), str(iss_script)], cwd=str(BASE_DIR / "installer"), capture_output=True, text=True)
            if res.returncode == 0:
                installer_exe = RELEASE_DIR.parent / "JARVIS_Mark_LVI_Setup.exe"
                if installer_exe.exists():
                    installer_exe_path = str(installer_exe)
                    exe_size_mb = round(installer_exe.stat().st_size / (1024 * 1024), 2)
                    print(f"  ✓ Native Windows Installer built: {installer_exe} ({exe_size_mb} MB)")
            else:
                print(f"  ⚠ iscc compilation returned code {res.returncode}: {res.stderr[:200]}")
        except Exception as e:
            print(f"  ⚠ Failed to execute iscc: {e}")
    else:
        print("  ℹ iscc.exe not found; skipping .exe compilation.")

    print("\n" + "=" * 75)
    print("  ✅ PUBLIC WINDOWS RELEASE PACKAGE & INSTALLER BUILT SUCCESSFULLY!")
    print(f"  Release Folder: {RELEASE_DIR}")
    print(f"  Portable ZIP  : {zip_path}")
    if installer_exe_path:
        print(f"  Installer EXE : {installer_exe_path}")
    print("=" * 75)
    return {
        "status": "SUCCESS",
        "release_path": str(RELEASE_DIR),
        "portable_zip_path": str(zip_path),
        "total_files": total_files,
        "total_mb": round(total_bytes / 1024 / 1024, 2),
        "zip_mb": zip_size_mb,
    }


if __name__ == "__main__":
    build_release_package()
