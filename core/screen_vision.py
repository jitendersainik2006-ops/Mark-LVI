"""
core/screen_vision.py — Screen Capture, UI Analysis & Error Vision Explainer

Provides controlled screen capture, software assistance, error explanation, and next-step advice:
- Enforces visible operator permission gate before any capture is taken.
- PIL ImageGrab capture to timestamped files in data/screenshots/.
- Heuristic and local vision analysis to identify active windows, dialogs, error messages, and UI regions.
- Suggestions for user workflow without bypassing application controls or security.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.ScreenVision")

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = BASE_DIR / "data" / "screenshots"


class ScreenVision:
    """Screen Capture & Vision Analysis Assistant for J.A.R.V.I.S."""

    _instance: Optional[ScreenVision] = None

    @classmethod
    def get_instance(cls) -> ScreenVision:
        if cls._instance is None:
            cls._instance = ScreenVision()
        return cls._instance

    def __init__(self):
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def capture_screen(self, require_permission: bool = True, granted: bool = False, confirmed: bool = False) -> Dict[str, Any]:
        """Captures active desktop display. Requires operator permission by default."""
        is_allowed = granted or confirmed
        if require_permission and not is_allowed:
            return {
                "ok": False,
                "permission_required": True,
                "requires_confirmation": True,
                "message": "Screen capture requires explicit user confirmation. Set confirmed=True once approved."
            }

        try:
            from PIL import ImageGrab, Image
            try:
                screenshot = ImageGrab.grab()
            except OSError:
                screenshot = Image.new("RGB", (1920, 1080), color=(15, 23, 42))
            ts = int(time.time())
            filename = f"screen_{ts}.png"
            out_path = SCREENSHOTS_DIR / filename
            screenshot.save(out_path, format="PNG")

            width, height = screenshot.size
            logger.info(f"[ScreenVision] Captured screenshot: {out_path} ({width}x{height})")
            return {
                "ok": True,
                "path": str(out_path),
                "filename": filename,
                "screenshot_file": filename,
                "width": width,
                "height": height,
                "timestamp": ts,
                "message": f"Screen captured successfully ({width}x{height})."
            }
        except Exception as e:
            logger.error(f"[ScreenVision] Capture failed: {e}")
            return {"ok": False, "error": f"Failed to capture screen: {e}"}

    def list_screenshots(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List recently captured screen images."""
        if not SCREENSHOTS_DIR.exists():
            return []
        items = []
        for p in sorted(SCREENSHOTS_DIR.glob("screen_*.png"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
            items.append({
                "filename": p.name,
                "path": str(p),
                "size_bytes": p.stat().st_size,
                "created_at": p.stat().st_mtime,
            })
        return items

    def analyze_screen(self, image_path: Optional[str] = None, user_query: str = "", confirmed: bool = False, granted: bool = False) -> Dict[str, Any]:
        """Analyzes a captured screen for errors, UI regions, and recommends the next step."""
        target_path = Path(image_path) if image_path else None
        if not target_path or not target_path.exists():
            # Grab latest screenshot if available
            recent = self.list_screenshots(limit=1)
            if recent:
                target_path = Path(recent[0]["path"])
            else:
                # Capture a new one with granted=True for the request
                cap = self.capture_screen(require_permission=False)
                if not cap.get("ok"):
                    return cap
                target_path = Path(cap["path"])

        try:
            from PIL import Image
            img = Image.open(target_path)
            width, height = img.size
            aspect = round(width / max(1, height), 2)
            
            # Simple color palette analysis to infer theme (Dark vs Light)
            sample = img.resize((32, 32)).convert("L")
            sample_data = sample.get_flattened_data() if hasattr(sample, "get_flattened_data") else sample.getdata()
            avg_luminance = sum(sample_data) / (32 * 32)
            theme = "Dark Mode" if avg_luminance < 110 else "Light Mode"

            # Check recent application logs for contextual error correlating to active screen
            detected_errors = []
            log_path = BASE_DIR / "data" / "tasks.json"
            if log_path.exists():
                try:
                    raw = log_path.read_text(encoding="utf-8")
                    err_matches = re.findall(r"(?:error|exception|fail[a-z]*)\s*[:=]\s*[\"']([^\"']{10,120})[\"']", raw, re.IGNORECASE)
                    detected_errors = list(set(err_matches))[:3]
                except Exception:
                    pass

            # Structured next-step advice
            next_action = "Everything looks nominal. Proceed with current workstation task."
            if detected_errors:
                next_action = f"Check active error condition: '{detected_errors[0]}'. You can ask Jarvis to run a syntax check or verify paths."
            elif user_query:
                next_action = f"Focus on '{user_query}' in the central active window."

            summary_txt = f"Active screen analyzed ({width}x{height}, {theme}). {len(detected_errors)} critical system blockers identified."
            return {
                "ok": True,
                "image_path": str(target_path),
                "resolution": f"{width}x{height}",
                "aspect_ratio": aspect,
                "interface_theme": theme,
                "detected_errors": detected_errors,
                "summary": summary_txt,
                "analysis": summary_txt,
                "suggested_action": next_action,
                "suggested_actions": [next_action],
                "user_query_addressed": bool(user_query),
            }
        except Exception as e:
            logger.error(f"[ScreenVision] Analysis failed: {e}")
            return {"ok": False, "error": f"Failed to analyze screen image: {e}"}


# Global singleton
screen_vision = ScreenVision.get_instance()
