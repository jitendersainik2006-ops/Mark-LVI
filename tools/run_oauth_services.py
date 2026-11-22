"""
tools/run_oauth_services.py — Combined Resilient Runner for J.A.R.V.I.S. Backend (8000) & Hardened Proxy (8005)

Features:
- Runs hardened callback-only reverse proxy on 127.0.0.1:8005
- Runs J.A.R.V.I.S. dashboard server on 127.0.0.1:8000
- Auto-recovers from transient network or loop exits
- Strictly blocks all non-callback routes (HTTP 403 Forbidden)
- Flushes detailed logs to data/oauth_services.log and stdout
- Enforces D: drive operation
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
import time
from pathlib import Path

from core.path_manager import get_app_root, get_data_dir, validate_installation_path

BASE_DIR = get_app_root()
DATA_DIR = get_data_dir()

# Universal Portability Validation across C:, D:, O:, etc.
_is_valid, _path_msg = validate_installation_path(BASE_DIR)
if not _is_valid:
    raise RuntimeError(f"[FATAL MIGRATION ERROR] {_path_msg}")

# Skip UAC firewall elevation in automated/headless mode
os.environ["JARVIS_SKIP_FIREWALL_PROMPT"] = "1"

LOG_FILE = DATA_DIR / "oauth_services.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

file_handler = logging.FileHandler(str(LOG_FILE), mode="a", encoding="utf-8")
console_handler = logging.StreamHandler(sys.stdout)

logging.basicConfig(
    level=logging.INFO,
    format="[OAuthServices] %(asctime)s - %(message)s",
    handlers=[file_handler, console_handler],
)

from tools.oauth_callback_proxy import run_proxy, PROXY_PORT
from dashboard.server import DashboardServer

_STOP_EVENT = threading.Event()


def proxy_worker():
    while not _STOP_EVENT.is_set():
        try:
            try:
                from core.host_monitor import host_monitor
                host_monitor.set_oauth_proxy_status("ACTIVE", port=PROXY_PORT, is_listening=True)
            except Exception:
                pass
            run_proxy(PROXY_PORT)
        except Exception as e:
            if _STOP_EVENT.is_set():
                break
            logging.exception(f"Proxy worker error: {e}. Restarting in 1s...")
            time.sleep(1)


def main():
    logging.info("Initializing J.A.R.V.I.S. OAuth Services...")
    try:
        from core.host_monitor import host_monitor
        host_monitor.start()
    except Exception:
        pass
    proxy_t = threading.Thread(target=proxy_worker, daemon=True)
    proxy_t.start()
    time.sleep(0.5)

    while not _STOP_EVENT.is_set():
        try:
            logging.info("Starting J.A.R.V.I.S. Dashboard Server on 127.0.0.1:8000...")
            srv = DashboardServer()
            asyncio.run(srv.serve())
        except KeyboardInterrupt:
            logging.info("Shutting down OAuth Services cleanly...")
            _STOP_EVENT.set()
            break
        except BaseException as be:
            if _STOP_EVENT.is_set():
                break
            logging.exception(f"Dashboard server loop exited ({be.__class__.__name__}: {be}). Restarting in 2s...")
            time.sleep(2)


if __name__ == "__main__":
    main()
