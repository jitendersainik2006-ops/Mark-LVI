"""
tests/test_user_manager_and_auth.py

Comprehensive Test Suite for J.A.R.V.I.S. Mark LVI Multi-User Account,
Authentication, Email Verification, Onboarding, and Data Isolation System.
"""

import hashlib
import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import core.user_manager as um_module
from core.user_manager import UserManager, UserProfile
import memory.memory_manager as mm_module


class TestUserManagerCore(unittest.TestCase):
    """Test PBKDF2 hashing, registration, verification, sessions, and lockout."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_data_dir = um_module.DATA_DIR
        self.orig_users_dir = um_module.USERS_DIR
        self.orig_users_db = um_module.USERS_DB
        self.orig_smtp_file = um_module.SMTP_CONFIG_FILE
        self.orig_audit_log = um_module.AUTH_AUDIT_LOG

        um_module.DATA_DIR = Path(self.test_dir) / "data"
        um_module.USERS_DIR = um_module.DATA_DIR / "users"
        um_module.USERS_DB = um_module.DATA_DIR / "users.json"
        um_module.SMTP_CONFIG_FILE = Path(self.test_dir) / "smtp_config.json"
        um_module.AUTH_AUDIT_LOG = um_module.DATA_DIR / "auth_audit.log"

        self.mgr = UserManager()

    def tearDown(self):
        um_module.DATA_DIR = self.orig_data_dir
        um_module.USERS_DIR = self.orig_users_dir
        um_module.USERS_DB = self.orig_users_db
        um_module.SMTP_CONFIG_FILE = self.orig_smtp_file
        um_module.AUTH_AUDIT_LOG = self.orig_audit_log
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_first_user_registration_is_owner(self):
        """First registered user should automatically become OWNER."""
        ok, msg, user, vcode = self.mgr.register_user(
            username="alice",
            password="SecurePassword123!",
            display_name="Alice Smith",
            local_only=True,
        )
        self.assertTrue(ok)
        self.assertIsNotNone(user)
        self.assertEqual(user.role, "OWNER")
        self.assertTrue(user.is_local_only)
        self.assertTrue(user.email_verified)
        self.assertEqual(user.username, "alice")

    def test_subsequent_user_registration_is_member(self):
        """Subsequent registered users become MEMBER."""
        self.mgr.register_user("alice", "Password123!", local_only=True)
        ok, msg, bob, vcode = self.mgr.register_user("bob", "Password456!", local_only=True)
        self.assertTrue(ok)
        self.assertIsNotNone(bob)
        self.assertEqual(bob.role, "MEMBER")

    def test_pbkdf2_password_hashing(self):
        """Passwords must be hashed with PBKDF2-HMAC-SHA256 and salt, never stored plain."""
        ok, msg, user, vcode = self.mgr.register_user("charlie", "MySecretPass99", local_only=True)
        self.assertTrue(ok)
        self.assertNotEqual(user.password_hash, "MySecretPass99")
        self.assertEqual(len(user.salt), 32)  # 16-byte hex salt
        self.assertEqual(len(user.password_hash), 64)  # SHA-256 hex digest
        self.assertTrue(user.verify_password("MySecretPass99"))
        self.assertFalse(user.verify_password("WrongPassword"))

    def test_email_verification_flow(self):
        """Online email registration requires 6-digit code verification."""
        ok, msg, user, vcode = self.mgr.register_user(
            username="david",
            password="Password123!",
            email="david@example.com",
            local_only=False,
        )
        self.assertTrue(ok)
        self.assertFalse(user.email_verified)
        self.assertTrue(len(user.verification_code) == 6)

        # Invalid code rejected
        ok_v, msg_v = self.mgr.verify_email_code("david", "000000")
        self.assertFalse(ok_v)

        # Valid code accepted
        ok_v2, msg_v2 = self.mgr.verify_email_code("david", user.verification_code)
        self.assertTrue(ok_v2)
        david = self.mgr.get_user_by_username("david")
        self.assertTrue(david.email_verified)

    def test_brute_force_lockout_after_five_attempts(self):
        """5 consecutive failed logins lock account for 15 minutes."""
        self.mgr.register_user("eve", "CorrectPassword123!", local_only=True)

        for attempt in range(1, 5):
            ok, msg, tok, u = self.mgr.login("eve", "WrongPass")
            self.assertFalse(ok)
            self.assertIn(f"{5 - attempt} attempts remaining", msg)

        # 5th failed attempt triggers lockout
        ok5, msg5, tok5, u5 = self.mgr.login("eve", "WrongPass")
        self.assertFalse(ok5)
        self.assertIn("locked for 15 minutes", msg5.lower())

        # Correct password is now also blocked while locked
        ok_blocked, msg_b, _, _ = self.mgr.login("eve", "CorrectPassword123!")
        self.assertFalse(ok_blocked)
        self.assertIn("locked", msg_b.lower())

    def test_successful_login_and_session_limit(self):
        """Successful login returns session token and enforces max 5 concurrent sessions."""
        self.mgr.register_user("frank", "FrankPass123!", local_only=True)

        tokens = []
        for i in range(7):
            ok, msg, tok, u = self.mgr.login("frank", "FrankPass123!")
            self.assertTrue(ok)
            self.assertIsNotNone(tok)
            tokens.append(tok)

        user = self.mgr.get_user_by_username("frank")
        # Max active sessions capped at 5
        self.assertEqual(len(user.session_tokens), 5)
        # Oldest tokens were revoked
        self.assertIsNone(self.mgr.get_user_by_session(tokens[0]))
        self.assertIsNone(self.mgr.get_user_by_session(tokens[1]))
        # Newest tokens are active
        self.assertIsNotNone(self.mgr.get_user_by_session(tokens[-1]))

    def test_password_recovery_flow(self):
        """Password recovery generates reset token and allows updating password."""
        self.mgr.register_user("grace", "OldPassword123!", email="grace@example.com", local_only=True)
        ok, msg, rtoken = self.mgr.request_password_reset("grace")
        self.assertTrue(ok)
        self.assertIsNotNone(rtoken)

        # Reset password with token
        ok_res, msg_res = self.mgr.reset_password(rtoken, "NewPassword456!")
        self.assertTrue(ok_res)

        # Old password no longer works
        ok_old, _, _, _ = self.mgr.login("grace", "OldPassword123!")
        self.assertFalse(ok_old)

        # New password works
        ok_new, _, tok, _ = self.mgr.login("grace", "NewPassword456!")
        self.assertTrue(ok_new)
        self.assertIsNotNone(tok)

    def test_user_directory_isolation(self):
        """Each user gets an isolated directory with memory, documents, reels subdirectories."""
        user_dir = self.mgr.get_user_storage_dir("user_9988_test")
        self.assertTrue(user_dir.exists())
        self.assertTrue((user_dir / "memory").exists())
        self.assertTrue((user_dir / "documents").exists())
        self.assertTrue((user_dir / "reels").exists())


class TestUserMemoryIsolation(unittest.TestCase):
    """Test multi-user isolation in memory/memory_manager.py."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.orig_base_dir = mm_module.BASE_DIR
        self.orig_memory_path = mm_module.MEMORY_PATH

        mm_module.BASE_DIR = Path(self.test_dir)
        mm_module.MEMORY_PATH = Path(self.test_dir) / "memory" / "long_term.json"
        mm_module.set_active_user(None)

    def tearDown(self):
        mm_module.BASE_DIR = self.orig_base_dir
        mm_module.MEMORY_PATH = self.orig_memory_path
        mm_module.set_active_user(None)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_multi_user_memory_isolation(self):
        """Facts remembered for User A must never bleed into User B's memory."""
        # User A facts
        mm_module.set_active_user("user_alice")
        mm_module.remember("favorite_food", "Sushi", category="preferences")
        mm_module.remember("pet", "Cat named Luna", category="relationships")

        # User B facts
        mm_module.set_active_user("user_bob")
        mm_module.remember("favorite_food", "Pizza", category="preferences")
        mm_module.remember("car", "Tesla Model 3", category="preferences")

        # Verify Alice's memory
        mm_module.set_active_user("user_alice")
        alice_search = mm_module.search_memory("food")
        self.assertIn("Sushi", alice_search)
        self.assertNotIn("Pizza", alice_search)
        self.assertNotIn("Tesla", mm_module.search_memory("car"))

        # Verify Bob's memory
        mm_module.set_active_user("user_bob")
        bob_search = mm_module.search_memory("food")
        self.assertIn("Pizza", bob_search)
        self.assertNotIn("Sushi", bob_search)
        self.assertIn("Tesla", mm_module.search_memory("car"))

        # Global/unauthenticated fallback is clean
        mm_module.set_active_user(None)
        self.assertNotIn("Sushi", mm_module.search_memory("food"))
        self.assertNotIn("Pizza", mm_module.search_memory("food"))

    def test_user_memory_pinning_and_prompt_formatting(self):
        """User-scoped memory supports pinning and formatting for system prompts."""
        mm_module.set_active_user("user_charlie")
        mm_module.remember("project_alpha", "Quantum Neural Engine", category="projects")
        mm_module.pin_memory("projects", "project_alpha", pinned=True)

        prompt_block = mm_module.format_memory_for_prompt()
        self.assertIn("Quantum Neural Engine", prompt_block)
        self.assertIn("📌", prompt_block)


