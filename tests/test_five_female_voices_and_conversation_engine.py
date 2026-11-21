"""
Unit and integration tests for J.A.R.V.I.S. Mark LVI:
- Five Selectable Female Voices (Swara Hindi default, Neerja Indian English, Ava US, Sonia British, Zira Offline)
- Human Conversation Engine (Language detection, style detection, adaptive prompts, offline fallback)
- Voice customization persistence (speed, pitch, volume)
- Offline fallback with Devanagari transliteration for Windows SAPI5
"""

import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.character_manager import (
    character_manager,
    CompanionCharacter,
    VOICE_PERSONAS,
    get_female_voice_personas,
    get_voice_persona,
)
from core.human_conversation_engine import (
    human_conversation_engine,
    HumanConversationEngine,
    ConversationContext,
)
from dashboard.server import _transliterate_devanagari_for_sapi5


class TestFiveFemaleVoices(unittest.TestCase):
    """Verifies all requirements for Phase 2: Five Selectable Female Voices."""

    def test_all_five_female_voice_personas_exist(self):
        """Verify exactly five distinct female voice personas are registered."""
        female_personas = get_female_voice_personas()
        self.assertEqual(len(female_personas), 5, "Expected exactly 5 female voice personas")

        expected_ids = [
            "SWARA_HINDI",
            "NEERJA_INDIAN_EN",
            "AVA_MODERN_EN",
            "SONIA_BRITISH_EN",
            "ZIRA_OFFLINE",
        ]
        actual_ids = [p["id"] for p in female_personas]
        self.assertEqual(actual_ids, expected_ids)

    def test_required_fields_in_each_female_persona(self):
        """Verify required metadata keys exist on all 5 female personas."""
        required_keys = {
            "id", "name", "label", "gender", "lang",
            "supported_languages", "system_voice", "is_neural",
            "is_offline", "description", "sample_text", "offline_fallback"
        }
        for p in get_female_voice_personas():
            for key in required_keys:
                self.assertIn(key, p, f"Key '{key}' missing in persona {p.get('id')}")
            self.assertEqual(p["gender"], "Female")
            self.assertTrue(len(p["sample_text"]) > 10, f"Sample text too short in {p['id']}")

    def test_swara_hindi_is_default_persona(self):
        """Verify Swara Hindi is persona index 0 and default for CompanionCharacter."""
        # 1. Index 0 in VOICE_PERSONAS
        self.assertEqual(VOICE_PERSONAS[0]["id"], "SWARA_HINDI")
        self.assertEqual(VOICE_PERSONAS[0]["lang"], "hi")
        self.assertTrue(VOICE_PERSONAS[0]["is_neural"])

        # 2. Default on a new CompanionCharacter
        char = CompanionCharacter()
        self.assertEqual(char.voice_persona, "SWARA_HINDI")

    def test_zira_is_designated_offline_sapi5_voice(self):
        """Verify Zira is properly identified as 100% offline Windows SAPI5."""
        zira = get_voice_persona("ZIRA_OFFLINE")
        self.assertIsNotNone(zira)
        self.assertTrue(zira["is_offline"])
        self.assertFalse(zira["is_neural"])
        self.assertIn("Zira", zira["system_voice"])

    def test_get_voice_persona_helper(self):
        """Verify get_voice_persona looks up correctly or returns default."""
        neerja = get_voice_persona("NEERJA_INDIAN_EN")
        self.assertIsNotNone(neerja)
        self.assertEqual(neerja["id"], "NEERJA_INDIAN_EN")

        # Unknown ID falls back to SWARA_HINDI
        unknown = get_voice_persona("NON_EXISTENT_VOICE")
        self.assertEqual(unknown["id"], "SWARA_HINDI")

    def test_companion_speed_pitch_dataclass_fields(self):
        """Verify speed and pitch controls exist in CompanionCharacter and serialize."""
        c = CompanionCharacter(
            voice_persona="NEERJA_INDIAN_EN",
            voice_speed=1.2,
            voice_pitch="+2Hz",
            voice_volume=0.9,
        )
        data = c.to_dict()
        self.assertEqual(data["voice_speed"], 1.2)
        self.assertEqual(data["voice_pitch"], "+2Hz")
        self.assertEqual(data["voice_volume"], 0.9)

        # Deserialize back
        c2 = CompanionCharacter.from_dict(data)
        self.assertEqual(c2.voice_persona, "NEERJA_INDIAN_EN")
        self.assertEqual(c2.voice_speed, 1.2)
        self.assertEqual(c2.voice_pitch, "+2Hz")
        self.assertEqual(c2.voice_volume, 0.9)


