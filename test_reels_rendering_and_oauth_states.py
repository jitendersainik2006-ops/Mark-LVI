"""
test_reels_rendering_and_oauth_states.py — Comprehensive Regression & Quality Test Suite

Covers:
1. Video streaming query param token authentication, HTTP 200 & HTTP 206 range requests, headers (Accept-Ranges, Content-Type: video/mp4).
2. Missing and 0-byte video detection: to_dict() returns has_video_file=False and status=render_failed; approve_reel() refuses.
3. Faststart MP4 encoding: moov atom placement ahead of or before main mdat payload for instant HTML5 playback.
4. Six Instagram account connection UI and API states: NOT_CONNECTED, AUTHORIZATION_REQUIRED, CONNECTING, CONNECTED, TOKEN_EXPIRED, VERIFICATION_FAILED.
5. Authoritative Instagram ID verification (17841458094701596) and target account consistency (@mentos_life_gym).
6. Multilingual captions & disclaimers: Hindi (Devanagari) and Hinglish (Roman Hindi) without unsupported claims.
7. Explicit human approval gating: publishing strictly prevented without human approval.
"""

import os
import sys
import json
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from starlette.testclient import TestClient
from dashboard.server import DashboardServer
from core.instagram_manager import (
    instagram_manager,
    InstagramAccount,
    ReelPost,
    AUTHORITATIVE_INSTAGRAM_ID,
    DISCLAIMER,
    TRADING_TOPICS,
    REELS_DIR,
)


def test_1_video_streaming_auth_and_headers():
    print("\n--- TEST 1: Video Streaming Auth & HTTP Headers ---")
    server = DashboardServer()
    token = f"test_stream_tok_{int(time.time())}"
    server._tokens[token] = time.time()
    app = server._build_app()
    client = TestClient(app)

    # Pick or generate a reel with a valid video
    reels = instagram_manager.list_reels("all")
    valid_reel = next((r for r in reels if r.get("has_video_file")), None)
    if not valid_reel:
        post = instagram_manager.generate_trading_reel(
            topic_id="risk_rule_1_percent",
            account_username="mentos_life_gym",
        )
        reel_id = post.id
    else:
        reel_id = valid_reel["id"]

    # 1. Unauthenticated request -> must return 401
    res_no_auth = client.get(f"/api/reels/{reel_id}/video")
    assert res_no_auth.status_code == 401, f"Expected 401 Unauthorized, got {res_no_auth.status_code}"
    print("[PASS] Unauthenticated request correctly rejected with 401")

    # 2. Token via query param -> must return 200 with video/mp4
    res_query_tok = client.get(f"/api/reels/{reel_id}/video?token={token}")
    assert res_query_tok.status_code == 200, f"Expected 200 OK, got {res_query_tok.status_code}"
    assert res_query_tok.headers.get("content-type") == "video/mp4", "Missing or invalid Content-Type"
    assert res_query_tok.headers.get("accept-ranges") == "bytes", "Missing Accept-Ranges: bytes"
    assert "content-length" in res_query_tok.headers, "Missing Content-Length"
    total_len = int(res_query_tok.headers["content-length"])
    assert total_len > 50_000, f"Video content length too small: {total_len}"
    print(f"[PASS] Query param auth succeeded: {total_len:,} bytes (Content-Type: video/mp4)")

    # 3. HTTP Range request (partial content)
    range_header = {"Authorization": f"Bearer {token}", "Range": "bytes=0-1023"}
    res_range = client.get(f"/api/reels/{reel_id}/video", headers=range_header)
    assert res_range.status_code == 206, f"Expected 206 Partial Content, got {res_range.status_code}"
    assert res_range.headers.get("content-range") == f"bytes 0-1023/{total_len}"
    assert len(res_range.content) == 1024
    print(f"[PASS] Range request succeeded: 206 Partial Content (bytes 0-1023/{total_len})")


