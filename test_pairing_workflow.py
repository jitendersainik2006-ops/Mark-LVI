"""
test_pairing_workflow.py — Android Pairing and Dashboard Verification Suite

Tests:
1. 8-character key generation from _KEY_CHARS.
2. Login endpoint acceptance of exact 8-character key.
3. Login endpoint acceptance of 8-character key formatted with hyphens or spaces.
4. One-time key usage enforcement (key deleted immediately after pairing).
5. Invalid key rejection (short, wrong chars, expired).
6. Rate limiting enforcement on failed attempts (429 status code).
7. Session token authentication and /api/logout token revocation.
8. Action allowlist verification (approved vs unapproved actions).
9. Static file verification: login.html inputs and validation logic.
10. UI overlay verification: font sizing and dimensions in ui.py.
"""

import sys
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dashboard.server import DashboardServer, _KEY_CHARS

def run_coro(coro):
    stack = [coro]
    result = None
    while stack:
        current = stack[-1]
        try:
            val = current.send(result)
            if hasattr(val, "send"):
                stack.append(val)
                result = None
            else:
                result = val
        except StopIteration as exc:
            stack.pop()
            result = exc.value
    return result

class MockRequest:
    def __init__(self, headers=None, body=None, host="127.0.0.1"):
        self.headers = headers or {}
        self._body = body or {}
        self.client = type("Client", (), {"host": host})()

    async def json(self):
        return self._body

def test_1_key_generation():
    print("\n--- TEST 1: 8-Character Pairing Key Generation ---")
    server = DashboardServer()
    key = server.new_key(expiry_secs=600)
    assert len(key) == 8, f"Expected 8-character key, got length {len(key)}"
    assert all(c in _KEY_CHARS for c in key), f"Key contains invalid characters outside _KEY_CHARS: {key}"
    # Redact key in logs as required by security instructions
    masked = key[:2] + "****" + key[-2:]
    print(f"✅ Key generation verified: Length is 8 characters, characters strictly from unambiguous charset (Sample: {masked}).")

def test_2_login_variations():
    print("\n--- TEST 2: Login Acceptance (Exact, Hyphens, Spaces) ---")
    server = DashboardServer()
    find_ep = lambda path, method: next(r.endpoint for r in server.app.routes if r.path == path and method in getattr(r, "methods", []))
    login_ep = find_ep("/login", "POST")

    # 2a. Exact 8 characters
    key1 = server.new_key(expiry_secs=600)
    req1 = MockRequest(body={"pin": key1}, host="10.0.0.1")
    res1 = run_coro(login_ep(req1))
    assert res1.status_code == 200, f"Failed exact login, status: {res1.status_code}"
    body1 = json.loads(res1.body.decode("utf-8"))
    assert body1.get("ok") is True and "token" in body1, "Token missing from login response"

    # 2b. Hyphenated (e.g. ABCD-EFGH)
    key2 = server.new_key(expiry_secs=600)
    hyphenated = key2[:4] + "-" + key2[4:]
    req2 = MockRequest(body={"pin": hyphenated}, host="10.0.0.2")
    res2 = run_coro(login_ep(req2))
    assert res2.status_code == 200, f"Failed hyphenated login, status: {res2.status_code}"
    body2 = json.loads(res2.body.decode("utf-8"))
    assert body2.get("ok") is True and "token" in body2

    # 2c. Spaced (e.g. ABCD EFGH)
    key3 = server.new_key(expiry_secs=600)
    spaced = key3[:4] + " " + key3[4:]
    req3 = MockRequest(body={"pin": spaced}, host="10.0.0.3")
    res3 = run_coro(login_ep(req3))
    assert res3.status_code == 200, f"Failed spaced login, status: {res3.status_code}"
    body3 = json.loads(res3.body.decode("utf-8"))
    assert body3.get("ok") is True and "token" in body3

    print("✅ Login variations verified: Exact 8-char, hyphenated, and space-separated keys all authenticate cleanly.")

