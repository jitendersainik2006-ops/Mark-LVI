"""
J.A.R.V.I.S. Mark LVI - Instagram Account Identity & Security Verification Suite
Tests:
1. discover_instagram_accounts() returns [] on invalid token (no placeholder substitution)
2. verify_account_identity() against live Meta API reports exact HTTP 400 OAuthException without fabrication
3. verify_with_meta_response() confirms authoritative ID 17841458094701596 for @mentos_life_gym
4. generate_trading_reel() strictly generates reels targeting only @mentos_life_gym
5. All 5 mismatched legacy drafts cannot be approved or published (strict security refusal)
6. Zero fabrication of follower counts, views, or Insights in get_account_analytics()
7. Stored account record in data/instagram_accounts.json has authoritative ID 17841458094701596 and DPAPI encrypted token
"""

import sys
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.instagram_manager import (
    InstagramManager,
    InstagramAccount,
    AUTHORITATIVE_INSTAGRAM_ID,
    KNOWN_PLACEHOLDER_IDS,
    ACCOUNTS_FILE,
    LEDGER_FILE,
)
from core.meta_oauth import (
    MetaOAuthManager,
    meta_oauth,
    AUTHORITATIVE_INSTAGRAM_ID as META_AUTH_ID,
)
from core.crypto_storage import is_encrypted, decrypt_token


def test_1_no_placeholder_substitution():
    print("\n--- TEST 1: No Placeholder Substitution on Discovery Failure ---")
    oauth = MetaOAuthManager()
    dummy_token = "EAABw_INVALID_OR_REVOKED_TOKEN_0000"
    
    # Discovery with invalid token must return empty list, never fabricated accounts
    discovered = oauth.discover_instagram_accounts(dummy_token)
    assert discovered == [], f"Expected empty list for invalid token, got: {discovered}"
    for acc in discovered:
        assert acc.get("instagram_user_id") not in KNOWN_PLACEHOLDER_IDS, "Placeholder ID detected!"
    print("[PASS] TEST 1 PASSED: Zero placeholder substitution when discovery fails; returned empty list.")


def test_2_live_meta_api_truthful_reporting():
    print("\n--- TEST 2: Live Meta API Truthful Reporting (No Fabrication) ---")
    oauth = MetaOAuthManager()
    mgr = InstagramManager()
    current_acc = mgr.get_account("mentos_life_gym")
    assert current_acc is not None, "mentos_life_gym account must exist in registry"
    
    # Verify account identity against live Meta API using the stored token
    identity = oauth.verify_account_identity(
        current_acc.access_token,
        target_username="mentos_life_gym",
        authoritative_id=AUTHORITATIVE_INSTAGRAM_ID
    )
    
    print(f"Meta Live API status response: {identity.get('status')}")
    val_err = identity.get("token_validity", {}).get("error", "") or identity.get("error", "")
    print(f"Meta Live API error summary: {val_err[:100]}...")
    
    # Must report truthfully without inventing mock data
    assert identity["verified"] is False, "Malformed/dummy token must not be reported as verified"
    assert identity["confirmed_id"] is None, "Unverified token must not confirm an Instagram ID"
    assert identity.get("status") in ("UNVERIFIED_BY_META", "UNVERIFIED_TOKEN_REJECTED", "API_ERROR")
    assert "OAuthException" in val_err or "HTTP 400" in val_err, (
        f"Unexpected error report: {identity}"
    )
    assert AUTHORITATIVE_INSTAGRAM_ID not in (identity.get("confirmed_id") or ""), "Must not claim authoritative ID confirmed by unverified token"
    print("[PASS] TEST 2 PASSED: Live Meta Graph API truthful reporting verified; exact HTTP 400 / OAuthException reported without fabrication.")


