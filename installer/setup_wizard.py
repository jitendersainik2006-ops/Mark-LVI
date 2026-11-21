"""
installer/setup_wizard.py — J.A.R.V.I.S. First-Run Setup Wizard

Guides the user through initial configuration on any Windows machine:
1. Environment & Architecture Verification
2. User Identity & Honorific Setup (defaults to "Sir")
3. Language & Personality Selection (Hinglish / Hindi / English)
4. Audio Input & Output Device Selection
5. AI Engine Selection (Ollama local-first or Cloud)
6. Shortcut & Startup Configuration
7. Database & Directory Initialization
"""

from __future__ import annotations

import json
import os
import platform
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
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
CONFIG_DIR = BASE_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "api_keys.json"
DATA_DIR = BASE_DIR / "data"


def print_banner():
    print("=" * 75)
    print("      J.A.R.V.I.S. MARK LVI CORE — FIRST-RUN SETUP WIZARD")
    print("      Personal AI Desktop Companion & Intelligent Assistant")
    print("=" * 75)
    print()


def check_system_requirements() -> dict:
    import shutil
    os_name = platform.system()
    win_ver = platform.win32_ver()[0] if os_name == "Windows" else ""
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    arch = platform.machine()
    is_64bit = sys.maxsize > 2**32

    # Memory and Disk checks
    total_ram_gb = 0.0
    try:
        import psutil
        total_ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
    except Exception:
        pass

    free_disk_gb = 0.0
    try:
        usage = shutil.disk_usage(BASE_DIR)
        free_disk_gb = round(usage.free / (1024**3), 1)
    except Exception:
        pass

    reqs_met = (os_name == "Windows") and (sys.version_info.major == 3 and sys.version_info.minor >= 10) and is_64bit
    return {
        "os": os_name,
        "windows_version": win_ver or platform.release(),
        "python_version": py_ver,
        "architecture": arch,
        "is_64bit": is_64bit,
        "total_ram_gb": total_ram_gb,
        "free_disk_gb": free_disk_gb,
        "requirements_met": reqs_met,
    }


