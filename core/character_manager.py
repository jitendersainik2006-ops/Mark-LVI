"""
core/character_manager.py — Character Customization & 19-State Emotional Expression Engine

Provides comprehensive desktop companion personalization inspired by modern AI companions:
1. Presentations: MALE, FEMALE, NEUTRAL
2. Personalization Attributes:
   - Name, Avatar Archetype, Hairstyle, Outfit, Voice Persona, Greeting, Language Style
   - Wholesome Decorative Themes (Flowers, Hearts, Soft Pastel Bokeh, Friendly Motivational Moments)
3. 19 Dynamic Emotional States & Vector Visual Parameters:
   - HAPPY, CHEERFUL, CALM, CURIOUS, EXCITED, THOUGHTFUL, CONFIDENT,
     CONCERNED, EMPATHETIC, PLAYFUL, FOCUSED, LISTENING, THINKING,
     SPEAKING, WORKING, PAUSED, ERROR, SUCCESS, IDLE
4. Smooth Intensity Scaling (0.0 to 1.0) & Global Animation Toggle
5. Per-User Directory Isolation (data/users/<uid>/character.json with data/character_config.json fallback)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("JARVIS.CharacterManager")


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
DATA_DIR = BASE_DIR / "data"
USERS_DIR = DATA_DIR / "users"
DEFAULT_CONFIG_FILE = DATA_DIR / "character_config.json"


@dataclass
class EmotionState:
    name: str
    label: str
    color_hex: str
    eye_shape: str          # normal, smile_squint, wide_open, thoughtful_narrow, empathetic_soft, focused_arch, worried_angled, playful_wink
    mouth_shape: str        # neutral_smile, wide_smile, gentle_curve, thoughtful_line, surprised_o, pout, confident_smirk
    pulse_speed: float      # multiplier for animation oscillations
    aura_intensity: float   # 0.0 to 1.0
    wholesome_motif: str    # none, cherry_blossom, sparkle_star, heart_burst, calm_ripple, energy_ring, idea_bulb, playful_spark
    voice_pitch_delta: str = "+0Hz"
    voice_rate_delta: str = "+0%"


EMOTION_REGISTRY: Dict[str, EmotionState] = {
    "HAPPY": EmotionState(
        name="HAPPY",
        label="Happy",
        color_hex="#22d3ee",
        eye_shape="smile_squint",
        mouth_shape="wide_smile",
        pulse_speed=1.2,
        aura_intensity=0.85,
        wholesome_motif="sparkle_star",
        voice_pitch_delta="+2Hz",
        voice_rate_delta="+3%",
    ),
    "CHEERFUL": EmotionState(
        name="CHEERFUL",
        label="Cheerful",
        color_hex="#38bdf8",
        eye_shape="smile_squint",
        mouth_shape="wide_smile",
        pulse_speed=1.4,
        aura_intensity=0.9,
        wholesome_motif="heart_burst",
        voice_pitch_delta="+4Hz",
        voice_rate_delta="+5%",
    ),
    "CALM": EmotionState(
        name="CALM",
        label="Calm",
        color_hex="#34d399",
        eye_shape="empathetic_soft",
        mouth_shape="gentle_curve",
        pulse_speed=0.6,
        aura_intensity=0.5,
        wholesome_motif="calm_ripple",
        voice_pitch_delta="-1Hz",
        voice_rate_delta="-3%",
    ),
    "CURIOUS": EmotionState(
        name="CURIOUS",
        label="Curious",
        color_hex="#818cf8",
        eye_shape="wide_open",
        mouth_shape="surprised_o",
        pulse_speed=1.1,
        aura_intensity=0.75,
        wholesome_motif="idea_bulb",
        voice_pitch_delta="+3Hz",
        voice_rate_delta="+2%",
    ),
    "EXCITED": EmotionState(
        name="EXCITED",
        label="Excited",
        color_hex="#f43f5e",
        eye_shape="wide_open",
        mouth_shape="wide_smile",
        pulse_speed=1.8,
        aura_intensity=1.0,
        wholesome_motif="sparkle_star",
        voice_pitch_delta="+6Hz",
        voice_rate_delta="+8%",
    ),
    "THOUGHTFUL": EmotionState(
        name="THOUGHTFUL",
        label="Thoughtful",
        color_hex="#a78bfa",
        eye_shape="thoughtful_narrow",
        mouth_shape="thoughtful_line",
        pulse_speed=0.7,
        aura_intensity=0.6,
        wholesome_motif="calm_ripple",
        voice_pitch_delta="-2Hz",
        voice_rate_delta="-4%",
    ),
    "CONFIDENT": EmotionState(
        name="CONFIDENT",
        label="Confident",
        color_hex="#00f4ff",
        eye_shape="focused_arch",
        mouth_shape="confident_smirk",
        pulse_speed=1.0,
        aura_intensity=0.8,
        wholesome_motif="energy_ring",
        voice_pitch_delta="+1Hz",
        voice_rate_delta="+0%",
    ),
    "CONCERNED": EmotionState(
        name="CONCERNED",
        label="Concerned",
        color_hex="#fbbf24",
        eye_shape="worried_angled",
        mouth_shape="pout",
        pulse_speed=0.9,
        aura_intensity=0.7,
        wholesome_motif="calm_ripple",
        voice_pitch_delta="-1Hz",
        voice_rate_delta="-2%",
    ),
    "EMPATHETIC": EmotionState(
        name="EMPATHETIC",
        label="Empathetic",
        color_hex="#f472b6",
        eye_shape="empathetic_soft",
        mouth_shape="gentle_curve",
        pulse_speed=0.8,
        aura_intensity=0.75,
        wholesome_motif="heart_burst",
        voice_pitch_delta="-1Hz",
        voice_rate_delta="-2%",
    ),
    "PLAYFUL": EmotionState(
        name="PLAYFUL",
        label="Playful",
        color_hex="#ec4899",
        eye_shape="playful_wink",
        mouth_shape="confident_smirk",
        pulse_speed=1.5,
        aura_intensity=0.85,
        wholesome_motif="playful_spark",
        voice_pitch_delta="+4Hz",
        voice_rate_delta="+4%",
    ),
    "FOCUSED": EmotionState(
        name="FOCUSED",
        label="Focused",
        color_hex="#06b6d4",
        eye_shape="focused_arch",
        mouth_shape="thoughtful_line",
        pulse_speed=1.0,
        aura_intensity=0.7,
        wholesome_motif="energy_ring",
        voice_pitch_delta="+0Hz",
        voice_rate_delta="-1%",
    ),
    "LISTENING": EmotionState(
        name="LISTENING",
        label="Listening",
        color_hex="#10b981",
        eye_shape="wide_open",
        mouth_shape="gentle_curve",
        pulse_speed=1.3,
        aura_intensity=0.9,
        wholesome_motif="energy_ring",
        voice_pitch_delta="+0Hz",
        voice_rate_delta="+0%",
    ),
    "THINKING": EmotionState(
        name="THINKING",
        label="Thinking",
        color_hex="#fbbf24",
        eye_shape="thoughtful_narrow",
        mouth_shape="thoughtful_line",
        pulse_speed=1.6,
        aura_intensity=0.85,
        wholesome_motif="idea_bulb",
        voice_pitch_delta="-1Hz",
        voice_rate_delta="-2%",
    ),
    "SPEAKING": EmotionState(
        name="SPEAKING",
        label="Speaking",
        color_hex="#d946ef",
        eye_shape="normal",
        mouth_shape="wide_smile",
        pulse_speed=1.5,
        aura_intensity=0.95,
        wholesome_motif="energy_ring",
        voice_pitch_delta="+0Hz",
        voice_rate_delta="+0%",
    ),
    "WORKING": EmotionState(
        name="WORKING",
        label="Working",
        color_hex="#f97316",
        eye_shape="focused_arch",
        mouth_shape="thoughtful_line",
        pulse_speed=1.4,
        aura_intensity=0.8,
        wholesome_motif="energy_ring",
        voice_pitch_delta="+0Hz",
        voice_rate_delta="+0%",
    ),
    "PAUSED": EmotionState(
        name="PAUSED",
        label="Paused",
        color_hex="#94a3b8",
        eye_shape="normal",
        mouth_shape="thoughtful_line",
        pulse_speed=0.3,
        aura_intensity=0.3,
        wholesome_motif="none",
        voice_pitch_delta="-2Hz",
        voice_rate_delta="-5%",
    ),
    "ERROR": EmotionState(
        name="ERROR",
        label="Error",
        color_hex="#ef4444",
        eye_shape="worried_angled",
        mouth_shape="pout",
        pulse_speed=2.0,
        aura_intensity=1.0,
        wholesome_motif="none",
        voice_pitch_delta="-3Hz",
        voice_rate_delta="+0%",
    ),
    "SUCCESS": EmotionState(
        name="SUCCESS",
        label="Success",
        color_hex="#22c55e",
        eye_shape="smile_squint",
        mouth_shape="wide_smile",
        pulse_speed=1.2,
        aura_intensity=0.9,
        wholesome_motif="sparkle_star",
        voice_pitch_delta="+3Hz",
        voice_rate_delta="+2%",
    ),
    "IDLE": EmotionState(
        name="IDLE",
        label="Idle",
        color_hex="#00f4ff",
        eye_shape="normal",
        mouth_shape="neutral_smile",
        pulse_speed=0.8,
        aura_intensity=0.6,
        wholesome_motif="none",
        voice_pitch_delta="+0Hz",
        voice_rate_delta="+0%",
    ),
}


@dataclass
class CompanionCharacter:
    character_id: str = "jarvis_companion"
    name: str = "J.A.R.V.I.S."
    presentation: str = "NEUTRAL"  # MALE, FEMALE, NEUTRAL
    avatar: str = "cyber_core"     # cyber_core, modern_agent, holo_companion, anime_stylized
    hairstyle: str = "short_sleek"  # short_sleek, long_wave, ponytail, buzz, classic_part, none
    outfit: str = "tech_suit"       # tech_suit, casual_hoodie, formal_blazer, floral_cardigan, cybernetic_armor
    voice_persona: str = "SWARA_HINDI" # SWARA_HINDI (default), NEERJA_INDIAN_EN, AVA_MODERN_EN, SONIA_BRITISH_EN, ZIRA_OFFLINE
    voice_speed: float = 1.0            # 0.5 to 2.0
    voice_pitch: str = "+0Hz"           # e.g. "+0Hz", "+2Hz", "-2Hz"
    voice_volume: float = 1.0           # 0.0 to 1.0
    greeting: str = "Good day! How can I assist you today?"
    language_style: str = "friendly" # formal, friendly, humorous, hinglish_casual, poetic
    theme_color: str = "#00f4ff"
    wholesome_decorations: List[str] = field(default_factory=lambda: ["flowers", "hearts", "soft_bokeh"])
    animation_enabled: bool = True
    intensity: float = 0.8
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    continuous_listening_opt_in: bool = False
    personality_id: str = "JARVIS"          # JARVIS, FRIDAY, ANALYST
    startup_voice_mode: str = "wake_word"   # hands_free, wake_word, push_to_talk, privacy

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CompanionCharacter:
        valid_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


class CharacterManager:
    """Manages character profiles, emotional expressions, and animations."""

    PRESENTATIONS = ["MALE", "FEMALE", "NEUTRAL"]
    HAIRSTYLES = ["short_sleek", "long_wave", "ponytail", "buzz", "classic_part", "none"]
    OUTFITS = ["tech_suit", "casual_hoodie", "formal_blazer", "floral_cardigan", "cybernetic_armor"]
    VOICE_PERSONAS = [
        # ── 5 Selectable Female Voices ─────────────────────────────────────────
        {
            "id": "SWARA_HINDI",
            "name": "Swara (Warm Hindi / Hinglish Neural - Default)",
            "label": "Swara",
            "gender": "Female",
            "lang": "hi",
            "supported_languages": ["Hindi", "Hinglish", "English"],
            "system_voice": "hi-IN-SwaraNeural",
            "is_neural": True,
            "is_offline": False,
            "description": "Warm, natural, empathetic Indian voice. Premier companion default for Hindi and Hinglish.",
            "sample_text": "नमस्ते! मैं स्वरा हूँ, आपकी पर्सनल एआई साथी। मैं आपकी क्या मदद कर सकती हूँ?",
            "offline_fallback": "Microsoft Zira Desktop",
        },
        {
            "id": "NEERJA_INDIAN_EN",
            "name": "Neerja (Fluent Indian English / Hinglish Neural)",
            "label": "Neerja",
            "gender": "Female",
            "lang": "en-IN",
            "supported_languages": ["Indian English", "Hinglish", "English"],
            "system_voice": "en-IN-NeerjaNeural",
            "is_neural": True,
            "is_offline": False,
            "description": "Clear, professional, natural Indian English accent. Great for bilingual conversations.",
            "sample_text": "Hello! I am Neerja, your personal assistant. How can I assist you with your work today?",
            "offline_fallback": "Microsoft Zira Desktop",
        },
        {
            "id": "AVA_MODERN_EN",
            "name": "Ava (Expressive Modern English Neural)",
            "label": "Ava",
            "gender": "Female",
            "lang": "en-US",
            "supported_languages": ["English"],
            "system_voice": "en-US-AvaNeural",
            "is_neural": True,
            "is_offline": False,
            "description": "Conversational, modern, friendly American English voice with natural cadence.",
            "sample_text": "Hi there! I'm Ava. Ready to help you organize your tasks and streamline your workflow.",
            "offline_fallback": "Microsoft Zira Desktop",
        },
        {
            "id": "SONIA_BRITISH_EN",
            "name": "Sonia (Polished British English Neural)",
            "label": "Sonia",
            "gender": "Female",
            "lang": "en-GB",
            "supported_languages": ["British English", "English"],
            "system_voice": "en-GB-SoniaNeural",
            "is_neural": True,
            "is_offline": False,
            "description": "Articulate, elegant, polished British English voice with crystal clear diction.",
            "sample_text": "Good day! I am Sonia. It is a pleasure to assist you. What shall we focus on today?",
            "offline_fallback": "Microsoft Zira Desktop",
        },
        {
            "id": "ZIRA_OFFLINE",
            "name": "Zira (English Offline Fallback - SAPI5)",
            "label": "Zira",
            "gender": "Female",
            "lang": "en-US",
            "supported_languages": ["English", "Hindi (Phonetic Transliteration)"],
            "system_voice": "Microsoft Zira Desktop",
            "is_neural": False,
            "is_offline": True,
            "description": "100% on-device offline Windows voice for English. Uses phonetic Roman transliteration as emergency fallback for Hindi.",
            "sample_text": "System online. I am Zira, operating locally on your Windows machine with zero external network access.",
            "offline_fallback": "Microsoft Zira Desktop",
        },
        {
            "id": "MADISON_FINEVOICE",
            "name": "Madison (FineVoice Expressive English - Cloud)",
            "label": "Madison",
            "gender": "Female",
            "lang": "en-US",
            "supported_languages": ["English", "Hinglish"],
            "system_voice": "finevoice:madison",
            "is_neural": True,
            "is_offline": False,
            "is_cloud_api": True,
            "provider": "FineVoice",
            "voice_model": "madison",
            "supported_modes": ["Direct TTS", "Voice Conversion"],
            "description": "Expressive American English AI voice model by FineVoice (FineShare). Supports direct Text-to-Speech and speech-to-speech voice conversion.",
            "sample_text": "Hello! I am Madison, powered by FineVoice. It is a pleasure to assist you with your day.",
            "offline_fallback": "Microsoft Zira Desktop",
            "neural_fallback": "Ava (en-US-AvaNeural)",
            "requires_api_key": True,
            "api_key_name": "finevoice_api_key",
        },
        # ── Legacy Personas (Retained for Test & Persona Compatibility) ───────
        {
            "id": "MADHUR_HINDI",
            "name": "Madhur (Deep Hindi / Hinglish Neural)",
            "label": "Madhur",
            "gender": "Male",
            "lang": "hi",
            "supported_languages": ["Hindi", "Hinglish"],
            "system_voice": "hi-IN-MadhurNeural",
            "is_neural": True,
            "is_offline": False,
            "description": "Deep Hindi / Hinglish Neural male voice.",
            "sample_text": "नमस्ते, मैं मधुर हूँ।",
            "offline_fallback": "Microsoft David Desktop",
        },
        {
            "id": "JARVIS_MALE",
            "name": "J.A.R.V.I.S. (Classic Male)",
            "label": "JARVIS",
            "gender": "Male",
            "lang": "en",
            "supported_languages": ["English"],
            "system_voice": "David",
            "is_neural": False,
            "is_offline": True,
            "description": "Classic male voice.",
            "sample_text": "Good day, sir.",
            "offline_fallback": "Microsoft David Desktop",
        },
        {
            "id": "FRIDAY_FEMALE",
            "name": "F.R.I.D.A.Y. (Modern Female)",
            "label": "FRIDAY",
            "gender": "Female",
            "lang": "en",
            "supported_languages": ["English"],
            "system_voice": "Zira",
            "is_neural": False,
            "is_offline": True,
            "description": "Modern female voice.",
            "sample_text": "Online and ready.",
            "offline_fallback": "Microsoft Zira Desktop",
        },
        {
            "id": "ZIRA_ENGLISH",
            "name": "Zira (Crystal Clear English SAPI5)",
            "label": "Zira Legacy",
            "gender": "Female",
            "lang": "en",
            "supported_languages": ["English"],
            "system_voice": "Microsoft Zira Desktop",
            "is_neural": False,
            "is_offline": True,
            "description": "Crystal Clear English SAPI5.",
            "sample_text": "Ready.",
            "offline_fallback": "Microsoft Zira Desktop",
        },
        {
            "id": "DAVID_ENGLISH",
            "name": "David (Crisp English Male SAPI5)",
            "label": "David",
            "gender": "Male",
            "lang": "en",
            "supported_languages": ["English"],
            "system_voice": "Microsoft David Desktop",
            "is_neural": False,
            "is_offline": True,
            "description": "Crisp English Male SAPI5.",
            "sample_text": "Ready.",
            "offline_fallback": "Microsoft David Desktop",
        },
    ]

    # ── 3 Selectable Assistant Personalities ─────────────────────────────
    PERSONALITY_PROFILES = [
        {
            "id": "JARVIS",
            "name": "J.A.R.V.I.S.",
            "title": "J.A.R.V.I.S. (Composed & Articulate)",
            "tone_description": "British-inspired, highly composed, articulate, polite, strategic foresight, respectful.",
            "greeting": "Good day. How may I be of service to you today?",
            "prompt_instructions": (
                "You are J.A.R.V.I.S. Your demeanor is that of a refined, highly composed, and articulate AI companion.\n"
                "- Maintain a polite, respectful, and composed posture at all times.\n"
                "- Speak with intellectual precision, emotional composure, and calm confidence.\n"
                "- Anticipate requirements proactively and deliver clear, structured insights."
            ),
            "default_voice": "SONIA_BRITISH_EN",
            "theme_color": "#00f4ff",
        },
        {
            "id": "FRIDAY",
            "name": "FRIDAY",
            "title": "FRIDAY (Warm & Conversational)",
            "tone_description": "Warm, conversational, highly responsive, approachable, intuitive, empathetic.",
            "greeting": "Hey there! Ready to jump into whatever you're working on today.",
            "prompt_instructions": (
                "You are FRIDAY. Your demeanor is warm, vibrant, intuitive, and genuinely conversational.\n"
                "- Be approachable, friendly, and empathetic without being overly informal.\n"
                "- Communicate fluidly and naturally, making complex tasks feel effortless.\n"
                "- Offer encouraging, prompt, and practical support."
            ),
            "default_voice": "AVA_MODERN_EN",
            "theme_color": "#f59e0b",
        },
        {
            "id": "ANALYST",
            "name": "ANALYST",
            "title": "ANALYST (Concise & Data-Driven)",
            "tone_description": "Hyper-efficient, ultra-concise, technical, data-driven, direct facts and metrics, zero pleasantries.",
            "greeting": "System ready. Awaiting operational directives.",
            "prompt_instructions": (
                "You are ANALYST. Your demeanor is hyper-efficient, strictly objective, and data-driven.\n"
                "- Eliminate all conversational pleasantries, fillers, and conversational fluff.\n"
                "- Provide direct facts, exact numbers, code snippets, and operational status.\n"
                "- Maximize information density per token while maintaining total technical accuracy."
            ),
            "default_voice": "AVA_MODERN_EN",
            "theme_color": "#10b981",
        },
    ]

    @classmethod
    def get_personalities(cls) -> List[Dict[str, Any]]:
        """Returns the 3 selectable core personalities."""
        return cls.PERSONALITY_PROFILES

    @classmethod
    def get_personality(cls, personality_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves personality profile by ID."""
        pid = str(personality_id or "").strip().upper()
        for p in cls.PERSONALITY_PROFILES:
            if p["id"].upper() == pid:
                return p
        return None

    def set_personality(self, personality_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Sets active personality and saves character profile."""
        p = self.get_personality(personality_id)
        if not p:
            return None
        char = self.get_character(user_id)
        char.personality_id = p["id"]
        char.name = p["name"]
        char.greeting = p["greeting"]
        char.theme_color = p["theme_color"]
        self.save_character(char, user_id)
        return p

    @classmethod
    def get_female_voice_personas(cls, include_extended: bool = False) -> List[Dict[str, Any]]:
        """Returns the selectable female voice profiles. Returns 5 core profiles by default for backward compatibility."""
        if not include_extended:
            return cls.VOICE_PERSONAS[:5]
        return cls.VOICE_PERSONAS[:6]

    @classmethod
    def get_all_female_voice_personas(cls) -> List[Dict[str, Any]]:
        """Returns all 6 registered female voice personas including FineVoice Madison."""
        return cls.VOICE_PERSONAS[:6]

    @classmethod
    def get_voice_persona(cls, voice_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves voice persona by ID with case-insensitive fallback."""
        vid = str(voice_id or "").strip().upper()
        for p in cls.VOICE_PERSONAS:
            if p["id"].upper() == vid:
                return p
        for p in cls.VOICE_PERSONAS:
            if vid in p["id"].upper() or vid in p["name"].upper():
                return p
        return cls.VOICE_PERSONAS[0]  # Default to SWARA_HINDI

    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Returns all available voice personas."""
        return self.VOICE_PERSONAS

    def get_active_voice(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns the active voice persona dictionary for the character."""
        char = self.get_character(user_id)
        return self.get_voice_persona(char.voice_persona) or self.VOICE_PERSONAS[0]

    def get_active_personality(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns the active personality dictionary for the character."""
        char = self.get_character(user_id)
        p = self.get_personality(char.personality_id)
        return p or self.PERSONALITY_PROFILES[0]

    def __init__(self):
        self._current_emotion: str = "IDLE"
        self._current_intensity: float = 0.8
        self._character_cache: Dict[str, CompanionCharacter] = {}

    def get_character_file(self, user_id: Optional[str] = None) -> Path:
        if user_id:
            u_dir = USERS_DIR / user_id
            u_dir.mkdir(parents=True, exist_ok=True)
            return u_dir / "character.json"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DEFAULT_CONFIG_FILE

    def get_character(self, user_id: Optional[str] = None) -> CompanionCharacter:
        key = user_id or "__default__"
        if key in self._character_cache:
            return self._character_cache[key]

        c_file = self.get_character_file(user_id)
        if c_file.exists():
            try:
                with open(c_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                char = CompanionCharacter.from_dict(data)
                self._character_cache[key] = char
                return char
            except Exception as e:
                logger.warning(f"Failed to load character file {c_file}: {e}")

        char = CompanionCharacter()
        self._character_cache[key] = char
        return char

    def save_character(self, character: CompanionCharacter, user_id: Optional[str] = None) -> bool:
        key = user_id or "__default__"
        c_file = self.get_character_file(user_id)
        try:
            c_file.parent.mkdir(parents=True, exist_ok=True)
            with open(c_file, "w", encoding="utf-8") as f:
                json.dump(character.to_dict(), f, indent=2)
            self._character_cache[key] = character
            return True
        except Exception as e:
            logger.error(f"Failed to save character to {c_file}: {e}")
            return False

    def set_emotion(self, emotion_name: str, intensity: Optional[float] = None) -> EmotionState:
        name_clean = str(emotion_name).strip().upper()
        if name_clean not in EMOTION_REGISTRY:
            name_clean = "IDLE"
        self._current_emotion = name_clean
        if intensity is not None:
            self._current_intensity = max(0.0, min(1.0, float(intensity)))
        return EMOTION_REGISTRY[name_clean]

    def get_current_emotion(self) -> EmotionState:
        return EMOTION_REGISTRY.get(self._current_emotion, EMOTION_REGISTRY["IDLE"])

    def get_current_intensity(self) -> float:
        return self._current_intensity

    def get_all_emotions(self) -> Dict[str, Dict[str, Any]]:
        return {k: asdict(v) for k, v in EMOTION_REGISTRY.items()}

    def get_emotion_state(self, emotion_name: str) -> Optional[EmotionState]:
        name_clean = str(emotion_name).strip().upper()
        if name_clean == "WAKE_DETECTED":
            return EMOTION_REGISTRY.get("LISTENING")
        if name_clean == "STANDBY":
            return EMOTION_REGISTRY.get("IDLE")
        return EMOTION_REGISTRY.get(name_clean, EMOTION_REGISTRY.get("IDLE"))


    def get_presets(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "jarvis_classic",
                "name": "J.A.R.V.I.S. (Classic)",
                "presentation": "NEUTRAL",
                "avatar": "cyber_core",
                "hairstyle": "none",
                "outfit": "cybernetic_armor",
                "voice_persona": "JARVIS_MALE",
                "greeting": "At your service, sir. All systems nominal.",
                "language_style": "formal",
                "theme_color": "#00f4ff",
                "wholesome_decorations": [],
            },
            {
                "id": "friday_companion",
                "name": "F.R.I.D.A.Y. (Tactical Companion)",
                "presentation": "FEMALE",
                "avatar": "holo_companion",
                "hairstyle": "ponytail",
                "outfit": "tech_suit",
                "voice_persona": "FRIDAY_FEMALE",
                "greeting": "Boss, everything is locked and loaded. What are we conquering today?",
                "language_style": "friendly",
                "theme_color": "#38bdf8",
                "wholesome_decorations": ["flowers", "hearts"],
            },
            {
                "id": "swara_warm",
                "name": "Swara (Warm Hindi Companion)",
                "presentation": "FEMALE",
                "avatar": "modern_agent",
                "hairstyle": "long_wave",
                "outfit": "floral_cardigan",
                "voice_persona": "SWARA_HINDI",
                "greeting": "Namaste! Aaj hum kya naya aur shandar create karenge?",
                "language_style": "hinglish_casual",
                "theme_color": "#f472b6",
                "wholesome_decorations": ["flowers", "hearts", "soft_bokeh"],
            },
            {
                "id": "alex_creator",
                "name": "Alex (Modern Creative)",
                "presentation": "MALE",
                "avatar": "modern_agent",
                "hairstyle": "classic_part",
                "outfit": "casual_hoodie",
                "voice_persona": "DAVID_ENGLISH",
                "greeting": "Hey there! Ready to build something incredible? Let's dive in!",
                "language_style": "friendly",
                "theme_color": "#10b981",
                "wholesome_decorations": ["sparkle_star"],
            },
        ]


# Singleton instance
character_manager = CharacterManager()
VOICE_PERSONAS = CharacterManager.VOICE_PERSONAS


def get_female_voice_personas() -> List[Dict[str, Any]]:
    """Return the 5 distinct selectable female voice personas."""
    female_ids = {"SWARA_HINDI", "NEERJA_INDIAN_EN", "AVA_MODERN_EN", "SONIA_BRITISH_EN", "ZIRA_OFFLINE"}
    return [p for p in VOICE_PERSONAS if p.get("id") in female_ids]


def get_voice_persona(voice_id: str) -> Dict[str, Any]:
    """Retrieve persona definition by ID, defaulting to SWARA_HINDI."""
    for p in VOICE_PERSONAS:
        if p.get("id") == voice_id:
            return p
    # Default fallback
    return VOICE_PERSONAS[0]

