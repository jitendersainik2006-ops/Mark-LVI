"""
core/hindi_voice_engine.py — Native Hindi Neural Voice & Timing Engine for J.A.R.V.I.S.

Provides authentic Hindi text-to-speech voiceovers with character-specific pitch,
rate, and emotional modulation using Microsoft Edge Neural Hindi voices (hi-IN-MadhurNeural,
hi-IN-SwaraNeural). Extracts exact sentence timing for Devanagari subtitle synchronization.
"""

from __future__ import annotations

import asyncio
import os
import re
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import av
import edge_tts
import numpy as np

from core.character_consistency_manager import character_consistency_manager
from core.hindi_story_engine import DEVANAGARI_REGEX, HindiScene, HindiReelStory

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = BASE_DIR / "data" / "reels" / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class VoiceSynthesisResult:
    scene_idx: int
    speaker: str
    character_id: str
    voice_name: str
    audio_path_mp3: str
    audio_path_wav: str
    duration_sec: float
    sample_rate: int
    dialogue_hindi: str
    timing_segments: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None


class HindiVoiceEngine:
    """
    Modular Hindi Voice Engine.
    Handles neural TTS generation, voice pitch/rate tuning per character,
    timing extraction, and audio stream formatting.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or AUDIO_DIR

    def validate_hindi_text(self, text: str) -> Tuple[bool, str]:
        """Checks if text contains native Hindi Devanagari characters."""
        if not text or not text.strip():
            return False, "Dialogue text is empty."
        devanagari_count = len(DEVANAGARI_REGEX.findall(text))
        if devanagari_count < 2:
            return False, f"Text '{text[:30]}' lacks Hindi Devanagari characters. System requires Hindi dialogue."
        return True, "Valid Hindi text."

    async def _synthesize_async(
        self,
        text: str,
        voice_name: str,
        pitch: str,
        rate: str,
        output_mp3: str,
    ) -> List[Dict[str, Any]]:
        """Invokes edge-tts to generate audio and captures sentence timing boundaries."""
        comm = edge_tts.Communicate(text=text, voice=voice_name, pitch=pitch, rate=rate)
        timing_segments: List[Dict[str, Any]] = []

        with open(output_mp3, "wb") as f:
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    # offset and duration are in 100ns ticks (10,000,000 ticks = 1 sec)
                    offset_sec = chunk["offset"] / 10_000_000.0
                    duration_sec = chunk["duration"] / 10_000_000.0
                    timing_segments.append({
                        "text": chunk.get("text", ""),
                        "start_sec": offset_sec,
                        "end_sec": offset_sec + duration_sec,
                        "duration_sec": duration_sec,
                    })

        return timing_segments

    def _convert_mp3_to_wav(self, mp3_path: str, wav_path: str) -> Tuple[float, int, np.ndarray]:
        """Decodes MP3 using PyAV and writes standard PCM WAV (16-bit 24kHz/44.1kHz)."""
        container = av.open(mp3_path)
        stream = container.streams.audio[0]
        frames = []
        for frame in container.decode(stream):
            frames.append(frame.to_ndarray())
        container.close()

        if not frames:
            raise RuntimeError(f"PyAV failed to decode audio frames from {mp3_path}")

        audio_data = np.concatenate(frames, axis=1)  # shape: (channels, samples)
        sample_rate = stream.rate
        num_channels = audio_data.shape[0]
        num_samples = audio_data.shape[1]
        duration_sec = num_samples / float(sample_rate)

        # Normalize to int16
        if audio_data.dtype != np.int16:
            # float32 to int16 scaling
            if np.issubdtype(audio_data.dtype, np.floating):
                audio_int16 = np.clip(audio_data * 32767.0, -32768, 32767).astype(np.int16)
            else:
                audio_int16 = audio_data.astype(np.int16)
        else:
            audio_int16 = audio_data

        # Write WAV using standard library
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            # Interleave channels
            interleaved = audio_int16.T.reshape(-1)
            wf.writeframes(interleaved.tobytes())

        return duration_sec, sample_rate, audio_int16

    def synthesize_scene_voice(
        self,
        scene: HindiScene,
        character_id: str,
        reel_id: str,
    ) -> VoiceSynthesisResult:
        """
        Synthesizes the spoken Hindi dialogue for a single scene.
        """
        valid, msg = self.validate_hindi_text(scene.dialogue_hindi)
        if not valid:
            return VoiceSynthesisResult(
                scene_idx=scene.scene_idx,
                speaker=scene.speaker,
                character_id=character_id,
                voice_name="unknown",
                audio_path_mp3="",
                audio_path_wav="",
                duration_sec=0.0,
                sample_rate=0,
                dialogue_hindi=scene.dialogue_hindi,
                success=False,
                error_message=f"Hindi validation failed: {msg}",
            )

        voice_params = character_consistency_manager.get_voice_parameters(character_id)
        voice_name = voice_params["voice_name"]
        pitch = voice_params["pitch"]
        rate = voice_params["rate"]

        file_prefix = f"{reel_id}_scene_{scene.scene_idx}"
        mp3_path = str(self.output_dir / f"{file_prefix}.mp3")
        wav_path = str(self.output_dir / f"{file_prefix}.wav")

        try:
            # Run async edge-tts in event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Running inside an active loop (e.g. FastAPI / asyncio worker)
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        timing = pool.submit(
                            asyncio.run,
                            self._synthesize_async(scene.dialogue_hindi, voice_name, pitch, rate, mp3_path)
                        ).result()
                else:
                    timing = loop.run_until_complete(
                        self._synthesize_async(scene.dialogue_hindi, voice_name, pitch, rate, mp3_path)
                    )
            except RuntimeError:
                timing = asyncio.run(
                    self._synthesize_async(scene.dialogue_hindi, voice_name, pitch, rate, mp3_path)
                )

            # Convert to WAV and get exact duration
            duration_sec, sample_rate, _ = self._convert_mp3_to_wav(mp3_path, wav_path)

            if not timing:
                timing = [{
                    "text": scene.dialogue_hindi,
                    "start_sec": 0.0,
                    "end_sec": duration_sec,
                    "duration_sec": duration_sec,
                }]

            return VoiceSynthesisResult(
                scene_idx=scene.scene_idx,
                speaker=scene.speaker,
                character_id=character_id,
                voice_name=voice_name,
                audio_path_mp3=mp3_path,
                audio_path_wav=wav_path,
                duration_sec=duration_sec,
                sample_rate=sample_rate,
                dialogue_hindi=scene.dialogue_hindi,
                timing_segments=timing,
                success=True,
            )
        except Exception as e:
            return VoiceSynthesisResult(
                scene_idx=scene.scene_idx,
                speaker=scene.speaker,
                character_id=character_id,
                voice_name=voice_name,
                audio_path_mp3="",
                audio_path_wav="",
                duration_sec=0.0,
                sample_rate=0,
                dialogue_hindi=scene.dialogue_hindi,
                success=False,
                error_message=f"Hindi TTS synthesis failed: {str(e)}",
            )

    def synthesize_story_voiceover(
        self,
        story: HindiReelStory,
        reel_id: str,
    ) -> List[VoiceSynthesisResult]:
        """
        Synthesizes voiceovers for all scenes in the story sequentially.
        """
        results: List[VoiceSynthesisResult] = []
        for sc in story.scenes:
            char_id = getattr(sc, "character_id", None) or story.character_id
            res = self.synthesize_scene_voice(sc, char_id, reel_id)
            results.append(res)
        return results


hindi_voice_engine = HindiVoiceEngine()