def test_3_authoritative_response_verification():
    print("\n--- TEST 3: Authoritative Meta Response Verification ---")
    oauth = MetaOAuthManager()
    
    # Mock authorized Meta API response matching authoritative Business Settings
    valid_meta_response = {
        "data": [
            {
                "id": "100998877665544",
                "name": "Mentos Life Gym Page",
                "access_token": "EAABw_VALID_PAGE_ACCESS_TOKEN_SAMPLE",
                "instagram_business_account": {
                    "id": "17841458094701596",
                    "username": "mentos_life_gym",
                    "name": "Mentos Life Gym"
                }
            }
        ]
    }
    
    result = oauth.verify_with_meta_response(valid_meta_response, target_username="mentos_life_gym")
    assert result["verified"] is True
    assert result["confirmed_id"] == AUTHORITATIVE_INSTAGRAM_ID
    assert result["id_match"] is True
    assert result["username"] == "mentos_life_gym"
    
    # Response with mismatched or placeholder ID must be flagged as mismatch
    mismatch_response = {
        "data": [
            {
                "id": "100998877665544",
                "name": "Mentos Life Gym Page",
                "access_token": "EAABw_VALID_PAGE_ACCESS_TOKEN_SAMPLE",
                "instagram_business_account": {
                    "id": "17841400011223344",  # Placeholder ID
                    "username": "mentos_life_gym",
                }
            }
        ]
    }
    result_mismatch = oauth.verify_with_meta_response(mismatch_response, target_username="mentos_life_gym")
    assert result_mismatch["verified"] is True
    assert result_mismatch["confirmed_id"] == "17841400011223344"
    assert result_mismatch["id_match"] is False, "Placeholder ID must not match AUTHORITATIVE_INSTAGRAM_ID"
    print("[PASS] TEST 3 PASSED: verify_with_meta_response confirms authoritative ID 17841458094701596 and flags mismatches.")


def test_4_reel_generation_strictly_targets_mentos_life_gym():
    print("\n--- TEST 4: Reel Generation Strictly Targets @mentos_life_gym ---")
    scratch_dir = Path("D:/JARVIS-AI/mark_lvi_core/scratch_test")
    scratch_dir.mkdir(exist_ok=True)
    scratch_ledger = scratch_dir / "test_scratch_ledger.json"
    if scratch_ledger.exists():
        scratch_ledger.unlink()
        
    with patch("core.instagram_manager.LEDGER_FILE", scratch_ledger):
        mgr = InstagramManager()
        reel = mgr.generate_trading_reel(
            topic_id="risk_rule_1_percent",
            account_username=None,  # default should be authoritative mentos_life_gym
        )
        assert reel.account_username == "mentos_life_gym", f"Generated reel must target @mentos_life_gym, got {reel.account_username}"
        assert getattr(reel, "target_mismatch", False) is False, "New reel for mentos_life_gym must not have target_mismatch"
        
        # Verify attempt to generate for unverified or mismatched account raises ValueError
        try:
            mgr.generate_trading_reel(
                topic_id="risk_rule_1_percent",
                account_username="trader_alpha_reels",
            )
            assert False, "Should have raised ValueError when requesting generation for mismatched account"
        except ValueError as ve:
            assert "unauthorized target account" in str(ve).lower() or "mentos_life_gym" in str(ve).lower()
            print("[PASS] Refusal to generate for mismatched account confirmed.")
    print("[PASS] TEST 4 PASSED: Reel generation strictly targets @mentos_life_gym.")


def test_5_mismatched_drafts_publication_blocked():
    print("\n--- TEST 5: Mismatched Legacy Drafts Publication Strictly Blocked ---")
    mismatched_draft_ids = [
        "reel_1793112021_914929",
        "reel_1793112098_e7a24f",
        "reel_1793374298_ae4bd9",
        "reel_1793374353_0b9881",
        "reel_1793374452_ceeff0",
    ]
    
    with open(LEDGER_FILE, "r", encoding="utf-8") as f:
        ledger = json.load(f)
        
    for rid in mismatched_draft_ids:
        assert rid in ledger, f"Draft {rid} must be preserved in ledger"
        entry = ledger[rid]
        assert entry.get("target_mismatch") is True, f"Draft {rid} must have target_mismatch == True"
        assert "Target Account Mismatch" in entry.get("error", ""), f"Draft {rid} must have descriptive error"
        assert entry.get("account_username") in ["trader_alpha_reels", "jarvis_trading_alpha"]
        
    # Test approval refusal and publish refusal on an isolated scratch copy to preserve production ledger
    scratch_dir = Path("D:/JARVIS-AI/mark_lvi_core/scratch_test")
    scratch_dir.mkdir(exist_ok=True)
    scratch_ledger = scratch_dir / "test_scratch_mismatch_ledger.json"
    scratch_ledger.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    
    with patch("core.instagram_manager.LEDGER_FILE", scratch_ledger):
        test_mgr = InstagramManager()
        for rid in mismatched_draft_ids:
            entry = ledger[rid]
            # Test approval refusal
            approved = test_mgr.approve_reel(rid)
            assert approved is False, f"Draft {rid} must not be approvable"
            
            # Test publish refusal
            res = test_mgr.publish_reel(rid)
            assert res["ok"] is False
            assert res.get("target_mismatch") is True or "mismatch" in res.get("error", "").lower()
            print(f"[PASS] Draft {rid} ({entry['account_username']}): approval refused ({approved}) and publication strictly blocked.")
            
    print("[PASS] TEST 5 PASSED: All 5 mismatched legacy drafts preserved but publication strictly prevented.")


