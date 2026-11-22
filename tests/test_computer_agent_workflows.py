"""
tests/test_computer_agent_workflows.py — Rigorous Verification of PC Computer-Use Agent

Tests the 4 Master Multi-Step Workflows:
1. File Organizer Workflow (Scan -> Dry-Run Preview -> Confirmation Gated Move)
2. Automated Test Runner Workflow (Detect -> Run -> Report)
3. Document Reader & Insights Workflow (Validate -> Extract -> Summarize)
4. Code Assistant Workflow (AST Parse -> Diagnose -> Confirmation Gated Patch)
5. Operator Emergency STOP Gate
6. Audit Logging & Sensitive Data Scrubbing
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from core.computer_agent import (
    DESTRUCTIVE_ACTIONS,
    ComputerAgent,
    scrub_sensitive_text,
)


class TestComputerAgentWorkflows(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.audit_log = Path(self.temp_dir) / "test_audit.log"
        self.agent = ComputerAgent(audit_file=self.audit_log)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_file_organizer_workflow_lifecycle(self):
        staging_dir = Path(self.temp_dir) / "staging"
        staging_dir.mkdir(parents=True, exist_ok=True)
        (staging_dir / "item1.tmp").write_text("artifact 1", encoding="utf-8")
        (staging_dir / "item2.tmp").write_text("artifact 2", encoding="utf-8")
        target_dir = Path(self.temp_dir) / "target_organized"

        plan = self.agent.create_file_organizer_plan(
            source_dir=str(staging_dir),
            pattern="*.tmp",
            target_dir=str(target_dir),
        )
        self.assertEqual(len(plan.steps), 3)
        self.assertFalse(plan.steps[0].is_destructive)
        self.assertFalse(plan.steps[1].is_destructive)
        self.assertTrue(plan.steps[2].is_destructive)

        # Initial run executes step 1 & 2, then pauses at step 3 awaiting permission
        res = self.agent.execute_plan(plan.plan_id)
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "AWAITING_PERMISSION")
        self.assertEqual(res["step"]["step_id"], 3)
        self.assertIn("organize_files_move", res["step"]["action_name"])

        # Grant permission and complete step 3
        granted = self.agent.grant_permission(plan.plan_id, 3, "CONFIRM")
        self.assertTrue(granted)

        res2 = self.agent.execute_plan(plan.plan_id)
        self.assertTrue(res2["ok"])
        self.assertEqual(res2["status"], "COMPLETED")
        self.assertTrue((target_dir / "item1.tmp").exists())
        self.assertTrue((target_dir / "item2.tmp").exists())

    def test_02_test_runner_workflow(self):
        plan = self.agent.create_test_runner_plan(target="tests/test_stonic_experience_and_distribution.py")
        self.assertEqual(len(plan.steps), 3)
        for s in plan.steps:
            self.assertFalse(s.is_destructive)

        # All steps are non-destructive and run autonomously
        res = self.agent.execute_plan(plan.plan_id)
        self.assertTrue(res["ok"])
        self.assertEqual(res["status"], "COMPLETED")
        self.assertIn("QA Regression Verification", res["report"])

    def test_03_document_reader_workflow(self):
        sample_doc = Path(self.temp_dir) / "GUIDE.md"
        sample_doc.write_text("# Overview\nJ.A.R.V.I.S. Architecture\n## Components\nVoice and Agent", encoding="utf-8")

        plan = self.agent.create_document_reader_plan(file_path=str(sample_doc))
        self.assertEqual(len(plan.steps), 3)

        res = self.agent.execute_plan(plan.plan_id)
        self.assertTrue(res["ok"])
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(plan.steps[0].status, "VERIFIED")
        self.assertEqual(plan.steps[1].status, "VERIFIED")
        self.assertEqual(plan.steps[2].status, "VERIFIED")
        self.assertIn("GUIDE.md", plan.steps[0].observed_result)

    def test_04_code_assistant_workflow(self):
        code_file = Path(self.temp_dir) / "sample_service.py"
        code_file.write_text("class Companion:\n    def speak(self):\n        pass\n", encoding="utf-8")

        plan = self.agent.create_code_assistant_plan(file_path=str(code_file), issue_description="Syntax and AST check")
        self.assertEqual(len(plan.steps), 3)
        self.assertTrue(plan.steps[2].is_destructive)

        # Executes step 1 & 2 autonomously, pauses before step 3
        res = self.agent.execute_goal(f"Code assistant on {code_file}")
        self.assertEqual(res["status"], "AWAITING_PERMISSION")
        self.assertEqual(res["step"]["step_id"], 3)

        # Confirm step 3
        self.agent.grant_permission(plan.plan_id, 3, "CONFIRM")
        res2 = self.agent.execute_plan(plan.plan_id)
        self.assertTrue(res2["ok"])
        self.assertEqual(res2["status"], "COMPLETED")

    def test_05_emergency_stop_button(self):
        plan = self.agent.create_plan("Long running plan", [
            {"action_name": "system_status", "parameters": {}, "description": "Step 1"},
            {"action_name": "system_status", "parameters": {}, "description": "Step 2"},
            {"action_name": "system_status", "parameters": {}, "description": "Step 3"}
        ])
        # Trigger stop before execute
        self.agent.stop(plan.plan_id)
        res = self.agent.execute_plan(plan.plan_id)
        self.assertFalse(res["ok"])
        self.assertEqual(res["status"], "STOPPED")

    def test_06_audit_logging_and_secret_scrubbing(self):
        self.agent.log_audit("TEST_CALL", {"api_key": "sk-1234567890abcdef1234567890", "token": "dpapi:v1:secretkey123"}, "OK")
        audits = self.agent.get_recent_audit(limit=10)
        self.assertTrue(len(audits) >= 1)
        last_log = audits[-1]
        self.assertNotIn("sk-1234567890", last_log)
        self.assertIn("[REDACTED_SECRET]", last_log)


if __name__ == "__main__":
    unittest.main()
