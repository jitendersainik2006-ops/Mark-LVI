"""
actions/computer_agent.py — Computer-Use AI Agent Automation Tool
Exposes the controlled PC automation agent (PLAN -> ACT -> OBSERVE -> VERIFY)
to ActionRegistry, TaskManager, and LLMs with strict safety boundaries.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("JARVIS.Actions.ComputerAgent")


def computer_agent_handler(parameters: dict = None, **kwargs) -> str:
    """Executes a computer-use automation task within authorized scopes."""
    from core.computer_agent import computer_agent

    params = parameters or {}
    goal = str(params.get("goal") or params.get("command") or params.get("instruction") or "").strip()
    if not goal:
        return "Error: 'goal' description is required for computer_agent."

    steps_data = params.get("steps")
    try:
        res = computer_agent.execute_goal(goal, steps_data=steps_data)
        if isinstance(res, dict):
            status = res.get("status", "UNKNOWN")
            result_msg = res.get("result", "")
            steps_count = res.get("steps_completed", 0)
            return f"ComputerAgent [{status}]: {result_msg} ({steps_count} steps processed)."
        return str(res)
    except Exception as e:
        logger.error(f"Error in computer_agent execution: {e}")
        return f"ComputerAgent execution error: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "computer_agent",
    "description": (
        "Executes verified computer-use automation tasks (file organizing, testing, document reading, "
        "code diagnostics, system checks) following the PLAN -> ACT -> OBSERVE -> VERIFY lifecycle "
        "with confirmation gates for consequential actions."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "goal": {
                "type": "STRING",
                "description": "The objective or command to execute on the workstation."
            },
            "steps": {
                "type": "ARRAY",
                "description": "Optional pre-structured execution plan steps."
            }
        },
        "required": ["goal"]
    },
    "handler": computer_agent_handler,
}
