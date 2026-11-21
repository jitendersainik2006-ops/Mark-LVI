"""
tests/test_viral_reels_studio_upgrade.py
========================================
Comprehensive automated test suite for the J.A.R.V.I.S. AI Viral Reels Studio Upgrade:
- Style A: 3D Talking Objects (iron_dumbbell, shaker_bottle)
- Style B: 3D Cinematic Storytelling (rocky_seb, badshah_burger)
- Style C: 2D Motion Comic / Educational Explainer (prof_gyani)

Validates character registry, multi-character story generation, voice tuning,
dual-character frame compositing, quality validation, and approval gate enforcement.
"""

import os
import sys
import unittest
from pathlib import Path

# Fix stdout encoding for Windows console Devanagari output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path("D:/JARVIS-AI/mark_lvi_core")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["JARVIS_SKIP_FIREWALL_PROMPT"] = "1"


class TestStyleAndCharacterRegistry(unittest.TestCase):
    """Test 1: Verification of New Reference Styles and Characters in Registry"""

    def test_valid_styles_contain_reference_styles(self):
        from core.hindi_story_engine import VALID_STYLES

        required_styles = ["talking_objects", "cinematic_story", "motion_comic"]
        for s in required_styles:
            self.assertIn(s, VALID_STYLES, f"Style '{s}' missing from VALID_STYLES")

    def test_character_profiles_exist_with_distinct_voices(self):
        from core.character_consistency_manager import character_consistency_manager

        chars = {
            "iron_dumbbell": ("डंबल भाई", "-6Hz", "3d_object"),
            "shaker_bottle": ("शेकर शर्मा जी", "+8Hz", "3d_object"),
            "rocky_seb": ("रॉकी सेब", "+3Hz", "3d_cinematic"),
            "badshah_burger": ("बादशाह बर्गर", "-7Hz", "3d_cinematic"),
            "prof_gyani": ("प्रोफेसर ज्ञानी", "+5Hz", "motion_comic"),
        }

        for cid, (expected_name, expected_pitch, expected_style) in chars.items():
            profile = character_consistency_manager.get_character(cid)
            self.assertIsNotNone(profile, f"Character '{cid}' not found in registry")
            self.assertEqual(profile.character_id, cid)
            self.assertIn(expected_name, profile.name_hindi)
            self.assertEqual(profile.voice_pitch, expected_pitch)
            self.assertEqual(profile.avatar_style, expected_style)
            self.assertTrue(len(profile.expressions) >= 4)


class TestMultiCharacterStoryGeneration(unittest.TestCase):
    """Test 2: Story Engine Multi-Scene Narrative & Dual-Character Generation"""

    def test_style_a_talking_objects_story(self):
        from core.hindi_story_engine import hindi_story_engine

        story = hindi_story_engine.generate_story(style="talking_objects")
        self.assertEqual(story.style, "talking_objects")
        self.assertGreaterEqual(len(story.scenes), 4)
        self.assertTrue(len(story.title_hindi) > 0)
        self.assertTrue(len(story.hook_hindi) > 0)

        # Check multi-character presence in scenes
        speakers = {sc.speaker for sc in story.scenes}
        self.assertTrue(len(speakers) >= 2, f"Expected multi-character conversation, got speakers: {speakers}")

        # Check scene-level character_id assignment
        scene_chars = [getattr(sc, "character_id", None) for sc in story.scenes]
        self.assertIn("iron_dumbbell", scene_chars)
        self.assertIn("shaker_bottle", scene_chars)

    def test_style_b_cinematic_story(self):
        from core.hindi_story_engine import hindi_story_engine

        story = hindi_story_engine.generate_story(style="cinematic_story")
        self.assertEqual(story.style, "cinematic_story")
        self.assertGreaterEqual(len(story.scenes), 4)

        speakers = {sc.speaker for sc in story.scenes}
        self.assertIn("रॉकी सेब", speakers)
        self.assertIn("बादशाह बर्गर", speakers)

    def test_style_c_motion_comic_story(self):
        from core.hindi_story_engine import hindi_story_engine

        story = hindi_story_engine.generate_story(style="motion_comic")
        self.assertEqual(story.style, "motion_comic")
        self.assertGreaterEqual(len(story.scenes), 4)
        self.assertEqual(story.character_id, "prof_gyani")

        # Check that panel layout is specified
        panel_layouts = [getattr(sc, "panel_layout", None) for sc in story.scenes]
        self.assertTrue(any(pl is not None for pl in panel_layouts))