class TestDashboardAuthEndpoints(unittest.TestCase):
    """Test dashboard REST authentication and onboarding endpoints via FastAPI TestClient."""

    @classmethod
    def setUpClass(cls):
        from dashboard.server import DashboardServer
        from fastapi.testclient import TestClient

        cls.server = DashboardServer()
        cls.client = TestClient(cls.server.app)

    def test_auth_api_lifecycle(self):
        """End-to-end test of register -> login -> me -> profile -> onboarding -> logout."""
        # 1. Register
        ts = int(time.time() * 1000)
        uname = f"test_api_{ts}"
        reg_payload = {
            "username": uname,
            "password": "StrongPassword123!",
            "display_name": "API Operator",
            "email": f"operator_{ts}@test.local",
            "local_only": True,
        }
        res_reg = self.client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(res_reg.status_code, 200, f"Register failed: {res_reg.text}")
        data_reg = res_reg.json()
        self.assertTrue(data_reg.get("ok"))
        self.assertEqual(data_reg["user"]["username"], reg_payload["username"])

        # 2. Login
        login_payload = {
            "email_or_username": reg_payload["username"],
            "password": "StrongPassword123!",
        }
        res_login = self.client.post("/api/auth/login", json=login_payload)
        self.assertEqual(res_login.status_code, 200)
        data_login = res_login.json()
        self.assertTrue(data_login.get("ok"))
        token = data_login.get("token")
        self.assertIsNotNone(token)

        headers = {"Authorization": f"Bearer {token}"}

        # 3. GET /api/auth/me
        res_me = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(res_me.status_code, 200)
        data_me = res_me.json()
        self.assertTrue(data_me.get("ok"))
        self.assertEqual(data_me["user"]["username"], reg_payload["username"])

        # 4. Profile update
        prof_payload = {
            "display_name": "Commander Jarvis",
            "language": "hinglish",
            "voice_preference": "Madhur",
            "personality": "sarcastic_ironman",
            "memory_consent": True,
        }
        res_prof = self.client.post("/api/auth/profile", json=prof_payload, headers=headers)
        self.assertEqual(res_prof.status_code, 200)
        data_prof = res_prof.json()
        self.assertTrue(data_prof.get("ok"))
        self.assertEqual(data_prof["user"]["display_name"], "Commander Jarvis")
        self.assertEqual(data_prof["user"]["personality"], "sarcastic_ironman")

        # 5. Onboarding update
        res_ob = self.client.post("/api/auth/onboarding/update", json={"step": 12, "completed": True}, headers=headers)
        self.assertEqual(res_ob.status_code, 200)
        data_ob = res_ob.json()
        self.assertTrue(data_ob.get("ok"))
        self.assertTrue(data_ob["user"]["onboarding_completed"])

        # 6. Logout
        res_logout = self.client.post("/api/auth/logout", headers=headers)
        self.assertEqual(res_logout.status_code, 200)
        self.assertTrue(res_logout.json().get("ok"))

        # Cleanup test user from user_manager singleton
        try:
            from core.user_manager import user_manager
            u = user_manager.get_user_by_username(uname)
            if u:
                user_manager._users.pop(u.user_id, None)
                user_manager._save_users()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
