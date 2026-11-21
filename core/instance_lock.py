"""
core/instance_lock.py — Single-Instance Process Lock & Lifecycle Guard for J.A.R.V.I.S.

Prevents duplicate launcher instances from starting and prevents terminating
healthy running J.A.R.V.I.S. processes.

Features:
- Lock file persistence in data/jarvis_host.lock
- Live PID validation with command-line fingerprinting (never kills healthy instances)
- Continuous heartbeat recording
- Graceful lock release on process exit
- Clear user-facing status messages
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import psutil

BASE_DIR = Path(__file__).resolve().parent.parent
LOCK_FILE = BASE_DIR / "data" / "jarvis_host.lock"


def is_pid_alive_and_jarvis(pid: int) -> bool:
    """Checks if a PID is alive, belongs to python, and is running J.A.R.V.I.S."""
    if pid <= 4:
        return False
    if not psutil.pid_exists(pid):
        return False
    try:
        proc = psutil.Process(pid)
        if not proc.is_running() or proc.status() in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD):
            return False
        # Inspect command line
        cmdline = proc.cmdline()
        cmd_str = " ".join(cmdline).lower()
        if "python" in proc.name().lower() and ("main.py" in cmd_str or "jarvis" in cmd_str or "mark_lvi_core" in cmd_str):
            return True
        return False
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def acquire_instance_lock(app_name: str = "JARVIS", lock_file: Optional[Path] = None) -> Tuple[bool, Optional[int]]:
    """Attempts to acquire the host lock.

    Returns:
        (True, None) if lock acquired successfully.
        (False, active_pid) if a healthy active instance is already running.
    """
    target_lock = lock_file or LOCK_FILE
    my_pid = os.getpid()
    target_lock.parent.mkdir(parents=True, exist_ok=True)

    if target_lock.exists():
        try:
            raw = target_lock.read_text(encoding="utf-8").strip()
            if raw:
                data = json.loads(raw)
                existing_pid = int(data.get("pid", 0))

                if existing_pid == my_pid:
                    # Re-entry in same process
                    return True, None

                if is_pid_alive_and_jarvis(existing_pid):
                    last_heartbeat = data.get("heartbeat_at", 0)
                    now = time.time()
                    # If process is alive and heartbeat is reasonably fresh (within 30s)
                    if now - last_heartbeat < 60:
                        logging.warning(
                            f"[{app_name}] An active instance is already running (PID: {existing_pid}, "
                            f"started: {data.get('started_at')}). Preventing duplicate launch."
                        )
                        return False, existing_pid
                    else:
                        logging.info(f"[{app_name}] Existing instance (PID {existing_pid}) has stale heartbeat. Reclaiming lock.")
                else:
                    logging.info(f"[{app_name}] Stale lockfile found (PID {existing_pid} not running). Reclaiming lock.")
        except Exception as e:
            logging.warning(f"[{app_name}] Could not parse existing lock file: {e}. Reclaiming.")

    # Write new lock
    lock_data = {
        "pid": my_pid,
        "app_name": str(app_name),
        "started_at": datetime.now().isoformat(),
        "heartbeat_at": time.time(),
        "host_machine": os.environ.get("COMPUTERNAME", "localhost"),
    }
    try:
        target_lock.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")
        return True, None
    except Exception as e:
        logging.error(f"[{app_name}] Failed to write lock file: {e}")
        return True, None  # Allow launch if filesystem error writing lock


def update_instance_heartbeat(lock_file: Optional[Path] = None) -> None:
    """Updates the heartbeat timestamp in the lock file."""
    target_lock = lock_file or LOCK_FILE
    if not target_lock.exists():
        return
    try:
        data = json.loads(target_lock.read_text(encoding="utf-8"))
        if data.get("pid") == os.getpid():
            data["heartbeat_at"] = time.time()
            target_lock.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def release_instance_lock(lock_file: Optional[Path] = None) -> None:
    """Releases the lock file if owned by the current process."""
    target_lock = lock_file or LOCK_FILE
    if not target_lock.exists():
        return
    try:
        data = json.loads(target_lock.read_text(encoding="utf-8"))
        if data.get("pid") == os.getpid():
            target_lock.unlink(missing_ok=True)
            logging.info("[JARVIS] Host lock released cleanly.")
    except Exception:
        pass
