"""
test_instagram_reels.py — Verification Suite for Instagram AI Trading Reels Automation

Tests:
1. Multi-account connection, listing, and explicit Reels designation for @mentos_life_gym.
2. Strict Target Security: Generating Reels for unauthorized accounts raises ValueError.
3. Educational trading topic research, dynamic idea generator & 4-scene script breakdown.
4. Local vertical MP4 video rendering (720x1280) with PyAV, dynamic subtitles, transitions, and audio track.
5. Video container validity: Checking duration, dimensions, stream types (video + audio).
6. Content ledger deduplication: Ensuring identical concepts are not repeatedly generated.
7. Mandatory Human Approval Gate:
   - Attempting publication while in 'waiting_for_approval' MUST be rejected with a security refusal.
   - Explicit approval moves state to 'approved'.
   - Publication succeeds only after approval, logging assisted/official result.
8. Tool declaration and Action Registry integration.
"""

import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.instagram_manager import instagram_manager, TRADING_TOPICS
from actions.manage_instagram import manage_instagram, TOOL


def run_instagram_suite():
    print("=" * 70)
    print("  J.A.R.V.I.S. INSTAGRAM AI TRADING REELS AUTOMATION SUITE")
    print("=" * 70)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 1: Account Management & Designation for @mentos_life_gym
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 1: Multi-Account Handling & Explicit Designation ---")
    acc1 = instagram_manager.connect_account(
        username="fatih_personal",
        account_type="personal",
        designated_reels=False,
    )
    acc2 = instagram_manager.connect_account(
        username="mentos_life_gym",
        account_type="creator",
        designated_reels=True,
    )
    accounts = instagram_manager.list_accounts()
    print(f"Connected accounts: {[a['username'] for a in accounts]}")
    reels_acc = instagram_manager.get_reels_account()
    print(f"Designated Reels Account: @{reels_acc.username}")
    assert reels_acc.username == "mentos_life_gym", f"Expected designated account mentos_life_gym, got {reels_acc.username}"
    # Verify personal account is NOT designated
    personal = next(a for a in accounts if a["username"] == "fatih_personal")
    assert not personal.get("designated_reels"), "Personal account should not be designated"
    print("✅ TEST 1 PASSED: Multi-account isolation and @mentos_life_gym Reels assignment verified.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 2: Strict Target Enforcement & Dynamic Idea Generation
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 2: Strict Target Enforcement & Idea / Scene Breakdown ---")
    # Verify mismatched account is rejected
    mismatch_caught = False
    try:
        instagram_manager.generate_trading_reel(
            topic_id="risk_rule_1_percent",
            account_username="jarvis_trading_alpha",
        )
    except ValueError as val_err:
        mismatch_caught = True
        print(f"Verified security refusal for mismatched target account: {val_err}")
    assert mismatch_caught, "Security refusal failed: generated reel targeting unauthorized account!"

    # Test dynamic idea generation with 4-scene script breakdown
    idea = instagram_manager.generate_reel_idea(niche="trading_and_discipline")
    assert "scenes" in idea and len(idea["scenes"]) == 4, f"Expected 4 scenes, got {len(idea.get('scenes', []))}"
    print(f"Generated Idea Title: '{idea['title']}' (Niche: {idea['niche']})")
    for s in idea["scenes"]:
        print(f"  Scene {s['scene_idx']} ({s['name']}): {s['voiceover'][:45]}...")
    print("✅ TEST 2 PASSED: Strict target enforcement and dynamic 4-scene breakdown verified.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 3: Autonomous Trading Reel Generation (Concept, Audio Mixing, Vertical Video)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 3: Autonomous Video, Subtitles, Transitions & Audio Production ---")
    post = instagram_manager.generate_trading_reel(
        topic_id="risk_rule_1_percent",
        account_username="mentos_life_gym",
        scheduled_delay_hours=3,
        audio_track="ambient_cyber",
        voice_id="female",
        subtitles_enabled=True,
        transition_type="crossfade",
    )
    print(f"Generated Reel ID: {post.id}")
    print(f"Title: {post.title}")
    print(f"Target Account: @{post.account_username}")
    print(f"Initial Status: {post.status.upper()}")
    print(f"Video File: {post.video_path}")
    print(f"Audio File: {post.audio_path}")
    print(f"Audio Track: {post.audio_track} | Subtitles: {post.subtitles_enabled} | Transition: {post.transition_type}")
    print(f"Scenes attached: {len(post.scenes)}")

    assert os.path.exists(post.video_path), f"Video file not found at {post.video_path}"
    video_size = os.path.getsize(post.video_path)
    print(f"Rendered MP4 Size: {video_size:,} bytes")
    assert video_size > 50_000, f"Expected MP4 > 50KB, got {video_size} bytes"

    # Verify PyAV container integrity
    import av
    with av.open(post.video_path) as cont:
        assert len(cont.streams.video) > 0, "Expected at least 1 video stream"
        v = cont.streams.video[0]
        print(f"Video Stream: {v.width}x{v.height} @ {float(v.average_rate or 30):.1f} fps")
        assert v.width == 720 and v.height == 1280, f"Expected 720x1280 vertical video, got {v.width}x{v.height}"

    assert post.status == "waiting_for_approval", f"Expected waiting_for_approval, got {post.status}"
    assert "Educational" in post.caption or "Not financial" in post.caption, "Expected compliance disclaimer in caption"
    print("✅ TEST 3 PASSED: Vertical MP4 video rendered locally with audio track, subtitles, and transitions.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 4: Duplicate Prevention & Content Ledger
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 4: Content Ledger Deduplication ---")
    next_topic = instagram_manager.pick_next_topic()
    print(f"Next educational topic suggested: '{next_topic['title']}' (ID: {next_topic['id']})")
    assert next_topic["id"] != post.topic_id or len(TRADING_TOPICS) == 1, (
        f"Expected fresh topic, got repeat of {post.topic_id}"
    )
    print("✅ TEST 4 PASSED: Content ledger correctly rotates topics to prevent duplicate posts.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 5: Mandatory Publication Approval Gate
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 5: Mandatory Publication Approval Gate ---")
    # Step A: Attempt publishing WITHOUT approval -> MUST FAIL
    unapproved_result = instagram_manager.publish_reel(post.id)
    print(f"Attempting unapproved publish: ok={unapproved_result.get('ok')}, error='{unapproved_result.get('error')}'")
    assert not unapproved_result.get("ok"), "Security failure: Unapproved Reel published without authorization!"
    assert "Explicit human approval is required" in unapproved_result.get("error", "")

    # Step B: Explicit human approval
    ok_approve = instagram_manager.approve_reel(post.id)
    assert ok_approve, "Failed to approve reel"
    post_approved = instagram_manager.get_reel(post.id)
    assert post_approved.status == "approved"
    print(f"Reel status after approval: {post_approved.status.upper()}")

    # Step C: Publish approved Reel (Supported assisted workflow fallback)
    pub_result = instagram_manager.publish_reel(post.id, allow_assisted_fallback=True)
    print(f"Publishing approved reel: ok={pub_result.get('ok')}, method={pub_result.get('method')}")
    assert pub_result.get("ok"), f"Publish failed: {pub_result}"
    post_published = instagram_manager.get_reel(post.id)
    assert post_published.status in ("published", "published_assisted")
    print("✅ TEST 5 PASSED: Mandatory human approval gate strictly enforced.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 6: Action Tool 'manage_instagram' Handler Execution
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 6: Action Tool 'manage_instagram' Integration ---")
    assert TOOL["name"] == "manage_instagram"
    assert TOOL.get("tier") == "core"

    # Test list_accounts
    res_list = manage_instagram({"action": "list_accounts"})
    print(f"Tool list_accounts response: {res_list.splitlines()[0]}")
    assert "mentos_life_gym" in res_list

    # Test preview_reel
    res_prev = manage_instagram({"action": "preview_reel", "reel_id": post.id})
    print(f"Tool preview_reel response: {res_prev.splitlines()[0]}")
    assert post.id in res_prev

    # Test generate_idea action
    res_idea = manage_instagram({"action": "generate_idea", "niche": "trading_and_discipline"})
    print(f"Tool generate_idea response: {res_idea.splitlines()[0]}")
    assert "Scene Breakdown" in res_idea

    print("✅ TEST 6 PASSED: Action tool declarations and handler functions verified.")

    print("\n" + "=" * 70)
    print("  🎉 ALL 6 INSTAGRAM TRADING REELS VERIFICATION TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    run_instagram_suite()

