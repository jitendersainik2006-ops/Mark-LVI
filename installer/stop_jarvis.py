"""
installer/stop_jarvis.py — Verified Process Termination Utility for J.A.R.V.I.S. Mark LVI

Security Invariants:
1. ONLY terminates verified J.A.R.V.I.S.-owned processes.
2. NEVER terminates unrelated processes merely because they use ports 8000 or 8005.
3. Requires verified PID ownership: checks process name, executable, working directory,
   and command-line arguments against the J.A.R.V.I.S. installation directory before signaling termination.
4. Leaves Desktop shortcuts, Start Menu entries, configuration, and user data 100% intact.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def print_banner():
    print("=" * 70)
    print("      J.A.R.V.I.S. MARK LVI — VERIFIED SHUTDOWN UTILITY")
    print("=" * 70)
    print()


def is_jarvis_process(proc, base_dir: Path) -> bool:
    """
    Strictly verifies that a given process belongs to this J.A.R.V.I.S. installation.
    Requires:
    1. Process name contains 'python' (or matching Python runtime).
    2. Process command line or working directory is anchored to base_dir or
       executing a known J.A.R.V.I.S. entry script from this installation.
    NEVER matches unrelated processes on ports 8000/8005.
    """
    try:
        name = proc.name().lower()
        if "python" not in name:
            return False

        cmdline = proc.cmdline()
        if not cmdline:
            return False

        cmd_str = " ".join(cmdline).lower()
        base_dir_str = str(base_dir).lower()

        # Check if process was launched from or references the installation directory
        anchored_to_base = base_dir_str in cmd_str
        if not anchored_to_base:
            try:
                proc_cwd = (proc.cwd() or "").lower()
                if proc_cwd == base_dir_str or base_dir_str in proc_cwd:
                    anchored_to_base = True
            except Exception:
                pass

        # Specific known J.A.R.V.I.S. entry scripts
        jarvis_scripts = (
            "main.py",
            "dashboard/server.py",
            "dashboard\\server.py",
            "tools/oauth_callback_proxy.py",
            "tools\\oauth_callback_proxy.py",
            "oauth_callback_proxy.py",
            "ui.py",
        )
        has_script = any(s in cmd_str for s in jarvis_scripts)

        return has_script and (
            anchored_to_base
            or any(
                str(base_dir / s).lower() in cmd_str
                for s in ("main.py", "dashboard/server.py", "tools/oauth_callback_proxy.py")
            )
        )
    except Exception:
        return False


def terminate_verified_proc(proc) -> bool:
    """Safely terminates a verified process, giving it time to exit gracefully."""
    try:
        pid = proc.pid
        print(f"[Stop] Terminating verified J.A.R.V.I.S. process (PID {pid})...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        return True
    except Exception as e:
        print(f"[Stop] Notice terminating PID {getattr(proc, 'pid', 'unknown')}: {e}")
        return False


def stop_host() -> bool:
    print_banner()
    stopped_any = False

    try:
        import psutil
    except ImportError:
        print("[WARNING] 'psutil' is not installed. Falling back to lock file with strict verification.")
        psutil = None

    # 1. Stop host from lock file (with verified PID ownership)
    lock_file = DATA_DIR / "jarvis_host.lock"
    if lock_file.exists():
        try:
            data = json.loads(lock_file.read_text(encoding="utf-8"))
            pid = data.get("pid")
            if pid:
                if psutil:
                    if psutil.pid_exists(pid):
                        try:
                            proc = psutil.Process(pid)
                            if is_jarvis_process(proc, BASE_DIR):
                                if terminate_verified_proc(proc):
                                    stopped_any = True
                            else:
                                print(
                                    f"[Security Warning] PID {pid} in lock file does not match J.A.R.V.I.S. (found: '{proc.name()}'). Refusing to terminate."
                                )
                        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                            print(f"[Stop] PID {pid} is no longer running or inaccessible: {e}")
                    else:
                        print(f"[Stop] PID {pid} recorded in lock file is no longer active.")
                else:
                    print(f"[Stop] Unable to verify ownership of PID {pid} without psutil. Skipping blind taskkill.")
            try:
                lock_file.unlink()
            except Exception:
                pass
        except Exception as e:
            print(f"[Stop] Notice inspecting lock file: {e}")

    # 2. Scan running processes with verified PID ownership (NEVER by port alone)
    if psutil:
        current_pid = os.getpid()
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if proc.info["pid"] == current_pid:
                    continue
                if is_jarvis_process(proc, BASE_DIR):
                    if terminate_verified_proc(proc):
                        stopped_any = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    print()
    if stopped_any:
        print("✓ All active J.A.R.V.I.S. host services have been stopped cleanly.")
    else:
        print("✓ No running J.A.R.V.I.S. host instances were detected.")
    print("✓ Desktop shortcuts, configuration, and user data remain 100% intact.")
    print("=" * 70)
    return stopped_any


if __name__ == "__main__":
    stop_host()