def test_6_zero_analytics_fabrication():
    print("\n--- TEST 6: Zero Analytics Fabrication ---")
    mgr = InstagramManager()
    analytics = mgr.get_account_analytics("mentos_life_gym")
    
    # Must report real status, zero mock follower count or fake insights
    assert analytics.get("views") in (0, None), f"Views must not be fabricated, got {analytics.get('views')}"
    assert analytics.get("reach") in (0, None), f"Reach must not be fabricated, got {analytics.get('reach')}"
    assert analytics.get("likes") in (0, None), f"Likes must not be fabricated, got {analytics.get('likes')}"
    assert analytics.get("shares") in (0, None), f"Shares must not be fabricated, got {analytics.get('shares')}"
    assert analytics.get("followers_count") in (0, None), f"Followers must not be fabricated, got {analytics.get('followers_count')}"
    assert analytics.get("official_insights_active") is False, "Insights must be inactive for unverified token"
    print(f"Analytics report status: {analytics.get('status')}")
    
    # Verify unverified account truthfully sets official_insights_active = False
    unverified_acc = InstagramAccount(
        username="unverified_test_gym",
        status="AUTHORIZATION_REQUIRED",
        access_token="",
    )
    mgr._accounts["unverified_test_gym"] = unverified_acc
    analytics_unverified = mgr.get_account_analytics("unverified_test_gym")
    assert analytics_unverified["official_insights_active"] is False
    assert analytics_unverified["status"] == "AWAITING_META_AUTHORIZATION"
    
    # Verify account missing insights permission sets official_insights_active = False
    no_perm_acc = InstagramAccount(
        username="no_perm_test_gym",
        status="CONNECTED",
        access_token="some_token",
        permissions=["instagram_basic", "instagram_content_publish"],
    )
    mgr._accounts["no_perm_test_gym"] = no_perm_acc
    analytics_no_perm = mgr.get_account_analytics("no_perm_test_gym")
    assert analytics_no_perm["official_insights_active"] is False
    assert analytics_no_perm["status"] == "INSIGHTS_PERMISSION_PENDING"
    print("[PASS] TEST 6 PASSED: Zero fabrication of follower counts, view numbers, or Insights.")


def test_7_disk_storage_and_dpapi_encryption():
    print("\n--- TEST 7: Disk Storage & DPAPI Encryption Audit ---")
    assert ACCOUNTS_FILE.exists(), f"Accounts file {ACCOUNTS_FILE} must exist"
    
    with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
        disk_data = json.load(f)
        
    assert "mentos_life_gym" in disk_data, "mentos_life_gym must be registered"
    acc_record = disk_data["mentos_life_gym"]
    
    assert acc_record["instagram_user_id"] == AUTHORITATIVE_INSTAGRAM_ID, (
        f"Stored ID must be {AUTHORITATIVE_INSTAGRAM_ID}, got {acc_record['instagram_user_id']}"
    )
    assert acc_record["instagram_user_id"] not in KNOWN_PLACEHOLDER_IDS, "Stored ID is a known placeholder!"
    assert is_encrypted(acc_record["access_token"]), "Stored access_token MUST be encrypted with Windows DPAPI!"
    assert not acc_record["access_token"].startswith("EAABw"), "Plaintext token must NEVER be written to disk!"
    
    # Test decryption in memory
    decrypted = decrypt_token(acc_record["access_token"])
    assert decrypted.startswith("EAABw"), "Decrypted token must recover original payload in memory"
    print(f"[PASS] Authoritative Instagram ID: {acc_record['instagram_user_id']}")
    print(f"[PASS] DPAPI Token ciphertext prefix: {acc_record['access_token'][:30]}...")
    print("[PASS] TEST 7 PASSED: Persistent account record correctly uses authoritative ID and DPAPI encryption.")


if __name__ == "__main__":
    print("======================================================================")
    print("J.A.R.V.I.S. Mark LVI - INSTAGRAM ACCOUNT IDENTITY VERIFICATION SUITE")
    print("======================================================================")
    
    test_1_no_placeholder_substitution()
    test_2_live_meta_api_truthful_reporting()
    test_3_authoritative_response_verification()
    test_4_reel_generation_strictly_targets_mentos_life_gym()
    test_5_mismatched_drafts_publication_blocked()
    test_6_zero_analytics_fabrication()
    test_7_disk_storage_and_dpapi_encryption()
    
    print("\n======================================================================")
    print("ALL 7 IDENTITY VERIFICATION & SECURITY CHECKS PASSED SUCCESSFULLY!")
    print("======================================================================")
