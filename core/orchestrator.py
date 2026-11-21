"""
core/orchestrator.py — Autonomous Multi-Agent Orchestration Layer

Decomposes complex, high-level user directives into structured, multi-step execution plans
with dependency tracking and automatic assignment to specialized agent roles:
- 7 Specialized Agent Roles: Research, Coding, File, Browser, Document, System, Knowledge.
- Shared Identity, Memory, Safety Gates & Central Backend.
- Dependency resolution, execution checkpoints, error recovery, and consolidated final reports.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("JARVIS.Orchestrator")

BASE_DIR = Path(__file__).resolve().parent.parent
PLANS_FILE = BASE_DIR / "data" / "orchestrator_plans.json"

# Specialized Agent Roles
AGENT_RESEARCH = "Research Agent"
AGENT_CODING = "Coding Agent"
AGENT_FILE = "File Agent"
AGENT_BROWSER = "Browser Agent"
AGENT_DOCUMENT = "Document Agent"
AGENT_SYSTEM = "System Assistant"
AGENT_KNOWLEDGE = "Knowledge Agent"


@dataclass
class OrchestrationStep:
    id: str
    title: str
    agent: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed, waiting_for_approval
    output: Any = None
    error: str = ""
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    @property
    def agent_role(self) -> str:
        return self.agent

    @property
    def step_num(self) -> str:
        return self.id.split("_")[-1]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["agent_role"] = self.agent
        d["step_num"] = self.step_num
        return d

    @classmethod
    def from_dict(cls, data: dict) -> OrchestrationStep:
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class OrchestrationPlan:
    plan_id: str
    objective: str
    steps: List[OrchestrationStep] = field(default_factory=list)
    status: str = "planned"  # planned, executing, completed, failed, paused
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    progress_percent: int = 0
    final_report: str = ""

    @property
    def id(self) -> str:
        return self.plan_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.plan_id,
            "plan_id": self.plan_id,
            "objective": self.objective,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "progress_percent": self.progress_percent,
            "final_report": self.final_report,
        }

    @classmethod
    def from_dict(cls, data: dict) -> OrchestrationPlan:
        steps_raw = data.get("steps", [])
        steps = [OrchestrationStep.from_dict(s) for s in steps_raw]
        return cls(
            plan_id=data.get("plan_id", data.get("id", f"plan_{int(time.time())}")),
            objective=data.get("objective", ""),
            steps=steps,
            status=data.get("status", "planned"),
            created_at=data.get("created_at", time.time()),
            completed_at=data.get("completed_at"),
            progress_percent=data.get("progress_percent", 0),
            final_report=data.get("final_report", ""),
        )


class AgentOrchestrator:
    """Coordinates specialized agent roles on multi-step workflows."""

    _instance: Optional[AgentOrchestrator] = None

    @classmethod
    def get_instance(cls) -> AgentOrchestrator:
        if cls._instance is None:
            cls._instance = AgentOrchestrator()
        return cls._instance

    def list_available_roles(self) -> List[str]:
        """Returns list of all 7 specialized agent roles."""
        return [
            AGENT_RESEARCH,
            AGENT_CODING,
            AGENT_FILE,
            AGENT_BROWSER,
            AGENT_DOCUMENT,
            AGENT_SYSTEM,
            AGENT_KNOWLEDGE,
        ]

    def __init__(self, plans_file: Path = PLANS_FILE):
        self._plans_file = plans_file
        self._lock = threading.Lock()
        self._plans: Dict[str, OrchestrationPlan] = {}
        self._load()

    def _load(self):
        with self._lock:
            if not self._plans_file.exists():
                return
            try:
                data = json.loads(self._plans_file.read_text(encoding="utf-8"))
                for item in data:
                    plan = OrchestrationPlan.from_dict(item)
                    self._plans[plan.plan_id] = plan
            except Exception as e:
                logger.error(f"[Orchestrator] Failed to load plans: {e}")

    def _save(self):
        try:
            self._plans_file.parent.mkdir(parents=True, exist_ok=True)
            plans_list = [p.to_dict() for p in self._plans.values()]
            self._plans_file.write_text(json.dumps(plans_list, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"[Orchestrator] Failed to save plans: {e}")

    # ── Plan Creation & Decomposition ──────────────────────────────────────────

    def plan_objective(self, objective: str) -> OrchestrationPlan:
        """Decomposes a user objective into an actionable multi-agent plan."""
        plan_id = f"plan_{int(time.time()*1000)%1000000}"
        obj_clean = str(objective or "").strip()
        obj_lower = obj_clean.lower()

        steps: List[OrchestrationStep] = []

        # Pattern 1: Project Audit & Error Fix
        if any(w in obj_lower for w in ["audit", "fix", "inspect errors", "jaanch", "theek karo"]):
            s1 = OrchestrationStep(
                id=f"{plan_id}_s1",
                title="System & Storage Telemetry Check",
                agent=AGENT_SYSTEM,
                action="system_status",
                params={},
            )
            s2 = OrchestrationStep(
                id=f"{plan_id}_s2",
                title="File Tree & Project Consistency Audit",
                agent=AGENT_FILE,
                action="file_list_directory",
                params={"path": str(BASE_DIR), "max_items": 40},
                dependencies=[s1.id],
            )
            s3 = OrchestrationStep(
                id=f"{plan_id}_s3",
                title="Python Syntax & Static Code Analysis",
                agent=AGENT_CODING,
                action="dev_syntax_check",
                params={"file_path": str(BASE_DIR / "core" / "skill_router.py")},
                dependencies=[s2.id],
            )
            s4 = OrchestrationStep(
                id=f"{plan_id}_s4",
                title="Compile Audit Findings & Verification Report",
                agent=AGENT_DOCUMENT,
                action="doc_create_note",
                params={"title": f"Audit_Report_{plan_id}.md", "content": "Initial audit in progress."},
                dependencies=[s3.id],
            )
            steps = [s1, s2, s3, s4]

        # Pattern 2: Research & Document Generation
        elif any(w in obj_lower for w in ["research", "summarize", "study", "khoj", "jankari"]):
            s1 = OrchestrationStep(
                id=f"{plan_id}_s1",
                title="Query Internal Knowledge Base",
                agent=AGENT_KNOWLEDGE,
                action="search_knowledge",
                params={"query": obj_clean},
            )
            s2 = OrchestrationStep(
                id=f"{plan_id}_s2",
                title="Deep Web Search & Content Synthesis",
                agent=AGENT_RESEARCH,
                action="research_topic",
                params={"query": obj_clean},
                dependencies=[s1.id],
            )
            s3 = OrchestrationStep(
                id=f"{plan_id}_s3",
                title="Generate Research Executive Briefing",
                agent=AGENT_DOCUMENT,
                action="doc_create_note",
                params={"title": f"Research_{plan_id}.md", "content": f"Executive summary for: {obj_clean}"},
                dependencies=[s2.id],
            )
            steps = [s1, s2, s3]

        # Pattern 3: Workstation Control & Screen Diagnosis
        elif any(w in obj_lower for w in ["screen", "display", "error on screen", "dekho"]):
            s1 = OrchestrationStep(
                id=f"{plan_id}_s1",
                title="Capture & Inspect Active Screen Display",
                agent=AGENT_SYSTEM,
                action="screen_analyze",
                params={"query": obj_clean},
            )
            s2 = OrchestrationStep(
                id=f"{plan_id}_s2",
                title="Formulate Technical Solution",
                agent=AGENT_CODING,
                action="dev_read_error_log",
                params={"lines": 25},
                dependencies=[s1.id],
            )
            steps = [s1, s2]

        # Default fallback plan: General task execution
        else:
            s1 = OrchestrationStep(
                id=f"{plan_id}_s1",
                title=f"Execute: {obj_clean[:50]}",
                agent=AGENT_RESEARCH,
                action="research_topic",
                params={"query": obj_clean},
            )
            s2 = OrchestrationStep(
                id=f"{plan_id}_s2",
                title="Summarize and Store In Memory",
                agent=AGENT_KNOWLEDGE,
                action="memory_add_fact",
                params={"category": "tasks", "key": f"task_{plan_id}", "value": f"Objective: {obj_clean}"},
                dependencies=[s1.id],
            )
            steps = [s1, s2]

        plan = OrchestrationPlan(
            plan_id=plan_id,
            objective=obj_clean,
            steps=steps,
            status="planned",
            progress_percent=0,
        )

        with self._lock:
            self._plans[plan.plan_id] = plan
            self._save()

        # Connect to persistent TaskManager
        try:
            from core.task_manager import TaskManager
            tm = TaskManager.get_instance()
            tm.create_task(
                title=f"[Orchestrator] {obj_clean[:60]}",
                description=f"Multi-Agent Plan {plan_id} ({len(steps)} steps)",
                priority="high",
                action_name="orchestrator_plan",
                action_args={"plan_id": plan_id},
            )
        except Exception as e:
            logger.warning(f"[Orchestrator] TaskManager link error: {e}")

        logger.info(f"[Orchestrator] Created plan {plan_id} with {len(steps)} steps for objective: '{obj_clean}'")
        return plan

    # ── Plan Execution ─────────────────────────────────────────────────────────

    def execute_plan(self, plan_id: str) -> Dict[str, Any]:
        """Executes all steps in a plan sequentially respecting dependencies."""
        plan = self._plans.get(plan_id)
        if not plan:
            return {"ok": False, "error": f"Plan '{plan_id}' not found."}

        plan.status = "executing"
        completed_steps = 0
        total_steps = len(plan.steps)
        step_outputs = []

        from core.skill_router import skill_router

        for step in plan.steps:
            # Check dependencies
            deps_met = all(
                any(s.id == dep_id and s.status == "completed" for s in plan.steps)
                for dep_id in step.dependencies
            )
            if not deps_met:
                step.status = "failed"
                step.error = "Unmet step dependency."
                continue

            step.status = "in_progress"
            step.started_at = time.time()
            self._save()

            # Execute via skill_router
            try:
                exec_res = skill_router.execute_skill(
                    skill_id=step.action,
                    params=step.params,
                    confirmed=True
                )
                if exec_res.get("ok"):
                    step.status = "completed"
                    step.output = exec_res.get("data")
                    step.error = ""
                    completed_steps += 1
                    step_outputs.append(f"• **{step.title}** ({step.agent}): ✅ {exec_res.get('spoken_summary', 'Success')}")
                else:
                    step.status = "failed"
                    step.error = str(exec_res.get("error") or exec_res.get("message") or "Action failed")
                    step_outputs.append(f"• **{step.title}** ({step.agent}): ❌ Error: {step.error}")
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                step_outputs.append(f"• **{step.title}** ({step.agent}): ❌ Exception: {e}")

            step.completed_at = time.time()
            plan.progress_percent = int((completed_steps / max(1, total_steps)) * 100)
            self._save()

        # Final Report Compilation
        plan.completed_at = time.time()
        if completed_steps == total_steps:
            plan.status = "completed"
        elif completed_steps > 0:
            plan.status = "partial"
        else:
            plan.status = "failed"

        report_md = f"""# Autonomous Multi-Agent Execution Report
**Plan ID:** `{plan.plan_id}`  
**Objective:** {plan.objective}  
**Status:** `{plan.status.upper()}` ({completed_steps}/{total_steps} steps completed)  
**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(plan.completed_at))}  

### Step Results:
{chr(10).join(step_outputs)}

---
*Generated autonomously by J.A.R.V.I.S. Multi-Agent Orchestrator.*
"""
        plan.final_report = report_md
        self._save()

        return {
            "ok": True,
            "plan_id": plan.plan_id,
            "status": plan.status,
            "progress_percent": plan.progress_percent,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "report": report_md,
        }

    def get_plan(self, plan_id: str) -> Optional[OrchestrationPlan]:
        return self._plans.get(plan_id)

    def list_plans(self, limit: int = 20) -> List[Dict[str, Any]]:
        plans = list(self._plans.values())
        return [p.to_dict() for p in sorted(plans, key=lambda x: -x.created_at)[:limit]]


# Global singleton
agent_orchestrator = AgentOrchestrator.get_instance()
