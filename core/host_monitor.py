"""
core/host_monitor.py — Host Stability, Connection Monitoring & Heartbeat Service for J.A.R.V.I.S.

Tracks:
- System resource utilization (CPU, memory, threads)
- Gemini Live connection status & reconnection attempts
- Local Ollama AI daemon status
- Dashboard server (port 8000) & hardened OAuth proxy (port 8005) listeners
- Audio input (mic) & output (speakers) readiness
- Dynamic uptime and continuous heartbeat telemetry
- Automatic background heartbeat persistence to data/host_heartbeat.json
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import psutil

BASE_DIR = Path(__file__).resolve().parent.parent
HEARTBEAT_FILE = BASE_DIR / "data" / "host_heartbeat.json"


class HostMonitor:
    def __init__(self, autostart: bool = True):
        self._start_time = time.time()
        self._pid = os.getpid()
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._state: Dict[str, Any] = {
            "status": "INITIALIZING",
            "pid": self._pid,
            "started_at": datetime.now().isoformat(),
            "uptime_seconds": 0,
            "heartbeat_timestamp": time.time(),
            "components": {
                "gemini_live": {
                    "status": "OFFLINE",
                    "model": "gemini-2.0-flash-exp",
                    "reconnect_count": 0,
                    "last_connected_at": None,
                    "last_error": None,
                },
                "ollama": {
                    "status": "STANDBY",
                    "endpoint": "http://127.0.0.1:11434",
                    "is_active": False,
                },
                "dashboard": {
                    "status": "STARTING",
                    "port": 8000,
                    "is_listening": False,
                },
                "oauth_proxy": {
                    "status": "STARTING",
                    "port": 8005,
                    "is_listening": False,
                },
                "audio_input": {
                    "status": "CHECKING",
                    "device": None,
                    "is_ready": False,
                },
                "audio_output": {
                    "status": "CHECKING",
                    "device": None,
                    "is_ready": False,
                },
            },
            "system_resources": {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "thread_count": 0,
            },
        }

        if autostart:
            self.start()

    def start(self) -> None:
        """Starts background heartbeat monitor thread and runs initial status sweep."""
        with self._lock:
            if self._running and self._thread and self._thread.is_alive():
                return
            self._running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="HostMonitorThread")
            self._thread.start()

            try:
                self._update_system_stats()
                self._check_ports()
                self._check_ollama()
                self._flush_heartbeat()
            except Exception as e:
                logging.debug(f"[HostMonitor] Initial sweep notice: {e}")

    def stop(self) -> None:
        """Stops background heartbeat monitor thread."""
        with self._lock:
            self._running = False

    def _monitor_loop(self) -> None:
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        while self._running:
            try:
                self._update_system_stats()
                self._check_ports()
                self._check_ollama()
                self._check_audio_devices()
                self._merge_external_heartbeat_if_available()
                self._flush_heartbeat()
            except Exception as e:
                logging.debug(f"[HostMonitor] Heartbeat loop notice: {e}")
            time.sleep(5)

    def _update_system_stats(self) -> None:
        with self._lock:
            now = time.time()
            self._state["uptime_seconds"] = int(now - self._start_time)
            self._state["heartbeat_timestamp"] = now

            try:
                proc = psutil.Process(self._pid)
                self._state["system_resources"]["cpu_percent"] = round(proc.cpu_percent(interval=None), 1)
                self._state["system_resources"]["memory_percent"] = round(proc.memory_percent(), 1)
                self._state["system_resources"]["thread_count"] = proc.num_threads()
            except Exception:
                pass

            self._update_composite_status()

    def _update_composite_status(self) -> None:
        comp = self._state["components"]
        gemini_st = comp.get("gemini_live", {}).get("status", "OFFLINE")
        dash_st = comp.get("dashboard", {}).get("status", "OFFLINE")
        dash_listening = comp.get("dashboard", {}).get("is_listening", False)

        if gemini_st == "CONNECTED" and (dash_st in ("ACTIVE", "BOUND") or dash_listening):
            self._state["status"] = "HEALTHY"
        elif gemini_st in ("RECONNECTING", "RATE_LIMITED"):
            self._state["status"] = "RECONNECTING"
        elif comp.get("audio_input", {}).get("status") == "UNAVAILABLE":
            self._state["status"] = "DEGRADED_AUDIO"
        elif dash_listening or dash_st in ("ACTIVE", "BOUND"):
            self._state["status"] = "STANDBY"
        else:
            self._state["status"] = "STANDBY"

    def _check_ports(self) -> None:
        """Lightweight check to see if ports 8000 and 8005 are listening."""
        import socket
        for comp_name, port in [("dashboard", 8000), ("oauth_proxy", 8005)]:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.05)
            try:
                result = sock.connect_ex(("127.0.0.1", port))
                is_open = (result == 0)
            except Exception:
                is_open = False
            finally:
                sock.close()

            with self._lock:
                self._state["components"][comp_name]["is_listening"] = is_open
                if is_open:
                    self._state["components"][comp_name]["status"] = "ACTIVE"
                else:
                    self._state["components"][comp_name]["status"] = (
                        "OFFLINE" if (time.time() - self._start_time > 3.0) else "STARTING"
                    )

    def _check_ollama(self) -> None:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.05)
        try:
            is_open = (sock.connect_ex(("127.0.0.1", 11434)) == 0)
        except Exception:
            is_open = False
        finally:
            sock.close()
        with self._lock:
            self._state["components"]["ollama"]["is_active"] = is_open
            self._state["components"]["ollama"]["status"] = "ACTIVE" if is_open else "STANDBY"

    def _check_audio_devices(self) -> None:
        with self._lock:
            if self._state["components"]["audio_input"]["status"] in ("CHECKING", "STANDBY") or not self._state["components"]["audio_input"]["device"]:
                try:
                    from memory.config_manager import get_input_device
                    from core import audio_devices
                    inp = get_input_device() or (audio_devices.list_devices("input") or [""])[0]
                    if inp:
                        self._state["components"]["audio_input"]["status"] = "READY"
                        self._state["components"]["audio_input"]["device"] = inp
                        self._state["components"]["audio_input"]["is_ready"] = True
                    else:
                        self._state["components"]["audio_input"]["status"] = "STANDBY"
                except Exception:
                    self._state["components"]["audio_input"]["status"] = "STANDBY"

            if self._state["components"]["audio_output"]["status"] in ("CHECKING", "STANDBY") or not self._state["components"]["audio_output"]["device"]:
                try:
                    from memory.config_manager import get_output_device
                    from core import audio_devices
                    outp = get_output_device() or (audio_devices.list_devices("output") or [""])[0]
                    if outp:
                        self._state["components"]["audio_output"]["status"] = "READY"
                        self._state["components"]["audio_output"]["device"] = outp
                        self._state["components"]["audio_output"]["is_ready"] = True
                    else:
                        self._state["components"]["audio_output"]["status"] = "STANDBY"
                except Exception:
                    self._state["components"]["audio_output"]["status"] = "STANDBY"

    def _merge_external_heartbeat_if_available(self) -> None:
        """If this process is a sub-service (e.g. standalone dashboard or OAuth proxy),
        and the primary JARVIS host is running and writing data/host_heartbeat.json,
        read its live Gemini Live and audio statuses so the dashboard API reflects
        the true whole-system health.
        """
        try:
            if not HEARTBEAT_FILE.exists():
                return
            raw = HEARTBEAT_FILE.read_text(encoding="utf-8").strip()
            if not raw:
                return
            data = json.loads(raw)
            ext_pid = data.get("pid")
            if ext_pid == self._pid:
                return

            if not ext_pid or not psutil.pid_exists(ext_pid):
                return

            ext_ts = float(data.get("heartbeat_timestamp", 0))
            if time.time() - ext_ts > 30:
                return

            ext_comp = data.get("components", {})
            if "gemini_live" in ext_comp:
                self._state["components"]["gemini_live"] = ext_comp["gemini_live"]
            if "audio_input" in ext_comp and ext_comp["audio_input"].get("status") not in (None, "CHECKING"):
                self._state["components"]["audio_input"] = ext_comp["audio_input"]
            if "audio_output" in ext_comp and ext_comp["audio_output"].get("status") not in (None, "CHECKING"):
                self._state["components"]["audio_output"] = ext_comp["audio_output"]
            if "ollama" in ext_comp and ext_comp["ollama"].get("is_active"):
                self._state["components"]["ollama"] = ext_comp["ollama"]
        except Exception:
            pass

    def _flush_heartbeat(self) -> None:
        try:
            snapshot = self.to_dict()
            tmp_file = HEARTBEAT_FILE.with_suffix(".tmp")
            tmp_file.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
            tmp_file.replace(HEARTBEAT_FILE)
        except Exception:
            pass

    # ── State Mutators ────────────────────────────────────────────────────────

    def set_gemini_status(self, status: str, model: Optional[str] = None, error: Optional[str] = None) -> None:
        with self._lock:
            g = self._state["components"]["gemini_live"]
            g["status"] = status
            if model:
                g["model"] = model
            if error:
                g["last_error"] = str(error)
            if status == "CONNECTED":
                g["last_connected_at"] = datetime.now().isoformat()
                g["last_error"] = None
            elif status == "RECONNECTING":
                g["reconnect_count"] = g.get("reconnect_count", 0) + 1
            self._update_composite_status()

    def set_ollama_status(self, status: str, is_active: bool = False) -> None:
        with self._lock:
            o = self._state["components"]["ollama"]
            o["status"] = status
            o["is_active"] = is_active
            self._update_composite_status()

    def set_dashboard_status(self, status: str, port: int = 8000, is_listening: bool = True) -> None:
        with self._lock:
            d = self._state["components"]["dashboard"]
            d["status"] = status
            d["port"] = port
            d["is_listening"] = is_listening
            self._update_composite_status()

    def set_oauth_proxy_status(self, status: str, port: int = 8005, is_listening: bool = True) -> None:
        with self._lock:
            p = self._state["components"]["oauth_proxy"]
            p["status"] = status
            p["port"] = port
            p["is_listening"] = is_listening
            self._update_composite_status()

    def set_audio_status(
        self,
        input_status: Optional[str] = None,
        output_status: Optional[str] = None,
        input_device: Optional[str] = None,
        output_device: Optional[str] = None,
    ) -> None:
        with self._lock:
            if input_status:
                self._state["components"]["audio_input"]["status"] = input_status
                self._state["components"]["audio_input"]["is_ready"] = (input_status == "READY")
            if input_device:
                self._state["components"]["audio_input"]["device"] = input_device

            if output_status:
                self._state["components"]["audio_output"]["status"] = output_status
                self._state["components"]["audio_output"]["is_ready"] = (output_status == "READY")
            if output_device:
                self._state["components"]["audio_output"]["device"] = output_device
            self._update_composite_status()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            self._state["uptime_seconds"] = int(now - self._start_time)
            self._state["heartbeat_timestamp"] = now
            self._update_composite_status()

            import copy
            return copy.deepcopy(self._state)


# Global singleton instance
host_monitor = HostMonitor()
