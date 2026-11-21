"""
tests/test_character_and_emotions.py — Comprehensive Unit Tests for Character Customization & 19 Emotions

Tests:
1. CompanionCharacter dataclass initialization and serialization.
2. 19-state EMOTION_REGISTRY completeness and parameter integrity.
3. CharacterManager load, save, and per-user directory isolation.
4. Setting active emotion and intensity bounds.
5. Wholesome decorative themes and female presentation options.
6. FloatingCompanionWidget state and emotion color compatibility.
7. PersonalityManager 7 presets and prompt injection addon.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.character_manager import (
    EMOTION_REGISTRY,
    CharacterManager,
    CompanionCharacter,
    EmotionState,
)
from core.floating_companion import FloatingCompanionWidget
from core.personality_manager import PRESETS, PersonalityManager, PersonalityPreset


class TestCharacterAndEmotions(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mgr = CharacterManager()
        # Redirect manager storage to temp dir
        self.mgr.get_character_file = lambda user_id=None: (
            Path(self.temp_dir) / (f"user_{user_id}.json" if user_id else "default.json")
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_emotion_registry_19_states(self):
        """Verifies that all 19 required emotional states are registered with full visual parameters."""
        expected_emotions = {
            "HAPPY", "CHEERFUL", "CALM", "CURIOUS", "EXCITED",
            "THOUGHTFUL", "CONFIDENT", "CONCERNED", "EMPATHETIC",
            "PLAYFUL", "FOCUSED", "LISTENING", "THINKING", "SPEAKING",
            "WORKING", "PAUSED", "ERROR", "SUCCESS", "IDLE"
        }
        self.assertEqual(set(EMOTION_REGISTRY.keys()), expected_emotions)
        self.assertEqual(len(EMOTION_REGISTRY), 19)

        for name, emo in EMOTION_REGISTRY.items():
            self.assertIsInstance(emo, EmotionState)
            self.assertTrue(emo.color_hex.startswith("#"))
            self.assertGreater(len(emo.eye_shape), 0)
            self.assertGreater(len(emo.mouth_shape), 0)
            self.assertGreater(emo.pulse_speed, 0.0)
            self.assertGreaterEqual(emo.aura_intensity, 0.0)

    def test_character_defaults_and_serialization(self):
        """Verifies character defaults and JSON dictionary roundtrip."""
        char = CompanionCharacter()
        self.assertEqual(char.name, "J.A.R.V.I.S.")
        self.assertEqual(char.presentation, "NEUTRAL")
        self.assertTrue(char.animation_enabled)

        data = char.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["name"], "J.A.R.V.I.S.")

        restored = CompanionCharacter.from_dict(data)
        self.assertEqual(restored.name, char.name)
        self.assertEqual(restored.presentation, char.presentation)

    def test_character_customization_and_saving(self):
        """Verifies saving and loading customized female character with wholesome themes."""
        char = CompanionCharacter(
            name="Swara",
            presentation="FEMALE",
            hairstyle="long_wave",
            outfit="floral_cardigan",
            voice_persona="SWARA_HINDI",
            wholesome_decorations=["flowers", "hearts", "soft_bokeh"],
            intensity=0.9,
        )
        ok = self.mgr.save_character(char, user_id="user_123")
        self.assertTrue(ok)

        loaded = self.mgr.get_character(user_id="user_123")
        self.assertEqual(loaded.name, "Swara")
        self.assertEqual(loaded.presentation, "FEMALE")
        self.assertIn("flowers", loaded.wholesome_decorations)
        self.assertIn("hearts", loaded.wholesome_decorations)
        self.assertEqual(loaded.intensity, 0.9)

    def test_set_emotion_and_intensity(self):
        """Verifies setting active emotions and intensity clamping."""
        emo = self.mgr.set_emotion("cheerful", intensity=0.85)
        self.assertEqual(emo.name, "CHEERFUL")
        self.assertEqual(self.mgr.get_current_emotion().name, "CHEERFUL")
        self.assertAlmostEqual(self.mgr.get_current_intensity(), 0.85)

        # Clamping
        self.mgr.set_emotion("happy", intensity=1.5)
        self.assertEqual(self.mgr.get_current_intensity(), 1.0)
        self.mgr.set_emotion("calm", intensity=-0.5)
        self.assertEqual(self.mgr.get_current_intensity(), 0.0)

        # Unknown fallback
        fallback = self.mgr.set_emotion("NON_EXISTENT")
        self.assertEqual(fallback.name, "IDLE")

    def test_floating_companion_state_colors_compatibility(self):
        """Verifies that FloatingCompanionWidget supports all 19 emotion colors."""
        for emo_name in EMOTION_REGISTRY.keys():
            self.assertIn(emo_name, FloatingCompanionWidget.STATE_COLORS)

    def test_personality_presets_and_prompt_addon(self):
        """Verifies 7 personality presets and system prompt addon generation."""
        pm = PersonalityManager()
        pm.get_config_file = lambda user_id=None: Path(self.temp_dir) / "test_personality.json"
        expected_presets = {
            "professional", "friendly", "cheerful", "calm_mentor",
            "playful", "minimalist", "custom"
        }
        self.assertEqual(set(PRESETS.keys()), expected_presets)

        # Test addon builder with clean default
        pm.save_user_personality("professional")
        addon_prof = pm.build_system_prompt_addon()
        self.assertIn("[PERSONALITY: PROFESSIONAL]", addon_prof)

        # Test preset selection
        pm.save_user_personality("cheerful", custom_guidelines="Speak with high optimism!")
        addon_cheerful = pm.build_system_prompt_addon()
        self.assertIn("[PERSONALITY: CHEERFUL]", addon_cheerful)
        self.assertIn("Speak with high optimism!", addon_cheerful)


if __name__ == "__main__":
    unittest.main()
