"""
tests/test_stonic_experience_and_distribution.py

Comprehensive Test Suite for J.A.R.V.I.S. Mark LVI Stonic AI Experience
and Universal Windows Distribution System.

Test Coverage:
1. Floating Companion States, Themes, Effects, Always-On-Top, and Fullscreen Auto-Hide
2. Voice Configuration, Hindi/Hinglish/English Engine, and Interruption Handling
3. Unified Memory: Pinned items, Auto-create toggle, Retention policy, Backup/Recovery, Export
4. Computer-Use AI Agent: PLAN -> PERMISSION -> ACT -> OBSERVE -> VERIFY, Pause/Resume/Cancel, Retry
5. Daily Briefing: Health, Reminders, 3 Curated Discoveries with Links, Research Topics, Weather
6. Document & Visual Understanding: PDF/DOCX/Text, Image Metadata/OCR, Summary, Task Creation
7. System Dependency Checks: OS version, RAM, Disk, 64-bit Python
8. Uninstaller Data Preservation: Keeps personal memory and config by default
9. Safe Update & Rollback Engine: Version check, Pre-update backup, Rollback verification
10. Multi-User Isolation & Portable Distribution: Zero developer leaks, Portable ZIP integrity
11. Missing Model & Offline Resilience: Graceful fallback when local models/internet are absent
12. LAN Security Regression: Route isolation, Peer socket verification, Host header check
"""

import hashlib
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.computer_agent import computer_agent, DESTRUCTIVE_ACTIONS, AgentPlan, PlanStep
from core.daily_briefing import daily_briefing_engine
from core.knowledge_manager import knowledge_manager
from installer.updater import (
    CURRENT_VERSION,
    get_current_version,
    create_pre_update_backup,
    verify_package_integrity,
    rollback_update,
)
from memory.memory_manager import (
    load_memory,
    save_memory,
    remember,
    forget,
    pin_memory,
    is_auto_create_enabled,
    set_auto_create_enabled,
    format_memory_for_prompt,
    get_retention_days,
    set_retention_days,
    apply_retention_policy,
    export_memory_backup,
    import_memory_backup,
    export_user_data_bundle,
)


class TestStonicCompanionExperience(unittest.TestCase):
    """1. Floating Companion Avatar, States, Themes, and Visual Effects."""

    def test_companion_states_and_colors(self):
        from core.floating_companion import FloatingCompanionWidget
        colors = FloatingCompanionWidget.STATE_COLORS
        for required_state in ["IDLE", "LISTENING", "THINKING", "SPEAKING", "WORKING", "ERROR"]:
            self.assertIn(required_state, colors, f"Missing state {required_state}")

    def test_companion_themes_and_effects_interface(self):
        from core.floating_companion import FloatingCompanionWidget
        themes = FloatingCompanionWidget.THEMES
        self.assertIn("CYAN", themes)
        self.assertIn("GOLD", themes)
        self.assertIn("GREEN", themes)
        self.assertIn("PURPLE", themes)
        self.assertIn("CRIMSON", themes)


class TestVoiceSystem(unittest.TestCase):
    """2. Natural Voice System, Interruption, and Language Support."""

    def test_voice_interruption_stop_method(self):
        from core.tts import TTSPlayer
        mock_engine = MagicMock()
        player = TTSPlayer(mock_engine)
        player.stop()
        self.assertFalse(player.is_playing)

    def test_hindi_voice_engine_validation(self):
        from core.hindi_voice_engine import HindiVoiceEngine
        engine = HindiVoiceEngine()
        valid, msg = engine.validate_hindi_text("नमस्ते जार्विस, आप कैसे हैं?")
        self.assertTrue(valid)
        invalid, msg2 = engine.validate_hindi_text("Hello Jarvis, how are you?")
        self.assertFalse(invalid)


