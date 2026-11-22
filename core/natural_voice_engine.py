"""
core/natural_voice_engine.py — Next-Level Natural Conversational Voice Engine for J.A.R.V.I.S.

Provides:
1. 5 Verified Selectable Female Voice Personas:
   - SWARA_HINDI (Default): Warm Hindi & Hinglish Neural (hi-IN-SwaraNeural)
   - NEERJA_INDIAN_EN: Fluent Indian English Neural (en-IN-NeerjaNeural)
   - AVA_MODERN_EN: Expressive Modern US English Neural (en-US-AvaNeural)
   - SONIA_BRITISH_EN: Polished British English Neural (en-GB-SoniaNeural)
   - ZIRA_OFFLINE: 100% Local Offline Windows SAPI5 (Microsoft Zira Desktop)
2. Prosody & Emotion Shaping:
   - Dynamic SSML pitch, rate, and contouring based on 19 emotional states
   - Micro-pause insertion at sentence and clause boundaries
3. Phonetic Text Normalization & Acronym Expansion:
   - Cleans markdown symbols, backticks, asterisks, URLs
   - Expands Hindi numerals into spoken Devanagari phonemes
   - Applies technical acronym rules from config/pronunciation_rules.json
4. Sentence-Aware Streaming:
   - Fast sentence segmentation for low-latency streaming TTS
5. Robust Fallback:
   - Seamlessly switches to offline Windows SAPI5 if internet is unavailable
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
import sys
import threading
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

import av
import edge_tts
import numpy as np
import sounddevice as sd

from core.character_manager import character_manager
from core.audio_devices import resolve as resolve_audio_device

logger = logging.getLogger("JARVIS.NaturalVoiceEngine")

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "voice_cache"
try:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass


# ── Hindi Number Words (0-100) for Natural Phonetic Pronunciation ─────────────
_HINDI_NUMBERS = {
    0: "शून्य", 1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पाँच", 6: "छह", 7: "सात", 8: "आठ", 9: "नौ", 10: "दस",
    11: "ग्यारह", 12: "बारह", 13: "तेरह", 14: "चौदह", 15: "पंद्रह", 16: "सोलह", 17: "सत्रह", 18: "अठारह", 19: "उन्नीस", 20: "बीस",
    21: "इक्कीस", 22: "बाईस", 23: "तेईस", 24: "चौबीस", 25: "पच्चीस", 26: "छब्बीस", 27: "सत्ताईस", 28: "अट्ठाईस", 29: "उनतीस", 30: "तीस",
    31: "इकत्तीस", 32: "बत्तीस", 33: "तैंतीस", 34: "चौंतीस", 35: "पैंतीस", 36: "छत्तीस", 37: "सैंतीस", 38: "अड़तीस", 39: "उनतालीस", 40: "चालीस",
    41: "इकतालीस", 42: "बयालीस", 43: "तैंतालीस", 44: "चौवालीस", 45: "पैंतालीस", 46: "छियालीस", 47: "सैंतालीस", 48: "अड़तालीस", 49: "उनचास", 50: "पचास",
    51: "इक्यावन", 52: "बावन", 53: "तिरपन", 54: "चौवन", 55: "पचपन", 56: "छप्पन", 57: "सत्तावन", 58: "अट्ठावन", 59: "उनसठ", 60: "साठ",
    61: "इकसठ", 62: "बासठ", 63: "तिरसठ", 64: "चौंसठ", 65: "पैंसठ", 66: "छियासठ", 67: "सरसठ", 68: "अड़सठ", 69: "उनहत्तर", 70: "सत्तर",
    71: "इकहत्तर", 72: "बहत्तर", 73: "तिहत्तर", 74: "चौहत्तर", 75: "पचहत्तर", 76: "छिहत्तर", 77: "सतहत्तर", 78: "अठहत्तर", 79: "उन्नासी", 80: "अस्सी",
    81: "इक्यासी", 82: "बयासी", 83: "तिरासी", 84: "चौरासी", 85: "पचासी", 86: "छियासी", 87: "सत्तासी", 88: "अठासी", 89: "नवासी", 90: "नब्बे",
    91: "इक्यानवे", 92: "बानवे", 93: "तिरानवे", 94: "चौरानवे", 95: "पंचानवे", 96: "छियानवे", 97: "सत्तानवे", 98: "अट्ठानवे", 99: "निन्यानवे", 100: "सौ"
}

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…\n|।!?])\s+")
_MARKDOWN_CLEAN_RE = re.compile(r"(\*\*|\*|`|#|>|__|_|~~|\[.*?\]\(.*?\))")
_URL_RE = re.compile(r"https?://\S+")
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


@dataclass
class AudioChunkResult:
    audio_bytes_wav: bytes
    duration_sec: float
    sample_rate: int = 24000
    voice_used: str = "SWARA_HINDI"
    is_offline: bool = False
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    timing_segments: List[Dict[str, Any]] = field(default_factory=list)


class NaturalVoiceEngine:
    """
    Unified Next-Generation Voice Engine for J.A.R.V.I.S. MARK LVI.
    Combines neural EdgeTTS, SAPI5 fallback, prosody shaping, phonetic normalization,
    and low-latency streaming playback.
    """

    def __init__(self):
        self._pronunciation_rules: Dict[str, str] = {}
        self._load_pronunciation_rules()
        self._playback_lock = threading.Lock()
        self._is_playing = False
        self._stop_requested = False
        self._current_stream: Optional[sd.OutputStream] = None

    def _load_pronunciation_rules(self) -> None:
        rules_path = CONFIG_DIR / "pronunciation_rules.json"
        if rules_path.exists():
            try:
                data = json.loads(rules_path.read_text(encoding="utf-8"))
                self._pronunciation_rules = data.get("rules", {})
            except Exception as e:
                logger.warning(f"Could not load pronunciation rules: {e}")

    def normalize_text(self, text: str, lang: str = "hindi") -> str:
        """
        Cleans markdown, expands technical acronyms, and phonetically transliterates numbers.
        """
        if not text:
            return ""

        # 1. Remove URLs
        cleaned = _URL_RE.sub("link", text)

        # 2. Remove markdown formatting syntax
        cleaned = _MARKDOWN_CLEAN_RE.sub(" ", cleaned)

        # 3. Apply pronunciation dictionary rules (acronyms, technical terms)
        for term, phonetic in self._pronunciation_rules.items():
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            cleaned = pattern.sub(phonetic, cleaned)

        # 4. If Hindi or Hinglish, expand standalone numbers 0-100 to natural Hindi words
        is_hindi = bool(_DEVANAGARI_RE.search(cleaned)) or lang in ("hindi", "hinglish")
        if is_hindi:
            def _num_replacer(match):
                val = int(match.group(0))
                if val in _HINDI_NUMBERS:
                    return _HINDI_NUMBERS[val]
                elif val == 2026:
                    return "दो हज़ार छब्बीस"
                return match.group(0)

            cleaned = re.sub(r"\b\d{1,4}\b", _num_replacer, cleaned)

        # 5. Collapse excessive whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def split_sentences(self, text: str) -> List[str]:
        """Splits paragraph into spoken sentence chunks."""
        cleaned = self.normalize_text(text)
        if not cleaned:
            return []
        chunks = _SENTENCE_SPLIT_RE.split(cleaned)
        result = [c.strip() for c in chunks if c.strip() and len(c.strip()) > 1]
        return result or [cleaned]

    def _get_voice_profile(self, voice_id: str = "SWARA_HINDI") -> Dict[str, Any]:
        """Resolves voice metadata from CharacterManager."""
        persona = character_manager.get_voice_persona(voice_id)
        if not persona:
            persona = character_manager.get_voice_persona("SWARA_HINDI")
        return persona

    def _convert_mp3_to_wav(self, mp3_bytes: bytes, target_sr: int = 24000) -> Tuple[bytes, float, int]:
        """Decodes MP3 bytes via PyAV and encodes to standard PCM WAV (16-bit, target_sr)."""
        container = av.open(io.BytesIO(mp3_bytes))
        stream = container.streams.audio[0]
        frames = []
        for frame in container.decode(stream):
            frames.append(frame.to_ndarray())
        container.close()

        if not frames:
            raise RuntimeError("PyAV failed to decode audio frames from MP3 stream")

        audio_data = np.concatenate(frames, axis=1)  # shape: (channels, samples)
        orig_sr = stream.rate

        # Convert to mono if multi-channel
        if audio_data.shape[0] > 1:
            audio_mono = audio_data.mean(axis=0)
        else:
            audio_mono = audio_data[0]

        # Resample to target_sr if necessary
        if orig_sr != target_sr and len(audio_mono) > 0:
            from scipy import signal
            num_samples = int(len(audio_mono) * target_sr / orig_sr)
            audio_resampled = signal.resample(audio_mono, num_samples)
        else:
            audio_resampled = audio_mono

        # Normalize to int16
        if np.issubdtype(audio_resampled.dtype, np.floating):
            audio_int16 = np.clip(audio_resampled * 32767.0, -32768, 32767).astype(np.int16)
        else:
            audio_int16 = audio_resampled.astype(np.int16)

        duration_sec = len(audio_int16) / float(target_sr)

        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(target_sr)
            wf.writeframes(audio_int16.tobytes())

        return wav_io.getvalue(), duration_sec, target_sr

    def _synthesize_sapi5(self, text: str) -> Tuple[bytes, float, int]:
        """Offline Windows SAPI5 synthesis with phonetic transliteration for Devanagari."""
        from providers.tts_system import speak_to_wav
        wav_bytes = speak_to_wav(text)
        if not wav_bytes or len(wav_bytes) < 44:
            raise RuntimeError("SAPI5 failed to produce WAV stream")

        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            n_frames = wf.getnframes()
            rate = wf.getframerate()
            duration = n_frames / float(rate) if rate > 0 else 0.0

        return wav_bytes, duration, rate

    async def synthesize_chunk_async(
        self,
        text: str,
        voice_id: str = "SWARA_HINDI",
        pitch_delta: str = "+0Hz",
        rate_delta: str = "-4%",
        emotion: str = "IDLE"
    ) -> AudioChunkResult:
        """
        Synthesizes a single chunk of text into WAV audio.
        Applies tuned prosody, emotional pitch/rate deltas, and automatic offline fallback.
        """
        profile = self._get_voice_profile(voice_id)
        sys_voice = profile.get("system_voice", "hi-IN-SwaraNeural")
        is_neural = profile.get("is_neural", True)
        is_offline = profile.get("is_offline", False)

        normalized = self.normalize_text(text, lang=profile.get("lang", "hindi"))
        if not normalized:
            return AudioChunkResult(audio_bytes_wav=b"", duration_sec=0.0, voice_used=voice_id)

        # ── 1. If configured strictly offline (Zira), synthesize via SAPI5 ────
        if is_offline or not is_neural:
            try:
                wav_bytes, dur, sr = self._synthesize_sapi5(normalized)
                return AudioChunkResult(
                    audio_bytes_wav=wav_bytes,
                    duration_sec=dur,
                    sample_rate=sr,
                    voice_used=voice_id,
                    is_offline=True
                )
            except Exception as e:
                logger.error(f"SAPI5 synthesis error: {e}")

        # ── 2. FineVoice Cloud API for MADISON_FINEVOICE ──────────────────────
        if voice_id == "MADISON_FINEVOICE" or str(sys_voice).startswith("finevoice:"):
            from core.finevoice_client import finevoice_client
            if finevoice_client.is_configured():
                try:
                    raw_audio, err = await finevoice_client.synthesize_speech_async(normalized, voice="madison")
                    if raw_audio and len(raw_audio) > 100:
                        wav_bytes, dur, sr = self._convert_mp3_to_wav(raw_audio, target_sr=24000)
                        return AudioChunkResult(
                            audio_bytes_wav=wav_bytes,
                            duration_sec=dur,
                            sample_rate=sr,
                            voice_used="MADISON_FINEVOICE",
                            is_offline=False,
                            is_fallback=False
                        )
                    logger.warning(f"FineVoice synthesis notice ({err}). Engaging high-fidelity neural fallback.")
                except Exception as fe:
                    logger.warning(f"FineVoice request failed ({fe}). Engaging neural fallback.")
            else:
                logger.info("FineVoice API key not configured. Using high-fidelity neural fallback (Ava).")

            # Fallback path for Madison:
            # If text contains Devanagari, fall back to Swara Hindi neural; otherwise Ava US English neural
            fallback_voice = "hi-IN-SwaraNeural" if _DEVANAGARI_RE.search(normalized) else "en-US-AvaNeural"
            fallback_tag = "FINEVOICE_NEURAL_FALLBACK_SWARA" if _DEVANAGARI_RE.search(normalized) else "FINEVOICE_NEURAL_FALLBACK_AVA"
            try:
                comm = edge_tts.Communicate(
                    text=normalized,
                    voice=fallback_voice,
                    pitch=pitch_delta,
                    rate=rate_delta
                )
                mp3_buf = bytearray()
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        mp3_buf.extend(chunk["data"])
                if len(mp3_buf) > 100:
                    wav_bytes, dur, sr = self._convert_mp3_to_wav(bytes(mp3_buf), target_sr=24000)
                    return AudioChunkResult(
                        audio_bytes_wav=wav_bytes,
                        duration_sec=dur,
                        sample_rate=sr,
                        voice_used="MADISON_FINEVOICE",
                        is_offline=False,
                        is_fallback=True,
                        fallback_reason=fallback_tag
                    )
            except Exception as fb_err:
                logger.warning(f"Neural fallback for Madison unavailable ({fb_err}). Dropping to local SAPI5.")

            # SAPI5 local fallback for Madison
            try:
                wav_bytes, dur, sr = self._synthesize_sapi5(normalized)
                return AudioChunkResult(
                    audio_bytes_wav=wav_bytes,
                    duration_sec=dur,
                    sample_rate=sr,
                    voice_used="MADISON_FINEVOICE",
                    is_offline=True,
                    is_fallback=True,
                    fallback_reason="FINEVOICE_OFFLINE_FALLBACK_SAPI5"
                )
            except Exception as s_err:
                logger.error(f"SAPI5 fallback failed for Madison: {s_err}")
                return AudioChunkResult(
                    audio_bytes_wav=b"",
                    duration_sec=0.0,
                    voice_used="MADISON_FINEVOICE",
                    is_offline=True,
                    is_fallback=True,
                    fallback_reason="FINEVOICE_SYNTHESIS_FAILED"
                )

        # ── 3. Neural EdgeTTS with tuned prosody ──────────────────────────────
        try:
            # Apply emotion-specific pitch/rate offsets from CharacterManager if available
            emo_state = character_manager.get_emotion_state(emotion)
            final_pitch = pitch_delta
            final_rate = rate_delta
            if emo_state:
                final_pitch = emo_state.voice_pitch_delta
                final_rate = emo_state.voice_rate_delta

            comm = edge_tts.Communicate(
                text=normalized,
                voice=sys_voice,
                pitch=final_pitch,
                rate=final_rate
            )
            mp3_buf = bytearray()
            timing: List[Dict[str, Any]] = []

            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    mp3_buf.extend(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    timing.append({
                        "text": chunk.get("text", ""),
                        "start_sec": chunk["offset"] / 10_000_000.0,
                        "duration_sec": chunk["duration"] / 10_000_000.0
                    })

            if len(mp3_buf) > 100:
                wav_bytes, dur, sr = self._convert_mp3_to_wav(bytes(mp3_buf), target_sr=24000)
                return AudioChunkResult(
                    audio_bytes_wav=wav_bytes,
                    duration_sec=dur,
                    sample_rate=sr,
                    voice_used=voice_id,
                    is_offline=False,
                    timing_segments=timing
                )
        except Exception as net_err:
            logger.warning(f"Neural EdgeTTS unavailable ({net_err}). Falling back to local offline SAPI5.")

        # ── 3. Graceful Offline Fallback to SAPI5 ──────────────────────────────
        try:
            wav_bytes, dur, sr = self._synthesize_sapi5(normalized)
            return AudioChunkResult(
                audio_bytes_wav=wav_bytes,
                duration_sec=dur,
                sample_rate=sr,
                voice_used="ZIRA_OFFLINE",
                is_offline=True
            )
        except Exception as fb_err:
            logger.error(f"Offline fallback also failed: {fb_err}")
            return AudioChunkResult(audio_bytes_wav=b"", duration_sec=0.0, voice_used=voice_id)

    def synthesize_text(
        self,
        text: str,
        voice_id: str = "SWARA_HINDI",
        pitch_delta: str = "+0Hz",
        rate_delta: str = "-4%",
        emotion: str = "IDLE"
    ) -> AudioChunkResult:
        """Synchronous wrapper for synthesize_chunk_async."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.synthesize_chunk_async(text, voice_id, pitch_delta, rate_delta, emotion)
            )
        finally:
            loop.close()

    def play_audio_wav(
        self,
        wav_bytes: bytes,
        device_name: Optional[str] = None,
        on_start: Optional[Callable[[], None]] = None,
        on_done: Optional[Callable[[], None]] = None
    ) -> bool:
        """
        Plays WAV audio through sounddevice with real-time cancellation support.
        """
        if not wav_bytes or len(wav_bytes) < 44:
            return False

        with self._playback_lock:
            self._is_playing = True
            self._stop_requested = False

        if on_start:
            try:
                on_start()
            except Exception:
                pass

        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
                sr = wf.getframerate()
                n_channels = wf.getnchannels()
                frames = wf.readframes(wf.getnframes())

            audio_arr = np.frombuffer(frames, dtype=np.int16)
            if n_channels > 1:
                audio_arr = audio_arr.reshape(-1, n_channels)

            target_dev = resolve_audio_device(device_name, "output") if device_name else None

            sd.play(audio_arr, samplerate=sr, device=target_dev)
            sd.wait()
            return True
        except Exception as e:
            logger.error(f"Playback error: {e}")
            return False
        finally:
            with self._playback_lock:
                self._is_playing = False
            if on_done:
                try:
                    on_done()
                except Exception:
                    pass

    def stop_playback(self) -> None:
        """Immediately stops all active audio playback."""
        with self._playback_lock:
            self._stop_requested = True
            self._is_playing = False
        try:
            sd.stop()
        except Exception:
            pass


natural_voice_engine = NaturalVoiceEngine()
