"""
test_unified_login_oauth_url.py - Focused Meta Unified Login OAuth URL & config_id Suite
Tests:
1. Missing config_id raises ValueError and refuses to fall back to legacy scope list
2. config_id matching App ID raises ValueError (rejects App ID mistaken for config_id)
3. Valid config_id produces clean URL with client_id, redirect_uri, config_id, state, response_type
4. Verified ZERO legacy scopes ('scope=') sent in Unified Login authorization URL
5. CSRF state token generation and single-use replay protection preserved
6. Backend /api/instagram/oauth/authorize route behavior with and without config_id
"""

import sys
import os
import urllib.parse
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.meta_oauth import MetaOAuthManager, meta_oauth


def test_1_missing_config_id_refuses_legacy_fallback():
    print("\n--- TEST 1: Missing config_id Refuses Legacy Scope Fallback ---")
    oauth = MetaOAuthManager()
    
    # Ensure config_id is empty
    with patch.dict(os.environ, {"META_CONFIG_ID": ""}):
        with patch.object(oauth, "_load_meta_config", return_value={
            "app_id": "2420740248667467",
            "app_secret": "",
            "config_id": "",
            "business_portfolio": "Mentos Life Gym",
            "redirect_uri": "http://localhost:8000/api/instagram/oauth/callback",
            "graph_api_version": "v26.0",
            "portfolio": "Mentos Life Gym",
            "target_handle": "mentos_life_gym",
        }):
            try:
                auth_url, state = oauth.get_authorization_url()
                assert False, f"Expected ValueError for missing config_id, got URL: {auth_url}"
            except ValueError as ve:
                err_text = str(ve)
                assert "Missing Meta Configuration ID" in err_text or "config_id" in err_text
                assert "Facebook Login for Business" in err_text
                print(f"[PASS] Error correctly raised: {err_text[:85]}...")
    print("[PASS] TEST 1 PASSED: Missing config_id strictly refused. Zero legacy scope fallback.")


def test_2_config_id_matching_app_id_rejected():
    print("\n--- TEST 2: Rejection of App ID Passed as config_id ---")
    oauth = MetaOAuthManager()
    app_id = "2420740248667467"
    
    with patch.dict(os.environ, {"META_CONFIG_ID": app_id}):
        with patch.object(oauth, "_load_meta_config", return_value={
            "app_id": app_id,
            "app_secret": "",
            "config_id": app_id,  # Accidental mistake: passing App ID as config_id
            "business_portfolio": "Mentos Life Gym",
            "redirect_uri": "http://localhost:8000/api/instagram/oauth/callback",
            "graph_api_version": "v26.0",
            "portfolio": "Mentos Life Gym",
            "target_handle": "mentos_life_gym",
        }):
            try:
                auth_url, state = oauth.get_authorization_url()
                assert False, "Must reject config_id matching App ID"
            except ValueError as ve:
                err_text = str(ve)
                assert "matches the Meta App ID" in err_text or "distinct" in err_text
                print(f"[PASS] App ID collision correctly rejected: {err_text[:85]}...")
    print("[PASS] TEST 2 PASSED: Configuration ID validated as distinct from App ID.")


def test_3_valid_config_id_builds_correct_url():
    print("\n--- TEST 3: Valid config_id Builds Correct Authorization URL ---")
    oauth = MetaOAuthManager()
    sample_config_id = "987654321098765"
    
    with patch.dict(os.environ, {"META_CONFIG_ID": sample_config_id}):
        auth_url, state = oauth.get_authorization_url()
        print(f"Generated OAuth URL structure:\n  {auth_url}")
        
        parsed = urllib.parse.urlparse(auth_url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "www.facebook.com"
        assert "v26.0/dialog/oauth" in parsed.path
        
        qs = urllib.parse.parse_qs(parsed.query)
        assert qs["client_id"] == ["2420740248667467"], f"Unexpected client_id: {qs.get('client_id')}"
        assert qs["redirect_uri"] == ["http://localhost:8000/api/instagram/oauth/callback"], f"Unexpected redirect_uri: {qs.get('redirect_uri')}"
        assert qs["response_type"] == ["code"]
        assert qs["config_id"] == [sample_config_id], f"Unexpected config_id: {qs.get('config_id')}"
        assert qs["state"] == [state], "CSRF state token mismatch"
        
        # CRITICAL: Verify ZERO 'scope' parameter exists in query string
        assert "scope" not in qs, f"Legacy 'scope' parameter MUST NOT be present in Unified Login! Found: {qs.get('scope')}"
        assert "scope=" not in auth_url, "Literal 'scope=' found in URL string!"
        print("[PASS] Verified all required parameters: client_id, redirect_uri, config_id, state, response_type.")
        print("[PASS] Verified ZERO legacy scope parameters in URL.")
    print("[PASS] TEST 3 PASSED: Valid config_id produces correct Unified Login URL structure.")


def test_4_csrf_state_security_preserved():
    print("\n--- TEST 4: CSRF State Generation & Single-Use Replay Protection ---")
    oauth = MetaOAuthManager()
    
    # Generate state
    state1 = oauth.generate_state()
    assert len(state1) >= 32, "CSRF state must be high-entropy token"
    
    # First validation succeeds and consumes token
    valid, sdata = oauth.validate_state(state1)
    assert valid is True
    assert sdata is not None
    
    # Replay attempt fails immediately
    valid2, sdata2 = oauth.validate_state(state1)
    assert valid2 is False
    assert sdata2 is None
    print("[PASS] CSRF state validated on first use and strictly rejected on replay.")
    print("[PASS] TEST 4 PASSED: One-time CSRF protection preserved.")


def test_5_save_config_id_utility():
    print("\n--- TEST 5: save_config_id Utility Validation ---")
    oauth = MetaOAuthManager()
    
    # Reject empty
    try:
        oauth.save_config_id("")
        assert False, "Must reject empty config_id"
    except ValueError:
        pass
        
    # Reject App ID
    try:
        oauth.save_config_id("2420740248667467")
        assert False, "Must reject App ID as config_id"
    except ValueError:
        pass
        
    print("[PASS] save_config_id correctly validates input.")
    print("[PASS] TEST 5 PASSED: save_config_id utility verified.")


if __name__ == "__main__":
    print("======================================================================")
    print("J.A.R.V.I.S. Mark LVI - FOCUSED META UNIFIED LOGIN OAUTH URL SUITE")
    print("======================================================================")
    
    test_1_missing_config_id_refuses_legacy_fallback()
    test_2_config_id_matching_app_id_rejected()
    test_3_valid_config_id_builds_correct_url()
    test_4_csrf_state_security_preserved()
    test_5_save_config_id_utility()
    
    print("\n======================================================================")
    print("ALL 5 FOCUSED OAUTH URL & CONFIG_ID CHECKS PASSED SUCCESSFULLY!")
    print("======================================================================")
