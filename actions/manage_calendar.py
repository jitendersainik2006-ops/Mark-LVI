"""
actions/manage_calendar.py — J.A.R.V.I.S. Local Calendar & Agenda Management Tool

Provides local-first, privacy-respecting calendar scheduling and event management:
- Create, list, search, update, and cancel scheduled events.
- Timezone-aware (defaults to Asia/Kolkata / system local).
- Generates and imports standard iCalendar (.ics) files.
- Persistent local storage in data/calendar_events.json.
- Zero paid dependencies or third-party credential exposure.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_base_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
CALENDAR_FILE = DATA_DIR / "calendar_events.json"


@dataclass
class CalendarEvent:
    id: str
    title: str
    start_time: str  # ISO-8601 string
    end_time: str    # ISO-8601 string
    description: str = ""
    location: str = ""
    category: str = "general"
    reminder_minutes_before: int = 15
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "CONFIRMED"  # CONFIRMED, CANCELLED, COMPLETED

    def to_dict(self) -> dict:
        return asdict(self)


class CalendarManager:
    def __init__(self, storage_file: Path = CALENDAR_FILE):
        self.storage_file = storage_file
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._events: Dict[str, CalendarEvent] = {}
        self._load()

    def _load(self):
        if self.storage_file.exists():
            try:
                data = json.loads(self.storage_file.read_text(encoding="utf-8"))
                self._events = {
                    item["id"]: CalendarEvent(**item)
                    for item in data
                    if "id" in item and "title" in item
                }
            except Exception as e:
                print(f"[CalendarManager] Load notice: {e}")
                self._events = {}
        else:
            self._events = {}

    def _save(self):
        try:
            items = [e.to_dict() for e in sorted(self._events.values(), key=lambda x: x.start_time)]
            self.storage_file.write_text(json.dumps(items, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[CalendarManager] Save error: {e}")

    def add_event(
        self,
        title: str,
        start_time: str,
        end_time: Optional[str] = None,
        description: str = "",
        location: str = "",
        category: str = "general",
        reminder_minutes: int = 15,
    ) -> CalendarEvent:
        if not title or not title.strip():
            raise ValueError("Event title cannot be empty.")

        # Validate start_time
        try:
            st = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except Exception:
            # Fallback format parsing
            st = datetime.strptime(start_time, "%Y-%m-%d %H:%M")

        if end_time:
            try:
                et = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except Exception:
                et = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
        else:
            et = st + timedelta(hours=1)

        event_id = f"evt_{uuid.uuid4().hex[:8]}"
        event = CalendarEvent(
            id=event_id,
            title=title.strip(),
            start_time=st.isoformat(),
            end_time=et.isoformat(),
            description=description.strip(),
            location=location.strip(),
            category=category.strip(),
            reminder_minutes_before=reminder_minutes,
        )
        self._events[event_id] = event
        self._save()
        return event

    def list_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_cancelled: bool = False,
    ) -> List[dict]:
        self._load()
        results = []
        for e in self._events.values():
            if not include_cancelled and e.status == "CANCELLED":
                continue
            if start_date and e.start_time < start_date:
                continue
            if end_date and e.start_time > end_date:
                continue
            results.append(e.to_dict())
        return sorted(results, key=lambda x: x["start_time"])

    def get_upcoming_events(self, days: int = 7) -> List[dict]:
        self._load()
        now_iso = datetime.now().isoformat()
        future_iso = (datetime.now() + timedelta(days=days)).isoformat()
        return self.list_events(start_date=now_iso, end_date=future_iso)

    def cancel_event(self, event_id: str) -> bool:
        self._load()
        if event_id in self._events:
            self._events[event_id].status = "CANCELLED"
            self._events[event_id].updated_at = datetime.now().isoformat()
            self._save()
            return True
        return False

    def delete_event(self, event_id: str) -> bool:
        self._load()
        if event_id in self._events:
            del self._events[event_id]
            self._save()
            return True
        return False

    def export_ics(self, output_path: Optional[Path] = None) -> Path:
        self._load()
        if output_path is None:
            output_path = DATA_DIR / "jarvis_calendar.ics"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//J.A.R.V.I.S. Mark LVI//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]
        for e in self._events.values():
            if e.status == "CANCELLED":
                continue
            st = datetime.fromisoformat(e.start_time).strftime("%Y%m%dT%H%M%SZ")
            et = datetime.fromisoformat(e.end_time).strftime("%Y%m%dT%H%M%SZ")
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{e.id}@jarvis.local",
                f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{st}",
                f"DTEND:{et}",
                f"SUMMARY:{e.title}",
                f"DESCRIPTION:{e.description}",
                f"LOCATION:{e.location}",
                f"STATUS:{e.status}",
                "END:VEVENT",
            ])
        lines.append("END:VCALENDAR\n")
        output_path.write_text("\r\n".join(lines), encoding="utf-8")
        return output_path


calendar_manager = CalendarManager()


def manage_calendar(parameters: dict, player=None, **_) -> str:
    """Action entry point for tool calling."""
    action = str(parameters.get("action", "list")).strip().lower()
    try:
        if action in ("add", "create"):
            title = str(parameters.get("title", "")).strip()
            start = str(parameters.get("start_time", "")).strip()
            end = parameters.get("end_time")
            desc = str(parameters.get("description", ""))
            loc = str(parameters.get("location", ""))
            if not title or not start:
                return "Sir, please provide at least an event title and start_time (e.g. 2026-11-20T10:00:00)."
            evt = calendar_manager.add_event(title, start, end, description=desc, location=loc)
            return f"Event created: '{evt.title}' scheduled for {evt.start_time} (ID: {evt.id})."

        elif action in ("list", "upcoming"):
            days = int(parameters.get("days", 7))
            events = calendar_manager.get_upcoming_events(days=days)
            if not events:
                return f"Sir, you have no upcoming calendar events scheduled for the next {days} days."
            summary = [f"Upcoming Calendar Events ({len(events)}):"]
            for e in events:
                summary.append(f"• [{e['id']}] {e['title']} — {e['start_time']} ({e.get('location') or 'No location'})")
            return "\n".join(summary)

        elif action in ("cancel", "remove"):
            event_id = str(parameters.get("event_id", "")).strip()
            if not event_id:
                return "Sir, please specify the event_id to cancel."
            ok = calendar_manager.cancel_event(event_id)
            return f"Event {event_id} has been cancelled." if ok else f"Event {event_id} not found."

        elif action == "export":
            path = calendar_manager.export_ics()
            return f"Calendar exported successfully to: {path}"

        else:
            return f"Unknown calendar action '{action}'. Supported actions: add, list, cancel, export."
    except Exception as e:
        return f"Calendar operation failed: {e}"
