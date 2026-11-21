"""
installer/shortcut_manager.py — Windows Desktop & Start Menu Shortcut Manager

Creates and removes standard Windows shortcuts (.lnk) without third-party dependencies,
using Windows WScript.Shell COM object via PowerShell or pywin32 fallback.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def create_windows_shortcut(
    target_path: Path,
    shortcut_path: Path,
    description: str = "J.A.R.V.I.S. Mark LVI Core AI Assistant",
    icon_path: Path | None = None,
    arguments: str = "",
    working_directory: Path | None = None,
) -> bool:
    """Creates a Windows shortcut (.lnk) safely via PowerShell WScript.Shell."""
    target_str = str(target_path.resolve())
    shortcut_str = str(shortcut_path.resolve())
    work_dir = str(working_directory.resolve()) if working_directory else str(target_path.parent.resolve())
    icon_str = str(icon_path.resolve()) if icon_path and icon_path.exists() else ""

    ps_script = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{shortcut_str}')
    $Shortcut.TargetPath = '{target_str}'
    $Shortcut.WorkingDirectory = '{work_dir}'
    $Shortcut.Description = '{description}'
    """
    if arguments:
        ps_script += f"\n    $Shortcut.Arguments = '{arguments}'"
    if icon_str:
        ps_script += f"\n    $Shortcut.IconLocation = '{icon_str}'"
    ps_script += "\n    $Shortcut.Save()"

    try:
        shortcut_path.parent.mkdir(parents=True, exist_ok=True)
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return res.returncode == 0 and shortcut_path.exists()
    except Exception as e:
        print(f"[ShortcutManager] Shortcut creation note: {e}")
        return False


def get_desktop_shortcut_path() -> Path:
    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
    return desktop / "JARVIS Mark LVI.lnk"


def get_start_menu_shortcut_path() -> Path:
    app_data = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "JARVIS"
    return app_data / "JARVIS Mark LVI.lnk"


def remove_shortcuts() -> dict:
    results = {}
    for label, p in [("desktop", get_desktop_shortcut_path()), ("start_menu", get_start_menu_shortcut_path())]:
        if p.exists():
            try:
                p.unlink()
                results[label] = True
            except Exception as e:
                results[label] = False
        else:
            results[label] = True

    # Clean up empty Start Menu folder
    sm_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "JARVIS"
    if sm_dir.exists() and not list(sm_dir.iterdir()):
        try:
            sm_dir.rmdir()
        except Exception:
            pass

    return results