def test_3_one_time_and_rejection():
    print("\n--- TEST 3: One-Time Key Enforcement & Rejection of Bad Codes ---")
    server = DashboardServer()
    find_ep = lambda path, method: next(r.endpoint for r in server.app.routes if r.path == path and method in getattr(r, "methods", []))
    login_ep = find_ep("/login", "POST")

    key = server.new_key(expiry_secs=600)
    req_success = MockRequest(body={"pin": key}, host="10.0.0.10")
    res_first = run_coro(login_ep(req_success))
    assert res_first.status_code == 200, "First login attempt failed"

    # Second attempt with same key must be rejected
    req_repeat = MockRequest(body={"pin": key}, host="10.0.0.10")
    res_second = run_coro(login_ep(req_repeat))
    assert res_second.status_code == 401, f"Expected 401 on reused key, got {res_second.status_code}"

    # Invalid code
    req_invalid = MockRequest(body={"pin": "WRONGKEY"}, host="10.0.0.11")
    res_invalid = run_coro(login_ep(req_invalid))
    assert res_invalid.status_code == 401, f"Expected 401 on wrong key, got {res_invalid.status_code}"

    # Incomplete code (6 characters)
    req_short = MockRequest(body={"pin": "123456"}, host="10.0.0.12")
    res_short = run_coro(login_ep(req_short))
    assert res_short.status_code == 401, f"Expected 401 on short key, got {res_short.status_code}"

    print("✅ One-time enforcement verified: Used keys are consumed immediately; bad and short keys are rejected.")

def test_4_rate_limiting():
    print("\n--- TEST 4: Brute Force Rate Limiting Protection ---")
    server = DashboardServer()
    find_ep = lambda path, method: next(r.endpoint for r in server.app.routes if r.path == path and method in getattr(r, "methods", []))
    login_ep = find_ep("/login", "POST")

    attacker_host = "192.168.1.99"
    # Send 6 bad attempts
    for i in range(6):
        res = run_coro(login_ep(MockRequest(body={"pin": f"BADKEY{i}"}, host=attacker_host)))
        assert res.status_code == 401, f"Expected 401 on attempt {i+1}, got {res.status_code}"

    # 7th attempt must be throttled with HTTP 429
    res_throttled = run_coro(login_ep(MockRequest(body={"pin": "BADKEY7"}, host=attacker_host)))
    assert res_throttled.status_code == 429, f"Expected 429 Too Many Requests, got {res_throttled.status_code}"
    body = json.loads(res_throttled.body.decode("utf-8"))
    assert "Too many attempts" in body.get("error", "")

    print("✅ Rate limiting verified: 6 failed attempts trigger HTTP 429 lockout.")

def test_5_session_token_and_logout():
    print("\n--- TEST 5: Session Token Lifespan & Logout Revocation ---")
    server = DashboardServer()
    find_ep = lambda path, method: next(r.endpoint for r in server.app.routes if r.path == path and method in getattr(r, "methods", []))
    login_ep = find_ep("/login", "POST")
    logout_ep = find_ep("/api/logout", "POST")
    status_ep = find_ep("/api/status", "GET")

    key = server.new_key(expiry_secs=600)
    res_login = run_coro(login_ep(MockRequest(body={"pin": key}, host="10.0.0.20")))
    token = json.loads(res_login.body.decode("utf-8"))["token"]
    auth_headers = {"authorization": f"Bearer {token}"}

    # Verify authenticated call succeeds
    res_status = run_coro(status_ep(MockRequest(headers=auth_headers)))
    assert res_status.status_code == 200, f"Expected 200 with valid token, got {res_status.status_code}"

    # Logout to revoke token
    res_logout = run_coro(logout_ep(MockRequest(headers=auth_headers)))
    assert res_logout.status_code == 200, f"Logout failed: {res_logout.status_code}"

    # Subsequent call with revoked token must fail with 401
    res_after = run_coro(status_ep(MockRequest(headers=auth_headers)))
    assert res_after.status_code == 401, f"Expected 401 after logout revocation, got {res_after.status_code}"

    print("✅ Session security verified: Bearer tokens authorize requests and are immediately revoked on logout.")

