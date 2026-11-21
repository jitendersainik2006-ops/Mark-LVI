"""
actions/manage_tasks.py — J.A.R.V.I.S. Task Management & Orchestration Tool

Allows the AI assistant and user to create, monitor, approve, cancel, and manage
background tasks with status tracking, priority scheduling, and human approval gates.
"""

from typing import Optional
from core.task_manager import task_manager


def manage_tasks(parameters: dict, player=None, **_) -> str:
    action = str(parameters.get("action", "list")).strip().lower()
    task_id = str(parameters.get("task_id", "")).strip()

    if action == "create":
        title = str(parameters.get("title", "")).strip()
        if not title:
            return "Please provide a 'title' for the task."
        description = str(parameters.get("description", "")).strip()
        priority = str(parameters.get("priority", "medium")).strip().lower()
        deadline = parameters.get("deadline")
        action_name = parameters.get("action_name")
        action_args = parameters.get("action_args") or {}

        task = task_manager.create_task(
            title=title,
            description=description,
            priority=priority,
            deadline=str(deadline) if deadline else None,
            action_name=str(action_name) if action_name else None,
            action_args=action_args if isinstance(action_args, dict) else {},
            source="voice",
        )
        if player:
            player.write_log(f"[Task] 📋 Created: {task.title} [{task.status}]")

        if task.status == "waiting_for_approval":
            return (
                f"Task created: '{task.title}' (ID: {task.id}). "
                f"This is a high-risk action requiring your explicit confirmation on the HUD or phone dashboard before execution."
            )
        return f"Task created and queued: '{task.title}' (ID: {task.id}, Priority: {task.priority})."

    if action == "list":
        filter_status = str(parameters.get("filter", "active")).strip().lower()
        tasks = task_manager.list_tasks(status=filter_status, limit=10)
        if not tasks:
            return f"No {filter_status} tasks found in the Task Manager."

        lines = [f"Found {len(tasks)} {filter_status} task(s):"]
        for t in tasks:
            prog = f" ({t.progress}%)" if t.status == "running" else ""
            lines.append(f"- [{t.status.upper()}]{prog} {t.title} (ID: {t.id}, Priority: {t.priority})")
        return "\n".join(lines)

    if action == "status":
        if not task_id:
            return "Please specify the 'task_id' to check status."
        task = task_manager.get_task(task_id)
        if not task:
            return f"Task '{task_id}' not found."
        details = [
            f"Task: {task.title} (ID: {task.id})",
            f"Status: {task.status.upper()}",
            f"Priority: {task.priority}",
            f"Progress: {task.progress}%",
            f"Created: {task.created_at}",
        ]
        if task.result:
            details.append(f"Result: {task.result}")
        if task.error:
            details.append(f"Error: {task.error}")
        return "\n".join(details)

    if action == "approve":
        if not task_id:
            return "Please specify the 'task_id' to approve."
        ok = task_manager.approve_task(task_id)
        if ok:
            if player:
                player.write_log(f"[Task] ✅ Approved {task_id}")
            return f"Task '{task_id}' has been approved and moved to execution queue."
        return f"Could not approve task '{task_id}'. It may not exist or is not waiting for approval."

    if action == "cancel":
        if not task_id:
            return "Please specify the 'task_id' to cancel."
        ok = task_manager.cancel_task(task_id)
        if ok:
            if player:
                player.write_log(f"[Task] 🛑 Cancelled {task_id}")
            return f"Task '{task_id}' has been cancelled."
        return f"Could not cancel task '{task_id}'. It may not exist or has already finished."

    if action == "retry":
        if not task_id:
            return "Please specify the 'task_id' to retry."
        ok = task_manager.retry_task(task_id)
        if ok:
            if player:
                player.write_log(f"[Task] 🔄 Retrying {task_id}")
            return f"Task '{task_id}' has been reset and requeued for execution."
        return f"Could not retry task '{task_id}'. Only failed or cancelled tasks can be retried."

    return f"Unknown task action: '{action}'. Use create, list, status, approve, cancel, or retry."


TOOL = {
    "name": "manage_tasks",
    "tier": "core",
    "brief": "Manage, create, list, check status, approve, or cancel background tasks.",
    "description": (
        "Create, view, monitor, approve, cancel, or retry tasks in J.A.R.V.I.S. Task Manager. "
        "Use action='create' to enqueue a background job. "
        "Use action='list' to check current or completed tasks. "
        "Use action='status' to get detailed progress of a specific task. "
        "Use action='approve' to confirm a task in waiting_for_approval. "
        "Use action='cancel' to stop a task. "
        "Use action='retry' to rerun a failed task."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "create | list | status | approve | cancel | retry"
            },
            "task_id": {
                "type": "STRING",
                "description": "The unique ID of the task for status, approve, cancel, or retry"
            },
            "title": {
                "type": "STRING",
                "description": "Short title describing the task (for create)"
            },
            "description": {
                "type": "STRING",
                "description": "Detailed explanation of the task (for create)"
            },
            "priority": {
                "type": "STRING",
                "description": "Priority: low | medium | high | urgent (default: medium)"
            },
            "deadline": {
                "type": "STRING",
                "description": "Optional deadline for task completion"
            },
            "action_name": {
                "type": "STRING",
                "description": "Optional tool name to run (e.g. system_status, web_search, delete_file)"
            },
            "action_args": {
                "type": "OBJECT",
                "description": "Parameters to pass to the tool action"
            },
            "filter": {
                "type": "STRING",
                "description": "Status filter for action='list': active | completed | all"
            }
        },
        "required": ["action"]
    },
    "handler": manage_tasks,
}
