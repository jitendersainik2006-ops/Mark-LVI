"""
core/user_manager.py — Multi-User Account, Email Verification, & Profile Isolation Engine for J.A.R.V.I.S. Mark LVI

Implements:
1. Multi-User Registration & Authentication (PBKDF2-HMAC-SHA256, 100k iterations, random salt).
2. Email Verification with SMTP Support and Local-Only Offline Fallback.
3. 12-Step Guided Onboarding State Tracking.
4. User Profile & Preferences (Language, Voice, Personality, Privacy/Memory Consent).
5. Secure Session Management & Token Revocation.
6. Multi-User Directory & Data Isolation (data/users/<user_id>/...).
7. Brute-Force Rate Limiting & Account Lockout.
8. Password Recovery & Reset Token Verification.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import secrets
import smtplib
import sys
import time
from dataclasses import asdict, dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("JARVIS.UserManager")


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
USERS_DIR = DATA_DIR / "users"
USERS_DB = DATA_DIR / "users.json"
SMTP_CONFIG_FILE = BASE_DIR / "config" / "smtp_config.json"
AUTH_AUDIT_LOG = DATA_DIR / "auth_audit.log"


@dataclass
class UserProfile:
    user_id: str
    username: str
    display_name: str
    email: str
    password_hash: str
    salt: str
    role: str = "OWNER"              # First registered user is OWNER; subsequent are MEMBER/VIEWER
    email_verified: bool = False
    is_local_only: bool = True       # True if created in Local-Only offline mode
    verification_code: str = ""
    verification_code_expiry: float = 0.0
    reset_token: str = ""
    reset_token_expiry: float = 0.0
    language: str = "en"             # en, hi, hinglish
    voice_preference: str = "Madhur" # Madhur, Swara, Zira, David
    personality: str = "jarvis_classic" # jarvis_classic, sarcastic_ironman, polite_assistant
    memory_consent: bool = True
    onboarding_step: int = 1         # 1 to 12
    onboarding_completed: bool = False
    created_at: float = field(default_factory=time.time)
    last_login: float = 0.0
    failed_attempts: int = 0
    locked_until: float = 0.0
    session_tokens: List[str] = field(default_factory=list)

    def to_public_dict(self) -> Dict[str, Any]:
        """Returns safe user representation omitting password, salt, and raw tokens."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "role": self.role,
            "email_verified": self.email_verified,
            "is_local_only": self.is_local_only,
            "language": self.language,
            "voice_preference": self.voice_preference,
            "personality": self.personality,
            "memory_consent": self.memory_consent,
            "onboarding_step": self.onboarding_step,
            "onboarding_completed": self.onboarding_completed,
            "created_at": self.created_at,
            "last_login": self.last_login,
        }

    def verify_password(self, password: str) -> bool:
        if not self.password_hash or not self.salt:
            return False
        test_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(self.salt), 100_000
        ).hex()
        return secrets.compare_digest(self.password_hash, test_hash)


