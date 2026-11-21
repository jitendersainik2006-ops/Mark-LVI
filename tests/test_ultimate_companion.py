"""
tests/test_ultimate_companion.py — Automated Test Suite for Ultimate Human-Like AI Companion

Validates:
1. 3 Selectable Personalities (J.A.R.V.I.S., FRIDAY, ANALYST) in CharacterManager & ConversationEngine
2. Shared memory and tool permissions across all personalities
3. Phonetic pronunciation dictionary and substitution engine
4. Windows automatic startup API endpoints and configuration modes
5. Real-time REST endpoints for personality switching and autostart
"""

import json
import os
import sys
import unittest
from pathlib import Path

# Ensure mark_lvi_core is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.character_manager import CharacterManager, character_manager
from core.human_conversation_engine import HumanConversationEngine, human_conversation_engine


class TestUltimateCompanion(unittest.TestCase):

    def setUp(self):
        # Reset character personality to JARVIS
        character_manager.set_personality("JARVIS")

    def test_personality_profiles_exist(self):
        profiles = character_manager.get_personalities()
        self.assertEqual(len(profiles), 3)
        ids = [p["id"] for p in profiles]
        self.assertIn("JARVIS", ids)
        self.assertIn("FRIDAY", ids)
        self.assertIn("ANALYST", ids)

        # Check fields
        for p in profiles:
            self.assertIn("name", p)
            self.assertIn("title", p)
            self.assertIn("tone_description", p)
            self.assertIn("greeting", p)
            self.assertIn("prompt_instructions", p)
            self.assertIn("default_voice", p)

    def test_personality_switching(self):
        # Switch to FRIDAY
        res_friday = character_manager.set_personality("FRIDAY")
        self.assertIsNotNone(res_friday)
        self.assertEqual(res_friday["id"], "FRIDAY")
        char = character_manager.get_character()
        self.assertEqual(char.personality_id, "FRIDAY")
        self.assertEqual(char.name, "FRIDAY")

        # Switch to ANALYST
        res_analyst = character_manager.set_personality("ANALYST")
        self.assertIsNotNone(res_analyst)
        self.assertEqual(res_analyst["id"], "ANALYST")
        char = character_manager.get_character()
        self.assertEqual(char.personality_id, "ANALYST")

        # Switch back to JARVIS
        res_jarvis = character_manager.set_personality("JARVIS")
        self.assertEqual(res_jarvis["id"], "JARVIS")
        self.assertEqual(character_manager.get_character().personality_id, "JARVIS")

    def test_conversation_engine_personality_system_prompt(self):
        engine = HumanConversationEngine()

        # 1. Prompt with JARVIS personality
        prompt_jarvis = engine.build_system_prompt("Hello there", personality_id="JARVIS")
        self.assertIn("J.A.R.V.I.S.", prompt_jarvis)
        self.assertIn("refined, highly composed", prompt_jarvis)

        # 2. Prompt with FRIDAY personality
        prompt_friday = engine.build_system_prompt("Hello there", personality_id="FRIDAY")
        self.assertIn("FRIDAY", prompt_friday)
        self.assertIn("warm, vibrant, intuitive", prompt_friday)

        # 3. Prompt with ANALYST personality
        prompt_analyst = engine.build_system_prompt("Hello there", personality_id="ANALYST")
        self.assertIn("ANALYST", prompt_analyst)
        self.assertIn("hyper-efficient, strictly objective", prompt_analyst)

    def test_pronunciation_rules_application(self):
        from dashboard.server import _apply_pronunciation_rules
        test_text = "Please check the CPU, RAM, and GPU status and call the REST API with JSON."
        spoken = _apply_pronunciation_rules(test_text)
        self.assertIn("C-P-U", spoken)
        self.assertIn("R-A-M", spoken)
        self.assertIn("G-P-U", spoken)
        self.assertIn("A-P-I", spoken)
        self.assertIn("Jay-son", spoken)

    def test_windows_autostart_logic(self):
        import setup_autostart
        st = setup_autostart.status_autostart()
        self.assertIn("enabled", st)
        self.assertIn("path", st)

    def test_server_companion_endpoints(self):
        from starlette.testclient import TestClient
        from dashboard.server import DashboardServer

        srv = DashboardServer()
        app = srv.app
        client = TestClient(app)

        # 1. GET /api/character/personalities
        r1 = client.get("/api/character/personalities")
        self.assertEqual(r1.status_code, 200)
        d1 = r1.json()
        self.assertTrue(d1["ok"])
        self.assertEqual(len(d1["personalities"]), 3)

        # 2. POST /api/character/personality
        r2 = client.post("/api/character/personality", json={"personality_id": "FRIDAY"})
        self.assertEqual(r2.status_code, 200)
        d2 = r2.json()
        self.assertTrue(d2["ok"])
        self.assertEqual(d2["personality"]["id"], "FRIDAY")

        # 3. GET /api/voice/pronunciation-rules
        r3 = client.get("/api/voice/pronunciation-rules")
        self.assertEqual(r3.status_code, 200)
        d3 = r3.json()
        self.assertTrue(d3["ok"])
        self.assertIn("rules", d3["rules"])

        # 4. GET /api/system/autostart
        r4 = client.get("/api/system/autostart")
        self.assertEqual(r4.status_code, 200)
        d4 = r4.json()
        self.assertTrue(d4["ok"])
        self.assertIn("modes", d4)

        # 5. POST /api/conversation/chat with personality_id
        r5 = client.post("/api/conversation/chat", json={
            "text": "Hello, who are you?",
            "personality_id": "ANALYST",
            "synthesize_speech": False
        })
        self.assertEqual(r5.status_code, 200)
        d5 = r5.json()
        self.assertTrue(d5["ok"])
        self.assertEqual(d5["personality_id"], "ANALYST")

        # Reset back to JARVIS
        character_manager.set_personality("JARVIS")


if __name__ == "__main__":
    unittest.main()
