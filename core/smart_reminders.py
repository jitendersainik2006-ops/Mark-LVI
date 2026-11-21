"""
core/smart_reminders.py — J.A.R.V.I.S. Mark LVI Smart Reminders & Scheduling Engine

Features:
1. Natural-language one-time reminders (relative minutes/hours, exact times).
2. Recurring intervals (daily, weekly, custom cron-like intervals).
3. Rich lifecycle: Create, List, Snooze (5m/10m/30m/60m), Edit, Dismiss, Delete.
4. Active background daemon monitoring due alerts without high CPU usage.
5. Persistent storage in data/reminders.json.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import secrets
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("JARVIS.SmartReminders")

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
REMINDERS_FILE = DATA_DIR / "reminders.json"


@dataclass
class ReminderItem:
    id: str
    title: str
    due_at: str  # ISO 8601 string
    created_at: str
    recurring_interval: Optional[str] = None  # None, "daily", "weekly", "hourly"
    status: str = "PENDING"  # PENDING, TRIGGERED, SNOOZED, DISMISSED
    snooze_count: int = 0
    tags: List[str] = field(default_factory=list)
    last_triggered_at: Optional[str] = None

    def is_due(self) -> bool:
        if self.status not in ("PENDING", "SNOOZED"):
            return False
        try:
            due_dt = datetime.datetime.fromisoformat(self.due_at)
            return datetime.datetime.now() >= due_dt
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SmartRemindersManager:
    def __init__(self, base_dir: Optional[Path] = None):
        self._lock = threading.RLock()
        self.base_dir = Path(base_dir) if base_dir else BASE_DIR
        self.data_dir = self.base_dir / "data"
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        self.reminders_file = self.data_dir / "reminders.json"
        self._reminders: Dict[str, ReminderItem] = {}
        self._monitor_active = False
        self._monitor_thread: Optional[threading.Thread] = None

        self._load()
        self.start_monitoring()

    def _load(self):
        with self._lock:
            if self.reminders_file.exists():
                try:
                    data = json.loads(self.reminders_file.read_text(encoding="utf-8"))
                    for r in data:
                        item = ReminderItem(**r)
                        self._reminders[item.id] = item
                except Exception as e:
                    logger.warning(f"Error reading reminders: {e}")
            if not self._reminders:
                # Seed welcome reminder
                now = datetime.datetime.now()
                r_id = "rem_welcome"
                self._reminders[r_id] = ReminderItem(
                    id=r_id,
                    title="Review J.A.R.V.I.S. Mark LVI Daily Briefing & Workflows",
                    due_at=(now + datetime.timedelta(hours=2)).isoformat(),
                    created_at=now.isoformat(),
                    recurring_interval="daily",
                    status="PENDING",
                    tags=["system", "routine"]
                )
                self._save()

    def _save(self):
        try:
            raw = [r.to_dict() for r in self._reminders.values()]
            self.reminders_file.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Error saving reminders: {e}")

    # ── Reminder Lifecycle ───────────────────────────────────────────────────

    def create_reminder(
        self,
        title: str,
        due_in_minutes: Optional[int] = None,
        exact_due_iso: Optional[str] = None,
        recurring_interval: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        with self._lock:
            now = datetime.datetime.now()
            if exact_due_iso:
                due_dt = datetime.datetime.fromisoformat(exact_due_iso)
            elif due_in_minutes is not None:
                due_dt = now + datetime.timedelta(minutes=max(1, due_in_minutes))
            else:
                due_dt = now + datetime.timedelta(minutes=30)

            rem_id = f"rem_{secrets.token_hex(4)}"
            item = ReminderItem(
                id=rem_id,
                title=title.strip() or "Untitled Reminder",
                due_at=due_dt.isoformat(),
                created_at=now.isoformat(),
                recurring_interval=recurring_interval,
                status="PENDING",
                tags=tags or []
            )
            self._reminders[rem_id] = item
            self._save()
            return item.to_dict()

    def list_reminders(self, include_dismissed: bool = False) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._reminders.values())
            if not include_dismissed:
                items = [i for i in items if i.status != "DISMISSED"]
            return sorted([i.to_dict() for i in items], key=lambda x: x["due_at"])

    def snooze_reminder(self, reminder_id: str, minutes: int = 10) -> Dict[str, Any]:
        with self._lock:
            item = self._reminders.get(reminder_id)
            if not item:
                return {"ok": False, "error": f"Reminder {reminder_id} not found"}
            now = datetime.datetime.now()
            item.due_at = (now + datetime.timedelta(minutes=max(1, minutes))).isoformat()
            item.status = "SNOOZED"
            item.snooze_count += 1
            self._save()
            return {"ok": True, "reminder": item.to_dict(), "message": f"Snoozed for {minutes} minute(s)"}

    def edit_reminder(self, reminder_id: str, new_title: Optional[str] = None, new_due_iso: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            item = self._reminders.get(reminder_id)
            if not item:
                return {"ok": False, "error": f"Reminder {reminder_id} not found"}
            if new_title:
                item.title = new_title.strip()
            if new_due_iso:
                item.due_at = new_due_iso
                item.status = "PENDING"
            self._save()
            return {"ok": True, "reminder": item.to_dict()}

    def dismiss_reminder(self, reminder_id: str) -> Dict[str, Any]:
        with self._lock:
            item = self._reminders.get(reminder_id)
            if not item:
                return {"ok": False, "error": f"Reminder {reminder_id} not found"}
            item.status = "DISMISSED"
            self._save()
            return {"ok": True, "reminder_id": reminder_id, "status": "DISMISSED"}

    def delete_reminder(self, reminder_id: str) -> bool:
        with self._lock:
            if reminder_id in self._reminders:
                del self._reminders[reminder_id]
                self._save()
                return True
            return False

    # ── Background Daemon ────────────────────────────────────────────────────

    def start_monitoring(self):
        with self._lock:
            if self._monitor_active:
                return
            self._monitor_active = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True, name="SmartRemindersMonitor")
            self._monitor_thread.start()

    def _monitor_loop(self):
        while self._monitor_active:
            try:
                self._check_due_reminders()
            except Exception as e:
                logger.error(f"Error in reminders monitor: {e}")
            time.sleep(10)

    def _check_due_reminders(self):
        due_items = []
        with self._lock:
            for item in self._reminders.values():
                if item.is_due():
                    due_items.append(item)

        for item in due_items:
            with self._lock:
                item.status = "TRIGGERED"
                item.last_triggered_at = datetime.datetime.now().isoformat()
                # If recurring, advance to next cycle
                if item.recurring_interval == "daily":
                    nxt = datetime.datetime.now() + datetime.timedelta(days=1)
                    item.due_at = nxt.isoformat()
                    item.status = "PENDING"
                elif item.recurring_interval == "hourly":
                    nxt = datetime.datetime.now() + datetime.timedelta(hours=1)
                    item.due_at = nxt.isoformat()
                    item.status = "PENDING"
                self._save()
            logger.info(f"[SmartReminders] 🔔 Due Alert: {item.title}")


# Singleton
smart_reminders = SmartRemindersManager()
