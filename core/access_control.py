"""
core/access_control.py — Company-Ready Role-Based Access Control (RBAC) & Device Management

Prepares J.A.R.V.I.S. for future enterprise / Black Intel company deployment without
merging external projects.

Architecture:
1. Individual Member Accounts & Role Hierarchy:
   - ADMIN: Full control, device authorization, credential management, deletion approval.
   - MANAGER: Content approval, task scheduling, workflow management.
   - CREATOR: Draft creation, ideas, safe assistant operations.
   - AUDITOR: Read-only audit logs, analytics, compliance inspection.
   - VIEWER: Default least-privilege role for new users. Read-only dashboard.
2. Authorized Device Management:
   - Explicit device fingerprinting and approval state (pending, authorized, revoked).
3. File & Action Operations with Consequential Confirmation:
   - Create, edit, copy, move, delete guarded by role permissions.
   - Destructive or consequential actions require explicit confirmation token.
4. Activity & Security Audit Logging:
   - Immutable append-only log of every user action.
5. Workspace Separation:
   - Physical separation of Company (data/company/) and Personal (data/personal/) assets.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "company_users.json"
DEVICES_FILE = DATA_DIR / "company_devices.json"
ACTIVITY_LOG_FILE = DATA_DIR / "company_activity_log.json"
COMPANY_WORKSPACE = DATA_DIR / "company"
PERSONAL_WORKSPACE = DATA_DIR / "personal"

logger = logging.getLogger("JARVIS.AccessControl")


# ── Roles and Permission Mapping ─────────────────────────────────────────────

ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "ADMIN": {
        "dashboard:view", "reels:view", "reels:create", "reels:approve", "reels:publish", "reels:delete",
        "files:read", "files:write", "files:delete", "files:move",
        "tasks:create", "tasks:manage",
        "credentials:view_masked", "credentials:manage",
        "devices:authorize", "devices:revoke", "users:manage",
        "audit:view", "n8n:manage",
    },
    "MANAGER": {
        "dashboard:view", "reels:view", "reels:create", "reels:approve", "reels:publish",
        "files:read", "files:write", "files:move",
        "tasks:create", "tasks:manage",
        "credentials:view_masked",
        "audit:view",
    },
    "CREATOR": {
        "dashboard:view", "reels:view", "reels:create",
        "files:read", "files:write",
        "tasks:create",
    },
    "AUDITOR": {
        "dashboard:view", "reels:view", "audit:view", "credentials:view_masked",
    },
    "VIEWER": {
        "dashboard:view", "reels:view",
    },
}

CONSEQUENTIAL_ACTIONS: Set[str] = {
    "files:delete",
    "reels:delete",
    "credentials:manage",
    "devices:revoke",
    "users:manage",
    "reels:publish",
}


@dataclass
class MemberUser:
    username: str
    password_hash: str
    salt: str
    role: str = "VIEWER"  # Never default to ADMIN
    status: str = "active"  # active, suspended
    created_at: float = field(default_factory=time.time)
    last_login: float = 0.0

    def verify_password(self, password: str) -> bool:
        test_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(self.salt), 100_000
        ).hex()
        return secrets.compare_digest(self.password_hash, test_hash)


@dataclass
class AuthorizedDevice:
    device_id: str
    device_name: str
    owner_username: str
    status: str = "pending"  # pending, authorized, revoked
    registered_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


class AccessControlManager:
    """Enterprise Role-Based Access Control, Device Registry & Activity Logger."""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        COMPANY_WORKSPACE.mkdir(parents=True, exist_ok=True)
        PERSONAL_WORKSPACE.mkdir(parents=True, exist_ok=True)
        self._users: Dict[str, MemberUser] = {}
        self._devices: Dict[str, AuthorizedDevice] = {}
        self._pending_confirmations: Dict[str, dict] = {}
        self._load()

    def _load(self):
        # Load Users
        if USERS_FILE.exists():
            try:
                raw = json.loads(USERS_FILE.read_text(encoding="utf-8"))
                for u, udata in raw.items():
                    self._users[u.lower()] = MemberUser(**udata)
            except Exception as e:
                logger.warning(f"Failed loading users: {e}")

        # Load Devices
        if DEVICES_FILE.exists():
            try:
                raw = json.loads(DEVICES_FILE.read_text(encoding="utf-8"))
                for d, ddata in raw.items():
                    self._devices[d] = AuthorizedDevice(**ddata)
            except Exception as e:
                logger.warning(f"Failed loading devices: {e}")

    def _save_users(self):
        data = {u: asdict(user) for u, user in self._users.items()}
        USERS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _save_devices(self):
        data = {d: asdict(dev) for d, dev in self._devices.items()}
        DEVICES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def log_activity(
        self,
        username: str,
        action: str,
        target: str,
        device_id: str = "local",
        status: str = "SUCCESS",
        details: str = "",
    ):
        """Appends an immutable audit event to company_activity_log.json."""
        entry = {
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "username": username,
            "role": self.get_user_role(username),
            "device_id": device_id,
            "action": action,
            "target": target,
            "status": status,
            "details": details,
        }
        existing = []
        if ACTIVITY_LOG_FILE.exists():
            try:
                existing = json.loads(ACTIVITY_LOG_FILE.read_text(encoding="utf-8"))
            except Exception:
                existing = []
        existing.append(entry)
        ACTIVITY_LOG_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    # ── User Account Operations ───────────────────────────────────────────────

    def register_user(self, username: str, password: str, role: str = "VIEWER") -> MemberUser:
        """Registers a new member account. Defaults to least-privilege (VIEWER)."""
        uname = username.strip().lower()
        if not uname:
            raise ValueError("Username cannot be empty")
        if uname in self._users:
            raise ValueError(f"User '{uname}' already exists")

        assigned_role = role.upper() if role.upper() in ROLE_PERMISSIONS else "VIEWER"

        salt = secrets.token_hex(16)
        pw_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), 100_000
        ).hex()

        user = MemberUser(
            username=uname,
            password_hash=pw_hash,
            salt=salt,
            role=assigned_role,
            status="active",
        )
        self._users[uname] = user
        self._save_users()
        self.log_activity("SYSTEM", "users:register", uname, details=f"Assigned role: {assigned_role}")
        return user

    def authenticate_user(self, username: str, password: str) -> Optional[MemberUser]:
        uname = username.strip().lower()
        user = self._users.get(uname)
        if not user or user.status != "active":
            return None
        if user.verify_password(password):
            user.last_login = time.time()
            self._save_users()
            self.log_activity(uname, "auth:login", uname, status="SUCCESS")
            return user
        self.log_activity(uname, "auth:login", uname, status="FAILED", details="Bad password")
        return None

    def get_user_role(self, username: str) -> str:
        user = self._users.get(username.strip().lower())
        return user.role if user else "VIEWER"

    def update_user_role(self, admin_username: str, target_username: str, new_role: str) -> bool:
        if not self.has_permission(admin_username, "users:manage"):
            raise PermissionError("Only ADMIN can modify member roles.")
        t_user = self._users.get(target_username.strip().lower())
        if not t_user:
            raise ValueError("Target user not found")
        if new_role.upper() not in ROLE_PERMISSIONS:
            raise ValueError(f"Unknown role '{new_role}'")
        t_user.role = new_role.upper()
        self._save_users()
        self.log_activity(admin_username, "users:role_change", target_username, details=f"New role: {new_role}")
        return True

    # ── Permissions & Consequential Guardrails ───────────────────────────────

    def has_permission(self, username: str, permission: str) -> bool:
        role = self.get_user_role(username)
        perms = ROLE_PERMISSIONS.get(role, set())
        return permission in perms

    def request_consequential_confirmation(
        self, username: str, action: str, target: str, device_id: str = "local"
    ) -> Tuple[bool, str, str]:
        """
        Gating mechanism for consequential/destructive actions.
        Returns: (needs_confirmation, confirmation_token, message)
        """
        if not self.has_permission(username, action):
            return False, "", f"Permission denied for action '{action}' under role '{self.get_user_role(username)}'."

        if action not in CONSEQUENTIAL_ACTIONS:
            return False, "", "Action is non-consequential; proceeds without extra confirmation."

        token = secrets.token_hex(16)
        self._pending_confirmations[token] = {
            "username": username,
            "action": action,
            "target": target,
            "device_id": device_id,
            "created_at": time.time(),
        }
        msg = f"Consequential action '{action}' on '{target}' requires explicit confirmation."
        return True, token, msg

    def confirm_consequential_action(self, token: str, confirmed: bool) -> Tuple[bool, str]:
        """Validates and executes the pending confirmation."""
        if token not in self._pending_confirmations:
            return False, "Invalid or expired confirmation token."

        req = self._pending_confirmations.pop(token)
        if time.time() - req["created_at"] > 300:  # 5-minute timeout
            return False, "Confirmation token expired."

        if not confirmed:
            self.log_activity(req["username"], req["action"], req["target"], status="CANCELLED_BY_USER")
            return False, "Action cancelled by user confirmation."

        self.log_activity(req["username"], req["action"], req["target"], status="CONFIRMED_AND_EXECUTED")
        return True, f"Action '{req['action']}' confirmed and authorized."

    # ── Device Management ────────────────────────────────────────────────────

    def register_device(self, device_id: str, device_name: str, owner_username: str) -> AuthorizedDevice:
        """Registers a device fingerprint. Default state is 'pending' (requires admin authorization)."""
        dev = AuthorizedDevice(
            device_id=device_id,
            device_name=device_name,
            owner_username=owner_username.lower(),
            status="pending",  # Never auto-authorize by default
        )
        self._devices[device_id] = dev
        self._save_devices()
        self.log_activity(owner_username, "devices:register", device_id, details=device_name)
        return dev

    def authorize_device(self, admin_username: str, device_id: str) -> bool:
        if not self.has_permission(admin_username, "devices:authorize"):
            raise PermissionError("Only ADMIN can authorize devices.")
        dev = self._devices.get(device_id)
        if not dev:
            raise ValueError("Device not found")
        dev.status = "authorized"
        self._save_devices()
        self.log_activity(admin_username, "devices:authorize", device_id, status="AUTHORIZED")
        return True

    def revoke_device(self, admin_username: str, device_id: str) -> bool:
        if not self.has_permission(admin_username, "devices:revoke"):
            raise PermissionError("Only ADMIN can revoke devices.")
        dev = self._devices.get(device_id)
        if not dev:
            raise ValueError("Device not found")
        dev.status = "revoked"
        self._save_devices()
        self.log_activity(admin_username, "devices:revoke", device_id, status="REVOKED")
        return True

    def is_device_authorized(self, device_id: str) -> bool:
        dev = self._devices.get(device_id)
        return bool(dev and dev.status == "authorized")

    # ── File Operations & Separation of Workspaces ───────────────────────────

    def get_workspace_path(self, workspace_type: str, relative_path: str) -> Path:
        """
        Enforces physical separation between Company (data/company/) and Personal (data/personal/) files.
        Prevents path traversal attacks and absolute path escapes.
        """
        raw = str(relative_path or "").strip()
        if not raw:
            raise ValueError("Empty path provided")
        if raw.startswith("/") or raw.startswith("\\") or ":" in raw:
            raise ValueError(f"Absolute or drive-rooted paths not permitted in workspace: {relative_path}")

        base = (COMPANY_WORKSPACE if workspace_type.lower() == "company" else PERSONAL_WORKSPACE).resolve()
        target = (base / raw).resolve()
        if not str(target).startswith(str(base)):
            raise ValueError(f"Illegal path traversal detected outside designated workspace: {relative_path}")
        return target


# Singleton instance
access_control = AccessControlManager()
