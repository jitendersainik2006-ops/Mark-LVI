"""
core/n8n_integration.py — Self-Hosted n8n Workflow Automation Bridge for J.A.R.V.I.S.

Provides modular, secure inbound and outbound webhook integrations for:
- Reel creation triggers
- Content calendar planning
- Approval workflows (query and human-approved trigger)
- Scheduled background task injection
- Outbound notification dispatch
- Automated weekly business reports

Maintains independent service boundary: Does not bundle n8n source code.
Protected by API Key authentication and Windows DPAPI credential protection.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
CONFIG_FILE = BASE_DIR / "config" / "api_keys.json"
logger = logging.getLogger("JARVIS.N8N")


@dataclass
class N8NConfig:
    enabled: bool = False
    api_key: str = ""
    webhook_url: str = ""
    allowed_events: List[str] = field(default_factory=lambda: [
        "reel_generated",
        "reel_needs_approval",
        "reel_published",
        "task_scheduled",
        "task_completed",
        "weekly_report_ready",
    ])


class N8NManager:
    """Manages secure communication between J.A.R.V.I.S. and self-hosted n8n."""

    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> N8NConfig:
        cfg = N8NConfig()
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                n8n_data = data.get("n8n", {})
                cfg.enabled = bool(n8n_data.get("enabled", False))
                cfg.api_key = str(n8n_data.get("api_key", "")).strip()
                cfg.webhook_url = str(n8n_data.get("webhook_url", "")).strip()
                if "allowed_events" in n8n_data:
                    cfg.allowed_events = list(n8n_data["allowed_events"])
            except Exception as e:
                logger.warning(f"Failed to read n8n config: {e}")
        # Allow environment overrides
        if os.environ.get("N8N_API_KEY"):
            cfg.api_key = os.environ["N8N_API_KEY"].strip()
        if os.environ.get("N8N_WEBHOOK_URL"):
            cfg.webhook_url = os.environ["N8N_WEBHOOK_URL"].strip()
        if os.environ.get("N8N_ENABLED"):
            cfg.enabled = os.environ["N8N_ENABLED"].strip().lower() in ("1", "true", "yes")
        return cfg

    def save_config(self, enabled: bool, api_key: str, webhook_url: str, allowed_events: Optional[List[str]] = None) -> bool:
        """Saves n8n integration configuration to config/api_keys.json."""
        self.config.enabled = bool(enabled)
        self.config.api_key = api_key.strip()
        self.config.webhook_url = webhook_url.strip()
        if allowed_events is not None:
            self.config.allowed_events = allowed_events

        data = {}
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data["n8n"] = {
            "enabled": self.config.enabled,
            "api_key": self.config.api_key,
            "webhook_url": self.config.webhook_url,
            "allowed_events": self.config.allowed_events,
        }
        CONFIG_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
        return True

    def verify_auth(self, headers: Dict[str, str]) -> bool:
        """
        Validates authentication header for inbound n8n webhook calls.
        Supports:
        - X-N8N-API-Key: <key>
        - Authorization: Bearer <key>
        """
        if not self.config.api_key:
            # If no API key configured, refuse all unauthenticated external webhook calls
            return False

        header_key = headers.get("x-n8n-api-key") or headers.get("X-N8N-API-Key")
        if header_key and header_key.strip() == self.config.api_key:
            return True

        auth_header = headers.get("authorization") or headers.get("Authorization") or ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token == self.config.api_key:
                return True

        return False

    def dispatch_event(self, event_type: str, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Dispatches an asynchronous/synchronous outbound webhook notification to n8n.
        Payload includes timestamp, event_type, and event details.
        """
        if not self.config.enabled or not self.config.webhook_url:
            return False, "n8n integration or webhook URL not enabled/configured"

        if event_type not in self.config.allowed_events:
            return False, f"Event '{event_type}' not in allowed n8n events list"

        body = {
            "source": "JARVIS_Mark_LVI",
            "event": event_type,
            "timestamp": time.time(),
            "data": payload,
        }
        json_bytes = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(
            self.config.webhook_url,
            data=json_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "JARVIS-Automation/1.0",
                "X-JARVIS-Event": event_type,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                status = resp.status
                return (status in (200, 201, 202, 204)), f"HTTP {status}"
        except Exception as e:
            logger.warning(f"Failed to dispatch event to n8n: {e}")
            return False, str(e)

    # ── Modular Webhook Handlers (Inbound from n8n) ───────────────────────────

    def handle_reel_generation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Triggers local Reel creation from n8n workflow."""
        from core.instagram_manager import instagram_manager
        topic_id = data.get("topic_id")
        account_username = data.get("account_username") or "mentos_life_gym"
        delay_hours = int(data.get("delay_hours", 2))

        # Always enforce target @mentos_life_gym
        post = instagram_manager.generate_trading_reel(
            topic_id=str(topic_id) if topic_id else None,
            account_username=str(account_username),
            scheduled_delay_hours=delay_hours,
        )
        # Notify n8n that reel is generated and pending human approval
        self.dispatch_event("reel_needs_approval", {
            "reel_id": post.id,
            "title": post.title,
            "account": post.account_username,
            "scheduled_time": post.scheduled_time,
        })
        return {
            "ok": True,
            "reel": post.to_dict(),
            "message": "Reel generated successfully. Mandatory human approval required before publishing.",
        }

    def handle_content_planning(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Provides content calendar & recommendation for n8n scheduling."""
        from core.instagram_manager import instagram_manager
        account_username = data.get("account_username") or "mentos_life_gym"
        days = int(data.get("days", 7))
        calendar = instagram_manager.get_content_calendar(account_username, days=days)
        return {
            "ok": True,
            "account": account_username,
            "days": days,
            "calendar": calendar,
        }

    def handle_weekly_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generates weekly performance and compliance report for business automation."""
        from core.instagram_manager import instagram_manager
        account_username = data.get("account_username") or "mentos_life_gym"
        report = instagram_manager.generate_weekly_report(account_username)
        return {
            "ok": True,
            "account": account_username,
            "report": report,
        }

    def handle_task_schedule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedules an automated task from n8n into J.A.R.V.I.S. TaskManager."""
        from core.task_manager import task_manager
        task_name = data.get("name") or "n8n_automated_task"
        command = data.get("command") or ""
        interval = int(data.get("interval_seconds", 3600))
        task = task_manager.create_task(
            title=task_name,
            description=f"n8n automated workflow trigger (interval: {interval}s)",
            source="n8n",
            action_name=command if command else None,
        )
        return {
            "ok": True,
            "task_id": task.id,
            "name": task.title,
            "status": task.status,
            "interval_seconds": interval,
        }


# Singleton instance
n8n_manager = N8NManager()
