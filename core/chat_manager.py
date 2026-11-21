"""
core/chat_manager.py — J.A.R.V.I.S. Multi-Device Synchronized Chat & Conversation History

Provides:
- Persistent conversation storage in `data/chat_history.json`.
- Strict message ID generation and deduplication (client_msg_id idempotency).
- Accurate message lifecycles: pending -> completed | failed.
- Dual-origin tracking ('phone' vs 'laptop') for proper voice and UI routing.
- Reconnection sync with since_id incremental retrieval.
- Thread-safe disk persistence before reporting completion.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
CHAT_FILE = DATA_DIR / "chat_history.json"


@dataclass
class ChatMessage:
    id: str
    speaker: str  # "user" | "jarvis" | "system"
    text: str
    origin: str = "phone"  # "phone" | "laptop"
    status: str = "completed"  # "pending" | "completed" | "failed"
    ts: str = field(default_factory=lambda: datetime.now().isoformat())
    audio_id: Optional[str] = None
    client_msg_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class ChatManager:
    """Manages synchronized conversation history across phone dashboard and laptop HUD."""

    def __init__(self, chat_file: Optional[Path] = None):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._chat_file = Path(chat_file) if chat_file else CHAT_FILE
        self._lock = Lock()
        self._messages: List[ChatMessage] = []
        self._msg_by_id: Dict[str, ChatMessage] = {}
        self._client_ids: Dict[str, str] = {}  # client_msg_id -> msg_id (last 100)
        self._load()

    def _load(self) -> None:
        with self._lock:
            if not self._chat_file.exists():
                return
            try:
                data = json.loads(self._chat_file.read_text(encoding="utf-8"))
                dirty = False
                for item in data:
                    msg = ChatMessage(**item)
                    if msg.speaker == "jarvis" and msg.status == "pending":
                        msg.status = "failed"
                        msg.error = "Request timed out or session was interrupted."
                        msg.text = "⚠️ Request timed out or session was interrupted."
                        dirty = True
                    self._messages.append(msg)
                    self._msg_by_id[msg.id] = msg
                    if msg.client_msg_id:
                        self._client_ids[msg.client_msg_id] = msg.id
                if dirty:
                    self._save_unlocked()
            except Exception as e:
                print(f"[ChatManager] Failed loading chat history: {e}")

    def _save_unlocked(self) -> None:
        try:
            # Keep latest 300 messages to prevent unbounded disk growth
            if len(self._messages) > 300:
                self._messages = self._messages[-300:]
                self._msg_by_id = {m.id: m for m in self._messages}
            raw = [m.to_dict() for m in self._messages]
            self._chat_file.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[ChatManager] Failed saving chat history: {e}")

    # ── Message Operations ───────────────────────────────────────────────────

    def add_user_message(
        self,
        text: str,
        origin: str = "phone",
        client_msg_id: str = "",
    ) -> Tuple[dict, dict, bool]:
        """
        Records a user message and generates a paired pending assistant placeholder.
        Returns: (user_msg_dict, assistant_msg_dict, is_duplicate)
        """
        clean_text = text.strip()
        cid = client_msg_id.strip()

        with self._lock:
            # Idempotency check: prevent duplicate responses on mobile reconnect or retry
            if cid and cid in self._client_ids:
                existing_user_id = self._client_ids[cid]
                user_msg = self._msg_by_id.get(existing_user_id)
                # Find corresponding assistant message
                idx = -1
                for i, m in enumerate(self._messages):
                    if m.id == existing_user_id:
                        idx = i
                        break
                asst_msg = None
                if idx >= 0 and idx + 1 < len(self._messages):
                    nxt = self._messages[idx + 1]
                    if nxt.speaker == "jarvis":
                        asst_msg = nxt
                if user_msg and asst_msg:
                    return user_msg.to_dict(), asst_msg.to_dict(), True

            t_now = datetime.now().isoformat()
            u_id = f"msg_{int(time.time())}_{uuid.uuid4().hex[:6]}"
            a_id = f"msg_{int(time.time())}_{uuid.uuid4().hex[:6]}"

            u_msg = ChatMessage(
                id=u_id,
                speaker="user",
                text=clean_text,
                origin=origin,
                status="completed",
                ts=t_now,
                client_msg_id=cid if cid else None,
            )

            a_msg = ChatMessage(
                id=a_id,
                speaker="jarvis",
                text="",
                origin=origin,
                status="pending",
                ts=t_now,
            )

            self._messages.append(u_msg)
            self._messages.append(a_msg)
            self._msg_by_id[u_id] = u_msg
            self._msg_by_id[a_id] = a_msg
            if cid:
                self._client_ids[cid] = u_id

            self._save_unlocked()
            return u_msg.to_dict(), a_msg.to_dict(), False

    def complete_assistant_message(
        self,
        msg_id: str,
        text: str,
        audio_id: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Updates assistant message to completed and saves to disk BEFORE returning.
        Ensures responses are saved before being reported as completed.
        """
        with self._lock:
            msg = self._msg_by_id.get(msg_id)
            if not msg:
                # If not found by ID, look for the most recent pending assistant message
                for m in reversed(self._messages):
                    if m.speaker == "jarvis" and m.status == "pending":
                        msg = m
                        break
            if not msg:
                # Create one if missing
                msg_id = f"msg_{int(time.time())}_{uuid.uuid4().hex[:6]}"
                msg = ChatMessage(
                    id=msg_id,
                    speaker="jarvis",
                    text=text,
                    status="completed",
                    audio_id=audio_id,
                )
                self._messages.append(msg)
                self._msg_by_id[msg_id] = msg
            else:
                msg.text = text
                msg.status = "completed"
                msg.audio_id = audio_id
                msg.error = None

            self._save_unlocked()
            return msg.to_dict()

    def fail_assistant_message(self, msg_id: str, error: str) -> Optional[dict]:
        """Marks assistant message as failed with error details and saves to disk."""
        with self._lock:
            msg = self._msg_by_id.get(msg_id)
            if not msg:
                for m in reversed(self._messages):
                    if m.speaker == "jarvis" and m.status == "pending":
                        msg = m
                        break
            if not msg:
                return None
            msg.status = "failed"
            msg.error = error
            msg.text = f"⚠️ Could not generate response: {error}"
            self._save_unlocked()
            return msg.to_dict()

    def record_laptop_exchange(
        self,
        user_text: str,
        asst_text: str,
        audio_id: Optional[str] = None,
    ) -> Tuple[dict, dict]:
        """
        Records a completed conversational turn originated from the laptop (mic or desktop HUD)
        so it immediately syncs into the phone's shared conversation history.
        """
        t_now = datetime.now().isoformat()
        u_id = f"msg_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        a_id = f"msg_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        with self._lock:
            u_msg = ChatMessage(
                id=u_id,
                speaker="user",
                text=user_text.strip() or "[Laptop Voice Input]",
                origin="laptop",
                status="completed",
                ts=t_now,
            )
            a_msg = ChatMessage(
                id=a_id,
                speaker="jarvis",
                text=asst_text.strip(),
                origin="laptop",
                status="completed",
                ts=t_now,
                audio_id=audio_id,
            )
            self._messages.append(u_msg)
            self._messages.append(a_msg)
            self._msg_by_id[u_id] = u_msg
            self._msg_by_id[a_id] = a_msg
            self._save_unlocked()
            return u_msg.to_dict(), a_msg.to_dict()

    def get_history(self, limit: int = 50, since_id: Optional[str] = None) -> List[dict]:
        """
        Retrieves message history. If since_id is provided, returns all messages
        created after that message for seamless reconnection catch-up.
        Automatically resolves any pending message older than 30s to failed.
        """
        with self._lock:
            # Check for any pending assistant messages older than 30 seconds and mark failed
            dirty = False
            now = datetime.now()
            for m in self._messages:
                if m.speaker == "jarvis" and m.status == "pending":
                    try:
                        created = datetime.fromisoformat(m.ts)
                        age = (now - created).total_seconds()
                    except Exception:
                        age = 999
                    if age > 30:
                        m.status = "failed"
                        m.error = "Request timed out (no response within 30s)"
                        m.text = "⚠️ Request timed out."
                        dirty = True
            if dirty:
                self._save_unlocked()

            if not since_id:
                return [m.to_dict() for m in self._messages[-limit:]]
            
            # Find index of since_id
            idx = -1
            for i, m in enumerate(self._messages):
                if m.id == since_id:
                    idx = i
                    break
            if idx >= 0:
                return [m.to_dict() for m in self._messages[idx + 1 : idx + 1 + limit]]
            # If since_id not found (e.g. purged), return latest limit
            return [m.to_dict() for m in self._messages[-limit:]]

    def cancel_message(self, msg_id: str) -> Optional[dict]:
        """Cancels a pending message and marks it failed."""
        with self._lock:
            msg = self._msg_by_id.get(msg_id)
            if not msg:
                return None
            if msg.status == "pending":
                msg.status = "failed"
                msg.error = "Cancelled by user"
                msg.text = "⚠️ Request cancelled."
                self._save_unlocked()
            return msg.to_dict()

    def cleanup_stale_pending(self, max_age_seconds: float = 30.0) -> int:
        """Forces all pending messages older than max_age_seconds to failed status."""
        count = 0
        now = datetime.now()
        with self._lock:
            for m in self._messages:
                if m.status == "pending":
                    try:
                        created = datetime.fromisoformat(m.ts)
                        age = (now - created).total_seconds()
                    except Exception:
                        age = 999
                    if age >= max_age_seconds:
                        m.status = "failed"
                        m.error = "Stale pending message auto-cleaned"
                        m.text = "⚠️ Request timed out."
                        count += 1
            if count > 0:
                self._save_unlocked()
        return count

    def get_message(self, msg_id: str) -> Optional[dict]:
        with self._lock:
            m = self._msg_by_id.get(msg_id)
            if m and m.status == "pending":
                try:
                    created = datetime.fromisoformat(m.ts)
                    if (datetime.now() - created).total_seconds() > 30:
                        m.status = "failed"
                        m.error = "Request timed out"
                        m.text = "⚠️ Request timed out."
                        self._save_unlocked()
                except Exception:
                    pass
            return m.to_dict() if m else None

    def clear_history(self) -> None:
        with self._lock:
            self._messages.clear()
            self._msg_by_id.clear()
            self._client_ids.clear()
            self._save_unlocked()


# Singleton instance
chat_manager = ChatManager()
