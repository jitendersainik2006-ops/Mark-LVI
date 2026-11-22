"""
actions/orchestrator_plan.py — Autonomous Multi-Agent Plan Execution Tool
Exposes the multi-agent orchestrator layer to ActionRegistry, TaskManager, and LLMs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("JARVIS.Actions.OrchestratorPlan")


def orchestrator_plan_handler(parameters: dict = None, **kwargs) -> str:
    """Executes or decomposes a multi-agent orchestration plan."""
    from core.orchestrator import orchestrator

    params = parameters or {}
    plan_id = str(params.get("plan_id") or params.get("id") or "").strip()

    if not plan_id:
        objective = str(params.get("objective") or params.get("goal") or "").strip()
        if objective:
            try:
                plan = orchestrator.create_plan(objective)
                plan_id = plan.plan_id
            except Exception as e:
                return f"Failed to create orchestration plan: {e}"
        else:
            return "Error: Either 'plan_id' or 'objective' is required to run orchestrator_plan."

    try:
        res = orchestrator.execute_plan(plan_id)
        if isinstance(res, dict):
            if res.get("ok"):
                completed = res.get("completed_steps", 0)
                total = res.get("total_steps", 0)
                status = res.get("status", "completed")
                return f"Multi-Agent Plan '{plan_id}' executed ({status}): {completed}/{total} steps completed."
            else:
                return f"Multi-Agent Plan '{plan_id}' failed: {res.get('error', 'Execution error')}"
        return str(res)
    except Exception as e:
        logger.error(f"Error executing plan '{plan_id}': {e}")
        return f"Orchestrator plan execution error: {e}"


# ── Tool declaration (auto-discovered by core/action_loader.py) ──────────────
TOOL = {
    "name": "orchestrator_plan",
    "description": (
        "Decomposes and executes multi-agent orchestration plans across specialized agent roles "
        "(Research, Coding, File, Browser, Document, System, Knowledge). Call when a task requires "
        "autonomous multi-step coordination, research, or structured execution."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "plan_id": {
                "type": "STRING",
                "description": "The unique ID of an existing orchestration plan to execute."
            },
            "objective": {
                "type": "STRING",
                "description": "High-level goal or objective to decompose into a new multi-agent plan and execute."
            }
        }
    },
    "handler": orchestrator_plan_handler,
}
