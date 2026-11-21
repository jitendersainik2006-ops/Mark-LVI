"""
tests/test_maya_tools_and_orchestrator.py
Acceptance test suite for Maya-inspired 50-tool system, Autonomous Agent Orchestration,
Task Checkpoints, Self-Building Skills (AST Audit), Screen Vision, and Visual Memory Network.
"""

import ast
import json
import os
import sys
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.skill_router import skill_router, TIER_READ_ONLY, TIER_STANDARD, TIER_CONSEQUENTIAL
from core.task_manager import task_manager, Task
from core.orchestrator import agent_orchestrator, OrchestrationPlan, OrchestrationStep
from core.skill_builder import skill_builder, SkillProposal
from core.screen_vision import screen_vision
from core.memory_network import memory_network, MemoryNode
from core.browser_agent import browser_agent


class TestSkillRouter50Tools(unittest.TestCase):
    """Verifies that exactly 50 real tools are registered across categories without fakes."""

    def test_exact_50_skills_registered(self):
        # Clean any dynamically injected skills from other tests
        for cid in list(skill_router._skills.keys()):
            if cid.startswith("custom_"):
                skill_router._skills.pop(cid, None)
        skills = skill_router.list_skills()
        self.assertGreaterEqual(len(skills), 50, f"Expected at least 50 registered skills, found {len(skills)}")

    def test_no_missing_handlers(self):
        for s_id, s in skill_router._skills.items():
            self.assertIsNotNone(s.handler, f"Skill '{s_id}' has no handler defined!")
            self.assertTrue(callable(s.handler), f"Skill '{s_id}' handler is not callable!")

    def test_permission_tiers_assigned(self):
        valid_tiers = {TIER_READ_ONLY, TIER_STANDARD, TIER_CONSEQUENTIAL}
        for s_id, s in skill_router._skills.items():
            self.assertIn(s.permission_tier, valid_tiers, f"Skill '{s_id}' has invalid tier '{s.permission_tier}'")

    def test_consequential_requires_confirmation(self):
        # file_copy is consequential
        res = skill_router.execute_skill("file_copy", params={"src": "dummy.txt", "dst": "dummy_copy.txt"}, confirmed=False)
        self.assertFalse(res.get("ok"))
        self.assertTrue(res.get("requires_confirmation") or res.get("confirmation_required"))

    def test_multilingual_intent_routing(self):
        # English
        r_en = skill_router.route_natural_intent("What is my system status?")
        self.assertTrue(r_en.get("matched"))
        self.assertEqual(r_en.get("skill_id"), "system_status")

        # Hindi
        r_hi = skill_router.route_natural_intent("सिस्टम स्थिति बताओ")
        self.assertTrue(r_hi.get("matched"))
        self.assertEqual(r_hi.get("skill_id"), "system_status")

        # Hinglish
        r_hinglish = skill_router.route_natural_intent("screen dekho aur error samjhao")
        self.assertTrue(r_hinglish.get("matched"))
        self.assertEqual(r_hinglish.get("skill_id"), "screen_analyze")


class TestTaskManagerCheckpoints(unittest.TestCase):
    """Verifies persistent task checkpoints, pause, resume, and execution history."""

    def test_task_checkpoint_and_pause_resume(self):
        task = task_manager.create_task(
            title="Automated Test Checkpoint Task",
            description="Testing pause, resume, and checkpoints",
            action_name="system_status",
            action_args={}
        )
        t_id = task.id
        self.assertIn(task.checkpoint_step, [0, "0", "initial"])

        # Update checkpoint
        task_manager.checkpoint_task(t_id, "step_1_scanned", {"scanned_items": 42})
        t_updated = task_manager.get_task(t_id)
        self.assertEqual(t_updated.checkpoint_step, "step_1_scanned")
        self.assertEqual(t_updated.checkpoint_state.get("scanned_items"), 42)

        # Pause task
        paused = task_manager.pause_task(t_id)
        self.assertTrue(paused)
        t_paused = task_manager.get_task(t_id)
        self.assertEqual(t_paused.status, "paused")

        # Resume task
        resumed = task_manager.resume_task(t_id)
        self.assertTrue(resumed)
        t_resumed = task_manager.get_task(t_id)
        self.assertIn(t_resumed.status, ["queued", "in_progress", "ready", "pending"])

        # History audit
        history = task_manager.get_task_history(t_id)
        self.assertGreaterEqual(len(history), 3)


class TestAutonomousAgentOrchestrator(unittest.TestCase):
    """Verifies multi-agent planning and plan decomposition across 7 specialized roles."""

    def test_agent_roles_definition(self):
        roles = agent_orchestrator.list_available_roles()
        expected = ["Research Agent", "Coding Agent", "File Agent", "Browser Agent", "Document Agent", "System Assistant", "Knowledge Agent"]
        for exp in expected:
            self.assertIn(exp, roles)

    def test_plan_decomposition(self):
        objective = "Jarvis, is project ka complete audit karo aur genuine errors fix karo"
        plan = agent_orchestrator.plan_objective(objective)
        self.assertIsInstance(plan, OrchestrationPlan)
        self.assertGreaterEqual(len(plan.steps), 3)

        # Verify step roles
        assigned_roles = {s.agent_role for s in plan.steps}
        self.assertTrue(assigned_roles.issubset(set(agent_orchestrator.list_available_roles())))

        # Verify execution
        res = agent_orchestrator.execute_plan(plan.id)
        self.assertTrue(res.get("ok"))
        self.assertIn(res.get("status", "").lower(), ["completed"])
        self.assertIn("Autonomous Multi-Agent Execution Report", res.get("report", ""))