class TestHumanConversationEngine(unittest.TestCase):
    """Verifies all requirements for Phase 3: Human Conversation Engine."""

    def setUp(self):
        self.engine = HumanConversationEngine()

    def test_language_detection_hindi(self):
        """Verify Devanagari text is accurately classified as Hindi."""
        sample_hindi = "नमस्ते जार्विस, आज का दिन कैसा रहेगा?"
        detected = self.engine.detect_language(sample_hindi)
        self.assertEqual(detected, "hindi")

    def test_language_detection_hinglish(self):
        """Verify Romanized Hindi tokens are classified as Hinglish."""
        sample_hinglish = "bhai suno aaj ka workout schedule kya hai aur gym kab jana hai"
        detected = self.engine.detect_language(sample_hinglish)
        self.assertEqual(detected, "hinglish")

    def test_language_detection_english(self):
        """Verify pure English input is classified as English."""
        sample_en = "Please summarize my latest unread Gmail messages and check system load."
        detected = self.engine.detect_language(sample_en)
        self.assertEqual(detected, "english")

    def test_conversational_style_detection(self):
        """Verify user conversational styles are recognized properly."""
        # Casual
        casual_txt = "hey dude what's up haha tell me something funny"
        self.assertEqual(self.engine.detect_conversational_style(casual_txt), "casual")

        # Technical
        tech_txt = "how do we fix the code error in the python api with high ram usage?"
        self.assertEqual(self.engine.detect_conversational_style(tech_txt), "technical")

        # Concise
        concise_txt = "what is the time"
        self.assertEqual(self.engine.detect_conversational_style(concise_txt), "concise")

        # Formal
        formal_txt = "could you kindly provide the formal verification report regarding deliverables?"
        self.assertEqual(self.engine.detect_conversational_style(formal_txt), "formal")

    def test_system_prompt_builder_includes_persona_and_instructions(self):
        """Verify adaptive system prompt dynamically injects rules for detected language."""
        # Hindi prompt
        hindi_prompt = self.engine.build_system_prompt("नमस्ते जार्विस")
        self.assertIn("Hindi", hindi_prompt)
        self.assertIn("Devanagari", hindi_prompt)

        # Hinglish prompt
        hinglish_prompt = self.engine.build_system_prompt("bhai suno aaj ka kya schedule hai")
        self.assertIn("Hinglish", hinglish_prompt)

        # English prompt
        en_prompt = self.engine.build_system_prompt("Please check the system diagnostics")
        self.assertIn("English", en_prompt)

    def test_offline_fallback_replies_honestly_in_detected_language(self):
        """Verify offline fallback produces warm, authentic replies without crashing."""
        hindi_reply = self.engine._get_offline_fallback_reply("नमस्ते आप कैसे हैं?", "hindi", "casual")
        self.assertTrue(len(hindi_reply) > 5)
        self.assertIn("नमस्ते", hindi_reply)

        hinglish_reply = self.engine._get_offline_fallback_reply("kya haal hai suno", "hinglish", "casual")
        self.assertTrue("haanji" in hinglish_reply.lower() or "samajh" in hinglish_reply.lower() or "j.a.r.v.i.s." in hinglish_reply.lower())

        en_reply = self.engine._get_offline_fallback_reply("hello assistant", "english", "casual")
        self.assertTrue(len(en_reply) > 5)

    def test_conversation_context_and_history(self):
        """Verify conversation contexts store turns and advance turn counts."""
        ctx = self.engine.get_context("user_test_42")
        self.assertEqual(ctx.turn_count, 0)
        self.assertEqual(len(ctx.history), 0)

        ctx.history.append({"role": "user", "content": "Hi Jarvis"})
        ctx.history.append({"role": "assistant", "content": "Good day! How can I assist?"})
        ctx.turn_count += 1

        self.assertEqual(len(ctx.history), 2)
        self.assertEqual(ctx.turn_count, 1)


class TestOfflineDevanagariTransliteration(unittest.TestCase):
    """Verifies SAPI5 offline fallback phonetic handling."""

    def test_transliterate_devanagari_words(self):
        """Verify Devanagari characters are safely mapped to Romanized syllables for SAPI5."""
        hindi_greeting = "नमस्ते"
        translit = _transliterate_devanagari_for_sapi5(hindi_greeting)
        # Should not contain raw Devanagari characters
        self.assertFalse(any('\u0900' <= char <= '\u097F' for char in translit))
        self.assertTrue(len(translit) > 0)

    def test_pure_ascii_remains_unchanged(self):
        """Verify ASCII English text is unchanged by the transliteration filter."""
        ascii_text = "Good morning, J.A.R.V.I.S. system is online."
        translit = _transliterate_devanagari_for_sapi5(ascii_text)
        self.assertEqual(translit, ascii_text)


if __name__ == "__main__":
    unittest.main()
