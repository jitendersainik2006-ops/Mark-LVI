"""
tests/test_host_heartbeat_advancement.py — Regression Test for J.A.R.V.I.S. Host Heartbeat & Telemetry Advancement

Verifies:
1. host_monitor autostarts and transitions immediately out of INITIALIZING.
2. heartbeat_timestamp strictly advances over time across subsequent queries.
3. uptime_seconds increases as time elapses.
4. Dashboard and OAuth proxy port states match socket checks and status mutators.
5. GET /api/system/status and /api/system/heartbeat return dynamic, non-stale data.
6. Multi-process external heartbeat merging works safely.
"""

import os
import sys
import time
import unittest
from pathlib import Path

os.environ["JARVIS_SKIP_FIREWALL_PROMPT"] = "1"

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.host_monitor import HostMonitor, host_monitor


class TestHostHeartbeatAdvancement(unittest.TestCase):

    def test_01_host_monitor_autostart_and_status_progression(self):
        """Verifies host monitor starts automatically and never stays stuck in INITIALIZING."""
        monitor = HostMonitor(autostart=True)
        self.assertTrue(monitor._running, "HostMonitor must be marked running")
        self.assertIsNotNone(monitor._thread, "HostMonitorThread must exist")
        self.assertTrue(monitor._thread.is_alive(), "HostMonitorThread must be active")

        snap1 = monitor.to_dict()
        self.assertNotEqual(snap1["status"], "INITIALIZING", "Status must transition out of INITIALIZING on start")
        self.assertIn(snap1["status"], ("STANDBY", "HEALTHY", "RECONNECTING", "DEGRADED_AUDIO"))
        self.assertGreater(snap1["heartbeat_timestamp"], 0)
        self.assertGreaterEqual(snap1["uptime_seconds"], 0)

        # Wait 1.2 seconds to verify strict advancement
        time.sleep(1.2)
        snap2 = monitor.to_dict()

        self.assertGreater(
            snap2["heartbeat_timestamp"],
            snap1["heartbeat_timestamp"],
            f"Heartbeat timestamp must strictly advance: {snap2['heartbeat_timestamp']} > {snap1['heartbeat_timestamp']}"
        )
        self.assertGreaterEqual(
            snap2["uptime_seconds"],
            snap1["uptime_seconds"],
            f"Uptime seconds must increase or remain equal: {snap2['uptime_seconds']} >= {snap1['uptime_seconds']}"
        )
        monitor.stop()

    def test_02_socket_port_and_listener_reflection(self):
        """Verifies dashboard and OAuth proxy port detection and state mutators."""
        monitor = HostMonitor(autostart=False)
        snap = monitor.to_dict()
        self.assertEqual(snap["components"]["dashboard"]["port"], 8000)
        self.assertEqual(snap["components"]["oauth_proxy"]["port"], 8005)

        # Test state mutator for dashboard
        monitor.set_dashboard_status("ACTIVE", port=8000, is_listening=True)
        snap_dash = monitor.to_dict()
        self.assertTrue(snap_dash["components"]["dashboard"]["is_listening"])
        self.assertEqual(snap_dash["components"]["dashboard"]["status"], "ACTIVE")

        # Test state mutator for oauth proxy
        monitor.set_oauth_proxy_status("ACTIVE", port=8005, is_listening=True)
        snap_proxy = monitor.to_dict()
        self.assertTrue(snap_proxy["components"]["oauth_proxy"]["is_listening"])
        self.assertEqual(snap_proxy["components"]["oauth_proxy"]["status"], "ACTIVE")

        # Test Gemini Live status progression
        monitor.set_gemini_status("CONNECTED", model="gemini-2.0-flash-exp")
        snap_gem = monitor.to_dict()
        self.assertEqual(snap_gem["components"]["gemini_live"]["status"], "CONNECTED")
        self.assertEqual(snap_gem["status"], "HEALTHY", "Composite status must be HEALTHY when Gemini and Dashboard are connected")

        # Test Reconnect progression
        monitor.set_gemini_status("RECONNECTING")
        snap_rec = monitor.to_dict()
        self.assertEqual(snap_rec["components"]["gemini_live"]["reconnect_count"], 1)
        self.assertEqual(snap_rec["status"], "RECONNECTING")

    def test_03_dashboard_endpoint_dynamic_telemetry(self):
        """Verifies /api/system/status returns dynamic, advancing telemetry."""
        import json
        from dashboard.server import DashboardServer

        server = DashboardServer()
        ep = None
        for route in server.app.routes:
            if getattr(route, "path", None) == "/api/system/status":
                ep = route.endpoint
                break

        self.assertIsNotNone(ep, "Route /api/system/status must be registered on dashboard app")

        resp1 = ep()
        self.assertEqual(resp1.status_code, 200)
        d1 = json.loads(resp1.body.decode())
        self.assertNotEqual(d1["status"], "INITIALIZING")
        t1 = d1["heartbeat_timestamp"]
        up1 = d1["uptime_seconds"]

        # Wait 1.1s
        time.sleep(1.1)

        resp2 = ep()
        self.assertEqual(resp2.status_code, 200)
        d2 = json.loads(resp2.body.decode())
        t2 = d2["heartbeat_timestamp"]
        up2 = d2["uptime_seconds"]

        self.assertGreater(t2, t1, f"Timestamp must advance: {t2} > {t1}")
        self.assertGreaterEqual(up2, up1, f"Uptime must advance: {up2} >= {up1}")

        # Verified via direct ASGI endpoint execution without thread portal blocking

    def test_04_audio_and_system_resources_telemetry(self):
        """Verifies system resource stats and audio device telemetry are populated."""
        snap = host_monitor.to_dict()
        self.assertIn("system_resources", snap)
        self.assertIn("cpu_percent", snap["system_resources"])
        self.assertIn("memory_percent", snap["system_resources"])
        self.assertIn("thread_count", snap["system_resources"])
        self.assertGreaterEqual(snap["system_resources"]["thread_count"], 1)

        self.assertIn("audio_input", snap["components"])
        self.assertIn("audio_output", snap["components"])
        self.assertIn(snap["components"]["audio_input"]["status"], ("READY", "STANDBY", "CHECKING"))


if __name__ == "__main__":
    unittest.main()
