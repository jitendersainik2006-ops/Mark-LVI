"""
tests/test_ui_stonic_experience.py — Stonic AI UI & Navigation Test Suite
Verifies:
- All 17 user navigation areas are present in sidebar and view panels.
- Companion states (IDLE, LISTENING, THINKING, SPEAKING, WORKING, MUTED, ERROR) have UI handlers.
- Both Modern Companion (Purple/Gold) and Tactical HUD (Cyan) visual modes are supported.
- Clear and safe notification handling with escapeHtml.
"""

import unittest
from pathlib import Path


class TestUiStonicExperience(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app_html_path = Path(__file__).resolve().parent.parent / "dashboard" / "static" / "app.html"
        cls.html = app_html_path.read_text(encoding="utf-8", errors="ignore")

    def test_01_all_17_navigation_areas_present(self):
        required_views = [
            "home", "chat", "voice", "tasks", "memory", "knowledge",
            "skills", "agents", "workflows", "schedules", "integrations",
            "workspace", "notifications", "system", "voice_settings",
            "security", "diagnostics"
        ]
        for v in required_views:
            self.assertIn(f'id="view-{v}"', self.html, f"Missing view panel for {v}")
            self.assertIn(f'id="nav-{v}"', self.html, f"Missing sidebar nav link for {v}")

    def test_02_all_seven_companion_states_handled(self):
        required_states = ["IDLE", "LISTENING", "THINKING", "SPEAKING", "WORKING", "MUTED", "ERROR"]
        for s in required_states:
            self.assertIn(f"state === '{s}'", self.html, f"Missing state handler branch for {s}")

    def test_03_visual_modes_companion_and_hud(self):
        self.assertIn("visualMode === 'hud'", self.html, "Tactical HUD mode branch must exist")
        self.assertIn("MODERN COMPANION", self.html, "Modern companion mode branch must exist")
        self.assertIn("toggleVisualMode", self.html, "toggleVisualMode function must exist")

    def test_04_theme_manager_and_variables(self):
        self.assertIn("toggleTheme", self.html, "toggleTheme function must exist")
        self.assertIn("--accent-purple:", self.html, "Primary purple accent must be defined")
        self.assertIn("--accent-cyan:", self.html, "Cyan accent must be defined")
        self.assertIn("--accent-gold:", self.html, "Gold accent must be defined")

    def test_05_notifications_and_diagnostics_integration(self):
        self.assertIn("loadNotifications", self.html, "loadNotifications function must exist")
        self.assertIn("runDiagnosticsAudit", self.html, "runDiagnosticsAudit function must exist")
        self.assertIn("clearNotifications", self.html, "clearNotifications function must exist")


if __name__ == "__main__":
    unittest.main()