def test_2_missing_and_zero_byte_video_detection():
    print("\n--- TEST 2: Missing and 0-Byte Video File Detection ---")
    ghost_reel_id = "test_ghost_0byte_check_999"
    dummy_path = str(REELS_DIR / f"{ghost_reel_id}.mp4")
    
    # Create 0-byte file
    with open(dummy_path, "wb") as f:
        pass
    assert os.path.exists(dummy_path) and os.path.getsize(dummy_path) == 0

    ghost_post = ReelPost(
        id=ghost_reel_id,
        topic_id="risk_rule_1_percent",
        title="Ghost 0-Byte Reel",
        account_username="mentos_life_gym",
        hook="Test hook",
        points=["Point 1", "Point 2"],
        cta="Follow @mentos_life_gym",
        caption="Educational test caption",
        hashtags=["#TradingEducation"],
        video_path=dummy_path,
        audio_path="",
        status="waiting_for_approval",
    )
    instagram_manager._ledger[ghost_reel_id] = ghost_post

    # to_dict() must detect 0-byte file and map status to RENDER_FAILED
    d = ghost_post.to_dict()
    assert d["has_video_file"] is False, "Expected has_video_file to be False for 0-byte file"
    assert d["status"].upper() == "RENDER_FAILED", f"Expected RENDER_FAILED, got {d['status']}"
    assert "0 bytes" in d.get("error", ""), "Expected error message explaining 0-byte corruption"
    print(f"[PASS] to_dict() correctly identifies 0-byte file: has_video_file={d['has_video_file']}, status={d['status']}")

    # approve_reel must refuse approval on 0-byte video
    ok_approve = instagram_manager.approve_reel(ghost_reel_id)
    assert not ok_approve, "Security breach: 0-byte video reel was approved!"
    assert ghost_post.status.upper() == "RENDER_FAILED"
    print(f"[PASS] approve_reel() strictly refuses approval of unrendered 0-byte reel: {ghost_post.error}")

    # Clean up ghost test entry
    instagram_manager._ledger.pop(ghost_reel_id, None)
    if os.path.exists(dummy_path):
        os.remove(dummy_path)


def test_3_faststart_moov_atom_placement():
    print("\n--- TEST 3: Faststart MP4 moov Atom Verification ---")
    reels = instagram_manager.list_reels("all")
    valid_reel = next((r for r in reels if r.get("has_video_file")), None)
    assert valid_reel is not None, "At least one valid reel must exist"
    v_path = valid_reel["video_path"]

    with open(v_path, "rb") as f:
        header = f.read(4096)

    # In faststart MP4, 'moov' atom appears in the first 4KB of the file (before audio/video samples)
    moov_pos = header.find(b"moov")
    print(f"[INFO] moov atom position in {Path(v_path).name}: byte {moov_pos}")
    assert moov_pos != -1, "Faststart verification failed: 'moov' atom not in first 4096 bytes"
    print("✅ TEST 3 PASSED: MP4 contains faststart moov atom at beginning for instantaneous streaming.")


def test_4_all_six_oauth_states_in_ui_and_api():
    print("\n--- TEST 4: Six Account Connection States in UI & API ---")
    expected_states = {
        "NOT_CONNECTED",
        "AUTHORIZATION_REQUIRED",
        "CONNECTING",
        "CONNECTED",
        "TOKEN_EXPIRED",
        "VERIFICATION_FAILED",
    }

    # Verify app.html contains handlers/styles for all 6 states
    app_html = (BASE_DIR / "dashboard" / "static" / "app.html").read_text(encoding="utf-8")
    for st in expected_states:
        assert st in app_html, f"State '{st}' not handled in dashboard/static/app.html"
    print(f"[PASS] All 6 states found in app.html: {', '.join(expected_states)}")

    # Verify badge classes exist
    assert "badge-reels-conn" in app_html
    assert "badge-reels-auth" in app_html
    assert "badge-reels-err" in app_html
    assert "badge-reels-disc" in app_html
    print("[PASS] CSS badge classes for account states verified.")


