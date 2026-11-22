"""
core/assistant_state.py — Central J.A.R.V.I.S. Assistant State & IPC Coordinator

Tracks real-time assistant state: IDLE, LISTENING, THINKING, SPEAKING, WORKING, MUTED, ERROR.
Synchronizes across web dashboard, voice engine, PC agent, and floating companion widget.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional


class AssistantStateManager:
    """Thread-safe state coordinator for J.A.R.V.I.S. companion and subsystems."""

    _instance: Optional[AssistantStateManager] = None
    _class_lock = threading.Lock()

    def __new__(cls) -> AssistantStateManager:
        with cls._class_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._lock = threading.RLock()
        self._state = "IDLE"
        self._active_task = ""
        self._active_plan_id: Optional[str] = None
        self._audio_level = 0.0
        self._is_muted = False
        self._last_change = time.time()
        self._initialized = True

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            effective_state = self._state
            effective_task = self._active_task

            # Auto-detect computer agent execution if state is not explicitly muted or in error
            try:
                from core.computer_agent import computer_agent
                active_plans = [
                    p for p in computer_agent._active_plans.values()
                    if getattr(p, "status", "") in ("IN_PROGRESS", "RUNNING")
                ]
                if active_plans and effective_state not in ("MUTED", "ERROR"):
                    effective_state = "WORKING"
                    effective_task = getattr(active_plans[0], "goal", effective_task)
            except Exception:
                pass

            return {
                "ok": True,
                "state": effective_state,
                "active_task": effective_task,
                "active_plan_id": self._active_plan_id,
                "audio_level": self._audio_level,
                "is_muted": self._is_muted,
                "timestamp": time.time(),
            }

    def set_state(
        self,
        state: str,
        active_task: Optional[str] = None,
        plan_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            valid_states = {
                "IDLE", "STANDBY", "LISTENING", "THINKING",
                "SPEAKING", "WORKING", "MUTED", "ERROR", "PAUSED", "SUCCESS",
            }
            st = str(state).strip().upper()
            if st in valid_states:
                self._state = st
            if active_task is not None:
                self._active_task = str(active_task)
            if plan_id is not None:
                self._active_plan_id = str(plan_id)

            if self._state == "MUTED":
                self._is_muted = True
            elif self._state in ("IDLE", "STANDBY", "LISTENING", "THINKING", "SPEAKING", "WORKING"):
                self._is_muted = False

            self._last_change = time.time()
            return self.get_state()

    def set_audio_level(self, level: float) -> None:
        with self._lock:
            self._audio_level = max(0.0, min(1.0, float(level)))

    def set_muted(self, muted: bool) -> Dict[str, Any]:
        with self._lock:
            self._is_muted = bool(muted)
            if self._is_muted:
                self._state = "MUTED"
            elif self._state == "MUTED":
                self._state = "IDLE"
            self._last_change = time.time()
            return self.get_state()

    def reset(self) -> None:
        """Reset state to default IDLE for testing."""
        with self._lock:
            self._state = "IDLE"
            self._active_task = ""
            self._active_plan_id = None
            self._audio_level = 0.0
            self._is_muted = False
            self._last_change = time.time()


assistant_state_manager = AssistantStateManager()