class UserManager:
    """Manages multi-user lifecycle, registration, authentication, sessions, and data isolation."""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        USERS_DIR.mkdir(parents=True, exist_ok=True)
        self._users: Dict[str, UserProfile] = {}
        self._sessions: Dict[str, str] = {}  # session_token -> user_id
        self._load_users()

    def _load_users(self):
        if USERS_DB.exists():
            try:
                raw = json.loads(USERS_DB.read_text(encoding="utf-8"))
                for uid, udata in raw.items():
                    user = UserProfile(**udata)
                    self._users[uid] = user
                    for tok in user.session_tokens:
                        self._sessions[tok] = uid
            except Exception as e:
                logger.error(f"Failed to load users DB: {e}")

    def _save_users(self):
        data = {uid: asdict(user) for uid, user in self._users.items()}
        USERS_DB.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _log_auth_event(self, action: str, username: str, status: str, details: str = ""):
        """Appends sanitized entry to authentication audit log."""
        entry = {
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "action": action,
            "username": username,
            "status": status,
            "details": details,
        }
        with open(AUTH_AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    # ── User Storage Isolation ────────────────────────────────────────────────

    def get_user_storage_dir(self, user_id: str) -> Path:
        """Returns isolated directory for user, enforcing safe alphanumeric pathing."""
        safe_uid = re.sub(r"[^a-zA-Z0-9_\-]", "", user_id)
        if not safe_uid:
            raise ValueError("Invalid user ID")
        user_dir = USERS_DIR / safe_uid
        user_dir.mkdir(parents=True, exist_ok=True)
        (user_dir / "memory").mkdir(parents=True, exist_ok=True)
        (user_dir / "documents").mkdir(parents=True, exist_ok=True)
        (user_dir / "reels").mkdir(parents=True, exist_ok=True)
        return user_dir

    # ── Registration & Onboarding ─────────────────────────────────────────────

    def register_user(
        self,
        username: str,
        password: str,
        display_name: str = "",
        email: str = "",
        language: str = "en",
        local_only: bool = True,
    ) -> Tuple[bool, str, Optional[UserProfile], Optional[str]]:
        """
        Registers a new user.
        Returns: (success, message, user_profile, local_verification_code_if_any)
        """
        uname = username.strip().lower()
        if not uname or len(uname) < 3:
            return False, "Username must be at least 3 characters.", None, None
        if not re.match(r"^[a-zA-Z0-9_\.]+$", uname):
            return False, "Username must contain only alphanumeric characters, dots, and underscores.", None, None

        clean_email = email.strip().lower()
        if clean_email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean_email):
            return False, "Invalid email address format.", None, None

        # Check existing
        for u in self._users.values():
            if u.username == uname:
                return False, f"Username '{uname}' is already registered.", None, None
            if clean_email and u.email and u.email == clean_email:
                return False, f"Email '{clean_email}' is already registered to another account.", None, None

        if len(password) < 6:
            return False, "Password must be at least 6 characters long.", None, None

        # Hash password with PBKDF2
        salt = secrets.token_hex(16)
        pw_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000
        ).hex()

        user_id = f"user_{int(time.time())}_{secrets.token_hex(4)}"
        is_first_user = len(self._users) == 0
        role = "OWNER" if is_first_user else "MEMBER"

        v_code = f"{secrets.randbelow(900000) + 100000}"  # 6-digit code
        v_expiry = time.time() + 900  # 15 minutes TTL

        user = UserProfile(
            user_id=user_id,
            username=uname,
            display_name=display_name.strip() or uname,
            email=clean_email,
            password_hash=pw_hash,
            salt=salt,
            role=role,
            email_verified=local_only,  # Local-only accounts are automatically ready locally
            is_local_only=local_only,
            verification_code=v_code,
            verification_code_expiry=v_expiry,
            language=language,
            onboarding_step=3 if not local_only else 5,
        )

        self._users[user_id] = user
        self.get_user_storage_dir(user_id)  # Ensure user directory tree exists
        self._save_users()
        self._log_auth_event("REGISTER", uname, "SUCCESS", f"Role: {role}, LocalOnly: {local_only}")

        # Send email or return local verification token
        local_code_returned = None
        if not local_only and clean_email:
            sent, send_err = self._send_verification_email(clean_email, v_code)
            if not sent:
                # Fallback to local code if SMTP fails
                local_code_returned = v_code
                return True, f"Account created. Email delivery failed ({send_err}); use local code: {v_code}", user, v_code
            return True, "Account created. Verification code sent to your email.", user, None
        else:
            local_code_returned = v_code
            return True, "Account created in Local-Only mode. Ready for immediate local use.", user, local_code_returned

    # ── Email Verification & Resend ───────────────────────────────────────────

    def verify_email_code(self, email_or_username: str, code: str) -> Tuple[bool, str]:
        """Verifies 6-digit email confirmation code."""
        target = email_or_username.strip().lower()
        user = self._find_user(target)
        if not user:
            return False, "User account not found."

        if user.email_verified:
            return True, "Email is already verified."

        if not user.verification_code or time.time() > user.verification_code_expiry:
            return False, "Verification code has expired. Please request a new code."

        if secrets.compare_digest(str(user.verification_code).strip(), str(code).strip()):
            user.email_verified = True
            user.verification_code = ""
            user.verification_code_expiry = 0.0
            user.onboarding_step = max(user.onboarding_step, 5)
            self._save_users()
            self._log_auth_event("VERIFY_EMAIL", user.username, "SUCCESS")
            return True, "Email verified successfully."

        self._log_auth_event("VERIFY_EMAIL", user.username, "FAILED", "Invalid code")
        return False, "Invalid verification code."

    def resend_verification(self, email_or_username: str) -> Tuple[bool, str, Optional[str]]:
        target = email_or_username.strip().lower()
        user = self._find_user(target)
        if not user:
            return False, "User account not found.", None

        if user.email_verified:
            return True, "Email is already verified.", None

        v_code = f"{secrets.randbelow(900000) + 100000}"
        user.verification_code = v_code
        user.verification_code_expiry = time.time() + 900
        self._save_users()

        if user.email and not user.is_local_only:
            sent, err = self._send_verification_email(user.email, v_code)
            if sent:
                return True, "A new verification code has been sent to your email.", None
            return True, f"Email delivery failed ({err}). Use local code: {v_code}", v_code
        return True, f"New local verification code generated: {v_code}", v_code

    # ── Authentication & Sessions ─────────────────────────────────────────────

    def login(self, email_or_username: str, password: str) -> Tuple[bool, str, Optional[str], Optional[Dict[str, Any]]]:
        """
        Authenticates user with rate-limiting and brute-force protection.
        Returns: (success, message, session_token, public_user_dict)
        """
        target = email_or_username.strip().lower()
        user = self._find_user(target)
        if not user:
            self._log_auth_event("LOGIN", target, "FAILED", "Unknown user")
            return False, "Invalid username or password.", None, None

        now = time.time()
        if user.locked_until > now:
            remaining = int(user.locked_until - now)
            self._log_auth_event("LOGIN", user.username, "BLOCKED", f"Account locked for {remaining}s")
            return False, f"Account locked due to multiple failed attempts. Try again in {remaining} seconds.", None, None

        if not user.verify_password(password):
            user.failed_attempts += 1
            if user.failed_attempts >= 5:
                user.locked_until = now + 900  # 15 minutes lockout
                self._save_users()
                self._log_auth_event("LOCKOUT", user.username, "LOCKED", "5 failed password attempts")
                return False, "Too many failed attempts. Account locked for 15 minutes.", None, None
            self._save_users()
            self._log_auth_event("LOGIN", user.username, "FAILED", f"Bad password ({user.failed_attempts}/5)")
            return False, f"Invalid username or password. ({5 - user.failed_attempts} attempts remaining)", None, None

        # Successful login
        user.failed_attempts = 0
        user.locked_until = 0.0
        user.last_login = now

        session_token = secrets.token_urlsafe(32)
        user.session_tokens.append(session_token)
        # Limit active sessions to 5 per user
        if len(user.session_tokens) > 5:
            oldest = user.session_tokens.pop(0)
            self._sessions.pop(oldest, None)

        self._sessions[session_token] = user.user_id
        self._save_users()
        self._log_auth_event("LOGIN", user.username, "SUCCESS")

        return True, "Login successful.", session_token, user.to_public_dict()

    def logout(self, session_token: str) -> bool:
        uid = self._sessions.pop(session_token, None)
        if uid and uid in self._users:
            if session_token in self._users[uid].session_tokens:
                self._users[uid].session_tokens.remove(session_token)
                self._save_users()
                self._log_auth_event("LOGOUT", self._users[uid].username, "SUCCESS")
                return True
        return False

    def revoke_all_sessions(self, user_id: str) -> int:
        user = self._users.get(user_id)
        if not user:
            return 0
        count = len(user.session_tokens)
        for tok in user.session_tokens:
            self._sessions.pop(tok, None)
        user.session_tokens.clear()
        self._save_users()
        self._log_auth_event("REVOKE_SESSIONS", user.username, "REVOKED", f"Revoked {count} sessions")
        return count

    def get_user_by_session(self, session_token: str) -> Optional[UserProfile]:
        uid = self._sessions.get(session_token)
        return self._users.get(uid) if uid else None

    def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[UserProfile]:
        return self._find_user(username)

    def list_users(self) -> List[Dict[str, Any]]:
        return [u.to_public_dict() for u in self._users.values()]

    # ── Profile & Onboarding State ────────────────────────────────────────────

    def update_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        language: Optional[str] = None,
        voice_preference: Optional[str] = None,
        personality: Optional[str] = None,
        memory_consent: Optional[bool] = None,
        onboarding_step: Optional[int] = None,
        onboarding_completed: Optional[bool] = None,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        user = self._users.get(user_id)
        if not user:
            return False, "User not found", None

        if display_name is not None and display_name.strip():
            user.display_name = display_name.strip()
        if language is not None and language.strip() in ("en", "hi", "hinglish"):
            user.language = language.strip()
        if voice_preference is not None and voice_preference.strip():
            user.voice_preference = voice_preference.strip()
        if personality is not None and personality.strip():
            user.personality = personality.strip()
        if memory_consent is not None:
            user.memory_consent = bool(memory_consent)
        if onboarding_step is not None:
            user.onboarding_step = max(1, min(12, int(onboarding_step)))
        if onboarding_completed is not None:
            user.onboarding_completed = bool(onboarding_completed)

        self._save_users()
        return True, "Profile updated successfully.", user.to_public_dict()

    # ── Password Recovery ─────────────────────────────────────────────────────

    def request_password_reset(self, email_or_username: str) -> Tuple[bool, str, Optional[str]]:
        target = email_or_username.strip().lower()
        user = self._find_user(target)
        if not user:
            return False, "User not found.", None

        reset_token = secrets.token_urlsafe(24)
        user.reset_token = reset_token
        user.reset_token_expiry = time.time() + 1800  # 30 minutes TTL
        self._save_users()
        self._log_auth_event("RESET_REQUEST", user.username, "TOKEN_ISSUED")

        if user.email and not user.is_local_only:
            sent, err = self._send_reset_email(user.email, reset_token)
            if sent:
                return True, "Password reset instructions sent to your email.", None
            return True, f"Email delivery failed ({err}). Use local reset token: {reset_token}", reset_token
        return True, f"Local password reset token: {reset_token}", reset_token

    def reset_password(self, reset_token: str, new_password: str) -> Tuple[bool, str]:
        if not reset_token or len(new_password) < 6:
            return False, "Invalid token or password too short (minimum 6 characters)."

        target_user = None
        for u in self._users.values():
            if u.reset_token and secrets.compare_digest(u.reset_token, reset_token):
                if time.time() <= u.reset_token_expiry:
                    target_user = u
                    break

        if not target_user:
            return False, "Invalid or expired reset token."

        salt = secrets.token_hex(16)
        pw_hash = hashlib.pbkdf2_hmac(
            "sha256", new_password.encode("utf-8"), bytes.fromhex(salt), 100_000
        ).hex()

        target_user.password_hash = pw_hash
        target_user.salt = salt
        target_user.reset_token = ""
        target_user.reset_token_expiry = 0.0
        target_user.failed_attempts = 0
        target_user.locked_until = 0.0
        self.revoke_all_sessions(target_user.user_id)
        self._save_users()
        self._log_auth_event("RESET_PASSWORD", target_user.username, "SUCCESS")
        return True, "Password reset successfully. Please log in with your new password."

    # ── Helpers & Email Sending ───────────────────────────────────────────────

    def _find_user(self, target: str) -> Optional[UserProfile]:
        t = target.strip().lower()
        for u in self._users.values():
            if u.username == t or (u.email and u.email.lower() == t):
                return u
        return None

    def _get_smtp_config(self) -> Optional[Dict[str, Any]]:
        if SMTP_CONFIG_FILE.exists():
            try:
                return json.loads(SMTP_CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    def configure_smtp(
        self, host: str, port: int, user: str, password: str, sender: str, use_tls: bool = True
    ) -> bool:
        """Saves SMTP configuration with credentials."""
        cfg = {
            "host": host.strip(),
            "port": int(port),
            "user": user.strip(),
            "password": password,
            "sender": sender.strip(),
            "use_tls": bool(use_tls),
            "updated_at": time.time(),
        }
        SMTP_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        SMTP_CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        return True

    def _send_verification_email(self, to_email: str, code: str) -> Tuple[bool, str]:
        cfg = self._get_smtp_config()
        if not cfg or not cfg.get("host"):
            return False, "SMTP not configured"

        try:
            msg = MIMEMultipart()
            msg["From"] = cfg.get("sender") or cfg.get("user")
            msg["To"] = to_email
            msg["Subject"] = f"J.A.R.V.I.S. Mark LVI — Verification Code: {code}"
            body = (
                f"Welcome to J.A.R.V.I.S. Mark LVI Core.\n\n"
                f"Your account verification code is:\n\n"
                f"    {code}\n\n"
                f"This code will expire in 15 minutes.\n"
                f"If you did not request this account, please ignore this email."
            )
            msg.attach(MIMEText(body, "plain"))

            port = cfg.get("port", 587)
            server = smtplib.SMTP(cfg.get("host"), port, timeout=10)
            if cfg.get("use_tls", True):
                server.starttls()
            if cfg.get("user") and cfg.get("password"):
                server.login(cfg.get("user"), cfg.get("password"))
            server.send_message(msg)
            server.quit()
            return True, "Delivered"
        except Exception as e:
            logger.warning(f"SMTP delivery failed to {to_email}: {e}")
            return False, str(e)

    def _send_reset_email(self, to_email: str, reset_token: str) -> Tuple[bool, str]:
        cfg = self._get_smtp_config()
        if not cfg or not cfg.get("host"):
            return False, "SMTP not configured"

        try:
            msg = MIMEMultipart()
            msg["From"] = cfg.get("sender") or cfg.get("user")
            msg["To"] = to_email
            msg["Subject"] = "J.A.R.V.I.S. Mark LVI — Password Reset Request"
            body = (
                f"A password reset request was received for your J.A.R.V.I.S. account.\n\n"
                f"Your password reset token is:\n\n"
                f"    {reset_token}\n\n"
                f"Enter this token in the dashboard to set a new password. This token expires in 30 minutes."
            )
            msg.attach(MIMEText(body, "plain"))

            port = cfg.get("port", 587)
            server = smtplib.SMTP(cfg.get("host"), port, timeout=10)
            if cfg.get("use_tls", True):
                server.starttls()
            if cfg.get("user") and cfg.get("password"):
                server.login(cfg.get("user"), cfg.get("password"))
            server.send_message(msg)
            server.quit()
            return True, "Delivered"
        except Exception as e:
            return False, str(e)


# Singleton Instance
user_manager = UserManager()