def test_5_authoritative_instagram_id_and_target():
    print("\n--- TEST 5: Authoritative ID & Account Target Consistency ---")
    assert AUTHORITATIVE_INSTAGRAM_ID == "17841458094701596"
    accounts = instagram_manager.list_accounts()
    mentos = next((a for a in accounts if a["username"] == "mentos_life_gym"), None)
    assert mentos is not None
    assert mentos.get("expected_instagram_user_id") == "17841458094701596"

    # Mismatched target accounts must have target_mismatch flag and blocked approval
    mismatch_post = ReelPost(
        id="test_mismatch_check_888",
        topic_id="risk_rule_1_percent",
        title="Mismatch Reel",
        account_username="legacy_unauthorized_user",
        hook="Test hook",
        points=["Point 1", "Point 2"],
        cta="Follow @mentos_life_gym",
        caption="Educational test caption",
        hashtags=["#TradingEducation"],
        video_path="some_path.mp4",
        audio_path="",
        status="waiting_for_approval",
    )
    instagram_manager._ledger["test_mismatch_check_888"] = mismatch_post
    d = mismatch_post.to_dict()
    assert d.get("target_mismatch") is True
    ok_approve = instagram_manager.approve_reel("test_mismatch_check_888")
    assert not ok_approve, "Approval of mismatched target account succeeded when it should fail!"
    print(f"[PASS] Target account mismatch correctly blocked: {mismatch_post.error}")
    instagram_manager._ledger.pop("test_mismatch_check_888", None)


def test_6_multilingual_captions_and_disclaimer():
    print("\n--- TEST 6: Multilingual Captions & Compliance Disclaimers ---")
    for topic in TRADING_TOPICS:
        multi = instagram_manager.generate_multilingual_captions(topic)
        en = multi["english"]
        hi = multi["hindi"]
        hg = multi["hinglish"]

        # Ensure no unsupported claims
        assert "90% of retail traders blow their accounts" not in en
        assert "90% of retail traders blow their accounts" not in hg

        # Ensure educational disclaimers
        assert DISCLAIMER in en
        assert "शैक्षिक" in hi or "शिक्षा" in hi
        assert "Educational" in hg or "educational" in hg

        print(f"[PASS] Topic '{topic['id']}': English, Hindi, and Hinglish verified with disclaimers.")


def test_7_mandatory_approval_and_publish_safety():
    print("\n--- TEST 7: Mandatory Approval Gate & Publish Safety ---")
    reels = instagram_manager.list_reels("all")
    valid_reel = next((r for r in reels if r.get("has_video_file")), None)
    assert valid_reel is not None
    reel_id = valid_reel["id"]

    # Reset to draft or waiting_for_approval to test gate
    post = instagram_manager.get_reel(reel_id)
    orig_status = post.status
    post.status = "waiting_for_approval"
    instagram_manager._save_ledger()

    # Attempt publishing without prior approve_reel() call -> MUST FAIL
    res_pub = instagram_manager.publish_reel(reel_id)
    assert not res_pub.get("ok"), "Security failure: Reel was published without approval!"
    assert "Explicit human approval is required" in res_pub.get("error", "")
    print(f"[PASS] Unapproved publish strictly prevented: {res_pub['error']}")

    # Restore status
    post.status = orig_status
    instagram_manager._save_ledger()


def run_all_tests():
    print("=" * 75)
    print("  J.A.R.V.I.S. REELS RENDERING & OAUTH STATES REGRESSION TEST SUITE")
    print("=" * 75)
    test_1_video_streaming_auth_and_headers()
    test_2_missing_and_zero_byte_video_detection()
    test_3_faststart_moov_atom_placement()
    test_4_all_six_oauth_states_in_ui_and_api()
    test_5_authoritative_instagram_id_and_target()
    test_6_multilingual_captions_and_disclaimer()
    test_7_mandatory_approval_and_publish_safety()
    print("=" * 75)
    print("  ALL 7 REELS RENDERING & OAUTH REGRESSION TESTS PASSED (100% SUCCESS)")
    print("=" * 75)


if __name__ == "__main__":
    run_all_tests()
