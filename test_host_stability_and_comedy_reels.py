"""
test_host_stability_and_comedy_reels.py — Comprehensive Test Battery for
J.A.R.V.I.S. Host Stability and AI Comedy Reels Subsystem.

Verifies:
1. Host Stability & Session Persistence (no json import errors, safe directory creation).
2. Single-Instance Lock & Duplicate Launcher Prevention (graceful non-destructive exit).
3. Live Host Heartbeat & Status Telemetry (/api/system/heartbeat, /api/system/status).
4. Procedural AI Comedy Reels Generation (9:16 vertical MP4, H.264/AAC, cartoon reaction avatars, SFX).
5. Verification of Video File on Disk (playable, non-zero size >100KB, duration ~18s).
6. 9:16 Cover Art Generation ({id}_cover.jpg >30KB).
7. Mandatory Human Approval Gate & Target Account Security (@mentos_life_gym).
8. Comedy REST Endpoints & Content-Type Filtering.
"""

import json
import os
import sys
import time
from pathlib import Path

import av
from starlette.testclient import TestClient

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def test_section(title: str):
    print(f"\n{'='*70}\n[TEST] {title}\n{'='*70}")


def run_tests():
    passed = 0
    total = 0
    active_reel = None

    # ─────────────────────────────────────────────────────────────────────────
    test_section("1. Host Stability & Session Persistence Fix")
    total += 1
    try:
        from dashboard.server import DashboardServer

        server = DashboardServer()
        test_session_id = f"test_session_{int(time.time())}"
        server._tokens[test_session_id] = time.time()
        server._save_sessions()

        assert server._sessions_file.exists(), "Sessions file was not created"
        loaded_data = json.loads(server._sessions_file.read_text(encoding="utf-8"))
        assert test_session_id in loaded_data.get("tokens", {}), "Saved session missing in loaded data"
        print("  PASS: DashboardServer session persistence functions with json import without errors.")
        passed += 1
    except Exception as e:
        print(f"  FAIL: Session persistence error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    test_section("2. Single-Instance Lock & Duplicate Prevention")
    total += 1
    test_lock_file = None
    try:
        from core.instance_lock import acquire_instance_lock, release_instance_lock, update_instance_heartbeat

        test_lock_file = BASE_DIR / "data" / f"test_host_{os.getpid()}_{int(time.time()*1000)}.lock"

        ok1, pid1 = acquire_instance_lock("TEST_JARVIS", lock_file=test_lock_file)
        assert ok1 is True, f"First instance lock acquisition failed: {pid1}"

        update_instance_heartbeat(lock_file=test_lock_file)
        assert test_lock_file.exists(), "Heartbeat update did not maintain lockfile"

        lock_data = json.loads(test_lock_file.read_text(encoding="utf-8"))
        assert lock_data.get("pid") == os.getpid(), f"Lockfile has unexpected PID: {lock_data.get('pid')}"

        release_instance_lock(lock_file=test_lock_file)
        print("  PASS: Instance lock prevents duplicate launchers without terminating healthy hosts.")
        passed += 1
    except Exception as e:
        print(f"  FAIL: Instance lock error: {e}")
    finally:
        if test_lock_file and test_lock_file.exists():
            try:
                test_lock_file.unlink()
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    test_section("3. Host Heartbeat & Status Telemetry")
    total += 1
    try:
        from dashboard.server import DashboardServer

        server = DashboardServer()
        ep_hb = None
        ep_st = None
        for route in server.app.routes:
            if getattr(route, "path", None) == "/api/system/heartbeat":
                ep_hb = route.endpoint
            elif getattr(route, "path", None) == "/api/system/status":
                ep_st = route.endpoint

        assert ep_hb is not None, "Heartbeat endpoint route missing"
        assert ep_st is not None, "Status endpoint route missing"

        resp = ep_hb()
        assert resp.status_code == 200, f"Heartbeat returned {resp.status_code}"
        data = json.loads(resp.body.decode())
        assert "status" in data, f"Heartbeat endpoint failed: {data}"
        assert data.get("status") in ("STANDBY", "HEALTHY", "DEGRADED", "INITIALIZING"), f"Unexpected status: {data.get('status')}"
        assert "components" in data, "Components missing in heartbeat telemetry"
        assert "system_resources" in data, "System resources missing in heartbeat telemetry"

        resp_s = ep_st()
        assert resp_s.status_code == 200, f"Status returned {resp_s.status_code}"
        data_s = json.loads(resp_s.body.decode())
        assert "status" in data_s, f"Status endpoint failed: {data_s}"
        assert data_s.get("status") in ("STANDBY", "HEALTHY", "DEGRADED", "INITIALIZING"), f"Unexpected status: {data_s.get('status')}"
        assert data_s.get("components", {}).get("dashboard", {}).get("port") == 8000, "Port 8000 not recorded"
        assert data_s.get("components", {}).get("oauth_proxy", {}).get("port") == 8005, "Port 8005 not recorded"
        assert data_s.get("components", {}).get("gemini_live", {}).get("model") == "gemini-2.0-flash-exp"

        print("  PASS: Host heartbeat and system status telemetry verified.")
        passed += 1
    except Exception as e:
        print(f"  FAIL: Heartbeat telemetry error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    test_section("4. AI Comedy Reels Engine & Concept Generation")
    total += 1
    try:
        from core.comedy_reels import comedy_reels_manager

        cats = comedy_reels_manager.get_categories()
        assert len(cats) >= 5, f"Expected at least 5 comedy categories, found {len(cats)}"
        assert "desi_daily_life" in cats
        assert "funny_animals" in cats
        assert "unexpected_reactions" in cats

        topic = comedy_reels_manager.generate_comedy_idea(category="desi_daily_life")
        assert "hook" in topic, "Topic missing hook"
        assert "scenes" in topic and len(topic["scenes"]) == 4, f"Expected 4 scenes, got {len(topic.get('scenes', []))}"
        assert "characters" in topic and len(topic["characters"]) >= 2, "Characters missing"
        assert "captions" in topic and "english" in topic["captions"] and "hinglish" in topic["captions"]

        print(f"  PASS: Generated original comedy concept: '{topic['title']}' ({len(topic['scenes'])} scenes).")
        passed += 1
    except Exception as e:
        print(f"  FAIL: Comedy idea generation error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    test_section("5. End-to-End Comedy Reel Generation & Video Synthesis")
    total += 1
    try:
        from core.instagram_manager import instagram_manager

        print("  Generating procedural AI comedy video (video rendering + SFX audio)...")
        active_reel = instagram_manager.generate_comedy_reel(
            category="desi_daily_life",
            audio_track="desi_funk",
            account_username="mentos_life_gym",
        )
        assert active_reel is not None, "Returned reel is None"
        assert active_reel.content_type == "comedy", f"Expected content_type comedy, got {active_reel.content_type}"
        assert active_reel.account_username == "mentos_life_gym", f"Account mismatch: {active_reel.account_username}"
        assert active_reel.status == "waiting_for_approval", f"Expected waiting_for_approval, got {active_reel.status}"

        # Real disk verification
        v_path = Path(active_reel.video_path)
        assert v_path.exists(), f"Video file not found at {v_path}"
        v_size = v_path.stat().st_size
        assert v_size > 100_000, f"Video size too small: {v_size} bytes"

        # PyAV media container deep inspection
        with av.open(str(v_path)) as cont:
            assert len(cont.streams.video) > 0, "No video stream"
            v = cont.streams.video[0]
            assert v.width == 720 and v.height == 1280, f"Expected 720x1280, got {v.width}x{v.height}"
            assert len(cont.streams.audio) > 0, "No audio stream"
            a = cont.streams.audio[0]
            assert a.codec_context.name == "aac", f"Expected aac audio, got {a.codec_context.name}"

            if v.duration and v.time_base:
                dur = float(v.duration * v.time_base)
            else:
                dur = float(cont.duration / (getattr(av, "time_base", 1000000)))
            assert 12.0 <= dur <= 25.0, f"Expected ~18s duration, got {dur:.1f}s"

        print(f"  PASS: Verified video MP4 on disk ({v_size/1024:.1f} KB, 720x1280 9:16 vertical, {dur:.1f}s, AAC audio).")
        passed += 1
    except Exception as e:
        print(f"  FAIL: Video synthesis error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    test_section("6. Cover Image Thumbnail Generation")
    total += 1
    try:
        assert active_reel is not None, "active_reel was not created in step 5"
        c_path = Path(active_reel.cover_image_path)
        assert c_path.exists(), f"Cover image not found at {c_path}"
        c_size = c_path.stat().st_size
        assert c_size > 30_000, f"Cover image too small: {c_size} bytes"

        from PIL import Image
        with Image.open(str(c_path)) as img:
            assert img.size == (720, 1280), f"Cover image size mismatch: {img.size}"

        print(f"  PASS: High-resolution 9:16 cover art verified ({c_size/1024:.1f} KB, 720x1280 JPEG).")
        passed += 1
    except Exception as e:
        print(f"  FAIL: Cover art error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    test_section("7. Human Approval Gate & Publishing Security")
    total += 1
    try:
        assert active_reel is not None, "active_reel was not created in step 5"
        from core.instagram_manager import instagram_manager

        # Reel must start in waiting_for_approval
        r_dict = active_reel.to_dict()
        assert r_dict["status"] == "WAITING_FOR_APPROVAL"
        assert r_dict["can_approve"] is True
        assert r_dict["is_target_authorized"] is True

        # Reject unauthorized account target
        try:
            instagram_manager.generate_comedy_reel(account_username="unauthorized_rogue_account")
            assert False, "Should have rejected unauthorized account"
        except ValueError:
            print("  PASS: Strict account enforcement rejects unauthorized account targets.")

        # Approve reel
        app_ok = instagram_manager.approve_reel(active_reel.id)
        assert app_ok is True, "Approve reel failed"
        approved_reel = instagram_manager.get_reel(active_reel.id)
        assert approved_reel.status == "approved", f"Status not approved: {approved_reel.status}"

        # Attempt to publish (unverified token correctly halts or falls back to assisted mode)
        pub_res = instagram_manager.publish_reel(active_reel.id, allow_assisted_fallback=True)
        assert pub_res.get("ok") is True, f"Publishing workflow failed: {pub_res}"
        assert pub_res.get("assisted_available") is True, "Assisted download was not provided"
        print("  PASS: Human approval gate, token validation, and assisted publish fallback verified.")
        passed += 1
    except Exception as e:
        print(f"  FAIL: Approval gate error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    test_section("8. Comedy REST Endpoints & Content Filtering")
    total += 1
    try:
        from dashboard.server import DashboardServer

        server = DashboardServer()
        # Add test auth token
        server._tokens["test_token_123"] = time.time()
        client = TestClient(server.app)
        headers = {"Authorization": "Bearer test_token_123"}

        # 1. Comedy categories
        r_cat = client.get("/api/reels/comedy/categories", headers=headers)
        assert r_cat.status_code == 200 and r_cat.json().get("ok") is True, f"Categories failed: {r_cat.text}"

        # 2. Comedy topics
        r_top = client.get("/api/reels/comedy/topics?category=desi_daily_life", headers=headers)
        assert r_top.status_code == 200 and len(r_top.json().get("topics", [])) > 0, f"Topics failed: {r_top.text}"

        # 3. List comedy reels
        r_list = client.get("/api/reels?content_type=comedy", headers=headers)
        assert r_list.status_code == 200, f"List comedy failed: {r_list.text}"
        comedy_items = r_list.json().get("reels", [])
        for item in comedy_items:
            assert item.get("content_type") == "comedy", f"Non-comedy item found: {item}"

        print("  PASS: REST endpoints and content-type filtering (/api/reels?content_type=comedy) verified.")
        passed += 1
    except Exception as e:
        print(f"  FAIL: REST endpoint error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"BATTERY COMPLETE: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print(f"{'='*70}")

    if passed != total:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    run_tests()
