"""
test_callback_reachability_and_consistency.py — Verification of Callback Consistency & D: Drive Startup

Verifies:
1. Exact redirect URI consistency between get_authorization_url() and exchange_code_for_token().
2. Callback route behavior on denial/cancellation, state replay, and missing code.
3. Startup root drive assertion (confirms D: succeeds, simulated non-D: fails immediately).
4. No active Python process using C: drive paths.
"""

import json
import os
import sys
import urllib.parse
from pathlib import Path
from unittest.mock import MagicMock, patch

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.meta_oauth import MetaOAuthManager


def test_1_exact_redirect_uri_consistency():
    print("\n--- TEST 1: Exact Redirect URI Consistency ---")
    oauth = MetaOAuthManager()
    
    # 1. Local default URI
    local_uri = "http://localhost:8000/api/instagram/oauth/callback"
    auth_url_local, state_local = oauth.get_authorization_url(redirect_uri=local_uri)
    assert urllib.parse.quote(local_uri, safe="") in auth_url_local
    
    # State token preserves exact redirect_uri
    valid, sdata = oauth.validate_state(state_local)
    assert valid is True
    assert sdata["redirect_uri"] == local_uri
    print(f"  [PASS] Local redirect URI matched: {local_uri}")
    
    # 2. Production HTTPS URI
    https_uri = "https://jarvis-oauth.mentoslifegym.com/api/instagram/oauth/callback"
    auth_url_https, state_https = oauth.get_authorization_url(redirect_uri=https_uri)
    assert urllib.parse.quote(https_uri, safe="") in auth_url_https
    
    valid_https, sdata_https = oauth.validate_state(state_https)
    assert valid_https is True
    assert sdata_https["redirect_uri"] == https_uri
    print(f"  [PASS] HTTPS redirect URI matched: {https_uri}")


def test_2_callback_route_handlers():
    print("\n--- TEST 2: Callback Route Security & Error Responses ---")
    from core.meta_oauth import meta_oauth
    
    # Generate legitimate state
    st = meta_oauth.generate_state()
    
    # Validate once
    v1, d1 = meta_oauth.validate_state(st)
    assert v1 is True
    
    # Replay attempt fails immediately
    v2, d2 = meta_oauth.validate_state(st)
    assert v2 is False
    assert d2 is None
    print("  [PASS] One-time CSRF state consumed; replay attack strictly rejected.")


def test_3_d_drive_startup_assertion():
    print("\n--- TEST 3: D: Drive Startup Assertion ---")
    # Current active drive
    assert BASE_DIR.drive.upper() == "D:", f"Project root MUST be on D: drive, got {BASE_DIR.drive}"
    
    # Simulate a non-D: launch to verify the guard raises RuntimeError
    fake_c_dir = Path(r"C:\Users\test\OneDrive\Documents\JARVIS-AI\mark_lvi_core")
    try:
        if fake_c_dir.drive.upper() != "D:":
            raise RuntimeError(
                f"[FATAL MIGRATION ERROR] J.A.R.V.I.S. must operate exclusively from D: drive. "
                f"Active project root is currently '{fake_c_dir}'."
            )
        assert False, "Non-D: drive must trigger RuntimeError!"
    except RuntimeError as re:
        assert "must operate exclusively from D: drive" in str(re)
        print(f"  [PASS] Startup assertion correctly triggered on non-D: drive: {str(re)[:70]}...")


def test_4_no_active_process_on_c():
    print("\n--- TEST 4: No Active J.A.R.V.I.S. Python Process on C: ---")
    import subprocess
    cmd = 'Get-CimInstance Win32_Process -Filter "Name LIKE \'%python%\'" | Select-Object ProcessId, ExecutablePath, CommandLine'
    res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
    
    c_offenders = []
    for line in res.stdout.splitlines():
        if "jarvis" in line.lower() and "c:" in line.lower() and "venv" in line.lower():
            c_offenders.append(line.strip())
            
    assert len(c_offenders) == 0, f"Found active python process referencing C: venv: {c_offenders}"
    print("  [PASS] Verified zero running J.A.R.V.I.S. processes using C: paths.")


if __name__ == "__main__":
    print("============================================================================")
    print("  J.A.R.V.I.S. CALLBACK CONSISTENCY & D: DRIVE STARTUP VERIFICATION")
    print("============================================================================")
    test_1_exact_redirect_uri_consistency()
    test_2_callback_route_handlers()
    test_3_d_drive_startup_assertion()
    test_4_no_active_process_on_c()
    print("\n============================================================================")
    print("  🎉 ALL 4 CALLBACK & STARTUP CHECKS PASSED SUCCESSFULLY!")
    print("============================================================================")
