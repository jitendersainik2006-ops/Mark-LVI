"""
Verification test suite for J.A.R.V.I.S. Instagram Reels, 10 Trading Topics,
Posting Times (Asia/Kolkata), 7-Day Calendar, and Truthful Analytics.
"""

import sys
import os
import json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.instagram_manager import instagram_manager, TRADING_TOPICS, DISCLAIMER
from actions.manage_instagram import manage_instagram


def run_tests():
    print("=" * 75)
    print("  J.A.R.V.I.S. INSTAGRAM REELS, CALENDAR & ANALYTICS TEST SUITE")
    print("=" * 75)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 1: Verify 10 Educational Trading Topics
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 1: 10 Educational Trading Topics ---")
    assert len(TRADING_TOPICS) == 10, f"Expected 10 topics, got {len(TRADING_TOPICS)}"
    print(f"Verified {len(TRADING_TOPICS)} comprehensive educational trading topics:")
    for idx, t in enumerate(TRADING_TOPICS, 1):
        assert "id" in t and "title" in t and "hook" in t and "points" in t and "cta" in t and "hashtags" in t
        assert len(t["points"]) == 3, f"Topic {t['id']} does not have 3 points"
        assert len(t["hashtags"]) >= 3, f"Topic {t['id']} does not have sufficient hashtags"
        print(f"  {idx}. [{t['id']}] {t['title']} (Hook: {t['hook'][:40]}...)")
    print("✅ TEST 1 PASSED: All 10 educational trading topics verified.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 2: Designated Account (@mentos_life_gym) Truthful Status
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 2: Designated Account (@mentos_life_gym) Status ---")
    acc = instagram_manager.get_account("mentos_life_gym")
    assert acc is not None, "@mentos_life_gym account not found in manager"
    acc_dict = acc.to_dict()
    assert acc_dict["is_designated"] is True, "@mentos_life_gym must be designated for Reels"
    assert acc_dict["status"] in ("AUTHORIZATION_REQUIRED", "UNVERIFIED_BY_META"), (
        f"Expected truthful AUTHORIZATION_REQUIRED or UNVERIFIED_BY_META status without Meta token, got {acc_dict['status']}"
    )
    print(f"Account: @{acc.username}")
    print(f"Status: {acc_dict['status']} (Truthful - no fake connection)")
    print(f"Designated for Reels: {acc_dict['is_designated']}")
    print("✅ TEST 2 PASSED: Designated account @mentos_life_gym verified with truthful status.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 3: Intelligent Posting Times for Asia/Kolkata (IST)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 3: Posting Times in Asia/Kolkata (IST) ---")
    times = instagram_manager.get_recommended_posting_times("mentos_life_gym")
    assert "Asia/Kolkata" in times["timezone"]
    assert "current_time_ist" in times
    assert times["has_real_insights"] is False
    assert "Experimental" in times["mode"]
    assert "note" in times and "@mentos_life_gym" in times["note"]
    windows = times["recommended_windows"]
    assert len(windows) == 4, f"Expected 4 high-engagement Indian market windows, got {len(windows)}"

    for w in windows:
        assert "name" in w and "time_range" in w and "target_audience" in w and "confidence" in w
        print(f"  • {w['name']}: {w['time_range']} (Confidence: {w['confidence']}%)")
    print("✅ TEST 3 PASSED: Asia/Kolkata posting windows with heuristic notice verified.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 4: 7-Day Content Calendar Generation
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 4: 7-Day Content Calendar ---")
    cal = instagram_manager.get_content_calendar("mentos_life_gym", days=7)
    assert isinstance(cal, list), "Calendar should return list of scheduled days"
    assert len(cal) == 7, f"Expected 7 days in calendar, got {len(cal)}"
    for item in cal:
        assert "day" in item and "date" in item and "scheduled_time" in item
        assert "slot_name" in item and "confidence" in item
        assert "title" in item and "hook" in item and "hashtags" in item
        assert "status" in item and "approval_gate" in item
        print(f"  {item['day']} ({item['date']}): {item['title'][:35]} at {item['scheduled_time']} [{item['approval_gate']}]")
    print("✅ TEST 4 PASSED: 7-day content schedule verified.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 5: Truthful Analytics (No Fabricated Numbers)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 5: Truthful Analytics & Meta Authorization Guard ---")
    analytics = instagram_manager.get_account_analytics("mentos_life_gym")
    assert "@mentos_life_gym" in analytics["account"]
    assert analytics["status"] == "AWAITING_META_AUTHORIZATION"
    assert analytics["official_insights_active"] is False
    assert "production_summary" in analytics
    ps = analytics["production_summary"]
    assert "total_reels_created" in ps
    assert "reels_published_assisted" in ps
    assert "reels_awaiting_approval" in ps
    assert "snapshots_tracked" in analytics
    print(f"Analytics Status: {analytics['status']} (Official Insights Active: {analytics['official_insights_active']})")
    print(f"Production ledger count: {ps['total_reels_created']}")
    print(f"Published (Assisted): {ps['reels_published_assisted']}, Awaiting Approval: {ps['reels_awaiting_approval']}")
    print("✅ TEST 5 PASSED: Unfabricated analytics and AWAITING_META_AUTHORIZATION status verified.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 6: Weekly Growth Report Generator
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 6: Weekly Growth Report Generator ---")
    weekly_rep = instagram_manager.generate_weekly_report("mentos_life_gym")
    assert "@mentos_life_gym" in weekly_rep["account"]
    assert "markdown_report" in weekly_rep
    md = weekly_rep["markdown_report"]
    assert "@mentos_life_gym" in md
    assert "Asia/Kolkata" in md
    assert "Weekly AI Reels Growth Report" in md
    print("Snippet of generated weekly report:")
    lines = md.strip().split("\n")[:8]
    for line in lines:
        print(f"  {line}")
    print("✅ TEST 6 PASSED: Weekly performance report markdown generated.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 7: Tool Action Execution via manage_instagram
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 7: Tool Action Execution (actions/manage_instagram.py) ---")
    res_times = manage_instagram({"action": "posting_times", "username": "mentos_life_gym"})
    assert "Asia/Kolkata" in res_times and "Recommended Posting Times" in res_times

    res_cal = manage_instagram({"action": "content_calendar", "username": "mentos_life_gym", "days": 7})
    assert "7-Day Educational Trading Reels Calendar" in res_cal

    res_ana = manage_instagram({"action": "view_analytics", "username": "mentos_life_gym"})
    assert "Instagram Performance & Growth Analytics" in res_ana

    res_rep = manage_instagram({"action": "weekly_report", "username": "mentos_life_gym"})
    assert "Weekly Instagram Reels Performance Report" in res_rep
    print("✅ TEST 7 PASSED: All manage_instagram tool actions executed successfully.")

    print("\n" + "=" * 75)
    print("  🎉 ALL 7 REELS, CALENDAR & ANALYTICS VERIFICATION TESTS PASSED!")
    print("=" * 75)


if __name__ == "__main__":
    run_tests()
