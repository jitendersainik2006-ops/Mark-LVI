"""
tests/test_master_upgrade_features.py — Comprehensive Test Suite for J.A.R.V.I.S. Master Upgrade

Verifies:
1. Ollama Manager & Dynamic Model Selection
2. Calendar & Agenda Management (Event CRUD + iCal Export)
3. Email & Notification Safeguards (Mandatory Human Approval Gate)
4. Daily Briefing Engine (System Health + Agenda Aggregation)
5. Computer Agent Safety Lifecycle (PLAN -> CONFIRM -> ACT -> OBSERVE -> VERIFY -> REPORT + Audit Log)
6. Floating Desktop Companion States & Visual Registry
7. Standalone Windows Release Package & Relocatable Script Invariants
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


class TestOllamaManager(unittest.TestCase):
    def test_01_paths_and_health(self):
        from core.ollama_manager import ollama_manager
        health = ollama_manager.check_health()
        self.assertIn("executable_found", health)
        self.assertIn("models", health)
        self.assertIn("current_model", health)

    def test_02_system_prompt_synthesis(self):
        from core.ollama_manager import ollama_manager
        hinglish_prompt = ollama_manager.build_system_prompt(language_mode="hinglish", user_name="Sir")
        self.assertIn("J.A.R.V.I.S.", hinglish_prompt)
        self.assertIn("Hinglish", hinglish_prompt)
        self.assertIn("Sir", hinglish_prompt)

        hindi_prompt = ollama_manager.build_system_prompt(language_mode="hindi", user_name="Sir")
        self.assertIn("हिंदी", hindi_prompt)

        english_prompt = ollama_manager.build_system_prompt(language_mode="english", user_name="Sir")
        self.assertIn("English", english_prompt)


class TestCalendarAndEmail(unittest.TestCase):
    def test_01_calendar_lifecycle_and_ics(self):
        from actions.manage_calendar import calendar_manager
        # Add event
        evt = calendar_manager.add_event(
            title="Automated Test Flight Check",
            start_time="2026-11-25 14:00",
            end_time="2026-11-25 15:30",
            description="Testing calendar scheduling",
            location="Command Bridge",
        )
        self.assertTrue(evt.id.startswith("evt_"))
        self.assertEqual(evt.title, "Automated Test Flight Check")

        # List events
        events = calendar_manager.list_events()
        found = any(e["id"] == evt.id for e in events)
        self.assertTrue(found, "Newly created event should appear in calendar list")

        # Export ICS
        ics_path = calendar_manager.export_ics()
        self.assertTrue(ics_path.exists())
        content = ics_path.read_text(encoding="utf-8")
        self.assertIn("BEGIN:VCALENDAR", content)
        self.assertIn("Automated Test Flight Check", content)

        # Cleanup event
        calendar_manager.delete_event(evt.id)

    def test_02_email_approval_gate(self):
        from actions.manage_email import email_manager
        # Create draft
        msg = email_manager.create_draft(
            recipient="test@example.com",
            subject="Status Report",
            body="All systems operational.",
        )
        self.assertEqual(msg.status, "DRAFT")
        self.assertFalse(msg.approval_granted)

        # Attempt to send without explicit confirmation -> MUST FAIL
        ok, res = email_manager.approve_and_send(msg.id, confirm=False)
        self.assertFalse(ok)
        self.assertIn("HUMAN CONFIRMATION REQUIRED", res)

        # Explicit confirmation -> SUCCESS
        ok, res = email_manager.approve_and_send(msg.id, confirm=True)
        self.assertTrue(ok)
        self.assertIn("APPROVED", res)


class TestDailyBriefing(unittest.TestCase):
    def test_01_briefing_aggregation(self):
        from core.daily_briefing import daily_briefing_engine
        briefing = daily_briefing_engine.generate_briefing(user_name="Sir")
        self.assertIn("greeting", briefing)
        self.assertIn("spoken_text", briefing)
        self.assertIn("system_health", briefing)
        self.assertIn("calendar_events", briefing)
        self.assertIn("tasks", briefing)
        self.assertTrue(len(briefing["spoken_text"]) > 20)


class TestComputerAgent(unittest.TestCase):
    def test_01_plan_permission_lifecycle(self):
        from core.computer_agent import computer_agent
        plan = computer_agent.create_plan(
            goal="Maintenance Sweep",
            steps_data=[
                {"action_name": "list_files", "description": "Scan temp files", "is_destructive": False},
                {"action_name": "delete_file", "description": "Purge cache", "is_destructive": True},
            ],
        )
        self.assertEqual(len(plan.steps), 2)

        # Non-destructive step auto-permission
        perm, _ = computer_agent.request_permission(plan.plan_id, 1)
        self.assertTrue(perm)

        # Destructive step requires user confirmation
        perm2, prompt = computer_agent.request_permission(plan.plan_id, 2)
        self.assertFalse(perm2)
        self.assertIn("CONFIRM", prompt)

        # Grant confirmation
        granted = computer_agent.grant_permission(plan.plan_id, 2, "CONFIRM")
        self.assertTrue(granted)

        # Execute
        ok, msg = computer_agent.execute_step(plan.plan_id, 2, lambda p: "File deleted successfully")
        self.assertTrue(ok)
        self.assertIn("verified", msg.lower())

        report = computer_agent.report_plan(plan.plan_id)
        self.assertIn("Maintenance Sweep", report)


class TestFloatingCompanion(unittest.TestCase):
    def test_01_states_and_colors(self):
        from core.floating_companion import FloatingCompanionWidget
        states = ["IDLE", "LISTENING", "THINKING", "SPEAKING", "WORKING"]
        for s in states:
            self.assertIn(s, FloatingCompanionWidget.STATE_COLORS)


class TestInstallerAndRelease(unittest.TestCase):
    def test_01_release_artifacts(self):
        rel_dir = Path(r"D:\JARVIS-AI\release\JARVIS_Mark_LVI_Windows_x64")
        self.assertTrue(rel_dir.exists(), "Release package directory must exist")
        self.assertTrue((rel_dir / "install_jarvis.bat").exists())
        self.assertTrue((rel_dir / "launch_jarvis.bat").exists())
        self.assertTrue((rel_dir / "stop_jarvis.bat").exists())
        self.assertTrue((rel_dir / "uninstall_jarvis.bat").exists())
        self.assertTrue((rel_dir / "README.txt").exists())
        self.assertTrue((rel_dir / "SHA256_MANIFEST.txt").exists())

        # Check relocatable batch script (Zero hardcoded D: drive paths)
        launch_bat_content = (rel_dir / "launch_jarvis.bat").read_text(encoding="utf-8")
        self.assertIn("%~dp0", launch_bat_content)
        self.assertNotIn("D:\\JARVIS-AI\\mark_lvi_core", launch_bat_content)


class TestAudioDevicesWrappers(unittest.TestCase):
    def test_01_device_wrappers(self):
        from core.audio_devices import get_input_devices, get_output_devices
        inputs = get_input_devices()
        outputs = get_output_devices()
        self.assertIsInstance(inputs, list)
        self.assertIsInstance(outputs, list)


class TestKnowledgeManagerAPI(unittest.TestCase):
    def test_01_sources_and_stats(self):
        from core.knowledge_manager import knowledge_manager
        sources = knowledge_manager.sources
        self.assertIsInstance(sources, list)
        stats = knowledge_manager.get_stats()
        self.assertIn("total_sources", stats)
        self.assertIn("active_sources", stats)
        self.assertIn("global_enabled", stats)


class TestSetupWizardVerification(unittest.TestCase):
    def test_01_system_requirements(self):
        from installer.setup_wizard import check_system_requirements
        reqs = check_system_requirements()
        self.assertIn("os", reqs)
        self.assertIn("python_version", reqs)
        self.assertIn("is_64bit", reqs)
        self.assertTrue(reqs["is_64bit"])


if __name__ == "__main__":
    unittest.main()

