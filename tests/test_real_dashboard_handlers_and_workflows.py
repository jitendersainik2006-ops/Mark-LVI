"""
tests/test_real_dashboard_handlers_and_workflows.py — End-to-End Functional Verification of 12 Handlers & 4 PC Agent Workflows
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from starlette.testclient import TestClient

from core.computer_agent import ComputerAgent, computer_agent
from dashboard.server import DashboardServer


class TestRealDashboardHandlersAndWorkflows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = DashboardServer()
        cls.client = TestClient(cls.server.app)

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.audit_log = Path(self.temp_dir) / "handler_test_audit.log"
        self.agent = ComputerAgent(audit_file=self.audit_log)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ── 12 Dashboard Handlers Real API Testing ────────────────────────────────

    def test_01_handler_rollback_proposal(self):
        # Invalid proposal ID returns clean failure without crash
        resp = self.client.post("/api/skills/rollback", json={"proposal_id": "nonexistent_999"})
        self.assertEqual(resp.status_code, 200)
        d = resp.json()
        self.assertFalse(d.get("ok"))
        self.assertIn("error", d)

    def test_02_handler_voice_diagnostics_live_api(self):
        resp = self.client.get("/api/voice/diagnostics")
        self.assertEqual(resp.status_code, 200)
        d = resp.json()
        self.assertTrue(d.get("ok"))
        self.assertIn("diagnostics", d)
        diag = d["diagnostics"]
        self.assertIn("audio_devices", diag)
        self.assertIn("llm", diag)
        self.assertIn("overall_health", diag)

    def test_03_handler_system_health_and_status(self):
        resp = self.client.get("/api/system/health")
        self.assertEqual(resp.status_code, 200)
        d = resp.json()
        self.assertEqual(d.get("status"), "healthy")
        self.assertEqual(d.get("version"), "56.1.0")

        resp_st = self.client.get("/api/system/status")
        self.assertEqual(resp_st.status_code, 200)
        dst = resp_st.json()
        self.assertIn("status", dst)

    def test_04_handler_knowledge_search_and_add_text(self):
        # Add text note
        title = "Integration Test Note"
        content = "J.A.R.V.I.S. Mark LVI is a high performance AI assistant with continuous voice and multi-agent coordination."
        add_resp = self.client.post("/api/knowledge/add_text", json={"title": title, "text": content})
        self.assertEqual(add_resp.status_code, 200)
        add_data = add_resp.json()
        self.assertTrue(add_data.get("ok"))

        # Search knowledge
        search_resp = self.client.post("/api/knowledge/search", json={"query": "continuous voice"})
        self.assertEqual(search_resp.status_code, 200)
        s_data = search_resp.json()
        self.assertTrue(s_data.get("ok"))
        self.assertIn("matches", s_data)

    def test_05_handler_memory_network_node_lifecycle(self):
        # Create memory node
        node_data = {
            "category": "preferences",
            "label": "Favorite Language",
            "content": "User prefers Hindi and Hinglish voice responses with English technical terms."
        }
        res = self.client.post("/api/memory/network/node", json=node_data)
        self.assertEqual(res.status_code, 200)
        d = res.json()
        self.assertTrue(d.get("ok"))
        node_id = d.get("node_id") or "Favorite Language"

        # Query memory network
        q_res = self.client.get("/api/memory/network?category=preferences")
        self.assertEqual(q_res.status_code, 200)
        qd = q_res.json()
        self.assertTrue(qd.get("ok"))

        # Delete node
        del_res = self.client.delete(f"/api/memory/network/node/{node_id}")
        self.assertEqual(del_res.status_code, 200)

    def test_06_handler_task_manager_lifecycle(self):
        # Create task
        t_data = {"title": "Verify Audio Hardware Diagnostics", "action_name": "system_status", "priority": "high"}
        c_res = self.client.post("/api/tasks", json=t_data)
        self.assertEqual(c_res.status_code, 200)
        cd = c_res.json()
        self.assertTrue(cd.get("ok"))
        task_id = cd.get("task", {}).get("id")

        # Query tasks
        t_list = self.client.get("/api/tasks")
        self.assertEqual(t_list.status_code, 200)
        ld = t_list.json()
        self.assertTrue(any(t.get("id") == task_id for t in ld.get("tasks", [])))

        # Task pause, resume, history
        if task_id:
            p_res = self.client.post(f"/api/tasks/{task_id}/pause")
            self.assertEqual(p_res.status_code, 200)
            r_res = self.client.post(f"/api/tasks/{task_id}/resume", json={"approved": True})
            self.assertEqual(r_res.status_code, 200)
            h_res = self.client.get(f"/api/tasks/{task_id}/history")
            self.assertEqual(h_res.status_code, 200)

    def test_07_handler_lan_pairing_and_character_update(self):
        # LAN Pairing Enable
        res = self.client.post("/api/lan-pairing/enable", json={})
        self.assertEqual(res.status_code, 200)
        d = res.json()
        self.assertTrue(d.get("ok"))
        self.assertIn("pairing_code", d)

        # Character Configuration Update
        char_res = self.client.post("/api/character/update", json={"voice_profile": "SWARA_HINDI", "language_mode": "hinglish"})
        self.assertEqual(char_res.status_code, 200)
        cd = char_res.json()
        self.assertTrue(cd.get("ok"))

    def test_08_handler_gmail_draft_creation(self):
        draft_payload = {
            "recipient": "review@example.com",
            "subject": "System Verification Checklist",
            "body": "All safety gates and workflows verified."
        }
        res = self.client.post("/api/gmail/draft", json=draft_payload)
        self.assertEqual(res.status_code, 200)
        d = res.json()
        self.assertTrue(d.get("ok"))

    # ── 4 Computer Agent Workflows Real Execution Testing ─────────────────────

    def test_09_workflow_file_organizer_in_temp_fixture(self):
        src_dir = Path(self.temp_dir) / "source_downloads"
        src_dir.mkdir(parents=True, exist_ok=True)
        (src_dir / "file_alpha.tmp").write_text("Alpha data", encoding="utf-8")
        (src_dir / "file_beta.tmp").write_text("Beta data", encoding="utf-8")
        tgt_dir = Path(self.temp_dir) / "organized_dest"

        plan = self.agent.create_file_organizer_plan(
            source_dir=str(src_dir),
            pattern="*.tmp",
            target_dir=str(tgt_dir)
        )
        # Execute until confirmation gate
        res = self.agent.execute_plan(plan.plan_id)
        self.assertEqual(res["status"], "AWAITING_PERMISSION")
        self.assertEqual(plan.steps[0].status, "VERIFIED")
        self.assertEqual(plan.steps[1].status, "VERIFIED")

        # Grant confirmation and complete relocation
        granted = self.agent.grant_permission(plan.plan_id, 3, "CONFIRM")
        self.assertTrue(granted)
        res_comp = self.agent.execute_plan(plan.plan_id)
        self.assertEqual(res_comp["status"], "COMPLETED")
        self.assertTrue((tgt_dir / "file_alpha.tmp").exists())
        self.assertTrue((tgt_dir / "file_beta.tmp").exists())

    def test_10_workflow_test_runner(self):
        plan = self.agent.create_test_runner_plan(target="tests/test_ui_security_xss.py")
        res = self.agent.execute_plan(plan.plan_id)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertTrue(plan.steps[0].verification_passed)
        self.assertTrue(plan.steps[1].verification_passed)
        self.assertTrue(plan.steps[2].verification_passed)
        self.assertIn("QA Regression Verification", plan.steps[2].observed_result)

    def test_11_workflow_document_reader_in_temp_fixture(self):
        fixture_doc = Path(self.temp_dir) / "SYSTEM_DESIGN.md"
        fixture_doc.write_text("# Core Architecture\nHigh fidelity companion.\n## Operational Boundaries\nStrict gates.", encoding="utf-8")

        plan = self.agent.create_document_reader_plan(file_path=str(fixture_doc))
        res = self.agent.execute_plan(plan.plan_id)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertIn("SYSTEM_DESIGN.md", plan.steps[0].observed_result)
        self.assertIn("Executive Insights Summary", plan.steps[2].observed_result)

    def test_12_workflow_code_assistant_ast_and_gated_patch(self):
        module_path = Path(self.temp_dir) / "target_service.py"
        module_path.write_text("def execute_task():\n    return 42\n", encoding="utf-8")

        plan = self.agent.create_code_assistant_plan(file_path=str(module_path), issue_description="Verify AST and add docstring")
        res = self.agent.execute_plan(plan.plan_id)
        # Step 1 & 2 pass, step 3 is gated
        self.assertEqual(res["status"], "AWAITING_PERMISSION")
        self.assertTrue(plan.steps[0].verification_passed)
        self.assertTrue(plan.steps[1].verification_passed)

        # Confirm step 3
        granted = self.agent.grant_permission(plan.plan_id, 3, "CONFIRM")
        self.assertTrue(granted)
        res_comp = self.agent.execute_plan(plan.plan_id)
        self.assertEqual(res_comp["status"], "COMPLETED")
        self.assertTrue(module_path.with_suffix(".py.bak").exists())


if __name__ == "__main__":
    unittest.main()
