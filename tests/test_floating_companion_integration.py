"""
tests/test_floating_companion_integration.py — Verified Acceptance Tests for Floating Companion & IPC

Tests:
1. AssistantStateManager unit state transitions, mute toggling, and computer agent sync.
2. FloatingCompanionWidget instantiation, window flags, color maps, and themes.
3. DashboardServer /api/assistant/state GET and POST integration endpoints.
4. Voice mute toggle and /api/status state integration.
5. Emergency STOP execution and active task reflection.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure QApplication exists for headless test runs
try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
    _app = QApplication.instance()
    if _app is None:
        _app = QApplication(["-platform", "offscreen"])
except Exception:
    _app = None


class TestFloatingCompanionIntegration(unittest.TestCase):
    """Test suite for floating companion widget and IPC coordination."""

    def setUp(self):
        from core.assistant_state import assistant_state_manager
        assistant_state_manager.reset()

    def tearDown(self):
        from core.assistant_state import assistant_state_manager
        assistant_state_manager.reset()

    def test_01_assistant_state_manager_transitions(self):
        """Verify AssistantStateManager correctly manages states, tasks, and muting."""
        from core.assistant_state import assistant_state_manager

        state = assistant_state_manager.get_state()
        self.assertTrue(state["ok"])
        self.assertEqual(state["state"], "IDLE")
        self.assertFalse(state["is_muted"])

        # Transition to LISTENING
        updated = assistant_state_manager.set_state("LISTENING")
        self.assertEqual(updated["state"], "LISTENING")
        self.assertFalse(updated["is_muted"])

        # Transition to WORKING with task
        updated = assistant_state_manager.set_state("WORKING", active_task="Organizing files in Downloads")
        self.assertEqual(updated["state"], "WORKING")
        self.assertEqual(updated["active_task"], "Organizing files in Downloads")

        # Set audio level
        assistant_state_manager.set_audio_level(0.75)
        self.assertAlmostEqual(assistant_state_manager.get_state()["audio_level"], 0.75, places=2)

        # Mute toggle
        muted_state = assistant_state_manager.set_muted(True)
        self.assertTrue(muted_state["is_muted"])
        self.assertEqual(muted_state["state"], "MUTED")

        # Unmute returns to IDLE
        unmuted_state = assistant_state_manager.set_muted(False)
        self.assertFalse(unmuted_state["is_muted"])
        self.assertEqual(unmuted_state["state"], "IDLE")

    def test_02_floating_companion_widget_properties(self):
        """Verify FloatingCompanionWidget initializes with frameless flags, state colors, and themes."""
        from core.floating_companion import FloatingCompanionWidget, _PYQT_AVAILABLE
        if not _PYQT_AVAILABLE or _app is None:
            self.skipTest("PyQt6 offscreen GUI not available in this environment.")

        widget = FloatingCompanionWidget(size=140)
        self.assertIsNotNone(widget)

        # Verify frameless and always-on-top flags
        flags = widget.windowFlags()
        self.assertTrue(bool(flags & Qt.WindowType.FramelessWindowHint))
        self.assertTrue(bool(flags & Qt.WindowType.WindowStaysOnTopHint))

        # Verify state colors
        self.assertIn("WORKING", widget.STATE_COLORS)
        self.assertIn("MUTED", widget.STATE_COLORS)
        self.assertIn("IDLE", widget.STATE_COLORS)

        # Verify state transition
        widget.set_state("WORKING", active_task="Automated build verification")
        self.assertEqual(widget.state, "WORKING")
        self.assertEqual(widget.active_task, "Automated build verification")

        # Verify theme switching
        widget.set_theme("GOLD")
        self.assertEqual(widget.current_theme, "GOLD")
        widget.set_theme("PURPLE")
        self.assertEqual(widget.current_theme, "PURPLE")

        # Verify visual effects toggles
        widget.set_visual_effect("rings", False)
        self.assertFalse(widget.show_rings)
        widget.set_visual_effect("rings", True)
        self.assertTrue(widget.show_rings)

        widget.close()

    def test_03_dashboard_server_assistant_state_endpoints(self):
        """Verify GET and POST /api/assistant/state endpoints on DashboardServer."""
        from dashboard.server import DashboardServer
        from starlette.testclient import TestClient

        server = DashboardServer()
        client = TestClient(server.app)

        # Test GET /api/assistant/state
        res_get = client.get("/api/assistant/state")
        self.assertEqual(res_get.status_code, 200)
        data = res_get.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("state", data)
        self.assertIn("active_task", data)

        # Test POST /api/assistant/state
        res_post = client.post(
            "/api/assistant/state",
            json={"state": "WORKING", "active_task": "Running workflow tests", "audio_level": 0.6},
        )
        self.assertEqual(res_post.status_code, 200)
        post_data = res_post.json()
        self.assertTrue(post_data.get("ok"))
        self.assertEqual(post_data.get("state"), "WORKING")
        self.assertEqual(post_data.get("active_task"), "Running workflow tests")

        # Verify GET reflects the newly set state
        res_verify = client.get("/api/assistant/state")
        self.assertEqual(res_verify.json().get("state"), "WORKING")
        self.assertEqual(res_verify.json().get("active_task"), "Running workflow tests")

    def test_04_status_endpoint_includes_assistant_state(self):
        """Verify GET /api/status includes assistant_state, active_task, and is_muted."""
        from core.assistant_state import assistant_state_manager
        from dashboard.server import DashboardServer
        from starlette.testclient import TestClient

        assistant_state_manager.set_state("THINKING", active_task="Evaluating reasoning graph")
        server = DashboardServer()
        client = TestClient(server.app)

        res = client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("assistant_state"), "THINKING")
        self.assertEqual(data.get("active_task"), "Evaluating reasoning graph")
        self.assertIn("is_muted", data)

    def test_05_companion_action_handlers_and_stop(self):
        """Verify companion methods for voice activation, mute toggle, and PC agent stop."""
        from core.assistant_state import assistant_state_manager
        from core.computer_agent import computer_agent
        from core.floating_companion import FloatingCompanionWidget, _PYQT_AVAILABLE
        if not _PYQT_AVAILABLE or _app is None:
            self.skipTest("PyQt6 offscreen GUI not available in this environment.")

        widget = FloatingCompanionWidget(size=140)

        # Test toggle_microphone_mute
        initial_mute = widget.is_muted
        widget.toggle_microphone_mute()
        self.assertEqual(widget.is_muted, not initial_mute)
        self.assertEqual(widget.state, "MUTED" if widget.is_muted else "IDLE")

        # Test quick_voice_activation
        widget.quick_voice_activation()
        self.assertEqual(widget.state, "LISTENING")

        # Test stop_pc_agent
        widget.set_state("WORKING", active_task="Automated task")
        self.assertEqual(widget.state, "WORKING")
        widget.stop_pc_agent()
        self.assertEqual(widget.state, "IDLE")
        self.assertEqual(widget.active_task, "")

        widget.close()


if __name__ == "__main__":
    unittest.main()
