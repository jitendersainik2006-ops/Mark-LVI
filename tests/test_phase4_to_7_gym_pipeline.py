"""
tests/test_phase4_to_7_gym_pipeline.py — Verification Suite for Phases 4–7

Tests required by Section 13:
1. Fresh gym ideas are generated.
2. Used ideas are not repeatedly suggested.
3. Veo directory import works.
4. Identical videos with different filenames are detected.
5. Published Reels never reappear in the pending queue.
6. Unapproved Reels cannot publish.
7. Editing invalidates approval.
8. Morning and evening scheduling work in Asia/Kolkata.
9. Restart does not duplicate scheduled jobs.
10. Missed approval prevents publication.
11. Uncertain uploads do not trigger blind retries.
12. Explicit republishing creates a separate history record.
13. Caption paragraphs and hashtags are generated correctly.
14. Existing 66 Reel records remain preserved.
15. Existing OAuth security and proxy tests remain passing.
"""

import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.instagram_manager import InstagramManager, ReelPost, instagram_manager
from core.gym_reels_studio import GymReelsStudio, gym_reels_studio
from core.character_consistency_manager import character_consistency_manager
from core.crypto_storage import encrypt_token, decrypt_token, mask_token


class TestPhase4To7GymPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = Path(tempfile.mkdtemp(prefix="jarvis_test_gym_"))
        cls.test_ledger_file = cls.temp_dir / "reels_ledger.json"
        cls.test_slots_file = cls.temp_dir / "scheduled_slots.json"
        cls.test_ideas_file = cls.temp_dir / "used_gym_ideas.json"
        cls.test_veo_dir = cls.temp_dir / "veo_output"
        cls.test_veo_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setUp(self):
        self.mgr = InstagramManager()
        # Ensure tests don't overwrite live ledger on disk
        self.mgr._save_ledger = lambda: None
        self.mgr._save_accounts = lambda: None
        self.mgr._save_scheduled_slots = lambda data: None

        self.studio = GymReelsStudio()
        self.studio._used_ideas_file = self.test_ideas_file
        self.studio._registry = {}

    # 1. Fresh gym ideas are generated
    def test_01_fresh_gym_ideas_generation(self):
        ideas = self.studio.generate_daily_ideas(count=3, force_fresh=False)
        self.assertGreaterEqual(len(ideas), 1)
        idea = ideas[0]
        self.assertTrue(idea.title)
        self.assertTrue(idea.hook)
        self.assertGreaterEqual(len(idea.scenes), 3)
        self.assertGreaterEqual(len(idea.hashtags), 5)
        self.assertTrue(idea.scenes[0].veo_prompt, "Scene must have a Veo prompt")
        self.assertFalse(idea.is_trending, "Never claim trending without verified information")

    # 2. Used ideas are not repeatedly suggested
    def test_02_used_ideas_not_repeated(self):
        batch1 = self.studio.generate_daily_ideas(count=2, force_fresh=False)
        ids_batch1 = {i.concept_hash for i in batch1}
        self.assertTrue(len(ids_batch1) > 0)

        batch2 = self.studio.generate_daily_ideas(count=2, force_fresh=True)
        for i2 in batch2:
            self.assertNotIn(i2.concept_hash, ids_batch1, "Used idea hash should not be repeatedly suggested")

    # 3. Veo directory import works
    def test_03_veo_directory_import(self):
        fake_video = self.test_veo_dir / "gym_workout_test1.mp4"
        fake_video.write_bytes(b"MOCK_VIDEO_DATA_" * 200)

        with patch.object(self.mgr, 'validate_reel_video', return_value={"is_valid": True, "duration_seconds": 35.0}):
            with patch.object(self.mgr, '_generate_cover_for_video', return_value=None):
                results = self.mgr.poll_veo_directory(veo_dir=str(self.test_veo_dir))
                self.assertGreaterEqual(len(results), 1)
                first = results[0]
                self.assertEqual(first["status"], "IMPORTED_WAITING_FOR_APPROVAL")
                reel_id = first["reel_id"]
                imported_reel = self.mgr._ledger.get(reel_id)
                self.assertIsNotNone(imported_reel)
                self.assertEqual(imported_reel.status, "waiting_for_approval")
                self.assertTrue(imported_reel.needs_approval)

    # 4. Identical videos with different filenames are detected
    def test_04_identical_videos_different_filenames_detected(self):
        sample_bytes = b"IDENTICAL_VIDEO_CONTENT_" * 100
        f1 = self.test_veo_dir / "original_gym.mp4"
        f2 = self.test_veo_dir / "renamed_copy_gym.mp4"
        f1.write_bytes(sample_bytes)
        f2.write_bytes(sample_bytes)

        hash1 = self.mgr.compute_file_sha256(f1)
        hash2 = self.mgr.compute_file_sha256(f2)
        self.assertEqual(hash1, hash2, "SHA-256 fingerprint must match for identical content")

        r1 = ReelPost(
            id="reel_orig_hash_test",
            title="Original Gym Video",
            video_path=str(f1),
            video_fingerprint=hash1,
            status="waiting_for_approval",
        )
        self.mgr._ledger[r1.id] = r1

        check = self.mgr.check_duplicate(str(f2))
        self.assertTrue(check["is_duplicate"])
        self.assertEqual(check["reel_id"], "reel_orig_hash_test")

    # 5. Published Reels never reappear in the pending queue
    def test_05_published_reels_never_reappear_in_pending_queue(self):
        f = self.test_veo_dir / "published_sample.mp4"
        f.write_bytes(b"PUBLISHED_STREAM_BYTES_" * 150)
        fp = self.mgr.compute_file_sha256(f)

        pub_reel = ReelPost(
            id="reel_pub_test_123",
            title="Published Bench Press",
            video_path=str(f),
            video_fingerprint=fp,
            status="published",
            published_at=datetime.now().isoformat(),
            meta_media_id="17999888777",
        )
        self.mgr._ledger[pub_reel.id] = pub_reel

        new_reel = ReelPost(
            id="reel_sneaky_duplicate",
            title="Sneaky Duplicate of Published",
            video_path=str(f),
            video_fingerprint=fp,
            status="approved",
        )
        self.mgr._ledger[new_reel.id] = new_reel

        res = self.mgr.publish_reel(new_reel.id, force_assisted=True)
        self.assertFalse(res["ok"])
        self.assertTrue(res.get("duplicate_published"))
        self.assertIn("DUPLICATE_PUBLISHED", res.get("error", ""))

    # 6. Unapproved Reels cannot publish
    def test_06_unapproved_reels_cannot_publish(self):
        reel = ReelPost(
            id="reel_unapproved_test",
            title="Unapproved Video",
            status="waiting_for_approval",
            needs_approval=True,
        )
        self.mgr._ledger[reel.id] = reel
        res = self.mgr.publish_reel(reel.id, force_assisted=True)
        self.assertFalse(res["ok"])
        self.assertIn("Explicit human approval is required", res.get("error", ""))

    # 7. Editing invalidates approval
    def test_07_editing_invalidates_approval(self):
        reel = ReelPost(
            id="reel_edit_gate_test",
            title="Approved Title",
            caption="Approved Caption",
            status="approved",
            approved_at="2026-11-15T10:00:00",
            needs_approval=False,
        )
        self.mgr._ledger[reel.id] = reel

        updated = self.mgr.edit_reel(reel.id, caption="Modified Caption After Approval")
        self.assertIsNotNone(updated)
        reloaded = self.mgr._ledger[reel.id]
        self.assertEqual(reloaded.status, "waiting_for_approval")
        self.assertTrue(reloaded.needs_approval)
        self.assertIsNone(reloaded.approved_at, "approved_at must be cleared on edit")

    # 8. Morning and evening scheduling work in Asia/Kolkata
    def test_08_morning_and_evening_scheduling_asia_kolkata(self):
        slots = self.mgr.get_daily_slots(date_str="2026-11-20")
        self.assertIn("morning", slots["slots"])
        self.assertIn("evening", slots["slots"])
        self.assertEqual(slots["slots"]["morning"]["time_ist"], "08:00")
        self.assertEqual(slots["slots"]["evening"]["time_ist"], "19:00")

        r1 = ReelPost(id="reel_slot_m", title="Morning Workout", status="approved")
        r2 = ReelPost(id="reel_slot_e", title="Evening Workout", status="approved")
        self.mgr._ledger[r1.id] = r1
        self.mgr._ledger[r2.id] = r2

        assign_m = self.mgr.assign_reel_to_slot(r1.id, "2026-11-20", "08:00")
        self.assertTrue(assign_m["ok"])

        assign_conflict = self.mgr.assign_reel_to_slot(r1.id, "2026-11-20", "19:00")
        self.assertFalse(assign_conflict["ok"])
        self.assertIn("Slot conflict", assign_conflict.get("error", ""))

        assign_e = self.mgr.assign_reel_to_slot(r2.id, "2026-11-20", "19:00")
        self.assertTrue(assign_e["ok"])

    # 9. Restart does not duplicate scheduled jobs
    def test_09_restart_does_not_duplicate_scheduled_jobs(self):
        slots_data = {
            "2026-11-25": {
                "morning": {"reel_id": "r_morning_persist", "status": "ASSIGNED", "time_ist": "08:00"},
                "evening": {"reel_id": "r_evening_persist", "status": "ASSIGNED", "time_ist": "19:00"},
            }
        }
        self.test_slots_file.write_text(json.dumps(slots_data), encoding="utf-8")

        new_mgr = InstagramManager()
        with patch.object(new_mgr, '_load_scheduled_slots', return_value=slots_data):
            day_slots = new_mgr.get_daily_slots("2026-11-25")
            self.assertEqual(day_slots["slots"]["morning"]["reel_id"], "r_morning_persist")
            self.assertEqual(day_slots["slots"]["evening"]["reel_id"], "r_evening_persist")

    # 10. Missed approval prevents publication
    def test_10_missed_approval_prevents_publication(self):
        past_slots = {
            "2026-01-01": {
                "morning": {"reel_id": "reel_missed_gate", "status": "ASSIGNED", "time_ist": "08:00"}
            }
        }
        r_unapproved = ReelPost(
            id="reel_missed_gate",
            title="Unapproved Missed Reel",
            status="waiting_for_approval",
            needs_approval=True,
        )
        self.mgr._ledger[r_unapproved.id] = r_unapproved

        with patch.object(self.mgr, '_load_scheduled_slots', return_value=past_slots):
            audit_events = self.mgr.check_scheduled_slots_and_missed_approvals()
            self.assertGreaterEqual(len(audit_events), 1)
            event = audit_events[0]
            self.assertEqual(event["result"], "MISSED_APPROVAL")
            self.assertEqual(r_unapproved.status, "missed_approval")

    # 11. Uncertain uploads do not trigger blind retries
    def test_11_uncertain_uploads_do_not_trigger_blind_retries(self):
        reel = ReelPost(id="reel_uncertain_net", title="Uncertain Upload", status="approved")
        self.mgr._ledger[reel.id] = reel

        res = self.mgr.reconcile_upload_status(reel.id)
        self.assertTrue(res["ok"])
        self.assertEqual(res["status"], "UPLOAD_STATUS_UNKNOWN")
        self.assertEqual(reel.status, "upload_status_unknown")

        pub_res = self.mgr.publish_reel(reel.id, force_assisted=True)
        self.assertFalse(pub_res["ok"])
        self.assertIn("Explicit human approval is required", pub_res["error"])

    # 12. Explicit republishing creates a separate history record
    def test_12_explicit_republishing_creates_separate_history_record(self):
        mock_vid = self.test_veo_dir / "gym_workout_test1.mp4"
        mock_vid.write_bytes(b"TEST_VIDEO_BYTES_" * 100)
        orig_id = "reel_published_historical"
        orig_reel = ReelPost(
            id=orig_id,
            title="Squat Day Original",
            video_path=str(mock_vid),
            status="published",
            published_at="2026-11-01T08:00:00",
            meta_media_id="17890123456",
            version=1,
        )
        self.mgr._ledger[orig_id] = orig_reel

        repub_res = self.mgr.republish_reel(orig_id, reason="Seasonal Gym Motivation", operator_notes="Fresh hook added")
        self.assertTrue(repub_res["ok"])
        new_reel_dict = repub_res["reel"]
        new_id = new_reel_dict["id"]
        self.assertNotEqual(new_id, orig_id)
        self.assertEqual(new_reel_dict["version"], 2)
        self.assertEqual(new_reel_dict["status"], "WAITING_FOR_APPROVAL")
        self.assertTrue(new_reel_dict["needs_approval"])

        orig_preserved = self.mgr._ledger[orig_id]
        self.assertEqual(orig_preserved.status, "published")
        self.assertEqual(orig_preserved.meta_media_id, "17890123456")

    # 13. Caption paragraphs and hashtags are generated correctly
    def test_13_caption_paragraphs_and_hashtags_generation(self):
        res = self.mgr.generate_gym_caption_and_hashtags(title="बेंच प्रेस सही तरीका")
        self.assertIn("\n\n", res["caption_paragraph"], "Caption must be a structured multi-line paragraph, not single line")
        self.assertGreaterEqual(len(res["hashtags"]), 10)
        self.assertTrue(res["hook"])
        self.assertTrue(res["cover_text"])

    # 14. Existing 66+ Reel records remain preserved
    def test_14_existing_reels_preserved(self):
        with open(BASE_DIR / "data" / "reels_ledger.json", "r", encoding="utf-8") as f:
            disk_ledger = json.load(f)
        self.assertGreaterEqual(len(disk_ledger), 66, f"Ledger must preserve all existing records (found {len(disk_ledger)})")

    # 15. Existing OAuth security and proxy tests remain passing
    def test_15_oauth_security_regression(self):
        secret = "meta_app_secret_regression_check_777"
        enc = encrypt_token(secret)
        self.assertNotEqual(enc, secret)
        dec = decrypt_token(enc)
        self.assertEqual(dec, secret)
        masked = mask_token(secret)
        self.assertTrue(masked.startswith("meta"))
        self.assertTrue(masked.endswith("k_777") or masked.endswith("_777") or masked.endswith("777"))


if __name__ == "__main__":
    unittest.main()
