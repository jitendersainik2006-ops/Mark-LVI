"""
core/task_manager.py — Persistent Background Task Manager & Execution Engine

Provides a complete task management subsystem for J.A.R.V.I.S.:
- Full task lifecycle: queued, running, waiting_for_approval, completed, failed, cancelled, paused.
- Persistence across restarts in data/tasks.json.
- Step-by-step progress tracking (0-100% and detailed steps).
- Priority queues (urgent > high > medium > low).
- Safety gating: autonomous execution for low-risk actions, strict human confirmation
  for consequential actions (file deletion, external messaging, system alterations).
- Deduplication within a sliding time window.
- Event broadcasting to laptop HUD and phone dashboard via registered listeners.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
TASKS_FILE = DATA_DIR / "tasks.json"

# Priorities
PRIORITY_ORDER = {"urgent": 0, "high": 1, "medium": 2, "low": 3}

# Low-risk action allowlist — can run autonomously
LOW_RISK_ACTIONS = {
    "system_status",
    "web_search",
    "reminder",
    "weather_report",
    "screen_process",
    "recall_memory",
    "manage_memory",
    "manage_monitor",
    "read_file",
    "summarize_file",
    "run_project_test",
}

# Consequential / high-risk actions requiring explicit human approval
HIGH_RISK_ACTIONS = {
    "delete_file",
    "overwrite_file",
    "install_software",
    "computer_settings",
    "send_message",
    "shutdown_jarvis",
}

# Deduplication window in seconds
DEDUP_WINDOW_SECONDS = 15.0


@dataclass
class TaskStep:
    name: str
    status: str = "pending"  # pending, running, completed, failed


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    priority: str = "medium"  # low, medium, high, urgent
    status: str = "queued"    # queued, running, waiting_for_approval, completed, failed, cancelled, paused
    deadline: Optional[str] = None
    action_name: Optional[str] = None
    action_args: Dict[str, Any] = field(default_factory=dict)
    progress: int = 0
    steps: List[Dict[str, str]] = field(default_factory=list)
    result: str = ""
    error: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    source: str = "system"    # voice, chat, phone, system
    checkpoint_step: int = 0
    checkpoint_state: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    execution_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        clean = dict(data)
        # Ensure default values for any missing keys
        if "steps" not in clean or not isinstance(clean["steps"], list):
            clean["steps"] = []
        if "action_args" not in clean or not isinstance(clean["action_args"], dict):
            clean["action_args"] = {}
        if "checkpoint_state" not in clean or not isinstance(clean["checkpoint_state"], dict):
            clean["checkpoint_state"] = {}
        if "execution_history" not in clean or not isinstance(clean["execution_history"], list):
            clean["execution_history"] = []
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in clean.items() if k in valid_fields}
        return cls(**filtered)


class TaskManager:
    """Threadsafe persistent Task Manager and async executor."""

    _instance: Optional[TaskManager] = None

    @classmethod
    def get_instance(cls) -> TaskManager:
        if cls._instance is None:
            cls._instance = TaskManager()
        return cls._instance

    def __init__(self, tasks_file: Path = TASKS_FILE):
        self._tasks_file = tasks_file
        self._lock = threading.Lock()
        self._tasks: Dict[str, Task] = {}
        self._listeners: List[Callable[[str, dict], None]] = []
        self._action_runner: Optional[Callable[[str, dict], Any]] = None
        self._recent_fingerprints: Dict[str, float] = {}  # fingerprint -> timestamp
        self._worker_running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._load()

    def set_action_runner(self, runner: Callable[[str, dict], Any]) -> None:
        """Register the runner callable that actually executes actions."""
        self._action_runner = runner

    def register_listener(self, listener: Callable[[str, dict], None]) -> None:
        """Register a callback for task events (e.g. WebSocket or UI log)."""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def unregister_listener(self, listener: Callable[[str, dict], None]) -> None:
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def _notify(self, event: str, task: Task) -> None:
        """Broadcast task change to registered listeners without blocking."""
        task_data = task.to_dict()
        listeners = list(self._listeners)
        for cb in listeners:
            try:
                cb(event, task_data)
            except Exception as e:
                print(f"[TaskManager]  Listener notification error: {e}")

    def _load(self) -> None:
        """Load tasks from disk."""
        with self._lock:
            if not self._tasks_file.exists():
                self._tasks = {}
                return
            try:
                data = json.loads(self._tasks_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for item in data:
                        t = Task.from_dict(item)
                        # If a task was running when JARVIS was closed, reset it to queued
                        if t.status == "running":
                            t.status = "queued"
                        self._tasks[t.id] = t
            except Exception as e:
                print(f"[TaskManager]  Failed to load tasks: {e}")
                self._tasks = {}

    def _save(self) -> None:
        """Persist tasks to disk."""
        try:
            self._tasks_file.parent.mkdir(parents=True, exist_ok=True)
            tasks_list = [t.to_dict() for t in self._tasks.values()]
            self._tasks_file.write_text(
                json.dumps(tasks_list, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[TaskManager]  Failed to save tasks: {e}")

    def _fingerprint(self, title: str, action_name: Optional[str], action_args: dict) -> str:
        norm_title = str(title or "").strip().lower()
        norm_act = str(action_name or "").strip().lower()
        args_str = json.dumps(action_args or {}, sort_keys=True)
        return f"{norm_title}|{norm_act}|{args_str}"

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: str = "medium",
        deadline: Optional[str] = None,
        action_name: Optional[str] = None,
        action_args: Optional[dict] = None,
        source: str = "system",
        requires_approval: Optional[bool] = None,
    ) -> Task:
        """Create a new task with deduplication and safety gating."""
        title = (title or "").strip()
        priority = priority.lower() if priority and priority.lower() in PRIORITY_ORDER else "medium"
        action_args = action_args or {}

        # 1. Deduplication check
        fp = self._fingerprint(title, action_name, action_args)
        now = time.time()
        with self._lock:
            # Purge expired fingerprints
            self._recent_fingerprints = {
                k: t for k, t in self._recent_fingerprints.items()
                if (now - t) < DEDUP_WINDOW_SECONDS
            }
            if fp in self._recent_fingerprints:
                for existing in reversed(list(self._tasks.values())):
                    if existing.status in ("queued", "running", "waiting_for_approval"):
                        if self._fingerprint(existing.title, existing.action_name, existing.action_args) == fp:
                            print(f"[TaskManager]  Duplicate task request ignored: '{title}'")
                            return existing

            self._recent_fingerprints[fp] = now

        # 2. Safety evaluation: determine initial status
        if requires_approval is True:
            initial_status = "waiting_for_approval"
        elif requires_approval is False:
            initial_status = "queued"
        elif action_name and action_name.lower() in HIGH_RISK_ACTIONS:
            initial_status = "waiting_for_approval"
        else:
            initial_status = "queued"

        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        steps = []
        if action_name:
            steps.append({"name": f"Execute action '{action_name}'", "status": "pending"})

        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            status=initial_status,
            deadline=deadline,
            action_name=action_name,
            action_args=action_args,
            progress=0,
            steps=steps,
            source=source,
        )

        with self._lock:
            self._tasks[task.id] = task
            self._save()

        print(f"[TaskManager]  Created task {task.id}: '{title}' [{initial_status}]")
        self._notify("task_created", task)
        return task

    def list_tasks(self, status: Optional[str] = None, limit: int = 50) -> List[Task]:
        """List tasks, optionally filtered by status category."""
        with self._lock:
            tasks = list(self._tasks.values())

        if status:
            st = status.lower().strip()
            if st == "active":
                tasks = [t for t in tasks if t.status in ("queued", "running", "waiting_for_approval")]
            elif st == "completed":
                tasks = [t for t in tasks if t.status == "completed"]
            elif st == "all":
                pass
            else:
                tasks = [t for t in tasks if t.status == st]

        # Sort: priority first, then creation time descending
        tasks.sort(
            key=lambda t: (
                PRIORITY_ORDER.get(t.priority, 2),
                -(datetime.fromisoformat(t.created_at).timestamp() if t.created_at else 0),
            )
        )
        return tasks[:limit]

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        result: Optional[str] = None,
        error: Optional[str] = None,
        step_index: Optional[int] = None,
        step_status: Optional[str] = None,
    ) -> Optional[Task]:
        """Update task fields and broadcast changes."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            if status is not None:
                task.status = status
                if status == "running" and not task.started_at:
                    task.started_at = datetime.now().isoformat()
                elif status in ("completed", "failed", "cancelled"):
                    task.completed_at = datetime.now().isoformat()
                    if status == "completed":
                        task.progress = 100

            if progress is not None:
                task.progress = max(0, min(100, int(progress)))

            if result is not None:
                task.result = str(result)

            if error is not None:
                task.error = str(error)

            if step_index is not None and 0 <= step_index < len(task.steps):
                if step_status:
                    task.steps[step_index]["status"] = step_status

            self._save()

        self._notify("task_updated", task)
        return task

    def approve_task(self, task_id: str) -> bool:
        """Approve a task held in waiting_for_approval."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != "waiting_for_approval":
                return False
            task.status = "queued"
            self._save()

        print(f"[TaskManager]  Approved task {task_id}: '{task.title}'")
        self._notify("task_approved", task)
        return True

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status in ("completed", "cancelled"):
                return False
            task.status = "cancelled"
            task.completed_at = datetime.now().isoformat()
            self._save()

        print(f"[TaskManager]  Cancelled task {task_id}: '{task.title}'")
        self._notify("task_cancelled", task)
        return True

    def retry_task(self, task_id: str) -> bool:
        """Retry a failed or cancelled task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status not in ("failed", "cancelled"):
                return False
            task.status = "queued"
            task.error = ""
            task.progress = 0
            task.started_at = None
            task.completed_at = None
            for s in task.steps:
                s["status"] = "pending"
            self._save()

        print(f"[TaskManager]  Retrying task {task_id}: '{task.title}'")
        self._notify("task_retried", task)
        return True

    def delete_task(self, task_id: str) -> bool:
        """Remove a task from storage."""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                self._save()
                return True
            return False

    def pause_task(self, task_id: str) -> bool:
        """Pause a running or queued task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status not in ("running", "queued"):
                return False
            task.status = "paused"
            task.execution_history.append({
                "timestamp": datetime.now().isoformat(),
                "event": "paused",
                "progress": task.progress,
                "step": task.checkpoint_step
            })
            self._save()
        print(f"[TaskManager]  Paused task {task_id}: '{task.title}'")
        self._notify("task_paused", task)
        return True

    def resume_task(self, task_id: str, approved: bool = False) -> bool:
        """Resume a paused task safely."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != "paused":
                return False
            # Consequential safety: if action is high risk, require explicit approval
            if task.action_name in HIGH_RISK_ACTIONS and not approved:
                task.status = "waiting_for_approval"
            else:
                task.status = "queued"
            task.execution_history.append({
                "timestamp": datetime.now().isoformat(),
                "event": "resumed",
                "target_status": task.status,
                "progress": task.progress,
                "step": task.checkpoint_step
            })
            self._save()
        print(f"[TaskManager]  Resumed task {task_id} -> [{task.status}]")
        self._notify("task_resumed", task)
        return True

    def checkpoint_task(self, task_id: str, step: Any, progress: Optional[Any] = None, state: Optional[dict] = None, note: str = "") -> Optional[Task]:
        """Save a progress checkpoint with snapshot state."""
        if isinstance(progress, dict) and state is None:
            state = progress
            progress = 50
        progress_val = int(progress) if progress is not None else 50
        state_dict = dict(state or {})

        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            try:
                task.checkpoint_step = int(step)
            except (ValueError, TypeError):
                task.checkpoint_step = str(step)
            task.progress = max(0, min(100, progress_val))
            task.checkpoint_state = state_dict
            task.execution_history.append({
                "timestamp": datetime.now().isoformat(),
                "event": "checkpoint",
                "step": task.checkpoint_step,
                "progress": task.progress,
                "note": note
            })
            if len(task.execution_history) > 100:
                task.execution_history = task.execution_history[-100:]
            self._save()
        self._notify("task_checkpoint", task)
        return task

    def get_task_history(self, task_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            task = self._tasks.get(task_id)
            return list(task.execution_history) if task else []

    # ── Autonomous Background Execution Loop ───────────────────────────────────

    def start_worker(self) -> None:
        """Start async worker loop if not already running."""
        if self._worker_running:
            return
        self._worker_running = True
        try:
            loop = asyncio.get_running_loop()
            self._worker_task = loop.create_task(self._worker_loop())
        except RuntimeError:
            # If no running event loop on current thread, start in background thread
            def _thread_worker():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(self._worker_loop())

            t = threading.Thread(target=_thread_worker, daemon=True, name="task-manager-worker")
            t.start()

    async def _worker_loop(self) -> None:
        """Poll and execute queued tasks safely."""
        while self._worker_running:
            try:
                next_task = self._get_next_queued_task()
                if next_task:
                    await self._execute_task(next_task)
                else:
                    await asyncio.sleep(1.0)
            except Exception as e:
                print(f"[TaskManager]  Worker loop error: {e}")
                await asyncio.sleep(2.0)

    def _get_next_queued_task(self) -> Optional[Task]:
        with self._lock:
            queued = [t for t in self._tasks.values() if t.status == "queued"]
            if not queued:
                return None
            queued.sort(
                key=lambda t: (
                    PRIORITY_ORDER.get(t.priority, 2),
                    datetime.fromisoformat(t.created_at).timestamp() if t.created_at else 0,
                )
            )
            return queued[0]

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task."""
        self.update_task(task.id, status="running", progress=10)
        print(f"[TaskManager]  Running task {task.id}: '{task.title}'")

        if not task.action_name:
            # Pure informational or tracked task
            self.update_task(task.id, status="completed", progress=100, result="Task completed successfully.")
            return

        try:
            self.update_task(task.id, progress=30, step_index=0, step_status="running")
            result = None

            if self._action_runner:
                # Run registered action handler
                if asyncio.iscoroutinefunction(self._action_runner):
                    result = await self._action_runner(task.action_name, task.action_args)
                else:
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, lambda: self._action_runner(task.action_name, task.action_args)
                    )
            else:
                # Default direct execution via ActionRegistry if available
                result = f"Action '{task.action_name}' registered for execution."

            res_str = str(result or "Done.")
            self.update_task(
                task.id,
                status="completed",
                progress=100,
                result=res_str,
                step_index=0,
                step_status="completed",
            )
            print(f"[TaskManager]  Completed task {task.id}: {res_str[:60]}")

        except Exception as e:
            err_str = str(e)
            print(f"[TaskManager]  Task {task.id} failed: {err_str}")
            self.update_task(
                task.id,
                status="failed",
                error=err_str,
                step_index=0,
                step_status="failed",
            )


# Global singleton instance
task_manager = TaskManager.get_instance()
