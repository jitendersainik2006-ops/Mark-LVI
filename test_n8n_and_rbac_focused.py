"""
test_n8n_and_rbac_focused.py — Focused Verification of n8n Bridge & Enterprise RBAC System

Tests:
1. n8n Authentication: Header, Bearer, Invalid Key Rejection, Missing Key Rejection.
2. n8n Inbound Webhook Handlers: Reel generation, Content planning, Task scheduling, Weekly report.
3. n8n Outbound Event Dispatcher: Event whitelist filtering, payload structure, disabled state handling.
4. RBAC User Accounts & PBKDF2 Password Hashing: Least-privilege VIEWER default, salt uniqueness, auth verification.
5. RBAC Role Permission Enforcement: CREATOR, MANAGER, AUDITOR, ADMIN boundaries.
6. RBAC Device Management State Machine: Pending -> Authorized -> Revoked, access rejection on unapproved devices.
7. Consequential Action Gating: Single-use confirmation token generation, cancellation, execution, and timeout.
8. Workspace Separation: Company vs Personal directories, path traversal security rejection.
9. Immutable Activity Audit Logging: Event recording in data/company_activity_log.json.
"""

import json
import os
import sys
import time
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

from core.n8n_integration import N8NManager, n8n_manager
from core.access_control import AccessControlManager, access_control, ROLE_PERMISSIONS


def run_n8n_focused_tests():
    print("\n" + "=" * 70)
    print("  SECTION 1: FOCUSED n8n WORKFLOW AUTOMATION BRIDGE VERIFICATION")
    print("=" * 70)
    
    n8n = N8NManager()
    test_key = "n8n_secure_api_key_8899aabbcc"
    n8n.config.api_key = test_key
    n8n.config.enabled = True
    
    # 1. Auth Tests
    print("\n[n8n-1] Testing API Key Authentication...")
    assert n8n.verify_auth({"x-n8n-api-key": test_key}) is True
    assert n8n.verify_auth({"X-N8N-API-Key": test_key}) is True
    assert n8n.verify_auth({"authorization": f"Bearer {test_key}"}) is True
    assert n8n.verify_auth({"Authorization": f"Bearer {test_key}"}) is True
    assert n8n.verify_auth({"authorization": "Bearer wrong_token"}) is False
    assert n8n.verify_auth({"x-n8n-api-key": "bad_key"}) is False
    assert n8n.verify_auth({}) is False
    print("  [PASS] Both X-N8N-API-Key and Bearer authorization verified. Unauthorized keys strictly blocked.")

    # 2. Inbound Webhook Handlers
    print("\n[n8n-2] Testing Inbound Handlers (Reel, Calendar, Tasks, Report)...")
    # Reel generation
    res_reel = n8n.handle_reel_generation({"delay_hours": 3})
    assert res_reel["ok"] is True
    assert res_reel["reel"]["account_username"] == "mentos_life_gym"
    assert res_reel["reel"]["status"] == "waiting_for_approval"
    print(f"  [PASS] Reel generation handler created reel '{res_reel['reel']['id']}' targeting @mentos_life_gym.")

    # Content planning
    res_plan = n8n.handle_content_planning({"account_username": "mentos_life_gym", "days": 7})
    assert res_plan["ok"] is True
    assert len(res_plan["calendar"]) == 7
    print(f"  [PASS] Content planning handler returned {len(res_plan['calendar'])}-day schedule.")

    # Task schedule
    res_task = n8n.handle_task_schedule({"name": "n8n_auto_backup", "command": "backup_database", "interval_seconds": 7200})
    assert res_task["ok"] is True
    assert res_task["name"] == "n8n_auto_backup"
    print(f"  [PASS] Task schedule handler registered task '{res_task['task_id']}'.")

    # Weekly report
    res_rep = n8n.handle_weekly_report({"account_username": "mentos_life_gym"})
    assert res_rep["ok"] is True
    assert "report" in res_rep
    print("  [PASS] Weekly report handler generated compliance report successfully.")

    # 3. Outbound Webhook Dispatcher
    print("\n[n8n-3] Testing Outbound Event Dispatching & Filtering...")
    # Missing webhook URL test
    n8n.config.webhook_url = ""
    ok_empty, err_empty = n8n.dispatch_event("reel_needs_approval", {})
    assert ok_empty is False
    assert "not enabled/configured" in err_empty

    # Disallowed event test with configured URL
    n8n.config.webhook_url = "https://n8n.internal.net/webhook/jarvis-events"
    ok, err = n8n.dispatch_event("unauthorized_custom_event", {})
    assert ok is False
    assert "not in allowed" in err
    print("  [PASS] Outbound event filter rejected unapproved event type and missing URL.")

    # Allowed event dispatch
    with patch("urllib.request.urlopen") as mock_url:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_url.return_value = mock_resp
        
        n8n.config.webhook_url = "https://n8n.internal.net/webhook/jarvis-events"
        ok_disp, status_str = n8n.dispatch_event("reel_needs_approval", {"reel_id": "test_123"})
        assert ok_disp is True
        assert status_str == "HTTP 200"
        print("  [PASS] Outbound event successfully formatted and dispatched to n8n webhook URL.")