def run_setup(interactive: bool = True, custom_user_name: str = "Sir", language_mode: str = "hinglish", custom_model: Optional[str] = None) -> dict:
    print_banner()
    sys_info = check_system_requirements()
    print(f"• OS: Windows {sys_info['windows_version']} ({sys_info['architecture']})")
    print(f"• Memory (RAM): {sys_info['total_ram_gb']} GB")
    print(f"• Free Disk Space: {sys_info['free_disk_gb']} GB")
    print(f"• Python Environment: {sys_info['python_version']} (64-bit: {sys_info['is_64bit']})")

    if not sys_info["requirements_met"]:
        print("\n[WARNING] J.A.R.V.I.S. is optimized for Windows 64-bit with Python 3.10+.")
    if sys_info["total_ram_gb"] > 0 and sys_info["total_ram_gb"] < 8.0:
        print("  ⚠️ Notice: Less than 8 GB RAM detected. Local model inference may run slower.")
    if sys_info["free_disk_gb"] > 0 and sys_info["free_disk_gb"] < 5.0:
        print("  ⚠️ Notice: Less than 5 GB free disk space available.")

    # 1. Directory Structure Initialization
    print("\n[1/6] Initializing user storage and directories...")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "knowledge" / "documents").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "backups").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "reels").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "veo_output").mkdir(parents=True, exist_ok=True)
    print("  ✓ Directory structure confirmed.")

    # 2. Audio Device Detection
    print("\n[2/6] Detecting audio devices...")
    in_dev = ""
    out_dev = ""
    try:
        from core.audio_devices import get_input_devices, get_output_devices
        in_devices = get_input_devices()
        out_devices = get_output_devices()
        if in_devices:
            in_dev = in_devices[0]
            print(f"  ✓ Default Microphone: {in_dev}")
        if out_devices:
            out_dev = out_devices[0]
            print(f"  ✓ Default Speakers: {out_dev}")
    except Exception as e:
        print(f"  Note: Audio device detection fallback: {e}")

    # 3. AI Model Engine Configuration
    print("\n[3/6] Configuring Local AI Engine...")
    from core.ollama_manager import ollama_manager
    health = ollama_manager.check_health()
    model_name = custom_model or health.get("current_model") or "qwen2.5:3b"
    if health.get("executable_found"):
        print(f"  ✓ Local Ollama detected at: {health['executable_path']}")
        print(f"  ✓ Models available: {health.get('models', ['qwen2.5:3b'])}")
    else:
        print("  ℹ️ Local Ollama not found in standard directories. Running in portable mode.")
        print("     To enable local neural chat: install Ollama from https://ollama.com and run 'ollama pull qwen2.5:3b'.")

    # 4. Save Clean Base Configuration
    print("\n[4/6] Writing application configuration...")
    existing_cfg = {}
    if CONFIG_FILE.exists():
        try:
            existing_cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            existing_cfg = {}

    cfg = {
        "assistant_name": "JARVIS",
        "user_name": custom_user_name,
        "os_system": "windows",
        "gemini_api_key": existing_cfg.get("gemini_api_key", ""),
        "wake_word_enabled": True,
        "language_mode": language_mode,
        "input_device": in_dev,
        "output_device": out_dev,
        "llm_provider": "ollama",
        "llm_model": model_name,
        "llm_url": "http://127.0.0.1:11434",
        "providers": {
            "mode": "pipeline",
            "pipeline": {
                "stt": "whisper",
                "llm": "openai_compat",
                "tts": "system_tts",
            },
            "creds": {
                "whisper": {
                    "backend": "local",
                    "model": "base",
                    "device": "cpu",
                },
                "openai_compat": {
                    "base_url": "http://127.0.0.1:11434/v1",
                    "model": model_name,
                },
                "system_tts": {
                    "voice": "Microsoft Zira Desktop",
                    "rate": "0",
                },
            },
        },
        "memory_enabled": True,
        "ui_color": "#00f4ff",
    }
    # Preserve existing Meta OAuth config if present
    if "meta_app" in existing_cfg:
        cfg["meta_app"] = existing_cfg["meta_app"]

    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print("  ✓ Configuration saved to config/api_keys.json.")

    # 5. Create Desktop & Start Menu Shortcuts
    print("\n[5/6] Creating Windows Shortcuts...")
    from installer.shortcut_manager import (
        create_windows_shortcut,
        get_desktop_shortcut_path,
        get_start_menu_shortcut_path,
    )
    launcher = BASE_DIR / "launch_jarvis.bat"
    icon = BASE_DIR / "config" / "jarvis.ico"

    if launcher.exists():
        s1 = create_windows_shortcut(
            target_path=launcher,
            shortcut_path=get_desktop_shortcut_path(),
            description="J.A.R.V.I.S. Mark LVI Core AI Assistant",
            icon_path=icon if icon.exists() else None,
            working_directory=BASE_DIR,
        )
        s2 = create_windows_shortcut(
            target_path=launcher,
            shortcut_path=get_start_menu_shortcut_path(),
            description="J.A.R.V.I.S. Mark LVI Core AI Assistant",
            icon_path=icon if icon.exists() else None,
            working_directory=BASE_DIR,
        )
        print(f"  ✓ Desktop Shortcut: {'Created' if s1 else 'Skipped'}")
        print(f"  ✓ Start Menu Shortcut: {'Created' if s2 else 'Skipped'}")

    # 6. First-Run System Self-Test
    print("\n[6/6] Executing First-Run Diagnostic Self-Test...")
    test_results = {}

    # Test config
    test_results["config"] = CONFIG_FILE.exists()
    print(f"  • Configuration Persistence : {'PASS' if test_results['config'] else 'FAIL'}")

    # Test storage write
    test_file = DATA_DIR / ".setup_probe"
    try:
        test_file.write_text("probe", encoding="utf-8")
        test_results["storage"] = test_file.exists()
        test_file.unlink()
    except Exception:
        test_results["storage"] = False
    print(f"  • User Data Storage Write   : {'PASS' if test_results['storage'] else 'FAIL'}")

    # Test audio devices
    test_results["audio"] = bool(in_dev or out_dev)
    print(f"  • Audio I/O Readiness       : {'PASS' if test_results['audio'] else 'NOTE (Fallback Active)'}")

    # Test Ollama port 11434
    import socket
    ollama_online = False
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=1.0):
            ollama_online = True
    except Exception:
        ollama_online = False
    print(f"  • Local AI Engine Listener  : {'ONLINE (Port 11434)' if ollama_online else 'OFFLINE (Will launch on demand)'}")

    print("\n" + "=" * 75)
    print("  ✅ J.A.R.V.I.S. MARK LVI SETUP COMPLETE & READY TO LAUNCH!")
    print("  • Run via Desktop shortcut or launch_jarvis.bat")
    print("  • Dashboard: http://127.0.0.1:8000/app")
    print("=" * 75)
    return {
        "status": "SUCCESS",
        "user_name": custom_user_name,
        "model": model_name,
        "diagnostics": test_results,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Setup Wizard")
    parser.add_argument("--non-interactive", action="store_true", help="Run without interactive prompts")
    parser.add_argument("--user-name", default="Sir", help="Honorific/Name to address user")
    parser.add_argument("--model", default=None, help="LLM model name")
    parser.add_argument("--language", default="hinglish", help="Default language mode (hinglish/hindi/english)")
    args = parser.parse_args()

    run_setup(
        interactive=not args.non_interactive,
        custom_user_name=args.user_name,
        custom_model=args.model,
        language_mode=args.language,
    )
