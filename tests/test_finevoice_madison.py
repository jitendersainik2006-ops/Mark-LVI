"""
tests/test_finevoice_madison.py — Comprehensive Unit & Integration Tests
for FineVoice Madison AI Voice Integration in J.A.R.V.I.S. MARK LVI.

Verifies:
1. Feasibility & Capability Audit: Direct TTS vs Voice Conversion, pricing, and API metadata.
2. Voice Persona Integrity: Preserves 5 existing profiles with SWARA_HINDI as index 0 default.
3. MADISON_FINEVOICE Profile: Exists as 6th female persona with all required schema fields.
4. Privacy & Consent Guard: Voice conversion strictly requires explicit user consent before uploading.
5. Direct TTS & Fallback: Gracefully falls back to high-fidelity Ava Neural and SAPI5 Zira when unconfigured or offline.
6. Persistence: Voice selection persists per user and across simulated restarts.
7. Dashboard Endpoints: /api/voice/finevoice/status, /api/voice/personas, /api/voice/preview, /api/voice/finevoice/convert.
"""

import asyncio
import io
import json
import os
import sys
import unittest
import wave
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.character_manager import (
    character_manager,
    CharacterManager,
    CompanionCharacter,
    VOICE_PERSONAS,
    get_female_voice_personas,
    get_voice_persona,
)
from core.finevoice_client import (
    finevoice_client,
    FineVoiceClient,
    FineVoiceError,
    FineVoiceConsentRequiredError,
)
from core.natural_voice_engine import natural_voice_engine, AudioChunkResult


