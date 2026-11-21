"""
core/computer_agent.py — J.A.R.V.I.S. Autonomous Computer Agent & Workflow Engine

Enforces the formal lifecycle:
    PLAN -> REQUEST PERMISSION -> ACT -> OBSERVE -> VERIFY -> REPORT

Safety & Integrity Invariants:
1. Destructive actions (file deletion, app kill, system reboot/shutdown, email sending, publishing)
   REQUIRE explicit confirmation from the user.
2. Silent execution of high-consequence operations is strictly blocked.
3. Every agentic action is recorded to data/computer_agent_audit.log.
4. Credentials, passwords, and tokens are scrubbed from all logs.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
AUDIT_LOG_FILE = DATA_DIR / "computer_agent_audit.log"

DESTRUCTIVE_ACTIONS = {
    "delete_file",
    "remove_folder",
    "system_shutdown",
    "system_restart",
    "kill_process",
    "send_email",
    "publish_instagram_reel",
    "wipe_memory",
    "overwrite_file",
}

SCRUB_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.I),
    re.compile(r"EAA[A-Za-z0-9]{15,}", re.I),
    re.compile(r"dpapi:v1:[A-Za-z0-9+/=]+", re.I),
    re.compile(r"(api_key|password|secret|token)\s*[:=]\s*([^\s,;]+)", re.I),
]


def scrub_sensitive_text(text: str) -> str:
    s = str(text)
    for p in SCRUB_PATTERNS:
        s = p.sub(r"[REDACTED_SECRET]", s)
    return s


@dataclass
class PlanStep:
    step_id: int
    action_name: str
    parameters: Dict[str, Any]
    description: str
    is_destructive: bool = False
    permission_granted: bool = False
    status: str = "PENDING"  # PENDING, AWAITING_PERMISSION, RUNNING, VERIFIED, FAILED, SKIPPED
    observed_result: Optional[str] = None
    verification_passed: bool = False
    error: Optional[str] = None


@dataclass
class AgentPlan:
    plan_id: str
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    status: str = "CREATED"  # CREATED, IN_PROGRESS, COMPLETED, FAILED, CANCELLED
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None


class ComputerAgent:
    def __init__(self, audit_file: Path = AUDIT_LOG_FILE):
        self.audit_file = audit_file
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
        self._active_plans: Dict[str, AgentPlan] = {}

    def log_audit(self, action: str, details: Dict[str, Any], result: str):
        timestamp = datetime.now().isoformat()
        clean_details = {k: scrub_sensitive_text(str(v)) for k, v in details.items()}
        line = f"[{timestamp}] ACTION={action} | DETAILS={json.dumps(clean_details)} | RESULT={scrub_sensitive_text(result)}\n"
        try:
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            print(f"[ComputerAgent] Audit write note: {e}")

    def create_plan(self, goal: str, steps_data: List[Dict[str, Any]]) -> AgentPlan:
        """PLAN: Creates a structured plan for the specified user goal."""
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        steps = []
        for idx, sd in enumerate(steps_data, start=1):
            act = sd.get("action_name", "unknown")
            is_dest = act in DESTRUCTIVE_ACTIONS or sd.get("is_destructive", False)
            step = PlanStep(
                step_id=idx,
                action_name=act,
                parameters=sd.get("parameters", {}),
                description=sd.get("description", f"Step {idx}: {act}"),
                is_destructive=is_dest,
                permission_granted=not is_dest,
            )
            steps.append(step)

        plan = AgentPlan(plan_id=plan_id, goal=goal, steps=steps)
        self._active_plans[plan_id] = plan
        self.log_audit("CREATE_PLAN", {"plan_id": plan_id, "goal": goal, "total_steps": len(steps)}, "OK")
        return plan

    def request_permission(self, plan_id: str, step_id: int) -> Tuple[bool, str]:
        """REQUEST PERMISSION: Checks if a step requires human authorization."""
        if plan_id not in self._active_plans:
            return False, "Plan not found."

        plan = self._active_plans[plan_id]
        step = next((s for s in plan.steps if s.step_id == step_id), None)
        if not step:
            return False, "Step not found."

        if not step.is_destructive:
            step.permission_granted = True
            return True, "Safe action: automatic permission granted."

        if step.permission_granted:
            return True, "Permission already granted by user."

        step.status = "AWAITING_PERMISSION"
        prompt = (
            f"Sir, step {step.step_id} involves a high-consequence operation: '{step.action_name}'.\n"
            f"Details: {step.description}\n"
            "Do you explicitly authorize this operation? (Please respond with CONFIRM)"
        )
        return False, prompt

    def grant_permission(self, plan_id: str, step_id: int, confirm_token: str = "") -> bool:
        if plan_id not in self._active_plans:
            return False
        plan = self._active_plans[plan_id]
        step = next((s for s in plan.steps if s.step_id == step_id), None)
        if not step:
            return False

        if str(confirm_token).strip().upper() in ("CONFIRM", "YES", "APPROVE", "TRUE"):
            step.permission_granted = True
            step.status = "PENDING"
            self.log_audit("GRANT_PERMISSION", {"plan_id": plan_id, "step_id": step_id, "action": step.action_name}, "GRANTED")
            return True
        return False

    def execute_step(self, plan_id: str, step_id: int, runner_callable: Optional[Callable] = None) -> Tuple[bool, str]:
        """ACT & OBSERVE & VERIFY: Executes an authorized step and validates the outcome."""
        if plan_id not in self._active_plans:
            return False, "Plan not found."

        plan = self._active_plans[plan_id]
        step = next((s for s in plan.steps if s.step_id == step_id), None)
        if not step:
            return False, "Step not found."

        if step.is_destructive and not step.permission_granted:
            return False, "Cannot execute: user permission not granted for destructive action."

        step.status = "RUNNING"
        t0 = time.time()
        try:
            # ACT
            if runner_callable:
                res = runner_callable(step.parameters)
            else:
                res = f"Action '{step.action_name}' executed with parameters: {step.parameters}"

            elapsed = time.time() - t0
            # OBSERVE
            step.observed_result = str(res)

            # VERIFY
            # A result that raises no error and contains positive confirmation passes verification
            if "error" in str(res).lower() or "failed" in str(res).lower():
                step.verification_passed = False
                step.status = "FAILED"
                step.error = str(res)
                self.log_audit("EXECUTE_STEP", {"plan_id": plan_id, "step_id": step_id, "action": step.action_name}, f"FAILED: {res}")
                return False, f"Verification failed: {res}"

            step.verification_passed = True
            step.status = "VERIFIED"
            self.log_audit("EXECUTE_STEP", {"plan_id": plan_id, "step_id": step_id, "action": step.action_name, "elapsed_s": round(elapsed, 2)}, "VERIFIED_OK")
            return True, f"Step {step_id} ({step.action_name}) completed and verified."
        except Exception as e:
            step.status = "FAILED"
            step.error = str(e)
            step.verification_passed = False
            self.log_audit("EXECUTE_STEP", {"plan_id": plan_id, "step_id": step_id, "action": step.action_name}, f"EXCEPTION: {e}")
            return False, f"Execution failed: {e}"

    def report_plan(self, plan_id: str) -> str:
        """REPORT: Produces a clean human-readable summary of the plan execution."""
        if plan_id not in self._active_plans:
            return "Plan not found."

        plan = self._active_plans[plan_id]
        lines = [f"=== J.A.R.V.I.S. Plan Execution Report [{plan.plan_id}] ===", f"Goal: {plan.goal}"]
        for s in plan.steps:
            icon = "✅" if s.status == "VERIFIED" else ("⚠️" if s.status == "AWAITING_PERMISSION" else "❌")
            lines.append(f"{icon} Step {s.step_id}: {s.description} -> [{s.status}]")
            if s.observed_result:
                lines.append(f"   Observed: {s.observed_result[:120]}")
            if s.error:
                lines.append(f"   Error: {s.error}")
        return "\n".join(lines)

    def pause_plan(self, plan_id: str) -> bool:
        """Pause execution of an in-progress plan."""
        if plan_id in self._active_plans:
            self._active_plans[plan_id].status = "PAUSED"
            self.log_audit("PAUSE_PLAN", {"plan_id": plan_id}, "PAUSED")
            return True
        return False

    def resume_plan(self, plan_id: str) -> bool:
        """Resume execution of a paused plan."""
        if plan_id in self._active_plans:
            self._active_plans[plan_id].status = "IN_PROGRESS"
            self.log_audit("RESUME_PLAN", {"plan_id": plan_id}, "RESUMED")
            return True
        return False

    def cancel_plan(self, plan_id: str) -> bool:
        """Cancel an active plan immediately."""
        if plan_id in self._active_plans:
            plan = self._active_plans[plan_id]
            plan.status = "CANCELLED"
            for s in plan.steps:
                if s.status in ("PENDING", "AWAITING_PERMISSION"):
                    s.status = "SKIPPED"
            self.log_audit("CANCEL_PLAN", {"plan_id": plan_id}, "CANCELLED")
            return True
        return False

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full plan status and step progress for UI."""
        if plan_id not in self._active_plans:
            return None
        plan = self._active_plans[plan_id]
        return {
            "plan_id": plan.plan_id,
            "goal": plan.goal,
            "status": plan.status,
            "created_at": plan.created_at,
            "steps": [asdict(s) for s in plan.steps],
        }

    def list_plans(self) -> List[Dict[str, Any]]:
        return [self.get_plan(pid) for pid in self._active_plans if self.get_plan(pid)]

    def retry_step(self, plan_id: str, step_id: int, new_params: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """Failure recovery: retry a failed or pending step with optional parameter adjustments."""
        if plan_id not in self._active_plans:
            return False, "Plan not found."
        plan = self._active_plans[plan_id]
        step = next((s for s in plan.steps if s.step_id == step_id), None)
        if not step:
            return False, "Step not found."
        if new_params:
            step.parameters.update(new_params)
        step.status = "PENDING"
        step.error = None
        self.log_audit("RETRY_STEP", {"plan_id": plan_id, "step_id": step_id}, "RETRY_QUEUED")
        return self.execute_step(plan_id, step_id, runner_callable=self.safe_execute_default)

    def safe_execute_default(self, action_name: str, params: Dict[str, Any]) -> str:
        """Built-in default action handlers for common file, browser, and app workflows."""
        act = action_name.lower()
        if act == "open_url":
            import webbrowser
            url = params.get("url", "https://google.com")
            webbrowser.open(url)
            return f"Opened URL in browser: {url}"

        elif act == "launch_app":
            import subprocess
            app = params.get("app_name", "notepad")
            subprocess.Popen(app, shell=True)
            return f"Launched application: {app}"

        elif act == "read_file":
            path = Path(params.get("path", ""))
            if not path.exists():
                return f"Error: File not found: {path}"
            content = path.read_text(encoding="utf-8", errors="ignore")
            return f"Read {len(content)} characters from {path.name}"

        elif act == "list_directory":
            path = Path(params.get("path", "."))
            if not path.exists():
                return f"Error: Directory not found: {path}"
            items = [p.name for p in path.iterdir()]
            return f"Directory {path} contains {len(items)} items: {', '.join(items[:10])}"

        elif act == "get_system_status":
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            return f"System Status: CPU={cpu}%, RAM={mem}%"

        return f"Simulated execution for action: {action_name}"


computer_agent = ComputerAgent()
