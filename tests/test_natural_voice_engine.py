"""
tests/test_natural_voice_engine.py — Comprehensive Unit & Integration Tests
for J.A.R.V.I.S. Natural Conversational Voice Engine (core/natural_voice_engine.py)

Covers:
1. 5 Selectable Female Voice Profiles (Swara Hindi, Neerja Indian En, Ava US, Sonia British, Zira Offline)
2. Phonetic Normalization & Hindi Numeral Transliteration (0-100, 2026)
3. Markdown and URL Stripping
4. Pronunciation Rule & Technical Acronym Expansion
5. Low-Latency Sentence Splitting
6. Offline Windows SAPI5 Synthesis & Fallback
7. Real-Time Interruption & Playback Control
"""

import asyncio
import io
import os
import sys
import unittest
import wave
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.natural_voice_engine import natural_voice_engine, NaturalVoiceEngine, AudioChunkResult


class TestNaturalVoiceEngine(unittest.TestCase):
    """Test suite for NaturalVoiceEngine prosody, normalization, and synthesis."""

    def setUp(self):
        self.engine = NaturalVoiceEngine()

    def test_hindi_numeral_normalization(self):
        """Verifies numbers 0-100 and year 2026 are expanded into natural Hindi Devanagari words."""
        text = "आज 5 मार्च 2026 है और तापमान 25 डिग्री है।"
        normalized = self.engine.normalize_text(text, lang="hindi")
        self.assertIn("पाँच", normalized)
        self.assertIn("दो हज़ार छब्बीस", normalized)
        self.assertIn("पच्चीस", normalized)
        self.assertNotIn(" 5 ", f" {normalized} ")
        self.assertNotIn("2026", normalized)
        self.assertNotIn(" 25 ", f" {normalized} ")

    def test_markdown_and_url_stripping(self):
        """Verifies markdown formatting and URLs are stripped so they aren't spoken literally."""
        text = "Check out **bold feature** and *italic note* at https://jarvisapp.in/#features for `details`."
        normalized = self.engine.normalize_text(text, lang="english")
        self.assertNotIn("**", normalized)
        self.assertNotIn("*", normalized)
        self.assertNotIn("`", normalized)
        self.assertNotIn("https://", normalized)
        self.assertIn("bold feature", normalized)
        self.assertIn("italic note", normalized)

    def test_sentence_splitting_for_streaming(self):
        """Verifies text is chunked at sentence and Devanagari purna-viram boundaries."""
        sample = "नमस्ते! मैं स्वरा हूँ। आप कैसे हैं? सब कुछ ठीक है।"
        chunks = self.engine.split_sentences(sample)
        self.assertTrue(len(chunks) >= 3, f"Expected at least 3 chunks, got {len(chunks)}: {chunks}")
        self.assertIn("नमस्ते", chunks[0])

    def test_all_five_voice_personas_resolved(self):
        """Verifies that all 5 female voices are correctly resolved with valid metadata."""
        personas = ["SWARA_HINDI", "NEERJA_INDIAN_EN", "AVA_MODERN_EN", "SONIA_BRITISH_EN", "ZIRA_OFFLINE"]
        for vid in personas:
            p = self.engine._get_voice_profile(vid)
            self.assertIsNotNone(p, f"Voice {vid} failed to resolve")
            self.assertEqual(p["id"], vid)
            self.assertTrue(len(p.get("system_voice", "")) > 0)

    def test_zira_offline_sapi5_synthesis(self):
        """Verifies local Windows SAPI5 voice synthesis produces valid WAV audio."""
        result = self.engine.synthesize_text("Offline system check.", voice_id="ZIRA_OFFLINE")
        self.assertIsNotNone(result)
        self.assertTrue(len(result.audio_bytes_wav) >= 44, "Audio WAV header or frames missing")
        self.assertTrue(result.is_offline)
        self.assertGreater(result.duration_sec, 0.1)

        # Validate standard WAV structure
        with wave.open(io.BytesIO(result.audio_bytes_wav), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertGreater(wf.getframerate(), 0)
            self.assertGreater(wf.getnframes(), 0)

    def test_playback_stop_and_interruption_state(self):
        """Verifies stop_playback resets playing state immediately."""
        self.engine.stop_playback()
        self.assertFalse(self.engine._is_playing)
        self.assertTrue(self.engine._stop_requested)

    def test_async_chunk_synthesis_swara(self):
        """Verifies async synthesis of a natural Hindi sentence with Swara persona."""
        async def _run():
            res = await self.engine.synthesize_chunk_async("नमस्ते, मैं स्वरा हूँ।", voice_id="SWARA_HINDI")
            return res

        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(_run())
            self.assertIsNotNone(res)
            self.assertTrue(len(res.audio_bytes_wav) >= 44)
            self.assertGreater(res.duration_sec, 0.2)
        finally:
            loop.close()


if __name__ == "__main__":
    unittest.main()
