"""
core/finevoice_client.py — FineVoice (FineShare) AI Voice Engine Client for J.A.R.V.I.S.

Provides:
1. Official FineVoice Cloud API Integration (https://apis.finevoice.ai)
2. Direct Text-to-Speech (TTS) via POST /v1/audio/speech-synthesis with model "madison"
3. Voice Conversion (Speech-to-Speech) via POST /v1/audio/voice-conversion with model "madison"
4. Strict Privacy Guard & Explicit Consent Enforcement:
   - Voice conversion requires explicit per-session user confirmation before transmitting audio
   - Zero silent microphone uploads
5. Safe Credential Handling:
   - Reads finevoice_api_key from config/api_keys.json or env FINEVOICE_API_KEY
   - Zero hardcoded keys or leaked secrets
   - Supports Windows DPAPI encrypted values (dpapi:v1:...)
6. Graceful Degradation & Fallback:
   - Returns structured error reason when unconfigured or offline
   - Coordinates with NaturalVoiceEngine for seamless neural/offline fallback
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import aiohttp

logger = logging.getLogger("JARVIS.FineVoiceClient")

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
VOICE_CACHE_DIR = DATA_DIR / "voice_cache" / "finevoice"

try:
    VOICE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

FINEVOICE_API_BASE = "https://apis.finevoice.ai"
DEFAULT_VOICE_MODEL = "madison"


class FineVoiceError(Exception):
    """Base exception for FineVoice API errors."""
    pass


class FineVoiceConsentRequiredError(FineVoiceError):
    """Raised when user consent is missing for audio upload operations."""
    pass


class FineVoiceClient:
    """
    Client for FineShare's FineVoice API.
    Handles authentication, Direct TTS synthesis, Voice Conversion,
    job polling, and privacy safeguards.
    """

    def __init__(self, api_base: str = FINEVOICE_API_BASE):
        self._api_base = api_base.rstrip("/")
        self._timeout_seconds = 15.0

    def get_api_key(self) -> Optional[str]:
        """
        Retrieves FineVoice API key from environment or config/api_keys.json.
        Decrypts DPAPI encryption if present.
        """
        # 1. Environment variable override
        env_key = os.environ.get("FINEVOICE_API_KEY", "").strip()
        if env_key:
            return env_key

        # 2. config/api_keys.json
        cfg_file = CONFIG_DIR / "api_keys.json"
        if cfg_file.exists():
            try:
                data = json.loads(cfg_file.read_text(encoding="utf-8"))
                val = data.get("finevoice_api_key", "")
                if isinstance(val, str) and val.strip():
                    val = val.strip()
                    # Check DPAPI encryption
                    if val.startswith("dpapi:v1:"):
                        try:
                            from core.crypto_storage import decrypt_token
                            val = decrypt_token(val)
                        except Exception as de:
                            logger.warning(f"Could not decrypt DPAPI finevoice_api_key: {de}")
                    return val
            except Exception as e:
                logger.warning(f"Could not load FineVoice API key: {e}")
        return None

    def is_configured(self) -> bool:
        """Returns True if a non-empty FineVoice API key is available."""
        key = self.get_api_key()
        return bool(key and len(key) >= 10)

    def mask_key(self, key: Optional[str] = None) -> str:
        """Returns masked API key representation for safe telemetry/UI display."""
        k = key if key is not None else self.get_api_key()
        if not k:
            return "NOT_CONFIGURED"
        if len(k) <= 8:
            return "****"
        return k[:4] + "****" + k[-4:]

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive configuration, capability, and pricing status."""
        configured = self.is_configured()
        return {
            "provider": "FineVoice (FineShare)",
            "api_base_url": self._api_base,
            "voice_id": "MADISON_FINEVOICE",
            "voice_model": DEFAULT_VOICE_MODEL,
            "configured": configured,
            "api_key_status": "VALID_FORMAT" if configured else "MISSING_OR_EMPTY",
            "masked_key": self.mask_key(),
            "supported_modes": {
                "direct_tts": {
                    "supported": True,
                    "endpoint": f"{self._api_base}/v1/audio/speech-synthesis",
                    "description": "Generates natural speech directly from text",
                    "requires_audio_upload": False,
                },
                "voice_conversion": {
                    "supported": True,
                    "endpoint": f"{self._api_base}/v1/audio/voice-conversion",
                    "description": "Transforms speech audio into Madison voice model",
                    "requires_audio_upload": True,
                    "requires_explicit_consent": True,
                }
            },
            "pricing_tiers": {
                "pricing_type": "Commercial Character-Based Packages (1-Year Validity)",
                "creator": "$90.00 for 6,000,000 characters (5 concurrent requests)",
                "pro": "$135.00 for 9,000,000 characters (5 concurrent requests)",
                "scale": "$156.00 for 12,000,000 characters (10 concurrent requests)",
                "business": "$195.00 for 15,000,000 characters (10 concurrent requests)",
                "is_free": False,
            },
            "privacy_guard": {
                "direct_tts_policy": "Sends text payload over TLS to FineVoice servers.",
                "voice_conversion_policy": "STRICT CONSENT: Input audio is NEVER uploaded automatically. User must explicitly grant consent per upload session.",
                "offline_fallback_target": "Microsoft Zira Desktop (SAPI5)",
                "neural_fallback_target": "en-US-AvaNeural (EdgeTTS)",
            }
        }

    async def synthesize_speech_async(
        self,
        text: str,
        voice: str = DEFAULT_VOICE_MODEL,
        timeout_sec: float = 12.0
    ) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Direct Text-to-Speech (TTS) synthesis via FineVoice API.
        
        Submits POST /v1/audio/speech-synthesis with {"voice": voice, "text": text, "useAsync": true}.
        Polls GET /v1/task/{task_id} until completed.
        Downloads and returns MP3/WAV audio bytes.

        Returns:
            (audio_bytes, None) on success.
            (None, error_reason) on failure or when unconfigured.
        """
        if not text or not text.strip():
            return None, "EMPTY_TEXT"

        api_key = self.get_api_key()
        if not api_key:
            return None, "FINEVOICE_API_KEY_NOT_CONFIGURED"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "JARVIS-Mark-LVI-Companion/56.1.0"
        }

        payload = {
            "voice": voice,
            "text": text.strip(),
            "useAsync": True
        }

        synth_url = f"{self._api_base}/v1/audio/speech-synthesis"

        try:
            timeout = aiohttp.ClientTimeout(total=timeout_sec)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # 1. Submit synthesis task
                async with session.post(synth_url, json=payload, headers=headers) as resp:
                    if resp.status == 401:
                        return None, "AUTHENTICATION_FAILED: Invalid or expired FineVoice API key"
                    if resp.status == 402 or resp.status == 429:
                        return None, "QUOTA_EXCEEDED: FineVoice character balance exhausted or rate limited"
                    if resp.status != 200:
                        err_text = await resp.text()
                        return None, f"HTTP_{resp.status}: {err_text[:120]}"

                    data = await resp.json()
                    task_id = data.get("task_id")
                    if not task_id:
                        return None, "NO_TASK_ID_RETURNED"

                # 2. Poll task status
                poll_url = f"{self._api_base}/v1/task/{task_id}"
                start_time = time.time()
                while time.time() - start_time < timeout_sec:
                    await asyncio.sleep(1.5)
                    async with session.get(poll_url, headers=headers) as poll_resp:
                        if poll_resp.status != 200:
                            continue
                        task_data = await poll_resp.json()
                        status = str(task_data.get("status", "")).lower()
                        if status == "completed":
                            audio_url = task_data.get("url")
                            if not audio_url:
                                return None, "NO_AUDIO_URL_IN_COMPLETED_TASK"
                            # 3. Download resulting audio file
                            async with session.get(audio_url) as audio_resp:
                                if audio_resp.status == 200:
                                    audio_bytes = await audio_resp.read()
                                    return audio_bytes, None
                                return None, f"DOWNLOAD_FAILED_HTTP_{audio_resp.status}"
                        elif status in ("failed", "error"):
                            err_msg = task_data.get("error", "Task execution failed")
                            return None, f"TASK_FAILED: {err_msg}"

                return None, "SYNTHESIS_TIMEOUT"

        except asyncio.TimeoutError:
            return None, "REQUEST_TIMEOUT"
        except aiohttp.ClientError as ce:
            return None, f"NETWORK_ERROR: {str(ce)[:100]}"
        except Exception as e:
            return None, f"UNEXPECTED_ERROR: {str(e)[:100]}"

    async def convert_voice_async(
        self,
        source_audio_url: str,
        voice: str = DEFAULT_VOICE_MODEL,
        user_consent_granted: bool = False,
        timeout_sec: float = 20.0
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Voice Conversion (Speech-to-Speech) via FineVoice API.
        
        CRITICAL PRIVACY SAFEGUARD:
        Requires explicit per-session user consent before transmitting any audio.
        """
        if not user_consent_granted:
            logger.warning("Voice conversion blocked: explicit user consent not granted.")
            return None, "CONSENT_REQUIRED: Voice conversion requires explicit user authorization before uploading audio."

        if not source_audio_url:
            return None, "MISSING_SOURCE_AUDIO_URL"

        api_key = self.get_api_key()
        if not api_key:
            return None, "FINEVOICE_API_KEY_NOT_CONFIGURED"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "JARVIS-Mark-LVI-Companion/56.1.0"
        }

        payload = {
            "voice": voice,
            "sourceUrl": source_audio_url
        }

        conv_url = f"{self._api_base}/v1/audio/voice-conversion"

        try:
            timeout = aiohttp.ClientTimeout(total=timeout_sec)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(conv_url, json=payload, headers=headers) as resp:
                    if resp.status == 401:
                        return None, "AUTHENTICATION_FAILED: Invalid or expired FineVoice API key"
                    if resp.status != 200:
                        err_text = await resp.text()
                        return None, f"HTTP_{resp.status}: {err_text[:120]}"

                    data = await resp.json()
                    task_id = data.get("task_id")
                    if not task_id:
                        return None, "NO_TASK_ID_RETURNED"

                poll_url = f"{self._api_base}/v1/task/{task_id}"
                start_time = time.time()
                while time.time() - start_time < timeout_sec:
                    await asyncio.sleep(2.0)
                    async with session.get(poll_url, headers=headers) as poll_resp:
                        if poll_resp.status != 200:
                            continue
                        task_data = await poll_resp.json()
                        status = str(task_data.get("status", "")).lower()
                        if status == "completed":
                            return task_data.get("url"), None
                        elif status in ("failed", "error"):
                            return None, f"TASK_FAILED: {task_data.get('error', 'Voice conversion failed')}"

                return None, "CONVERSION_TIMEOUT"

        except Exception as e:
            return None, f"ERROR: {str(e)[:100]}"


finevoice_client = FineVoiceClient()
