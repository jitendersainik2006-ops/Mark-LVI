"""
setup_autostart.py — J.A.R.V.I.S. Windows User Startup Management Utility

Allows enabling, disabling, and checking the status of automatic startup for J.A.R.V.I.S. on Windows sign-in.
- Uses the standard Windows Startup folder (Shell:Startup / APPDATA) — non-invasive, no admin rights required.
- Ensures Ollama local AI server is active on 127.0.0.1:11434 with designated models folder.
- Enforces single-instance protection: will never launch a duplicate if J.A.R.V.I.S. is already running or port 8000 is listening.
- Can be inspected and disabled at any time from Windows Task Manager (Startup apps tab) or via this script.
"""

import argparse
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_startup_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        appdata = str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def get_bat_content() -> str:
    base_dir = Path(__file__).resolve().parent
    root_dir = base_dir.parent
    python_exe = sys.executable
    localapp = os.environ.get("LOCALAPPDATA", "")
    import shutil
    candidate_exes = [
        root_dir / "Ollama" / "ollama.exe",
        base_dir / "Ollama" / "ollama.exe",
        Path(localapp) / "Programs" / "Ollama" / "ollama.exe" if localapp else None,
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Ollama" / "ollama.exe",
    ]
    ollama_exe = None
    for c in candidate_exes:
        if c and c.exists():
            ollama_exe = c
            break
    if not ollama_exe:
        which = shutil.which("ollama")
        ollama_exe = Path(which) if which else Path("ollama.exe")

    candidate_models = [
        root_dir / "ollama_models",
        base_dir / "ollama_models",
        Path.home() / ".ollama" / "models",
    ]
    ollama_models = candidate_models[0]
    for m in candidate_models:
        if m.exists():
            ollama_models = m
            break
    main_py = base_dir / "main.py"

    return f"""@echo off
REM ======================================================================
REM  J.A.R.V.I.S. AUTOMATIC STARTUP LAUNCHER
REM  Executes on Windows User Sign-In (Safe, Non-Admin, User-Controlled)
REM ======================================================================

echo [JARVIS-Startup] Checking local AI server (Ollama)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$conn = Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue; if (-not $conn) {{ Write-Host '[JARVIS-Startup] Starting Ollama serve...'; $env:OLLAMA_HOST='127.0.0.1:11434'; $env:OLLAMA_MODELS='{ollama_models}'; Start-Process -FilePath '{ollama_exe}' -ArgumentList 'serve' -WindowStyle Hidden; Start-Sleep -Seconds 3 }} else {{ Write-Host '[JARVIS-Startup] Ollama server is already active on 127.0.0.1:11434.' }}"

echo [JARVIS-Startup] Checking for existing J.A.R.V.I.S. instance (Single-Instance Guard)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$conn = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; if ($conn) {{ Write-Host '[JARVIS-Startup] Port 8000 is already active. J.A.R.V.I.S. is already running. Exiting without duplicate.'; exit 0 }} else {{ Write-Host '[JARVIS-Startup] Launching J.A.R.V.I.S. Mark-LVI Core...'; Start-Process -FilePath '{python_exe}' -ArgumentList '{main_py}' -WorkingDirectory '{base_dir}' }}"
"""


def enable_autostart() -> bool:
    startup_dir = get_startup_dir()
    if not startup_dir.exists():
        startup_dir.mkdir(parents=True, exist_ok=True)
    target_file = startup_dir / "JARVIS_AutoStart.bat"
    target_file.write_text(get_bat_content(), encoding="utf-8")
    print(f"✅ Automatic startup ENABLED successfully.")
    print(f"Target location: {target_file}")
    print(f"J.A.R.V.I.S. will start automatically whenever you sign in to Windows.")
    print(f"To disable, run: python setup_autostart.py --disable")
    return True


def disable_autostart() -> bool:
    target_file = get_startup_dir() / "JARVIS_AutoStart.bat"
    if target_file.exists():
        target_file.unlink()
        print(f"🛑 Automatic startup DISABLED successfully.")
        print(f"Removed: {target_file}")
        return True
    else:
        print(f"ℹ️ Automatic startup was not enabled ({target_file} not found).")
        return False


def status_autostart() -> dict:
    target_file = get_startup_dir() / "JARVIS_AutoStart.bat"
    enabled = target_file.exists()
    print(f"=== J.A.R.V.I.S. Windows Startup Status ===")
    print(f"Auto-Start Enabled: {'YES (Active)' if enabled else 'NO (Disabled)'}")
    print(f"Startup Shortcut Path: {target_file}")
    return {"enabled": enabled, "path": str(target_file)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Windows Auto-Start Configurator")
    parser.add_argument("--enable", action="store_true", help="Enable automatic launch on Windows sign-in")
    parser.add_argument("--disable", action="store_true", help="Disable automatic launch on Windows sign-in")
    parser.add_argument("--status", action="store_true", help="Check current auto-start configuration status")

    args = parser.parse_args()

    if args.enable:
        enable_autostart()
    elif args.disable:
        disable_autostart()
    else:
        status_autostart()