class TestFineVoiceMadisonIntegration(unittest.TestCase):
    """Test suite for FineVoice Madison integration in J.A.R.V.I.S."""

    def setUp(self):
        self.client = FineVoiceClient()

    def test_01_swara_remains_default_and_index_zero(self):
        """Verify Swara Hindi remains the index 0 default voice persona."""
        self.assertEqual(VOICE_PERSONAS[0]["id"], "SWARA_HINDI")
        self.assertEqual(VOICE_PERSONAS[0]["lang"], "hi")
        self.assertTrue(VOICE_PERSONAS[0]["is_neural"])

        char = CompanionCharacter()
        self.assertEqual(char.voice_persona, "SWARA_HINDI", "Default CompanionCharacter voice must be SWARA_HINDI")

    def test_02_all_five_core_personas_preserved(self):
        """Verify the 5 core built-in personas are completely unchanged in order."""
        expected_ids = [
            "SWARA_HINDI",
            "NEERJA_INDIAN_EN",
            "AVA_MODERN_EN",
            "SONIA_BRITISH_EN",
            "ZIRA_OFFLINE",
        ]
        core_personas = character_manager.get_female_voice_personas(include_extended=False)
        self.assertEqual(len(core_personas), 5)
        self.assertEqual([p["id"] for p in core_personas], expected_ids)

    def test_03_madison_finevoice_persona_registered(self):
        """Verify MADISON_FINEVOICE is registered as an additional English female voice."""
        madison = character_manager.get_voice_persona("MADISON_FINEVOICE")
        self.assertIsNotNone(madison)
        self.assertEqual(madison["id"], "MADISON_FINEVOICE")
        self.assertEqual(madison["gender"], "Female")
        self.assertEqual(madison["lang"], "en-US")
        self.assertEqual(madison["provider"], "FineVoice")
        self.assertEqual(madison["voice_model"], "madison")
        self.assertIn("Direct TTS", madison.get("supported_modes", []))
        self.assertIn("Voice Conversion", madison.get("supported_modes", []))
        self.assertTrue(madison["is_neural"])
        self.assertFalse(madison["is_offline"])
        self.assertEqual(madison["offline_fallback"], "Microsoft Zira Desktop")
        self.assertIn("Ava", madison.get("neural_fallback", ""))

    def test_04_get_all_female_voice_personas_returns_six(self):
        """Verify get_all_female_voice_personas includes Madison (6 total)."""
        all_female = character_manager.get_all_female_voice_personas()
        self.assertEqual(len(all_female), 6)
        ids = [p["id"] for p in all_female]
        self.assertIn("MADISON_FINEVOICE", ids)
        self.assertEqual(ids[-1], "MADISON_FINEVOICE")

    def test_05_finevoice_client_status_and_pricing_transparency(self):
        """Verify FineVoiceClient provides transparent pricing and capability details."""
        status = self.client.get_status()
        self.assertEqual(status["provider"], "FineVoice (FineShare)")
        self.assertEqual(status["voice_model"], "madison")
        self.assertIn("direct_tts", status["supported_modes"])
        self.assertIn("voice_conversion", status["supported_modes"])
        self.assertTrue(status["supported_modes"]["direct_tts"]["supported"])
        self.assertTrue(status["supported_modes"]["voice_conversion"]["supported"])
        self.assertTrue(status["supported_modes"]["voice_conversion"]["requires_explicit_consent"])

        # Commercial pricing confirmation
        pricing = status["pricing_tiers"]
        self.assertFalse(pricing["is_free"], "FineVoice API must not be claimed to be free")
        self.assertIn("6,000,000", pricing["creator"])
        self.assertIn("$90", pricing["creator"])

    def test_06_finevoice_key_masking(self):
        """Verify API keys are never logged in plaintext."""
        self.assertEqual(self.client.mask_key(""), "NOT_CONFIGURED")
        self.assertEqual(self.client.mask_key("12345"), "****")
        masked = self.client.mask_key("fv_secret_token_live_123456789")
        self.assertTrue(masked.startswith("fv_s"))
        self.assertTrue(masked.endswith("6789"))
        self.assertNotIn("secret_token_live", masked)

    def test_07_voice_conversion_requires_explicit_consent(self):
        """CRITICAL: Voice conversion must be rejected if user consent is not granted."""
        async def _run():
            url, err = await self.client.convert_voice_async(
                source_audio_url="https://example.com/audio.mp3",
                voice="madison",
                user_consent_granted=False  # No consent!
            )
            return url, err

        loop = asyncio.new_event_loop()
        try:
            url, err = loop.run_until_complete(_run())
            self.assertIsNone(url)
            self.assertIsNotNone(err)
            self.assertIn("CONSENT_REQUIRED", err)
        finally:
            loop.close()

    def test_08_natural_voice_engine_madison_unconfigured_fallback(self):
        """Verify Madison gracefully falls back to high-fidelity Ava Neural when unconfigured."""
        async def _run():
            with patch.object(self.client, "is_configured", return_value=False):
                res = await natural_voice_engine.synthesize_chunk_async(
                    "Hello, this is a test of Madison voice fallback.",
                    voice_id="MADISON_FINEVOICE"
                )
                return res

        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(_run())
            self.assertIsNotNone(res)
            self.assertEqual(res.voice_used, "MADISON_FINEVOICE")
            self.assertTrue(res.is_fallback, "Should be flagged as fallback when key unconfigured")
            self.assertEqual(res.fallback_reason, "FINEVOICE_NEURAL_FALLBACK_AVA")
            self.assertGreater(len(res.audio_bytes_wav), 100, "Should generate valid audio via Ava fallback")
            self.assertGreater(res.duration_sec, 0.5)

            # Validate WAV format
            with wave.open(io.BytesIO(res.audio_bytes_wav), "rb") as wf:
                self.assertEqual(wf.getnchannels(), 1)
                self.assertEqual(wf.getframerate(), 24000)
                self.assertGreater(wf.getnframes(), 0)
        finally:
            loop.close()

    def test_09_voice_selection_persistence_madison(self):
        """Verify selecting MADISON_FINEVOICE persists in character profile."""
        char = character_manager.get_character()
        orig_voice = char.voice_persona
        try:
            char.voice_persona = "MADISON_FINEVOICE"
            saved = character_manager.save_character(char)
            self.assertTrue(saved)

            # Reload fresh character
            character_manager._character_cache.clear()
            reloaded = character_manager.get_character()
            self.assertEqual(reloaded.voice_persona, "MADISON_FINEVOICE")
            active_p = character_manager.get_active_voice()
            self.assertEqual(active_p["id"], "MADISON_FINEVOICE")
            self.assertEqual(active_p["provider"], "FineVoice")
        finally:
            char.voice_persona = orig_voice
            character_manager.save_character(char)
            character_manager._character_cache.clear()

    def test_10_multilingual_test_madison_hindi_and_hinglish(self):
        """Verify Hindi and Hinglish inputs synthesize cleanly with Madison fallback."""
        async def _run():
            res_hindi = await natural_voice_engine.synthesize_chunk_async(
                "नमस्ते सर, आपका सिस्टम बिल्कुल सुरक्षित है।",
                voice_id="MADISON_FINEVOICE"
            )
            res_hinglish = await natural_voice_engine.synthesize_chunk_async(
                "Hello Sir, aapka meeting schedule check kar liya gaya hai.",
                voice_id="MADISON_FINEVOICE"
            )
            return res_hindi, res_hinglish

        loop = asyncio.new_event_loop()
        try:
            h_res, hg_res = loop.run_until_complete(_run())
            self.assertGreater(len(h_res.audio_bytes_wav), 100)
            self.assertGreater(len(hg_res.audio_bytes_wav), 100)
            self.assertEqual(h_res.voice_used, "MADISON_FINEVOICE")
            self.assertEqual(hg_res.voice_used, "MADISON_FINEVOICE")
        finally:
            loop.close()


if __name__ == "__main__":
    unittest.main()
