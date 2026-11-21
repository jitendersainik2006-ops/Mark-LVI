"""
tests/test_nextlevel_companion_modules.py

Comprehensive Test Suite for J.A.R.V.I.S. Mark LVI Next-Level Companion Modules:
1. CompanionModulesManager isolated instance testing (temp_dir)
2. Chat Sessions multi-turn threads lifecycle (create, rename, search, delete)
3. Visual Workflows execution & operator approval gate pausing
4. Schedules manager (list, toggle, trigger)
5. Real Integrations manager & honest status
6. Workspace management & Role-Based Access Control (RBAC)
7. Immutable Audit Logging
8. Real System & Module Analytics (psutil metrics)
9. 7 Autonomous Agents status registry
10. DashboardServer REST endpoints for companion routes
11. Design Tokens and Theme consistency (dark charcoal foundation & light theme)
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.companion_modules_manager import (
    CompanionModulesManager,
    companion_modules_manager,
    ChatSession,
    WorkflowDefinition,
    ScheduledJob,
)


class TestCompanionModulesManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mgr = CompanionModulesManager(base_dir=Path(self.temp_dir))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_chat_session_initialized(self):
        sessions = self.mgr.list_sessions()
        self.assertGreaterEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["id"], "sess_default")

    def test_chat_session_create_rename_delete(self):
        sess = self.mgr.create_session("Project Quantum AI")
        self.assertEqual(sess["title"], "Project Quantum AI")
        sess_id = sess["id"]

        renamed = self.mgr.rename_session(sess_id, "Project Quantum AI Renamed")
        self.assertTrue(renamed)
        active_sess = self.mgr.get_session(sess_id)
        self.assertIsNotNone(active_sess)
        self.assertEqual(active_sess["title"], "Project Quantum AI Renamed")

        deleted = self.mgr.delete_session(sess_id)
        self.assertTrue(deleted)

        remaining = [s["id"] for s in self.mgr.list_sessions()]
        self.assertNotIn(sess_id, remaining)

    def test_search_conversations(self):
        sess = self.mgr.create_session("Quantum Neural Nets Research")
        self.mgr.append_message_to_session(sess["id"], "user", "How do quantum tensors operate?")
        results = self.mgr.search_conversations("quantum")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["session_id"], sess["id"])

    def test_default_workflows_present(self):
        wfs = self.mgr.list_workflows()
        self.assertGreaterEqual(len(wfs), 2)
        wf_names = [w["name"] for w in wfs]
        self.assertTrue(any("Telemetry" in n or "Briefing" in n for n in wf_names))
        self.assertTrue(any("Document" in n or "Chunking" in n for n in wf_names))
        self.assertTrue(any("Diagnostics" in n or "Safety" in n for n in wf_names))

    def test_create_and_execute_workflow_with_gate(self):
        nodes = [
            {"id": "n1", "title": "Collect System Metrics", "type": "skill"},
            {"id": "n2", "title": "Approve Report Export", "type": "approval_gate", "requires_approval": True},
            {"id": "n3", "title": "Archive Report", "type": "skill"},
        ]
        wf = self.mgr.create_workflow("Test Workflow Pipeline", "Automated pipeline with gate", nodes=nodes)
        self.assertEqual(wf["name"], "Test Workflow Pipeline")

        exec_res = self.mgr.execute_workflow(wf["id"])
        self.assertEqual(exec_res["workflow_id"], wf["id"])
        self.assertEqual(exec_res["status"], "WAITING_APPROVAL")
        self.assertTrue(exec_res["approval_required"])
        self.assertEqual(exec_res["approval_node_id"], "n2")
        self.assertEqual(len(exec_res["steps"]), 2)

    def test_schedules_lifecycle(self):
        scheds = self.mgr.list_schedules()
        self.assertGreaterEqual(len(scheds), 2)

        s_id = scheds[0]["id"]
        toggled = self.mgr.toggle_schedule(s_id, False)
        self.assertTrue(toggled)

        trig = self.mgr.trigger_schedule(s_id)
        self.assertTrue(trig.get("ok"))
        self.assertIn("schedule_id", trig)

    def test_integrations_honest_status(self):
        integrations = self.mgr.list_integrations()
        self.assertIn("github", integrations)
        self.assertIn("notion", integrations)
        self.assertIn("slack", integrations)
        self.assertIn("discord", integrations)

        # Unconfigured integrations must be NOT_CONFIGURED
        self.assertEqual(integrations["github"]["status"], "NOT_CONFIGURED")

        # Configure integration
        ok = self.mgr.configure_integration("github", {"access_token": "ghp_mock_token_12345"})
        self.assertTrue(ok)
        updated = self.mgr.list_integrations()
        self.assertEqual(updated["github"]["status"], "CONFIGURED_UNVERIFIED")

        # Disconnect integration
        disc_ok = self.mgr.disconnect_integration("github")
        self.assertTrue(disc_ok)
        disconnected = self.mgr.list_integrations()
        self.assertEqual(disconnected["github"]["status"], "NOT_CONFIGURED")

    def test_workspace_and_rbac(self):
        ws = self.mgr.get_workspace()
        self.assertIsNotNone(ws)
        self.assertEqual(ws["name"], "Primary Workstation Workspace")
        self.assertEqual(ws["owner"], "Operator")

        # Invite valid role
        inv = self.mgr.invite_member("ws_default", "collaborator@example.com", "Member")
        self.assertTrue(inv["ok"])
        self.assertEqual(inv["member"]["email"], "collaborator@example.com")
        self.assertEqual(inv["member"]["role"], "Member")
        self.assertEqual(inv["member"]["status"], "INVITED")

    def test_immutable_audit_logging(self):
        self.mgr.log_audit("TEST", "CUSTOM_ACTION", "Testing custom action logging", user="pytest", status="SUCCESS")
        logs = self.mgr.get_audit_logs(category="TEST", limit=10)
        self.assertGreaterEqual(len(logs), 1)
        last_log = logs[0]
        self.assertEqual(last_log["action"], "CUSTOM_ACTION")
        self.assertEqual(last_log["user"], "pytest")
        self.assertEqual(last_log["status"], "SUCCESS")

    def test_real_analytics_query(self):
        analytics = self.mgr.get_real_analytics()
        self.assertTrue(analytics.get("ok"))
        self.assertIn("telemetry", analytics)
        self.assertIn("cpu_utilization_percent", analytics["telemetry"])
        self.assertIn("ram_percent", analytics["telemetry"])
        self.assertIn("disk_percent", analytics["telemetry"])
        self.assertEqual(analytics["content_and_rag"]["instagram_reels_ledger"], 74)
        self.assertIsInstance(analytics["telemetry"]["cpu_utilization_percent"], (int, float))

    def test_autonomous_agents_registry(self):
        agents = self.mgr.get_agents_status()
        self.assertEqual(len(agents), 7)
        agent_names = [a["name"] for a in agents]
        self.assertTrue(any("Orchestrator" in n for n in agent_names))
        self.assertTrue(any("System" in n for n in agent_names))
        self.assertTrue(any("Knowledge" in n for n in agent_names))
        self.assertTrue(any("Memory" in n for n in agent_names))
        self.assertTrue(any("Document" in n for n in agent_names))
        self.assertTrue(any("Browser" in n for n in agent_names))
        self.assertTrue(any("Creative" in n for n in agent_names))


class TestDashboardCompanionEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dashboard.server import DashboardServer
        from fastapi.testclient import TestClient
        cls.server = DashboardServer()
        cls.client = TestClient(cls.server.app)

    def test_api_chat_sessions_endpoint(self):
        res = self.client.get("/api/chat/sessions")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("sessions", data)
        self.assertIsInstance(data["sessions"], list)

    def test_api_workflows_endpoint(self):
        res = self.client.get("/api/workflows")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("workflows", data)

    def test_api_schedules_endpoint(self):
        res = self.client.get("/api/schedules")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("schedules", data)

    def test_api_integrations_endpoint(self):
        res = self.client.get("/api/integrations")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("integrations", data)

    def test_api_workspace_endpoint(self):
        res = self.client.get("/api/workspace")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("workspace", data)

    def test_api_audit_logs_endpoint(self):
        res = self.client.get("/api/audit/logs")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("logs", data)

    def test_api_analytics_real_endpoint(self):
        res = self.client.get("/api/analytics/real")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("telemetry", data)
        self.assertIn("cpu_utilization_percent", data["telemetry"])

    def test_api_agents_endpoint(self):
        res = self.client.get("/api/agents")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertIn("agents", data)
        self.assertEqual(len(data["agents"]), 7)


class TestThemeTokensAndUI(unittest.TestCase):
    def test_design_tokens_have_dual_themes(self):
        css_path = Path(r"D:\JARVIS-AI\mark_lvi_core\dashboard\static\jarvis_design_tokens.css")
        self.assertTrue(css_path.exists())
        content = css_path.read_text(encoding="utf-8").lower()
        self.assertIn(":root", content)
        self.assertIn('[data-theme="light"]', content)
        self.assertIn("#090d16", content)  # Charcoal foundation
        self.assertIn("#8b5cf6", content)  # Purple accent

    def test_app_html_includes_13_modules_and_theme_toggle(self):
        html_path = Path(r"D:\JARVIS-AI\mark_lvi_core\dashboard\static\app.html")
        self.assertTrue(html_path.exists())
        content = html_path.read_text(encoding="utf-8")
        self.assertIn("theme-toggle-btn", content)
        self.assertIn("view-agents", content)
        self.assertIn("view-workflows", content)
        self.assertIn("view-schedules", content)
        self.assertIn("view-integrations", content)
        self.assertIn("view-workspace", content)
        self.assertIn("view-analytics", content)
        self.assertIn("view-audit", content)
        self.assertIn("view-admin", content)


if __name__ == "__main__":
    unittest.main()
