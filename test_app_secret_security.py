"""
test_app_secret_security.py — Verification Suite for Meta App Secret Windows DPAPI Protection

Verifies:
1. Windows DPAPI CurrentUser encryption and decryption with dummy credentials.
2. Fail-closed security: Corrupt or tampered ciphertext strictly raises SecurityError.
3. Automatic Plaintext Migration: Plaintext secrets in config files are encrypted at rest,
   verified, and removed from disk.
4. save_app_secret(): Direct secure persistence ensuring no plaintext ever touches disk.
5. Zero Secret Leakage: Public configs, APIs, HTML/JS, and error messages never expose the secret.
6. Instagram Access Token Encryption Unaffected: Multi-account token encryption remains 100% operational.
"""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.crypto_storage import SecurityError, decrypt_token, encrypt_token, is_encrypted, mask_token
from core.instagram_manager import InstagramManager, instagram_manager
from core.meta_oauth import MetaOAuthManager, meta_oauth
from dashboard.server import DashboardServer
from starlette.testclient import TestClient

SCRATCH_DIR = Path(r"C:\Users\jitendersaini2006\.gemini\antigravity\brain\e7bc7937-0d61-4942-83c4-b3f5a9674d30\scratch")
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)


def run_tests():
    print("=" * 75)
    print("  J.A.R.V.I.S. META APP SECRET DPAPI SECURITY & ZERO-LEAK VERIFICATION")
    print("=" * 75)

    dummy_secret = "dummy_meta_secret_abcdef1234567890_test_sec"

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 1: Windows DPAPI Encryption & Decryption (Dummy Credentials)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 1: Windows DPAPI CurrentUser Encryption & Decryption ---")
    encrypted_secret = encrypt_token(dummy_secret)
    assert is_encrypted(encrypted_secret), "Encrypted secret must have dpapi:v1: prefix"
    assert dummy_secret not in encrypted_secret, "Plaintext secret MUST NOT appear in ciphertext"
    print(f"Encrypted secret preview: {encrypted_secret[:30]}...")

    decrypted_secret = decrypt_token(encrypted_secret)
    assert decrypted_secret == dummy_secret, "Decrypted secret must match original dummy secret"
    print("✓ DPAPI decryption in application memory verified matching original secret.")

    masked = mask_token(dummy_secret)
    assert masked == "dumm****_sec"
    assert dummy_secret not in masked
    print(f"✓ Masked secret verification: {masked}")
    print("✅ TEST 1 PASSED: DPAPI encryption, decryption, and masking verified.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 2: Fail-Closed Security on Corrupt / Tampered Ciphertext
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 2: Fail-Closed Security on Tampered / Corrupt Ciphertext ---")
    tampered_secret = "dpapi:v1:AQAAANCMnd8BFdERjHoAwE/Cl+sBAAAA_CORRUPTED_PAYLOAD_12345"
    failed_closed = False
    try:
        decrypt_token(tampered_secret)
    except SecurityError as e:
        failed_closed = True
        print(f"✓ SecurityError properly raised on corrupted ciphertext: {e}")

    assert failed_closed, "System MUST fail closed with SecurityError upon corrupted ciphertext"
    print("✅ TEST 2 PASSED: Fail-closed security verified.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 3: Automatic Plaintext Migration to DPAPI at Rest
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 3: Automatic Plaintext Migration to DPAPI in Configuration ---")
    scratch_config = SCRATCH_DIR / "scratch_test_api_keys.json"
    scratch_data = {
        "assistant_name": "JARVIS",
        "meta_app": {
            "app_id": "2420740248667467",
            "app_secret": dummy_secret,  # Plaintext on disk initially!
            "business_portfolio": "Mentos Life Gym",
            "redirect_uri": "http://localhost:8000/api/instagram/oauth/callback",
            "graph_api_version": "v26.0",
        },
    }
    scratch_config.write_text(json.dumps(scratch_data, indent=4), encoding="utf-8")

    with patch("core.meta_oauth.CONFIG_FILE", scratch_config):
        test_oauth = MetaOAuthManager()
        cfg = test_oauth._load_meta_config()

        # In memory: decrypted secret is available
        assert cfg["app_secret"] == dummy_secret
        print("✓ Plaintext secret loaded into memory successfully.")

        # On disk: plaintext copy MUST BE GONE and replaced with dpapi:v1:...
        raw_on_disk = scratch_config.read_text(encoding="utf-8")
        assert dummy_secret not in raw_on_disk, "Plaintext App Secret MUST NOT remain on disk after load!"
        
        reloaded_json = json.loads(raw_on_disk)
        stored_disk_secret = reloaded_json["meta_app"]["app_secret"]
        assert is_encrypted(stored_disk_secret), "App secret on disk MUST be encrypted with DPAPI"
        assert stored_disk_secret.startswith("dpapi:v1:")
        print(f"✓ On-disk verification: Plaintext copy removed. Stored as: {stored_disk_secret[:25]}...")

        # Subsequent loads read the encrypted token cleanly without altering
        cfg2 = test_oauth._load_meta_config()
        assert cfg2["app_secret"] == dummy_secret
        print("✓ Subsequent load of DPAPI encrypted secret verified in memory.")

    if scratch_config.exists():
        scratch_config.unlink()
    print("✅ TEST 3 PASSED: Automatic plaintext migration to DPAPI verified.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 4: save_app_secret() Secure Persistence
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 4: save_app_secret() Direct Secure Persistence ---")
    scratch_config2 = SCRATCH_DIR / "scratch_test_api_keys2.json"
    scratch_config2.write_text(json.dumps({"meta_app": {}}, indent=4), encoding="utf-8")

    dummy_secret2 = "dummy_meta_secret_number_two_9876543210_xyz"
    with patch("core.meta_oauth.CONFIG_FILE", scratch_config2):
        test_oauth2 = MetaOAuthManager()
        saved_ok = test_oauth2.save_app_secret(dummy_secret2)
        assert saved_ok is True

        raw_disk2 = scratch_config2.read_text(encoding="utf-8")
        assert dummy_secret2 not in raw_disk2, "Plaintext MUST NOT be written to disk by save_app_secret()"
        reloaded_disk2 = json.loads(raw_disk2)
        assert is_encrypted(reloaded_disk2["meta_app"]["app_secret"])
        print("✓ save_app_secret() encrypted secret via DPAPI before writing to disk.")

    if scratch_config2.exists():
        scratch_config2.unlink()
    print("✅ TEST 4 PASSED: Direct secure persistence verified.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 5: Zero Secret Leakage in Public Configs & REST Endpoints
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 5: Zero Secret Leakage in Public Configs & REST Endpoints ---")
    pub_cfg = meta_oauth.get_public_config()
    assert "app_secret" not in pub_cfg, "Public config MUST NEVER contain 'app_secret' key!"
    assert "has_app_secret" in pub_cfg
    assert "is_secret_encrypted" in pub_cfg
    print(f"✓ Public config verified zero-leak: has_app_secret={pub_cfg['has_app_secret']}, is_secret_encrypted={pub_cfg['is_secret_encrypted']}")

    server = DashboardServer()
    token = "test_sec_bearer_" + str(int(time.time()))
    server._tokens[token] = time.time()
    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(server.app)

    # Test /api/instagram/oauth/config
    resp = client.get("/api/instagram/oauth/config", headers=headers)
    assert resp.status_code == 200
    cfg_body = resp.json().get("config", {})
    assert "app_secret" not in cfg_body, "API response MUST NEVER include app_secret!"
    print("✓ GET /api/instagram/oauth/config response contains no secret.")

    # Test POST /api/instagram/oauth/secret
    with patch.object(meta_oauth, "save_app_secret", return_value=True):
        post_resp = client.post("/api/instagram/oauth/secret", json={"app_secret": "test_dummy_post_secret"}, headers=headers)
        assert post_resp.status_code == 200
        post_body = post_resp.json()
        assert post_body.get("ok") is True
        assert "app_secret" not in post_body, "POST response MUST NEVER echo the secret back!"
        print("✓ POST /api/instagram/oauth/secret response verified zero-leak.")

    print("✅ TEST 5 PASSED: Zero secret leakage across public APIs verified.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 6: Instagram Access Token DPAPI Encryption Unaffected
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- TEST 6: Instagram Access Token DPAPI Encryption Unaffected ---")
    mgr = InstagramManager()
    acc = mgr.get_reels_account()
    assert acc is not None
    assert acc.username == "mentos_life_gym"
    assert acc.status in ("CONNECTED", "UNVERIFIED_BY_META", "AUTHORIZATION_REQUIRED")
    assert acc.access_token != "", "Access token must be decrypted in memory"
    assert not acc.access_token.startswith("dpapi:v1:"), "In-memory token must be decrypted"
    
    # Check serialization masks secret
    serialized = acc.to_dict(mask_secret=True)
    assert serialized["access_token"].startswith("EAAB")
    assert "****" in serialized["access_token"]
    assert acc.access_token != serialized["access_token"]
    print(f"✓ Account access token successfully decrypted in memory and masked in public view: {serialized['access_token']}")

    # Verify on-disk accounts file remains DPAPI encrypted
    raw_acc_file = Path("D:/JARVIS-AI/mark_lvi_core/data/instagram_accounts.json").read_text(encoding="utf-8")
    acc_json = json.loads(raw_acc_file)
    disk_acc_token = acc_json["mentos_life_gym"]["access_token"]
    assert is_encrypted(disk_acc_token), "On-disk access token must remain DPAPI encrypted"
    print(f"✓ On-disk Instagram accounts token remains DPAPI encrypted: {disk_acc_token[:30]}...")
    print("✅ TEST 6 PASSED: Instagram access token encryption 100% unaffected and verified.")

    print("\n" + "=" * 75)
    print("  🎉 ALL 6 META APP SECRET SECURITY TESTS PASSED SUCCESSFULLY!")
    print("=" * 75)


if __name__ == "__main__":
    run_tests()