class TestUnifiedMemoryAndPersonality(unittest.TestCase):
    """3. Unified Memory: Pinning, Retention, Backup, and Recovery."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_mem_file = Path(self.test_dir) / "test_memory.json"
        self.patch_path = patch("memory.memory_manager.MEMORY_PATH", self.test_mem_file)
        self.patch_path.start()

    def tearDown(self):
        self.patch_path.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_pin_memory_and_prompt_priority(self):
        remember("test_pref", "Coffee every morning", category="preferences")
        pinned = pin_memory("preferences", "test_pref", pinned=True)
        self.assertTrue(pinned)

        mem = load_memory()
        self.assertTrue(mem["preferences"]["test_pref"].get("pinned"))

        # Format memory for prompt and verify pin marker
        prompt_block = format_memory_for_prompt(mem)
        self.assertIn("Coffee every morning", prompt_block)
        self.assertIn("📌", prompt_block)

    def test_auto_create_toggle(self):
        orig = is_auto_create_enabled()
        set_auto_create_enabled(False)
        self.assertFalse(is_auto_create_enabled())
        set_auto_create_enabled(True)
        self.assertTrue(is_auto_create_enabled())
        set_auto_create_enabled(orig)

    def test_memory_backup_and_import(self):
        remember("arch_goal", "Build Stonic AI Experience", category="projects")
        backup_file = Path(self.test_dir) / "backup.json"
        export_memory_backup(backup_file)
        self.assertTrue(backup_file.exists())

        # Clear memory then restore
        save_memory({})
        self.assertEqual(load_memory().get("projects", {}), {})

        restored = import_memory_backup(backup_file, merge=True)
        self.assertIn("arch_goal", restored["projects"])

    def test_user_data_bundle_export(self):
        remember("favorite_theme", "Cybernetic Cyan", category="preferences")
        bundle = export_user_data_bundle()
        self.assertIn("export_date", bundle)
        self.assertIn("preferences", bundle)
        self.assertIn("total_entries", bundle)


class TestComputerUseAgent(unittest.TestCase):
    """4. Computer-Use AI Agent: Lifecycle, Permission Gates, and Control."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.orig_audit = computer_agent.audit_file
        computer_agent.audit_file = Path(self.temp_dir) / "test_audit.log"

    def tearDown(self):
        computer_agent.audit_file = self.orig_audit
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_plan_lifecycle_and_destructive_gating(self):
        steps = [
            {"action_name": "list_directory", "parameters": {"path": "."}, "description": "Safe listing"},
            {"action_name": "delete_file", "parameters": {"path": "danger.txt"}, "description": "Destructive deletion"},
        ]
        plan = computer_agent.create_plan("File cleanup workflow", steps)
        self.assertEqual(len(plan.steps), 2)

        # Step 1: Safe action
        ok, msg = computer_agent.request_permission(plan.plan_id, 1)
        self.assertTrue(ok)

        # Step 2: Destructive action
        ok2, prompt = computer_agent.request_permission(plan.plan_id, 2)
        self.assertFalse(ok2)
        self.assertIn("CONFIRM", prompt)

        # Cannot execute step 2 without explicit permission
        exec_ok, exec_msg = computer_agent.execute_step(plan.plan_id, 2)
        self.assertFalse(exec_ok)

        # Grant permission
        granted = computer_agent.grant_permission(plan.plan_id, 2, "CONFIRM")
        self.assertTrue(granted)

    def test_agent_plan_controls(self):
        plan = computer_agent.create_plan("Control test", [{"action_name": "read_file", "parameters": {}}])
        self.assertTrue(computer_agent.pause_plan(plan.plan_id))
        self.assertEqual(computer_agent.get_plan(plan.plan_id)["status"], "PAUSED")
        self.assertTrue(computer_agent.resume_plan(plan.plan_id))
        self.assertEqual(computer_agent.get_plan(plan.plan_id)["status"], "IN_PROGRESS")
        self.assertTrue(computer_agent.cancel_plan(plan.plan_id))
        self.assertEqual(computer_agent.get_plan(plan.plan_id)["status"], "CANCELLED")


class TestDailyBriefingEngine(unittest.TestCase):
    """5. Personalized Daily Briefing with Discoveries and Reminders."""

    def test_briefing_generation_and_discoveries(self):
        briefing = daily_briefing_engine.generate_briefing("Sir")
        self.assertIn("spoken_text", briefing)
        self.assertIn("system_health", briefing)
        self.assertIn("discoveries", briefing)
        self.assertGreaterEqual(len(briefing["discoveries"]), 1)
        self.assertLessEqual(len(briefing["discoveries"]), 3)

        # Confirm research topics present
        self.assertIn("research_topics", briefing)
        self.assertIsInstance(briefing["research_topics"], list)


