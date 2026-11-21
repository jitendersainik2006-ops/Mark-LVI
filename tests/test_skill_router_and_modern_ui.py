"""
tests/test_skill_router_and_modern_ui.py — Verification of Central Skill Router and Modern Voice UI
"""

import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.skill_router import (
    SkillRouter,
    SkillDefinition,
    TIER_READ_ONLY,
    TIER_STANDARD,
    TIER_CONSEQUENTIAL,
    skill_router
)


class TestSkillRouterAndModernUI(unittest.TestCase):
    def setUp(self):
        self.router = skill_router

    def test_built_in_skills_registration(self):
        """Verify that all core built-in skills are registered with appropriate permission tiers."""
        skills = self.router.list_skills()
        self.assertGreaterEqual(len(skills), 10)
        
        skill_ids = [s["id"] for s in skills]
        expected_skills = [
            "system_status",
            "search_files",
            "list_tasks",
            "query_memory",
            "search_knowledge",
            "android_status",
            "voice_settings",
            "gmail_draft",
            "list_available_skills",
            "reels_ledger"
        ]
        for exp in expected_skills:
            self.assertIn(exp, skill_ids, f"Expected skill {exp} not registered in SkillRouter")

    def test_permission_tier_isolation(self):
        """Verify that read-only skills do not require consequential confirmation."""
        status_skill = self.router.get_skill("system_status")
        self.assertIsNotNone(status_skill)
        self.assertEqual(status_skill.permission_tier, TIER_READ_ONLY)
        
        reels_skill = self.router.get_skill("reels_ledger")
        self.assertIsNotNone(reels_skill)
        self.assertEqual(reels_skill.permission_tier, TIER_READ_ONLY)

    def test_multilingual_intent_routing_english(self):
        """Verify natural language routing in English."""
        res = self.router.route_natural_intent("Jarvis, check the system status please", lang="english")
        self.assertIsNotNone(res)
        self.assertTrue(res.get("matched"))
        self.assertEqual(res.get("skill_id"), "system_status")
        
        exec_res = self.router.execute_skill(res["skill_id"], res.get("proposed_params", {}), lang="english")
        self.assertTrue(exec_res.get("ok"))
        self.assertIn("CPU", exec_res.get("spoken_summary", ""))

    def test_multilingual_intent_routing_hindi(self):
        """Verify natural language routing in pure Hindi."""
        res = self.router.route_natural_intent("जार्विस, सिस्टम स्टेटस दिखाओ", lang="hindi")
        self.assertIsNotNone(res)
        self.assertTrue(res.get("matched"))
        self.assertEqual(res.get("skill_id"), "system_status")
        
        exec_res = self.router.execute_skill(res["skill_id"], res.get("proposed_params", {}), lang="hindi")
        self.assertTrue(exec_res.get("ok"))
        self.assertIn("सीपीयू", exec_res.get("spoken_summary", ""))

    def test_multilingual_intent_routing_hinglish(self):
        """Verify natural language routing in Hinglish."""
        res = self.router.route_natural_intent("Jarvis, meri files search karo", lang="hinglish")
        self.assertIsNotNone(res)
        self.assertTrue(res.get("matched"))
        self.assertEqual(res.get("skill_id"), "search_files")

    def test_reels_ledger_skill_integrity(self):
        """Verify that reels_ledger skill correctly reports the 74-entry ledger."""
        res = self.router.route_natural_intent("Show me my Instagram reels", lang="english")
        self.assertIsNotNone(res)
        self.assertTrue(res.get("matched"))
        self.assertEqual(res.get("skill_id"), "reels_ledger")
        
        exec_res = self.router.execute_skill(res["skill_id"], res.get("proposed_params", {}), lang="english")
        self.assertTrue(exec_res.get("ok"))
        self.assertIn("74", exec_res.get("spoken_summary", ""))
        self.assertEqual(exec_res["data"].get("count"), 74)

    def test_dashboard_app_html_companion_integrity(self):
        """Verify that app.html contains all 18 navigation sections and companion canvas."""
        app_html_path = PROJECT_ROOT / "dashboard" / "static" / "app.html"
        self.assertTrue(app_html_path.exists())
        content = app_html_path.read_text(encoding="utf-8")
        
        # Verify old cyan HUD face.png is gone
        self.assertNotIn("face.png", content)
        
        # Verify 18 sections
        expected_views = [
            'id="view-home"',
            'id="view-voice"',
            'id="view-chat"',
            'id="view-memory"',
            'id="view-knowledge"',
            'id="view-skills"',
            'id="view-tasks"',
            'id="view-pc_control"',
            'id="view-files"',
            'id="view-android"',
            'id="view-notifications"',
            'id="view-gmail"',
            'id="view-reels"',
            'id="view-system"',
            'id="view-models"',
            'id="view-voice_settings"',
            'id="view-security"',
            'id="view-diagnostics"'
        ]
        for v in expected_views:
            self.assertIn(v, content, f"Missing view panel {v} in app.html")
            
        # Verify companion canvas and command palette
        self.assertIn('id="hero-avatar-canvas"', content)
        self.assertIn('id="cmd-palette"', content)


if __name__ == "__main__":
    unittest.main()
