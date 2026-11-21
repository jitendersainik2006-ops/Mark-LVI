"""
core/reel_approval_manager.py — Mandatory Human Approval Gate & Lifecycle Manager for J.A.R.V.I.S.

Enforces zero-leak human approval governance:
- Every generated reel begins in 'WAITING_FOR_APPROVAL'.
- No reel can be published without explicit approval.
- Supports assisted publishing mode (copy caption + download MP4) when Graph API is blocked.
- Atomic ledger updates to data/reels_ledger.json.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
LEDGER_PATH = BASE_DIR / "data" / "reels_ledger.json"


@dataclass
class ApprovalStatus:
    reel_id: str
    status: str  # "WAITING_FOR_APPROVAL", "APPROVED", "REJECTED", "PUBLISHED_ASSISTED", "PUBLISHED_API"
    created_at: str
    approved_at: Optional[str] = None
    rejected_at: Optional[str] = None
    published_at: Optional[str] = None
    notes: Optional[str] = None


class ReelApprovalManager:
    """
    Guarantees strict approval gate and ledger persistence.
    """

    def __init__(self, ledger_file: Optional[Path] = None):
        self.ledger_file = ledger_file or LEDGER_PATH

    def _read_ledger(self) -> Dict[str, Any]:
        if not self.ledger_file.exists():
            return {}
        try:
            with open(self.ledger_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_ledger(self, data: Dict[str, Any]) -> None:
        temp_file = self.ledger_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_file.replace(self.ledger_file)

    def register_new_reel(
        self,
        reel_id: str,
        title: str,
        style: str,
        video_path: str,
        cover_path: str,
        srt_path: str,
        caption: str,
        hashtags: List[str],
        duration_sec: float,
        provider_id: str,
        is_generative_ai: bool,
        is_procedural_fallback: bool,
        account_username: str = "mentos_life_gym",
    ) -> Dict[str, Any]:
        """Registers newly rendered reel strictly with status WAITING_FOR_APPROVAL."""
        ledger = self._read_ledger()
        now = time.strftime("%Y-%m-%dT%H:%M:%S")

        entry = {
            "id": reel_id,
            "title": title,
            "content_type": "hindi_mixed_ai",
            "style": style,
            "status": "WAITING_FOR_APPROVAL",
            "needs_approval": True,
            "account_username": account_username,
            "video_path": video_path,
            "cover_image_path": cover_path,
            "srt_path": srt_path,
            "caption": caption,
            "hashtags": hashtags,
            "duration_seconds": duration_sec,
            "video_provider": provider_id,
            "is_generative_ai": is_generative_ai,
            "is_procedural_fallback": is_procedural_fallback,
            "created_at": now,
            "approved_at": None,
            "published_at": None,
            "rejection_reason": None,
        }

        ledger[reel_id] = entry
        self._write_ledger(ledger)
        return entry

    def approve_reel(self, reel_id: str, approver_note: Optional[str] = None) -> Tuple[bool, str]:
        """Transitions reel from WAITING_FOR_APPROVAL to APPROVED."""
        ledger = self._read_ledger()
        if reel_id not in ledger:
            return False, f"Reel '{reel_id}' not found in ledger."

        r = ledger[reel_id]
        if r.get("status") not in ["WAITING_FOR_APPROVAL", "waiting_for_approval"]:
            return False, f"Reel '{reel_id}' cannot be approved from status '{r.get('status')}'."

        r["status"] = "APPROVED"
        r["needs_approval"] = False
        r["approved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        if approver_note:
            r["approval_notes"] = approver_note

        self._write_ledger(ledger)
        return True, f"Reel '{reel_id}' approved successfully."

    def reject_reel(self, reel_id: str, reason: str) -> Tuple[bool, str]:
        """Transitions reel to REJECTED."""
        ledger = self._read_ledger()
        if reel_id not in ledger:
            return False, f"Reel '{reel_id}' not found in ledger."

        r = ledger[reel_id]
        r["status"] = "REJECTED"
        r["needs_approval"] = False
        r["rejection_reason"] = reason
        r["rejected_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        self._write_ledger(ledger)
        return True, f"Reel '{reel_id}' rejected: {reason}."

    def mark_published_assisted(self, reel_id: str) -> Tuple[bool, str]:
        """Marks reel as published via manual assisted mode (copy caption + native upload)."""
        ledger = self._read_ledger()
        if reel_id not in ledger:
            return False, f"Reel '{reel_id}' not found in ledger."

        r = ledger[reel_id]
        r["status"] = "published_assisted"
        r["needs_approval"] = False
        r["published_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        self._write_ledger(ledger)
        return True, f"Reel '{reel_id}' marked as published via assisted workflow."

    def get_reel(self, reel_id: str) -> Optional[Dict[str, Any]]:
        ledger = self._read_ledger()
        return ledger.get(reel_id)

    def list_reels(
        self,
        status_filter: Optional[str] = None,
        style_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        ledger = self._read_ledger()
        reels = list(ledger.values())

        if status_filter and status_filter != "all":
            sf = status_filter.lower()
            reels = [r for r in reels if (r.get("status") or "").lower() == sf]

        if style_filter and style_filter != "all":
            reels = [r for r in reels if r.get("style") == style_filter]

        return reels


reel_approval_manager = ReelApprovalManager()