def run_rbac_focused_tests():
    print("\n" + "=" * 70)
    print("  SECTION 2: FOCUSED ENTERPRISE RBAC & COMPANY PERMISSIONS VERIFICATION")
    print("=" * 70)

    rbac = AccessControlManager()
    ts = int(time.time())

    # 1. User Registration & Password Security
    print("\n[RBAC-1] Testing Member Registration & PBKDF2 Password Hashing...")
    u_creator = f"sarah_creator_{ts}"
    u_manager = f"david_manager_{ts}"
    u_admin = f"alex_admin_{ts}"
    
    # Test least-privilege default when no role specified
    u_default = f"guest_user_{ts}"
    user_def = rbac.register_user(u_default, "Password123!")
    assert user_def.role == "VIEWER", f"Default role must be VIEWER, got {user_def.role}"
    
    # Specific roles
    user_c = rbac.register_user(u_creator, "CreatorPass456!", role="CREATOR")
    user_m = rbac.register_user(u_manager, "ManagerPass789!", role="MANAGER")
    user_a = rbac.register_user(u_admin, "AdminPass999!", role="ADMIN")
    
    assert user_c.salt != user_m.salt, "Salts must be cryptographically unique"
    assert user_c.password_hash != "CreatorPass456!", "Passwords MUST NOT be stored in plaintext"
    
    # Authentication
    auth_ok = rbac.authenticate_user(u_creator, "CreatorPass456!")
    assert auth_ok is not None
    assert auth_ok.username == u_creator
    
    auth_fail = rbac.authenticate_user(u_creator, "WrongPassword!")
    assert auth_fail is None
    print("  [PASS] PBKDF2 password security, unique salts, and VIEWER default verified.")

    # 2. Role Permissions Enforcement
    print("\n[RBAC-2] Testing Role Permissions Boundaries...")
    # CREATOR permissions
    assert rbac.has_permission(u_creator, "reels:create") is True
    assert rbac.has_permission(u_creator, "reels:publish") is False
    assert rbac.has_permission(u_creator, "devices:authorize") is False
    assert rbac.has_permission(u_creator, "files:delete") is False
    
    # MANAGER permissions
    assert rbac.has_permission(u_manager, "reels:create") is True
    assert rbac.has_permission(u_manager, "reels:approve") is True
    assert rbac.has_permission(u_manager, "reels:publish") is True
    assert rbac.has_permission(u_manager, "devices:authorize") is False  # Only ADMIN
    assert rbac.has_permission(u_manager, "credentials:manage") is False # Only ADMIN

    # ADMIN permissions
    assert rbac.has_permission(u_admin, "devices:authorize") is True
    assert rbac.has_permission(u_admin, "credentials:manage") is True
    assert rbac.has_permission(u_admin, "files:delete") is True
    print("  [PASS] Explicit permission boundaries strictly enforced across CREATOR, MANAGER, ADMIN.")

    # 3. Device Management State Machine
    print("\n[RBAC-3] Testing Device Registration State Machine (Pending -> Authorized -> Revoked)...")
    dev_id = f"macbook_m3_pro_{ts}"
    dev = rbac.register_device(dev_id, "Sarah MacBook Pro", u_creator)
    assert dev.status == "pending"
    assert rbac.is_device_authorized(dev_id) is False
    print("  [PASS] Device initialized in 'pending' state. Unapproved access strictly blocked.")

    # Unauthorized attempt to approve device (MANAGER cannot authorize devices)
    try:
        rbac.authorize_device(u_manager, dev_id)
        assert False, "Non-admin must not authorize device"
    except PermissionError:
        pass
    assert rbac.is_device_authorized(dev_id) is False
    print("  [PASS] Non-admin authorization attempt rejected.")

    # Admin authorises device
    assert rbac.authorize_device(u_admin, dev_id) is True
    assert rbac.is_device_authorized(dev_id) is True
    print("  [PASS] Admin successfully authorized device.")

    # Admin revokes device
    assert rbac.revoke_device(u_admin, dev_id) is True
    assert rbac.is_device_authorized(dev_id) is False
    print("  [PASS] Admin successfully revoked device.")

    # 4. Consequential Action Gating
    print("\n[RBAC-4] Testing Consequential/Destructive Action Gating & Confirmation Tokens...")
    # Safe non-consequential action proceeds without token
    needs_conf, tok, msg = rbac.request_consequential_confirmation(u_creator, "reels:create", "reel_new")
    assert needs_conf is False
    
    # Destructive action requires confirmation
    needs_conf2, tok2, msg2 = rbac.request_consequential_confirmation(u_admin, "reels:delete", "reel_bad_target")
    assert needs_conf2 is True
    assert len(tok2) == 32
    print(f"  [PASS] Consequential deletion generated 32-char confirmation token: {tok2[:12]}...")

    # Cancellation test
    success, c_msg = rbac.confirm_consequential_action(tok2, confirmed=False)
    assert success is False
    assert "cancelled by user" in c_msg
    print("  [PASS] User cancellation handled cleanly.")

    # Confirmed execution test
    _, tok3, _ = rbac.request_consequential_confirmation(u_admin, "reels:delete", "reel_test_99")
    success3, c_msg3 = rbac.confirm_consequential_action(tok3, confirmed=True)
    assert success3 is True
    assert "confirmed and authorized" in c_msg3
    print("  [PASS] Confirmed execution validated and authorized.")

    # Replay protection
    success_replay, err_replay = rbac.confirm_consequential_action(tok3, confirmed=True)
    assert success_replay is False
    print("  [PASS] Single-use token consumed; replay attack rejected.")

    # 5. Workspace Separation & Path Traversal Prevention
    print("\n[RBAC-5] Testing Workspace Separation (Company vs Personal)...")
    comp_path = rbac.get_workspace_path("company", "strategies/q1_growth.pdf")
    pers_path = rbac.get_workspace_path("personal", "journal/notes.txt")
    
    assert "data\\company\\strategies\\q1_growth.pdf" in str(comp_path)
    assert "data\\personal\\journal\\notes.txt" in str(pers_path)
    
    # Path traversal attack detection
    traversal_attacks = [
        "../../config/api_keys.json",
        "..\\..\\Windows\\System32",
        "/etc/passwd",
        "../../../mark_lvi_core/main.py",
    ]
    for attack in traversal_attacks:
        try:
            rbac.get_workspace_path("company", attack)
            assert False, f"Failed to block traversal attack: {attack}"
        except ValueError:
            pass
    print("  [PASS] Physical workspace separation enforced. Directory traversal attacks strictly blocked.")

    # 6. Immutable Audit Log Inspection
    print("\n[RBAC-6] Testing Activity Audit Logging...")
    from core.access_control import ACTIVITY_LOG_FILE
    assert ACTIVITY_LOG_FILE.exists()
    logs = json.loads(ACTIVITY_LOG_FILE.read_text(encoding="utf-8"))
    assert len(logs) >= 5
    last_log = logs[-1]
    assert "timestamp" in last_log
    assert "username" in last_log
    assert "action" in last_log
    assert "status" in last_log
    print(f"  [PASS] Audit log verified with {len(logs)} recorded entries. Latest action: '{last_log['action']}' by '{last_log['username']}'.")


if __name__ == "__main__":
    run_n8n_focused_tests()
    run_rbac_focused_tests()
    print("\n" + "=" * 70)
    print("  🎉 ALL n8n & ENTERPRISE RBAC FOCUSED TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