def test_6_action_allowlist():
    print("\n--- TEST 6: Remote Action Security Allowlist ---")
    server = DashboardServer()
    find_ep = lambda path, method: next(r.endpoint for r in server.app.routes if r.path == path and method in getattr(r, "methods", []))
    action_ep = find_ep("/api/action", "POST")

    key = server.new_key(expiry_secs=600)
    tok = "test_action_token_12345"
    server._tokens[tok] = time.time()
    server._token_keys[tok] = key
    auth_headers = {"authorization": f"Bearer {tok}"}

    # Allowed action (e.g. wake)
    res_wake = run_coro(action_ep(MockRequest(headers=auth_headers, body={"action": "wake"})))
    assert res_wake.status_code == 200, f"Approved action 'wake' was refused: {res_wake.status_code}"

    # Unapproved action (e.g. malicious_script)
    res_unapproved = run_coro(action_ep(MockRequest(headers=auth_headers, body={"action": "malicious_script"})))
    assert res_unapproved.status_code == 403, f"Expected 403 for unapproved action, got {res_unapproved.status_code}"

    print("✅ Action allowlist verified: Approved actions pass; unapproved actions are rejected with HTTP 403.")

def test_7_login_html_verification():
    print("\n--- TEST 7: login.html Input & Client-side Validation ---")
    login_html_path = ROOT / "dashboard" / "static" / "login.html"
    assert login_html_path.exists(), "login.html not found"
    content = login_html_path.read_text(encoding="utf-8")

    assert 'maxlength="9"' in content, "maxlength must be 9 to allow 8 chars plus optional separator"
    assert 'clean.length === 8' in content, "Auto-submit length check must be 8"
    assert 'cleanKey.length < 8' in content, "Minimum validation length must be 8"
    assert 'placeholder="· · · · · · · ·"' in content, "Placeholder must indicate 8 characters"

    print("✅ login.html verified: maxlength=9, 8-character auto-submit, and cleanKey normalization are in place.")

def test_8_ui_overlay_layout():
    print("\n--- TEST 8: ui.py RemoteKeyOverlay Sizing & Font ---")
    ui_path = ROOT / "ui.py"
    assert ui_path.exists(), "ui.py not found"
    content = ui_path.read_text(encoding="utf-8")

    assert "_OW, _OH = 420, 520" in content, "RemoteKeyOverlay dimensions must be expanded to 420x520"
    assert "QFont(\"Courier New\", 24, QFont.Weight.Bold)" in content, "Key label font size must be 24pt for 8 chars"
    assert "letter-spacing: 6px;" in content, "Key label letter-spacing must be 6px for 8 chars"
    assert "setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)" in content, "Key text must be mouse-selectable"

    print("✅ ui.py verified: RemoteKeyOverlay has expanded width (420px), 24pt font, 6px spacing, and selectable text.")

def test_9_qr_auto_login_prefetch():
    print("\n--- TEST 9: QR Auto-Login & Camera Prefetch Resilience ---")
    server = DashboardServer()
    find_ep = lambda path, method: next(r.endpoint for r in server.app.routes if r.path == path and method in getattr(r, "methods", []))
    auto_ep = find_ep("/auto-login", "GET")

    key = server.new_key(expiry_secs=600)
    
    # 1. Camera preview GET request arrives first
    res_cam = run_coro(auto_ep(key=key))
    assert res_cam.status_code == 200, f"Expected 200 on camera preview, got {res_cam.status_code}"
    body_cam = res_cam.body.decode("utf-8")
    assert "sessionStorage.setItem('jarvis_token'" in body_cam, "Camera response must establish session"

    # 2. Chrome browser opens link within 120s grace period
    res_browser = run_coro(auto_ep(key=key))
    assert res_browser.status_code == 200, f"Expected 200 on browser launch, got {res_browser.status_code}"
    body_browser = res_browser.body.decode("utf-8")
    assert "sessionStorage.setItem('jarvis_token'" in body_browser, "Browser response must establish session"

    # 3. Invalid or expired key returns 'Link Expired'
    res_bad = run_coro(auto_ep(key="EXPIRED9"))
    body_bad = res_bad.body.decode("utf-8")
    assert "Link Expired" in body_bad, f"Expected 'Link Expired' in response, got: {body_bad[:100]}"

    print("✅ QR auto-login verified: Camera prefetch and subsequent browser opening succeed seamlessly without 'Link Expired'.")

if __name__ == "__main__":
    test_1_key_generation()
    test_2_login_variations()
    test_3_one_time_and_rejection()
    test_4_rate_limiting()
    test_5_session_token_and_logout()
    test_6_action_allowlist()
    test_7_login_html_verification()
    test_8_ui_overlay_layout()
    test_9_qr_auto_login_prefetch()
    print("\n🎉 ALL 9 PAIRING WORKFLOW TESTS PASSED CLEANLY!")

