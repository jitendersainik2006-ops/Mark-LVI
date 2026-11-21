"""
tests/test_voice_and_gmail_companion.py — Unit Tests for Voice Diagnostics, DPAPI Gmail Integration & Confirmation Gate

Tests:
1. VoiceDiagnosticsEngine diagnostic checks and overall health aggregation.
2. GmailManager Google OAuth URL generation & scope isolation (basic auth vs gmail).
3. GmailManager DPAPI token encryption, persistence, and safe masking.
4. Two-step email dispatch confirmation gate (unconfirmed blocked, confirmed success, single-use token consumption).
5. LAN security route restriction: /api/gmail must be in _RESTRICTED_LAN_PREFIXES.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from core.gmail_manager import GmailManager
from core.voice_diagnostics import VoiceDiagnosticsEngine
from dashboard.server import DashboardServer


class TestVoiceAndGmailCompanion(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.gmail = GmailManager()
        # Mock file storage
        self.orig_tokens_file = Path(self.temp_dir) / "gmail_tokens.json"
        import core.gmail_manager as gm_mod
        self._saved_tokens_file = gm_mod.GMAIL_TOKENS_FILE
        gm_mod.GMAIL_TOKENS_FILE = self.orig_tokens_file

    def tearDown(self):
        import core.gmail_manager as gm_mod
        gm_mod.GMAIL_TOKENS_FILE = self._saved_tokens_file
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_voice_diagnostics_structure(self):
        """Verifies voice diagnostics engine returns valid schema and runs without crashing."""
        vdiag = VoiceDiagnosticsEngine()
        diag = vdiag.run_full_diagnostics()

        self.assertIn("overall_health", diag)
        self.assertIn(diag["overall_health"], ("HEALTHY", "DEGRADED", "OFFLINE"))
        self.assertIn("audio_devices", diag)
        self.assertIn("stt", diag)
        self.assertIn("tts", diag)
        self.assertIn("llm", diag)
        self.assertIn("barge_in", diag)
        self.assertTrue(diag["barge_in"]["barge_in_enabled"])

    def test_gmail_scope_isolation(self):
        """Verifies basic sign-in requests only profile scopes, and Gmail scopes are opt-in."""
        basic = self.gmail.generate_auth_url(request_gmail=False)
        self.assertFalse(any("gmail" in s for s in basic["requested_scopes"]))
        self.assertIn("openid", basic["requested_scopes"])

        with_gmail = self.gmail.generate_auth_url(request_gmail=True)
        self.assertTrue(any("gmail.readonly" in s for s in with_gmail["requested_scopes"]))
        self.assertTrue(any("gmail.send" in s for s in with_gmail["requested_scopes"]))

    def test_dpapi_token_storage_and_masking(self):
        """Verifies tokens are encrypted on disk and masked for public client status."""
        ok = self.gmail.save_tokens({
            "user_email": "test@example.com",
            "user_name": "Test User",
            "access_token": "secret_access_token_abc12345",
            "refresh_token": "secret_refresh_token_xyz98765",
            "granted_scopes": ["openid", "email"],
        })
        self.assertTrue(ok)
        self.assertTrue(self.orig_tokens_file.exists())

        # Check raw file on disk has DPAPI prefix and does not contain plain secret
        with open(self.orig_tokens_file, "r", encoding="utf-8") as f:
            raw_content = f.read()
        self.assertNotIn("secret_access_token_abc12345", raw_content)
        self.assertIn("dpapi:v1:", raw_content)

        # Check status masking
        status = self.gmail.get_status()
        self.assertTrue(status["connected"])
        self.assertNotIn("secret", status["masked_token"])
        self.assertIn("****", status["masked_token"])

        # Check decryption
        loaded = self.gmail.load_tokens()
        self.assertEqual(loaded["access_token"], "secret_access_token_abc12345")

    def test_unbypassable_send_confirmation_gate(self):
        """Verifies sending requires preview generation, explicit confirmed=True, and burns the token."""
        # Step 1: Prepare preview
        prev = self.gmail.prepare_send_preview(
            to="recipient@example.com",
            subject="Status Report",
            body="Important release updates inside.",
        )
        self.assertEqual(prev["status"], "PREVIEW_READY")
        self.assertTrue(prev["confirmation_required"])
        token = prev["confirmation_token"]

        # Step 2: Unconfirmed send MUST fail
        res_unconfirmed = self.gmail.confirm_and_send(token, confirmed=False)
        self.assertEqual(res_unconfirmed["status"], "BLOCKED")
        self.assertIn("blocked", res_unconfirmed["error"].lower())

        # Step 3: Confirmed send succeeds
        res_confirmed = self.gmail.confirm_and_send(token, confirmed=True)
        self.assertEqual(res_confirmed["status"], "SUCCESS")
        self.assertIn("message_id", res_confirmed)

        # Step 4: Replay attempt with consumed token MUST fail
        res_replay = self.gmail.confirm_and_send(token, confirmed=True)
        self.assertEqual(res_replay["status"], "ERROR")

    def test_lan_route_restriction_for_gmail(self):
        """Verifies that /api/gmail is strictly protected from remote LAN callers."""
        server = DashboardServer()
        self.assertIn("/api/gmail", server._RESTRICTED_LAN_PREFIXES)


if __name__ == "__main__":
    unittest.main()