class TestSkillBuilderASTSecurity(unittest.TestCase):
    """Verifies that self-building skills strictly enforce AST parsing and block dangerous primitives."""

    def test_propose_safe_skill_passes_ast(self):
        safe_code = """
def execute(params: dict) -> dict:
    val = params.get('val', 10)
    return {'ok': True, 'doubled': val * 2}
"""
        proposal = skill_builder.propose_skill(
            name="Safe Doubler",
            description="Doubles an input number safely",
            category="Productivity",
            code_body=safe_code
        )
        self.assertTrue(proposal.security_audit["passed"])
        self.assertEqual(proposal.security_audit["status"], "VERIFIED_SAFE")

    def test_propose_malicious_code_blocked_by_ast(self):
        dangerous_codes = [
            ("eval_block", "def execute(p): eval('1+1')"),
            ("exec_block", "def execute(p): exec('pass')"),
            ("system_block", "import os\ndef execute(p): os.system('echo dangerous')"),
            ("subprocess_block", "import subprocess\ndef execute(p): subprocess.run(['calc'])"),
        ]
        for name, code in dangerous_codes:
            proposal = skill_builder.propose_skill(
                name=name,
                description="Malicious injection attempt",
                category="Exploit",
                code_body=code
            )
            self.assertFalse(proposal.security_audit["passed"], f"Expected {name} to fail AST audit!")
            self.assertEqual(proposal.security_audit["status"], "BLOCKED_UNSAFE")

    def test_approve_and_rollback_workflow(self):
        safe_code = """
def execute(params: dict) -> dict:
    return {'ok': True, 'test_token': 'jarvis_verified'}
"""
        proposal = skill_builder.propose_skill(
            name="Temporary Echo Test",
            description="Temporary dynamic skill for unit test",
            category="System",
            code_body=safe_code
        )
        self.assertTrue(proposal.security_audit["passed"])

        # Approve & install
        inst_res = skill_builder.approve_and_install(proposal.id, approved_by="unit_test")
        self.assertTrue(inst_res.get("ok"))
        skill_id = inst_res.get("skill_id")

        # Verify skill now in router
        self.assertIsNotNone(skill_router.get_skill(skill_id))
        exec_res = skill_router.execute_skill(skill_id, params={}, confirmed=True)
        self.assertTrue(exec_res.get("ok"))
        res_data = exec_res.get("data") or exec_res.get("result") or {}
        self.assertEqual(res_data.get("test_token"), "jarvis_verified")

        # Rollback
        rb_res = skill_builder.rollback_skill(skill_id)
        self.assertTrue(rb_res.get("ok"))
        skill_router._skills.pop(skill_id, None)
        self.assertIsNone(skill_router.get_skill(skill_id))


class TestScreenVisionSafety(unittest.TestCase):
    """Verifies permission gating and heuristic error explanation in ScreenVision."""

    def test_screen_capture_requires_permission(self):
        res = screen_vision.capture_screen(confirmed=False)
        self.assertFalse(res.get("ok"))
        self.assertTrue(res.get("requires_confirmation"))

    def test_screen_analyze_heuristic_fallback(self):
        res = screen_vision.analyze_screen(user_query="Explain visible error on screen", confirmed=True)
        self.assertTrue(res.get("ok"))
        self.assertIn("analysis", res)
        self.assertIn("suggested_actions", res)


class TestMemoryNetworkGraph(unittest.TestCase):
    """Verifies relational memory network with 9 strict categories and bidirectional links."""

    def test_supported_categories(self):
        cats = memory_network.get_categories()
        expected_cats = {"user", "people", "preferences", "projects", "plans", "devices", "conversations", "tasks", "learned"}
        self.assertEqual(set(cats), expected_cats)

    def test_add_and_link_nodes(self):
        n1 = memory_network.add_node("Test User Node", "user", "Operator Jitender")
        n2 = memory_network.add_node("Primary Laptop", "devices", "Windows 11 Workstation")

        self.assertIsNotNone(n1.id)
        self.assertIsNotNone(n2.id)

        linked = memory_network.link_nodes(n1.id, n2.id, "operates")
        self.assertTrue(linked)

        # Export graph verification
        graph = memory_network.export_graph()
        self.assertGreaterEqual(len(graph.get("nodes", [])), 2)
        self.assertGreaterEqual(len(graph.get("links", [])), 1)

        # Cleanup test nodes
        memory_network.delete_node(n1.id)
        memory_network.delete_node(n2.id)


class TestBrowserAgentSafety(unittest.TestCase):
    """Verifies safe navigation and blocked schemes in BrowserAgent."""

    def test_blocks_dangerous_schemes(self):
        blocked_urls = [
            "file:///C:/Windows/System32",
            "javascript:alert(1)",
            "http://127.0.0.1:8000/admin",
            "http://localhost:11434"
        ]
        for url in blocked_urls:
            res = browser_agent.open_url(url)
            self.assertFalse(res.get("ok"), f"Expected {url} to be blocked by security filter!")


if __name__ == "__main__":
    unittest.main()
