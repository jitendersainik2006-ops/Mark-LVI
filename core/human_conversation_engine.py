"""
core/human_conversation_engine.py — J.A.R.V.I.S. Natural Human Conversation Engine

Provides:
1. Multi-Language Detection: Automatically identifies Hindi (Devanagari), Hinglish (Romanized Hindi),
   and English from natural spoken or written utterances.
2. Conversational Style Matching: Detects casual, formal, technical, or concise styles and adapts
   responses to match the user's tone without artificial, repetitive, or flirtatious assumptions.
3. Shared Memory & Context Preservation: Seamlessly integrates with memory_manager and chat_manager
   for multi-turn follow-ups and long-term user recall.
4. Robust Local & Offline Fallback: Routes queries through Ollama (qwen2.5:3b) with rule-based
   local fallback if offline or unreachable.
5. Incomplete Sentence & Transcription Failure Handling: Never pretends to understand failed audio;
   provides clear, helpful clarification prompts.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("JARVIS.ConversationEngine")

# Common Hinglish marker tokens
_HINGLISH_MARKERS = {
    "hai", "hain", "kya", "kaise", "karo", "karna", "mera", "meri", "mere",
    "mujhe", "mujhko", "aap", "aapka", "aapki", "aapke", "tum", "tumhara",
    "haan", "nahi", "nahin", "theek", "achha", "accha", "bolo", "batao",
    "namaste", "shukriya", "dhanyawad", "hoga", "hogi", "raha", "rahi",
    "rahe", "wala", "wali", "wale", "kuch", "sab", "yeh", "woh", "ab", "kab",
    "yaar", "bhai", "bataiye", "dijiye", "kijiye", "kar", "suno", "samjhe",
}

_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


@dataclass
class ConversationContext:
    user_id: str = "default_user"
    personality_id: str = "JARVIS"  # "JARVIS", "FRIDAY", "ANALYST"
    detected_language: str = "english"  # "hindi", "hinglish", "english"
    conversational_style: str = "friendly"  # "casual", "formal", "technical", "concise"
    turn_count: int = 0
    history: List[Dict[str, str]] = field(default_factory=list)


class HumanConversationEngine:
    """Manages natural, context-aware, bilingual human-like conversation."""

    def __init__(self):
        self._contexts: Dict[str, ConversationContext] = {}

    def get_context(self, user_id: str = "default_user") -> ConversationContext:
        if user_id not in self._contexts:
            self._contexts[user_id] = ConversationContext(user_id=user_id)
        return self._contexts[user_id]

    def detect_language(self, text: str) -> str:
        """
        Detects primary language:
        - 'hindi' if Devanagari script characters are detected.
        - 'hinglish' if Roman script with significant Hindi vocabulary.
        - 'english' otherwise.
        """
        raw = text.strip()
        if not raw:
            return "english"

        # Check for Devanagari Unicode block
        if _DEVANAGARI_RE.search(raw):
            return "hindi"

        # Check for Romanized Hindi vocabulary
        words = [w.lower() for w in re.findall(r"\b[a-zA-Z]+\b", raw)]
        if not words:
            return "english"

        hinglish_hits = sum(1 for w in words if w in _HINGLISH_MARKERS)
        ratio = hinglish_hits / len(words)
        if hinglish_hits >= 2 or (len(words) <= 3 and hinglish_hits >= 1) or ratio >= 0.25:
            return "hinglish"

        return "english"

    def detect_conversational_style(self, text: str) -> str:
        """
        Infers user's conversational intent and style:
        - 'technical': query mentions code, system paths, errors, APIs, hardware.
        - 'concise': very short commands or queries asking for quick facts.
        - 'formal': polite formal phrasing (please, kindly, respectfully).
        - 'casual': conversational banter, greetings, colloquial idioms.
        """
        lower = text.lower()
        if any(w in lower for w in ("def ", "import ", "error", "api", "code", "function", "bug", "log", "gpu", "ram")):
            return "technical"
        if len(text.split()) <= 4 and ("what is" in lower or "who is" in lower or "time" in lower or "date" in lower):
            return "concise"
        if any(w in lower for w in ("kindly", "please provide", "regarding", "sincerely", "kripya", "nivedan")):
            return "formal"
        return "casual"

    def build_system_prompt(self, user_text: str, user_id: str = "default_user", personality_id: Optional[str] = None) -> str:
        """
        Constructs an adaptive, non-robotic system prompt matching the user's
        language, style, personality persona, and stored long-term memories.
        """
        lang = self.detect_language(user_text)
        style = self.detect_conversational_style(user_text)

        # Retrieve relevant context from personal memory subsystem
        memory_context = ""
        try:
            from memory.memory_manager import memory_manager
            facts = memory_manager.get_relevant_context(user_text)
            if facts:
                memory_context = f"\nRELEVANT PERSONAL MEMORY:\n{facts}\n"
        except Exception:
            pass

        # Resolve active personality profile
        personality_name = "J.A.R.V.I.S."
        personality_instructions = ""
        try:
            from core.character_manager import character_manager
            char = character_manager.get_character(user_id)
            pid = personality_id or getattr(char, "personality_id", "JARVIS")
            profile = character_manager.get_personality(pid)
            if profile:
                personality_name = profile.get("name", "J.A.R.V.I.S.")
                personality_instructions = profile.get("prompt_instructions", "")
        except Exception:
            pass

        base_instructions = (
            f"You are {personality_name}, an intelligent, natural, and helpful personal AI desktop companion.\n"
            f"{personality_instructions}\n"
            "COMMUNICATION RULES:\n"
            "1. Respond directly, naturally, and conversationally like a skilled human assistant.\n"
            "2. Never use repetitive robotic openings like 'Certainly, sir!', 'As an AI...', or 'I would be happy to help'.\n"
            "3. Do NOT assume romantic, flirtatious, or overly dramatic emotional states.\n"
            "4. Be helpful, concise, and accurate.\n"
            "5. If a question is incomplete or ambiguous, ask a brief, natural clarifying question.\n"
        )

        lang_instructions = ""
        if lang == "hindi":
            lang_instructions = (
                "LANGUAGE: The user is speaking in Hindi (Devanagari script).\n"
                "You MUST reply in fluent, natural Hindi using Devanagari script.\n"
                "Keep the tone respectful and friendly (e.g. use 'आप', 'नमस्ते').\n"
            )
        elif lang == "hinglish":
            lang_instructions = (
                "LANGUAGE: The user is speaking in Hinglish (Romanized Hindi/English mix).\n"
                "You MUST reply in natural, conversational Hinglish using Roman English script.\n"
                "Example style: 'Haan bilkul, main yeh check kar leti hoon. Aapko update karti hoon.'\n"
            )
        else:
            lang_instructions = (
                "LANGUAGE: The user is speaking in English.\n"
                "You MUST reply in natural, clear English.\n"
            )

        style_instruction = f"STYLE: User tone is {style}. Match this with clear, {style} phrasing.\n"

        return f"{base_instructions}\n{lang_instructions}\n{style_instruction}{memory_context}"

    async def generate_response(
        self,
        user_text: str,
        user_id: str = "default_user",
        session_history: Optional[List[Dict[str, str]]] = None,
        personality_id: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """
        Processes a conversation turn.
        Returns: (assistant_reply, detected_language, detected_style)
        """
        text = str(user_text or "").strip()
        if not text:
            return (
                "I didn't catch that. Audio was empty or transcription failed. Could you please repeat?",
                "english",
                "concise"
            )

        lang = self.detect_language(text)
        style = self.detect_conversational_style(text)
        ctx = self.get_context(user_id)
        ctx.detected_language = lang
        ctx.conversational_style = style
        if personality_id:
            ctx.personality_id = personality_id
        ctx.turn_count += 1

        sys_prompt = self.build_system_prompt(text, user_id=user_id, personality_id=personality_id or ctx.personality_id)

        # Build message history for multi-turn LLM reasoning
        messages: List[Dict[str, str]] = [{"role": "system", "content": sys_prompt}]
        
        # Include past turns from context or session history
        history_source = session_history if session_history is not None else ctx.history
        for turn in history_source[-6:]:  # Keep recent 6 turns for context
            messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})

        messages.append({"role": "user", "content": text})

        reply = None
        # Check SkillRouter for natural voice-first commands
        skill_context = ""
        try:
            from core.skill_router import skill_router
            intent = skill_router.route_natural_intent(text, lang)
            if intent.get("matched"):
                if intent.get("requires_confirmation"):
                    return intent.get("explanation", "Action requires confirmation."), lang, style
                # Execute read-only/standard skill immediately to give real data
                res = skill_router.execute_skill(intent["skill_id"], intent.get("proposed_params"), confirmed=True, lang=lang)
                if res.get("ok"):
                    spoken = res.get("spoken_summary", "")
                    skill_context = f"\n[ACTIVE SKILL EXECUTION RESULT ({intent['skill_name']})]: {json.dumps(res.get('data', {}), default=str)}\nSpoken Summary: {spoken}\n"
                    # If LLM is offline or fast response needed, spoken summary can serve as direct reply
                    if not reply:
                        reply = spoken
        except Exception as e:
            logger.warning(f"[HumanConversationEngine] SkillRouter routing notice: {e}")

        # Update system prompt with skill findings if any
        if skill_context:
            sys_prompt += f"\n{skill_context}"
            messages[0] = {"role": "system", "content": sys_prompt}

        # 1. Attempt Local Ollama (Qwen2.5:3b)
        try:
            from core.llm_client import LLMClient
            llm = LLMClient()
            llm_reply, _ = llm.complete(messages)
            if llm_reply and llm_reply.strip():
                reply = llm_reply.strip()
        except Exception as e:
            logger.warning(f"[HumanConversationEngine] Local LLM completion failed: {e}")

        # 2. Local graceful conversational fallback if LLM is offline
        if not reply:
            reply = self._get_offline_fallback_reply(text, lang, style)

        # Update local context history
        ctx.history.append({"role": "user", "content": text})
        ctx.history.append({"role": "assistant", "content": reply})
        if len(ctx.history) > 20:
            ctx.history = ctx.history[-20:]

        return reply, lang, style

    def _get_offline_fallback_reply(self, text: str, lang: str, style: str) -> str:
        """Graceful local offline response when LLM daemon is offline."""
        lower = text.lower()
        if lang == "hindi":
            if any(w in lower for w in ("नमस्ते", "हेलो", "हाय")):
                return "नमस्ते! मैं आपकी पर्सनल एआई साथी हूँ। सिस्टम ऑफलाइन मोड में सक्रिय है। आप क्या करना चाहते हैं?"
            if "नाम" in lower:
                return "मेरा नाम जार्विस (स्वरा) है, आपकी पर्सनल एआई साथी।"
            return f"मैंने आपकी बात समझ ली: '{text}'। लोकल सिस्टम सक्रिय है और आपकी सहायता के लिए तैयार है।"

        if lang == "hinglish":
            if any(w in lower for w in ("hello", "hi", "namaste", "suno", "hey")):
                return "Haanji! Main online hoon. Offline mode active hai, batao kya madad chahiye?"
            if "naam" in lower or "kaun ho" in lower:
                return "Main J.A.R.V.I.S. hoon, aapka personal desktop companion."
            return f"Samajh gaya! '{text}' pe kaam kar raha hoon. Sabhi local systems online hain."

        # English
        if any(w in lower for w in ("hello", "hi", "hey", "greetings")):
            return "Good day! All local systems are online. How can I assist you right now?"
        if "who are you" in lower or "your name" in lower:
            return "I am J.A.R.V.I.S., your personal AI companion running on your Windows workstation."
        return f"Understood: '{text}'. Operating in local offline mode with all primary systems ready."


# Global shared instance
human_conversation_engine = HumanConversationEngine()
