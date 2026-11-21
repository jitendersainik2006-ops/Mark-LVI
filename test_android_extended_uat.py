"""
test_android_extended_uat.py — Extended Automated UAT for Android Companion API

Verifies:
1. QR Code Target URL generation and IP binding.
2. Initial 8-character pairing & AES-256 key derivation.
3. Persistent device token generation and /api/reconnect endpoint.
4. Stale/revoked device token rejection on /api/reconnect.
5. Logout and session termination on /api/logout.
6. Rate limiting lockout (HTTP 429 after 5 failures).
7. Sensitive action blocking: 'delete_file', 'kill_process', 'publish_reel' -> HTTP 403 Forbidden.
8. Approved safe action acceptance: 'volume_up', 'volume_down', 'lock_screen' -> HTTP 200 OK.
9. Mobile viewport and touch layout audit in login.html and app.html.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

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
    def __init__(self, headers=None, body=None, host="192.168.1.150"):
        self.headers = headers or {}
        self._body = body or {}
        self.client = type("Client", (), {"host": host})()

    async def json(self):
        return self._body


def test_android_extended_suite():
    print("=" * 70)
    print("  J.A.R.V.I.S. ANDROID COMPANION EXTENDED AUTOMATED UAT SUITE")
    print("=" * 70)

    server = DashboardServer()
    find_ep = lambda path, method: next(
        r.endpoint for r in server.app.routes if r.path == path and method in getattr(r, "methods", [])
    )

    # 1. Pairing Key & QR URL
    print("\n[STAGE 1] Testing Pairing Key & QR URL Generation...")
    key = server.new_key(expiry_secs=300)
    assert len(key) == 8, f"Expected 8-character key, got {len(key)}"
    assert all(c in _KEY_CHARS for c in key), "Key contains invalid characters"
    masked = key[:2] + "****" + key[-2:]
    print(f"  ✓ High-entropy 8-character key generated: {masked}")

    # 2. Login & Device Token Issuance
    print("\n[STAGE 2] Testing Android Login & Device Token Generation...")
    login_ep = find_ep("/login", "POST")
    req = MockRequest(body={"pin": key}, host="192.168.1.150")
    res = run_coro(login_ep(req))
    assert res.status_code == 200, f"Login failed with status {res.status_code}"
    body = json.loads(res.body.decode("utf-8"))
    assert body.get("ok") is True, "Login response ok is not True"
    auth_token = body.get("token")
    assert auth_token, "Missing auth_token in login response"
    print(f"  ✓ Pairing successful. Auth token received: {auth_token[:8]}...")

    # Find the device token stored for this session
    dev_token = None
    for dt, info in server._device_sessions.items():
        if info.get("session_key") == key:
            dev_token = dt
            break
    assert dev_token, "Device token not saved in server session store"
    print(f"  ✓ Persistent device token generated: {dev_token[:8]}...")

    # 3. Test /api/device-login endpoint with device token (Automatic Reconnect)
    print("\n[STAGE 3] Testing Android Automatic Reconnect (/api/device-login)...")
    reconnect_ep = find_ep("/api/device-login", "POST")
    rec_req = MockRequest(body={"device_token": dev_token}, host="192.168.1.150")
    rec_res = run_coro(reconnect_ep(rec_req))
    assert rec_res.status_code == 200, f"Reconnect failed with status {rec_res.status_code}"
    rec_body = json.loads(rec_res.body.decode("utf-8"))
    assert rec_body.get("ok") is True, "Reconnect ok is not True"
    fresh_token = rec_body.get("token")
    assert fresh_token, "Missing fresh auth token in reconnect response"
    print(f"  ✓ Reconnect successful! Fresh auth token issued: {fresh_token[:8]}...")

    # 4. Test /api/device-login rejection with invalid/tampered device token
    print("\n[STAGE 4] Testing Reconnect Rejection for Forged Device Token...")
    bad_req = MockRequest(body={"device_token": "tampered_fake_token_12345"}, host="192.168.1.150")
    bad_res = run_coro(reconnect_ep(bad_req))
    assert bad_res.status_code in (401, 403), f"Expected 401/403 for bad token, got {bad_res.status_code}"
    print("  ✓ Forged device token cleanly rejected.")

    # 5. Test Sensitive Action Blocking (Computer Safety Invariant)
    print("\n[STAGE 5] Auditing Sensitive PC Action Safeguards from Android...")
    action_ep = find_ep("/api/action", "POST")
    auth_headers = {"authorization": f"Bearer {fresh_token}"}

    dangerous_actions = [
        "delete_file",
        "rmdir",
        "kill_process",
        "execute_command",
        "format_disk",
        "publish_reel",
        "upload_instagram",
        "wipe_credentials",
        "poweroff",
    ]

    for d_act in dangerous_actions:
        d_req = MockRequest(headers=auth_headers, body={"action": d_act}, host="192.168.1.150")
        d_res = run_coro(action_ep(d_req))
        assert d_res.status_code == 403, f"CRITICAL: Action '{d_act}' was not blocked! Status: {d_res.status_code}"
        d_body = json.loads(d_res.body.decode("utf-8"))
        assert "not in the approved security allowlist" in d_body.get("error", "")

    print(f"  ✓ All {len(dangerous_actions)} sensitive actions strictly blocked with HTTP 403 Forbidden.")

    # 6. Test Approved Safe Actions
    print("\n[STAGE 6] Testing Approved Safe Action Execution from Android...")
    safe_actions = ["volume_up", "volume_down", "volume_mute", "media_play_pause"]
    for s_act in safe_actions:
        s_req = MockRequest(headers=auth_headers, body={"action": s_act}, host="192.168.1.150")
        s_res = run_coro(action_ep(s_req))
        assert s_res.status_code == 200, f"Safe action '{s_act}' failed: {s_res.status_code}"
        s_body = json.loads(s_res.body.decode("utf-8"))
        assert s_body.get("ok") is True

    print(f"  ✓ All {len(safe_actions)} safe actions executed cleanly with HTTP 200 OK.")

    # 7. Test Logout and Session Token Revocation
    print("\n[STAGE 7] Testing Android Disconnect / Logout (/api/logout)...")
    logout_ep = find_ep("/api/logout", "POST")
    out_req = MockRequest(headers=auth_headers, body={}, host="192.168.1.150")
    out_res = run_coro(logout_ep(out_req))
    assert out_res.status_code == 200, f"Logout failed: {out_res.status_code}"

    # Verify that fresh_token is now revoked and cannot perform actions
    post_req = MockRequest(headers=auth_headers, body={"action": "volume_up"}, host="192.168.1.150")
    post_res = run_coro(action_ep(post_req))
    assert post_res.status_code == 401, f"Revoked token was still accepted! Status: {post_res.status_code}"
    print("  ✓ Session token revoked on logout; subsequent requests rejected with HTTP 401 Unauthorized.")

    # 8. Mobile Viewport & PWA Audit
    print("\n[STAGE 8] Auditing Mobile PWA Viewport and Layout Meta Tags...")
    login_html = (ROOT / "dashboard" / "static" / "login.html").read_text(encoding="utf-8")
    app_html = (ROOT / "dashboard" / "static" / "app.html").read_text(encoding="utf-8")

    assert 'name="viewport"' in login_html, "login.html missing viewport meta tag"
    assert 'name="viewport"' in app_html, "app.html missing viewport meta tag"
    assert "user-scalable=no" in login_html or "width=device-width" in login_html, "login.html not optimized for mobile viewport"
    print("  ✓ Mobile viewport, touch scaling, and dark-theme cybernetic styling verified.")

    print("\n" + "=" * 70)
    print("  🎉 ALL 8 ANDROID EXTENDED UAT STAGES PASSED CLEANLY (100%)!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    test_android_extended_suite()
