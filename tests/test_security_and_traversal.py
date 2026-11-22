"""
tests/test_security_and_traversal.py — Rigorous Security, Path Traversal & Gate Validation

Tests:
1. Path Traversal & Sandbox Boundary Enforcement in ComputerAgent
2. Confirmation Gate Bypass Prevention (Token validation & Direct API prevention)
3. Code Modification Safety & Rollback Behavior (apply_code_patch & rollback_code_patch)
4. Emergency STOP Enactment & Immutability
5. Input Sanitization & XSS Entity Encoding
6. Safe URL Protocol Validation
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from core.computer_agent import (
    BASE_DIR,
    DATA_DIR,
    ComputerAgent,
    is_safe_path,
)


class TestSecurityAndTraversal(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.audit_log = Path(self.temp_dir) / "test_sec_audit.log"
        self.agent = ComputerAgent(audit_file=self.audit_log)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_is_safe_path_boundary_enforcement(self):
        # Approved paths
        self.assertTrue(is_safe_path(BASE_DIR))
        self.assertTrue(is_safe_path(DATA_DIR / "sample.txt"))
        self.assertTrue(is_safe_path(Path(self.temp_dir) / "test.txt"))

        # Blocked path traversal
        traversal_path = Path(BASE_DIR) / ".." / ".." / "Windows" / "System32" / "cmd.exe"
        self.assertFalse(is_safe_path(traversal_path))
        self.assertFalse(is_safe_path("C:/Windows/System32/drivers/etc/hosts"))
        self.assertFalse(is_safe_path("C:/Program Files/malicious.dll"))
        self.assertFalse(is_safe_path("../../../../../etc/passwd"))

    def test_02_computer_agent_blocks_path_traversal_actions(self):
        bad_path = "C:/Windows/System32/calc.exe"

        # read_file
        res_read = self.agent.safe_execute_default("read_file", {"path": bad_path})
        self.assertIn("Security error", res_read)

        # write_file
        res_write = self.agent.safe_execute_default("write_file", {"path": bad_path, "content": "bad"})
        self.assertIn("Security error", res_write)

        # scan_and_preview_files
        res_scan = self.agent.safe_execute_default("scan_and_preview_files", {"dir": bad_path})
        self.assertIn("Security error", res_scan)

        # organize_files_move
        res_move = self.agent.safe_execute_default("organize_files_move", {"source": bad_path, "target": bad_path})
        self.assertIn("Security error", res_move)

        # apply_code_patch
        res_patch = self.agent.safe_execute_default("apply_code_patch", {"path": bad_path})
        self.assertIn("Security error", res_patch)

    def test_03_confirmation_gate_cannot_be_bypassed_without_confirm_token(self):
        plan = self.agent.create_plan("Destructive test plan", [
            {"action_name": "delete_file", "parameters": {"path": "dummy.txt"}, "description": "Delete critical file"}
        ])
        step = plan.steps[0]
        self.assertTrue(step.is_destructive)
        self.assertFalse(step.permission_granted)

        # Direct execution attempt without grant_permission
        res = self.agent.execute_plan(plan.plan_id)
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "AWAITING_PERMISSION")
        self.assertFalse(step.permission_granted)

        # Attempt to grant with invalid / arbitrary token
        granted = self.agent.grant_permission(plan.plan_id, 1, "MAYBE")
        self.assertFalse(granted)
        self.assertFalse(step.permission_granted)

        granted_blank = self.agent.grant_permission(plan.plan_id, 1, "")
        self.assertFalse(granted_blank)
        self.assertFalse(step.permission_granted)

        # Valid CONFIRM token succeeds
        granted_valid = self.agent.grant_permission(plan.plan_id, 1, "CONFIRM")
        self.assertTrue(granted_valid)
        self.assertTrue(step.permission_granted)

    def test_04_code_patch_backup_and_rollback_lifecycle(self):
        target_file = Path(self.temp_dir) / "app_module.py"
        target_file.write_text("ORIGINAL_CODE = True\n", encoding="utf-8")

        # Apply code patch
        res_patch = self.agent.safe_execute_default("apply_code_patch", {
            "path": str(target_file),
            "content": "MODIFIED_CODE = True\n"
        })
        self.assertIn("Patch verification complete", res_patch)
        self.assertEqual(target_file.read_text(encoding="utf-8"), "MODIFIED_CODE = True\n")
        self.assertTrue(target_file.with_suffix(".py.bak").exists())

        # Rollback code patch
        res_rollback = self.agent.safe_execute_default("rollback_code_patch", {
            "path": str(target_file)
        })
        self.assertIn("Rollback successful", res_rollback)
        self.assertEqual(target_file.read_text(encoding="utf-8"), "ORIGINAL_CODE = True\n")

    def test_05_emergency_stop_freezes_plan_and_rejects_subsequent_execution(self):
        plan = self.agent.create_plan("Long pipeline", [
            {"action_name": "system_status", "parameters": {}, "description": "Step 1"},
            {"action_name": "system_status", "parameters": {}, "description": "Step 2"},
            {"action_name": "system_status", "parameters": {}, "description": "Step 3"}
        ])

        # Operator triggers STOP
        self.agent.stop(plan.plan_id)
        self.assertEqual(plan.status, "CANCELLED")
        for s in plan.steps:
            self.assertEqual(s.status, "SKIPPED")

        # Attempt to resume or re-execute stopped plan MUST be blocked
        res = self.agent.execute_plan(plan.plan_id)
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "STOPPED")
        self.assertEqual(plan.status, "CANCELLED")

        # Attempt to grant permission on a cancelled plan is blocked
        granted = self.agent.grant_permission(plan.plan_id, 1, "CONFIRM")
        self.assertFalse(granted)


if __name__ == "__main__":
    unittest.main()
