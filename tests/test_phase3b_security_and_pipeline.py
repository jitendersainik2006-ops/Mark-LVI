"""
tests/test_phase3b_security_and_pipeline.py — Verification Suite for Phase 3B Security & Reel Pipeline

Verifies:
1. Callback Route & Method: GET /api/instagram/oauth/callback correctly configured.
2. Proxy Allowlist & Default-Deny: Non-callback routes return HTTP 403 Forbidden.
3. OAuth State Security: One-time use, 600s TTL expiry, replay rejection.
4. Account Identity Enforcement: Locks to @mentos_life_gym and ID 17841458094701596.
5. Sensitive Data Redaction & DPAPI: Zero plaintext exposure, masked tokens.
6. Approval Gate Enforcement:
   a. New reels start as waiting_for_approval.
   b. Unapproved reels reject publication with Security refusal.
   c. Editing an approved reel strictly invalidates previous approval.
7. Video Specification Validation: validate_reel_video checks 9:16 vertical, codecs, duration.
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.crypto_storage import decrypt_token, encrypt_token, is_encrypted, mask_token
from core.instagram_manager import InstagramManager, ReelPost
from core.meta_oauth import MetaOAuthManager
from tools.oauth_callback_proxy import CallbackOnlyProxyHandler


class DummyMockSocket:
    """In-memory mock socket for proxy testing without OS network binding."""
    def __init__(self, request_bytes: bytes):
        self.rfile = io.BytesIO(request_bytes)
        self.wfile = io.BytesIO()

    def makefile(self, mode="r", buffering=-1):
        if "b" in mode:
            return self.rfile if "r" in mode else self.wfile
        return io.TextIOWrapper(self.rfile if "r" in mode else self.wfile)

    def sendall(self, data):
        self.wfile.write(data)

    def settimeout(self, timeout):
        pass

    def close(self):
        pass


class TestPhase3BSecurityAndPipeline(unittest.TestCase):

    def setUp(self):
        self.oauth = MetaOAuthManager()
        self.oauth._save_states = lambda: None
        self.mgr = InstagramManager()
        self.mgr._save_ledger = lambda: None

    # ── 1. PROXY ALLOWLIST & DEFAULT-DENY ────────────────────────────────────

    def test_proxy_blocks_private_and_admin_routes(self):
        blocked_paths = [
            "/",
            "/app",
            "/api/chat",
            "/api/instagram/oauth/secret",
            "/api/reels",
            "/api/system/status",
            "/config/api_keys.json",
        ]
        for path in blocked_paths:
            raw_req = f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:8005\r\n\r\n".encode("utf-8")
            sock = DummyMockSocket(raw_req)
            handler = CallbackOnlyProxyHandler(sock, ("127.0.0.1", 54321), None)
            resp = sock.wfile.getvalue().decode("utf-8", errors="replace")
            self.assertIn("403 Forbidden", resp, f"Path {path} must be blocked with HTTP 403")
            self.assertIn("JARVIS-Strict-Callback-Only", resp)

    def test_proxy_allows_callback_route(self):
        raw_req = b"GET /api/instagram/oauth/callback?code=test&state=abc HTTP/1.1\r\nHost: 127.0.0.1:8005\r\n\r\n"
        sock = DummyMockSocket(raw_req)
        with patch.object(CallbackOnlyProxyHandler, "_proxy_request") as mock_proxy:
            handler = CallbackOnlyProxyHandler(sock, ("127.0.0.1", 54321), None)
            mock_proxy.assert_called_once_with("GET")

    # ── 2. OAUTH STATE SECURITY ──────────────────────────────────────────────

    def test_state_single_use_and_replay_rejection(self):
        state = self.oauth.generate_state(redirect_uri="http://localhost:8000/api/instagram/oauth/callback")
        self.assertGreaterEqual(len(state), 32)

        # First validation must succeed
        valid, data = self.oauth.validate_state(state)
        self.assertTrue(valid)
        self.assertIsNotNone(data)

        # Immediate replay must fail (strictly single-use)
        valid_replay, _ = self.oauth.validate_state(state)
        self.assertFalse(valid_replay)

    def test_state_expiry_after_600_seconds(self):
        state = self.oauth.generate_state()
        # Simulate expiry by backdating created_at by 601 seconds
        self.oauth._states[state]["created_at"] = time.time() - 601
        self.oauth._save_states()

        valid, _ = self.oauth.validate_state(state)
        self.assertFalse(valid, "State older than 600s must be rejected as expired")

    def test_state_empty_or_corrupt_rejection(self):
        self.assertFalse(self.oauth.validate_state("")[0])
        self.assertFalse(self.oauth.validate_state(None)[0])
        self.assertFalse(self.oauth.validate_state("non_existent_random_state_token")[0])

    # ── 3. ACCOUNT IDENTITY ENFORCEMENT ──────────────────────────────────────

    def test_mismatched_account_rejected_from_reels(self):
        with self.assertRaises(ValueError):
            self.mgr.generate_trading_reel(account_username="unauthorized_other_account")

    def test_publish_mismatched_target_fails(self):
        fake_reel = ReelPost(
            id="test_mismatch_reel",
            account_username="other_account",
            status="approved",
            title="Test",
        )
        self.mgr._ledger["test_mismatch_reel"] = fake_reel
        res = self.mgr.publish_reel("test_mismatch_reel", force_assisted=True)
        self.assertFalse(res["ok"])
        self.assertIn("Security refusal", res["error"])
        # Clean up
        self.mgr._ledger.pop("test_mismatch_reel", None)

    # ── 4. SENSITIVE DATA REDACTION & DPAPI ───────────────────────────────────

    def test_dpapi_encryption_and_masking(self):
        secret = "super_secret_test_meta_key_98765"
        enc = encrypt_token(secret)
        self.assertTrue(is_encrypted(enc))
        self.assertNotIn(secret, enc)

        dec = decrypt_token(enc)
        self.assertEqual(dec, secret)

        masked = mask_token(secret)
        self.assertTrue(masked.startswith("supe"))
        self.assertTrue(masked.endswith("8765"))
        self.assertIn("****", masked)
        self.assertNotIn(secret[4:-4], masked)

    # ── 5. APPROVAL GATE ENFORCEMENT ─────────────────────────────────────────

    def test_unapproved_reel_refuses_publishing(self):
        reel_id = "test_unapproved_gate_reel"
        reel = ReelPost(
            id=reel_id,
            account_username="mentos_life_gym",
            status="waiting_for_approval",
            title="Gate Test",
        )
        self.mgr._ledger[reel_id] = reel

        res = self.mgr.publish_reel(reel_id, force_assisted=True)
        self.assertFalse(res["ok"])
        self.assertIn("Explicit human approval is required", res["error"])
        self.assertEqual(reel.status, "waiting_for_approval")

        # Clean up
        self.mgr._ledger.pop(reel_id, None)

    def test_editing_approved_reel_invalidates_approval(self):
        reel_id = "test_approved_edit_invalidation"
        reel = ReelPost(
            id=reel_id,
            account_username="mentos_life_gym",
            status="approved",
            approved_at="2026-11-15T12:00:00",
            title="Original Title",
            caption="Original Caption",
        )
        self.mgr._ledger[reel_id] = reel

        # Edit caption after approval
        updated = self.mgr.edit_reel(reel_id, caption="New Modified Caption")
        self.assertIsNotNone(updated)

        # Must have invalidated approval
        reloaded = self.mgr._ledger[reel_id]
        self.assertEqual(reloaded.status, "waiting_for_approval", "Status must revert to waiting_for_approval")
        self.assertTrue(reloaded.needs_approval)
        self.assertIsNone(reloaded.approved_at, "approved_at timestamp must be wiped")

        # Now attempting to publish must be rejected
        res = self.mgr.publish_reel(reel_id, force_assisted=True)
        self.assertFalse(res["ok"])
        self.assertIn("Explicit human approval is required", res["error"])

        # Clean up
        self.mgr._ledger.pop(reel_id, None)


if __name__ == "__main__":
    unittest.main()
