"""
tests/test_action_registry_and_tools.py — Test ActionRegistry Discovery and Execution of Core Actions
Verifies that:
- system_status is discovered and returns live hardware telemetry.
- orchestrator_plan is discovered and executes multi-agent plans.
- computer_agent is discovered and executes PC automation safely.
- TaskManager routes and executes these actions cleanly without 'action not found' errors.
"""

import asyncio
import unittest
from pathlib import Path

from core.action_loader import discover_actions
from core.task_manager import TaskManager


class TestActionRegistryAndTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actions_dir = Path(__file__).resolve().parent.parent / "actions"
        cls.registry = discover_actions(cls.actions_dir, logger=lambda m: None)

    def test_01_core_actions_discovered(self):
        self.assertTrue(self.registry.has("system_status"), "system_status must be discovered in ActionRegistry")
        self.assertTrue(self.registry.has("orchestrator_plan"), "orchestrator_plan must be discovered in ActionRegistry")
        self.assertTrue(self.registry.has("computer_agent"), "computer_agent must be discovered in ActionRegistry")

    def test_02_system_status_execution(self):
        res = self.registry.run("system_status", {})
        self.assertIsInstance(res, str)
        self.assertIn("System Status:", res)
        self.assertIn("CPU:", res)
        self.assertIn("RAM:", res)
        self.assertIn("Uptime:", res)

    def test_03_orchestrator_plan_execution(self):
        # Create and execute plan with goal
        res = self.registry.run("orchestrator_plan", {"objective": "Audit system configuration"})
        self.assertIsInstance(res, str)
        self.assertIn("Multi-Agent Plan", res)
        self.assertIn("completed", res.lower())

    def test_04_computer_agent_execution(self):
        res = self.registry.run("computer_agent", {"goal": "Check system status and display metrics"})
        self.assertIsInstance(res, str)
        self.assertIn("ComputerAgent", res)

    def test_05_task_manager_autonomous_action_execution(self):
        tm = TaskManager.get_instance()
        # Create a low-risk autonomous task
        task = tm.create_task(
            title="Periodic Telemetry Collection",
            action_name="system_status",
            action_args={},
            requires_approval=False
        )
        self.assertEqual(task.status, "queued")

        # Execute task via TaskManager worker loop
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(tm._execute_task(task))
        finally:
            loop.close()

        updated = tm.get_task(task.id)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, "completed")
        self.assertEqual(updated.progress, 100)
        self.assertIn("System Status:", updated.result)


if __name__ == "__main__":
    unittest.main()