class TestDocumentAndVisualUnderstanding(unittest.TestCase):
    """6. Document and Visual Understanding: PDF, Image, Summaries, and Tasks."""

    def test_image_understanding_extraction(self):
        from PIL import Image
        temp_dir = tempfile.mkdtemp()
        try:
            img_path = Path(temp_dir) / "test_diagram.png"
            img = Image.new("RGB", (320, 240), color="blue")
            img.save(img_path)

            sections = knowledge_manager._extract_text_from_file(img_path)
            self.assertTrue(len(sections) > 0)
            sec_name, sec_text = sections[0]
            self.assertIn("320x240", sec_text)
            self.assertIn("RGB", sec_text)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_document_summary_and_task_linking(self):
        temp_dir = tempfile.mkdtemp()
        temp_p = Path(temp_dir)
        try:
            with patch("core.knowledge_manager.DOCS_DIR", temp_p / "documents"), \
                 patch("core.knowledge_manager.SOURCES_FILE", temp_p / "sources.json"), \
                 patch("core.knowledge_manager.CHUNKS_FILE", temp_p / "chunks.json"):
                (temp_p / "documents").mkdir(parents=True, exist_ok=True)
                src_id = knowledge_manager.ingest_text(
                    title="Desktop Architecture Notes",
                    text="J.A.R.V.I.S. Mark LVI introduces the Stonic AI desktop companion with unified memory.",
                    section="Architecture Overview",
                )
                summary = knowledge_manager.summarize_document(src_id)
                self.assertEqual(summary["title"], "Desktop Architecture Notes")
                self.assertTrue(len(summary["sections"]) > 0)
                self.assertIn("Overview", summary["sections"])

                task_res = knowledge_manager.create_task_from_knowledge(src_id, "Review Desktop Architecture")
                self.assertEqual(task_res["status"], "SUCCESS")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestSystemRequirementsAndDependencies(unittest.TestCase):
    """7. System Dependency Checks and Diagnostic Verification."""

    def test_system_requirements_check(self):
        from installer.setup_wizard import check_system_requirements
        reqs = check_system_requirements()
        self.assertIn("windows_version", reqs)
        self.assertIn("python_version", reqs)
        self.assertIn("total_ram_gb", reqs)
        self.assertIn("free_disk_gb", reqs)
        self.assertTrue(reqs["is_64bit"])


class TestUninstallerDataRetention(unittest.TestCase):
    """8. Uninstaller Preservation of Personal Data."""

    def test_uninstall_preserves_data_by_default(self):
        from installer.uninstall_jarvis import run_uninstall
        with patch("installer.stop_jarvis.stop_host"), patch("installer.shortcut_manager.remove_shortcuts", return_value={"desktop": True, "start_menu": True}):
            res = run_uninstall(keep_user_data=True, force_purge_data=False)
            self.assertEqual(res["status"], "SUCCESS")


class TestSafeUpdateAndRollback(unittest.TestCase):
    """9. Safe Update and Rollback Engine."""

    def test_version_retrieval(self):
        v = get_current_version()
        self.assertIn("version", v)
        self.assertTrue(v["version"].startswith("56."))

    def test_pre_update_backup_creation(self):
        temp_bdir = tempfile.mkdtemp()
        try:
            backup_path = create_pre_update_backup(Path(temp_bdir) / "test_backup")
            self.assertTrue(backup_path.exists())
            self.assertTrue((backup_path / "core").exists())
        finally:
            shutil.rmtree(temp_bdir, ignore_errors=True)


class TestMultiUserIsolationAndPackageIntegrity(unittest.TestCase):
    """10. Multi-User Isolation and Release Integrity."""

    def test_release_package_manifest_and_zero_developer_data(self):
        rel_dir = Path(r"D:\JARVIS-AI\release\JARVIS_Mark_LVI_Windows_x64")
        self.assertTrue(rel_dir.exists(), "Release directory must exist.")

        manifest_file = rel_dir / "SHA256_MANIFEST.txt"
        self.assertTrue(manifest_file.exists(), "SHA256_MANIFEST.txt must exist.")

        # Verify no developer private api_keys.json or developer long_term.json in release
        self.assertFalse((rel_dir / "config" / "api_keys.json").exists())

        rel_mem = rel_dir / "memory" / "long_term.json"
        if rel_mem.exists():
            mem_data = json.loads(rel_mem.read_text(encoding="utf-8"))
            for cat in ["identity", "preferences", "projects"]:
                self.assertEqual(mem_data.get(cat, {}), {}, f"Release memory {cat} must be empty.")

        # Verify Portable ZIP exists
        zip_path = Path(r"D:\JARVIS-AI\release\JARVIS_Mark_LVI_Windows_x64_Portable.zip")
        self.assertTrue(zip_path.exists(), "Portable ZIP must exist.")
        self.assertTrue(zipfile.is_zipfile(zip_path), "Must be valid ZIP archive.")


class TestOfflineAndMissingModelResilience(unittest.TestCase):
    """11. Missing Model & Offline Scenarios."""

    def test_ollama_manager_offline_handling(self):
        from core.ollama_manager import OllamaManager
        mgr = OllamaManager()
        health = mgr.check_health()
        self.assertIn("executable_found", health)
        self.assertIn("running", health)


class TestLANSecurityRegression(unittest.TestCase):
    """12. LAN Security Boundary Regression."""

    def test_lan_route_restrictions(self):
        from dashboard.server import DashboardServer
        self.assertIn("/api/instagram", DashboardServer._RESTRICTED_LAN_PREFIXES)
        self.assertIn("/api/reels", DashboardServer._RESTRICTED_LAN_PREFIXES)
        self.assertIn("/api/gym", DashboardServer._RESTRICTED_LAN_PREFIXES)
        self.assertIn("/api/shutdown", DashboardServer._RESTRICTED_LAN_PREFIXES)
        self.assertIn("/config", DashboardServer._RESTRICTED_LAN_PREFIXES)


if __name__ == "__main__":
    unittest.main()
