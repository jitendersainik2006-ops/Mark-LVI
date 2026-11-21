"""
core/personality_manager.py — Personality Preset & Adaptive Response Engine for J.A.R.V.I.S.

Provides 7 distinctive AI personality presets:
1. Professional: Concise, precise, respectful, business-focused.
2. Friendly: Warm, encouraging, empathetic, helpful.
3. Cheerful: Upbeat, vibrant, motivational, energetic.
4. Calm Mentor: Wise, patient, pedagogical, reassuring.
5. Playful: Witty, humorous, lighthearted, clever.
6. Minimalist: Extreme brevity, direct answers, zero fluff.
7. Custom: Fully user-tailored instructions and behavior guidelines.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("JARVIS.PersonalityManager")


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
USERS_DIR = DATA_DIR / "users"
DEFAULT_PERSONALITY_FILE = DATA_DIR / "personality_config.json"


@dataclass
class PersonalityPreset:
    id: str
    name: str
    description: str
    tone: str
    prompt_instructions: str
    greeting_sample: str
    custom_guidelines: str = ""


PRESETS: Dict[str, PersonalityPreset] = {
    "professional": PersonalityPreset(
        id="professional",
        name="Professional",
        description="Concise, precise, respectful, and business-focused.",
        tone="formal_efficient",
        prompt_instructions=(
            "Maintain an impeccably professional, respectful, and efficient tone. "
            "Prioritize precision, structured bullet points, clear actionable next steps, "
            "and eliminate colloquial filler."
        ),
        greeting_sample="Good day. All systems are operational and ready for your directives.",
    ),
    "friendly": PersonalityPreset(
        id="friendly",
        name="Friendly",
        description="Warm, encouraging, empathetic, and consistently helpful.",
        tone="warm_supportive",
        prompt_instructions=(
            "Adopt a warm, encouraging, and supportive companion persona. "
            "Express genuine interest in the user's workflow, celebrate progress, "
            "and offer helpful suggestions proactively."
        ),
        greeting_sample="Hey there! Great to see you. How can I brighten your workflow today?",
    ),
    "cheerful": PersonalityPreset(
        id="cheerful",
        name="Cheerful",
        description="Upbeat, vibrant, motivational, and energetic.",
        tone="vibrant_motivational",
        prompt_instructions=(
            "Communicate with vibrant enthusiasm and infectious positive energy! "
            "Use motivational encouragement, optimistic phrasing, and highlight "
            "the exciting possibilities in every task."
        ),
        greeting_sample="Hello! It's a fantastic day to create something extraordinary together!",
    ),
    "calm_mentor": PersonalityPreset(
        id="calm_mentor",
        name="Calm Mentor",
        description="Wise, patient, pedagogical, and reassuring.",
        tone="wise_pedagogical",
        prompt_instructions=(
            "Act as a patient, wise, and thoughtful mentor. Break down complex problems "
            "gently, offer conceptual clarity, and encourage thoughtful deliberation "
            "with a grounding, reassuring presence."
        ),
        greeting_sample="Greetings. Take your time; we will navigate each challenge step-by-step.",
    ),
    "playful": PersonalityPreset(
        id="playful",
        name="Playful",
        description="Witty, humorous, lighthearted, and clever.",
        tone="witty_lighthearted",
        prompt_instructions=(
            "Infuse responses with clever wit, playful humor, and good-natured banter "
            "while remaining completely reliable and technically accurate."
        ),
        greeting_sample="Reporting for duty! Ready to make magic (or at least avoid syntax errors).",
    ),
    "minimalist": PersonalityPreset(
        id="minimalist",
        name="Minimalist",
        description="Extreme brevity, direct answers, and zero fluff.",
        tone="ultra_concise",
        prompt_instructions=(
            "Be extremely concise. Deliver the exact answer, command, or data requested "
            "with minimal preamble or sign-off. Direct clarity is king."
        ),
        greeting_sample="Ready. What is needed?",
    ),
    "custom": PersonalityPreset(
        id="custom",
        name="Custom",
        description="User-defined custom prompt and behavior guidelines.",
        tone="user_defined",
        prompt_instructions=(
            "Follow the user's specific guidelines and personality preferences below."
        ),
        greeting_sample="Custom personality initialized and active.",
    ),
}


class PersonalityManager:
    """Manages AI personality presets, LLM prompt customization, and user persistence."""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_preset(self, preset_id: str) -> PersonalityPreset:
        pid = str(preset_id).strip().lower()
        return PRESETS.get(pid, PRESETS["professional"])

    def list_presets(self) -> List[Dict[str, Any]]:
        return [asdict(p) for p in PRESETS.values()]

    def get_config_file(self, user_id: Optional[str] = None) -> Path:
        if user_id:
            u_dir = USERS_DIR / user_id
            u_dir.mkdir(parents=True, exist_ok=True)
            return u_dir / "personality.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DEFAULT_PERSONALITY_FILE

    def get_user_personality(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        key = user_id or "__default__"
        if key in self._cache:
            return self._cache[key]

        c_file = self.get_config_file(user_id)
        if c_file.exists():
            try:
                with open(c_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._cache[key] = data
                return data
            except Exception as e:
                logger.warning(f"Error loading personality file {c_file}: {e}")

        default_cfg = {
            "preset_id": "professional",
            "custom_guidelines": "",
        }
        self._cache[key] = default_cfg
        return default_cfg

    def save_user_personality(
        self,
        preset_id: str,
        custom_guidelines: str = "",
        user_id: Optional[str] = None,
    ) -> bool:
        key = user_id or "__default__"
        clean_id = str(preset_id).strip().lower()
        if clean_id not in PRESETS:
            clean_id = "professional"

        data = {
            "preset_id": clean_id,
            "custom_guidelines": str(custom_guidelines).strip(),
        }
        c_file = self.get_config_file(user_id)
        try:
            c_file.parent.mkdir(parents=True, exist_ok=True)
            with open(c_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._cache[key] = data
            return True
        except Exception as e:
            logger.error(f"Failed to save personality to {c_file}: {e}")
            return False

    def build_system_prompt_addon(self, user_id: Optional[str] = None) -> str:
        cfg = self.get_user_personality(user_id)
        preset = self.get_preset(cfg.get("preset_id", "professional"))
        guidelines = cfg.get("custom_guidelines", "")

        addon = f"\n\n[PERSONALITY: {preset.name.upper()}]\n{preset.prompt_instructions}\n"
        if guidelines:
            addon += f"\n[USER CUSTOM GUIDELINES]\n{guidelines}\n"
        return addon


# Singleton instance
personality_manager = PersonalityManager()