class TestMultiCharacterVoiceSwitching(unittest.TestCase):
    """Test 3: Voice Engine Scene-Level Character Parameter Switching"""

    def test_voice_parameter_switching(self):
        from core.character_consistency_manager import character_consistency_manager

        dumbbell_params = character_consistency_manager.get_voice_parameters("iron_dumbbell")
        shaker_params = character_consistency_manager.get_voice_parameters("shaker_bottle")

        # Distinct pitch values ensure auditory contrast
        self.assertNotEqual(dumbbell_params["pitch"], shaker_params["pitch"])
        self.assertEqual(dumbbell_params["pitch"], "-6Hz")
        self.assertEqual(shaker_params["pitch"], "+8Hz")


class TestVideoProviderCapabilities(unittest.TestCase):
    """Test 4: Video Provider Capabilities & Metadata Transparency"""

    def test_local_cinematic_provider_capabilities(self):
        from core.video_providers import video_provider_manager

        provider = video_provider_manager.get_provider("local_cinematic")
        caps = provider.get_capabilities()

        self.assertIn("talking_objects", caps.supported_styles)
        self.assertIn("cinematic_story", caps.supported_styles)
        self.assertIn("motion_comic", caps.supported_styles)
        self.assertEqual(caps.max_resolution, (720, 1280))
        self.assertEqual(caps.target_fps, 30)
        self.assertFalse(caps.is_procedural_fallback)

    def test_avatar_rendering_for_all_new_characters(self):
        from core.character_consistency_manager import character_consistency_manager
        from core.video_providers import LocalCinematicProvider

        provider = LocalCinematicProvider()
        test_characters = ["iron_dumbbell", "shaker_bottle", "rocky_seb", "badshah_burger", "prof_gyani"]

        for cid in test_characters:
            char = character_consistency_manager.get_character(cid)
            for viseme in ["closed", "open"]:
                avatar = provider._draw_character_avatar(char, "smug", viseme, "talking_objects", box_size=240)
                self.assertIsNotNone(avatar)
                self.assertEqual(avatar.size, (240, 240))
                # Ensure non-empty alpha channel
                bbox = avatar.getbbox()
                self.assertIsNotNone(bbox, f"Avatar for '{cid}' rendered completely transparent")


class TestApprovalGateAndLedger(unittest.TestCase):
    """Test 5: Mandatory Approval Gate & Ledger Registration"""

    def test_approval_gate_status_is_waiting_for_approval(self):
        import tempfile
        from core.reel_approval_manager import ReelApprovalManager

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_ledger = Path(tf.name)
        try:
            temp_ledger.write_text("{}", encoding="utf-8")
            mgr = ReelApprovalManager(ledger_file=temp_ledger)
            test_reel_id = f"test_verify_{int(os.getpid())}"
            entry = mgr.register_new_reel(
                reel_id=test_reel_id,
                title="टेस्ट रील्स सत्यापन",
                style="talking_objects",
                video_path="dummy.mp4",
                cover_path="dummy.jpg",
                srt_path="dummy.srt",
                caption="कैप्शन",
                hashtags=["#Test"],
                duration_sec=20.0,
                provider_id="local_cinematic",
                is_generative_ai=True,
                is_procedural_fallback=False,
            )

            self.assertEqual(entry["status"], "WAITING_FOR_APPROVAL")
            self.assertEqual(entry["id"], test_reel_id)
        finally:
            if temp_ledger.exists():
                try:
                    temp_ledger.unlink()
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
