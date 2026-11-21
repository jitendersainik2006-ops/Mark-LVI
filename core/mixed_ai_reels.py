"""
core/mixed_ai_reels.py — Central Mixed-Style AI Viral Reels Creation Studio for J.A.R.V.I.S.

Orchestrates:
1. HindiStoryEngine: 4 styles (Realistic AI, Cinematic 3D, AI Animals, AI Transformations)
2. CharacterConsistencyManager: Recurring personas (Sheru Bhai, Chatur Bandar, Desi Dog, etc.)
3. HindiVoiceEngine: Native Hindi neural voices with character tuning
4. LipSyncEngine: Spoken audio amplitude viseme modulation
5. SubtitleEngine: Devanagari subtitles on video + .srt export
6. VideoProviderManager: Local cinematic / open-source cloud / procedural fallback
7. VideoRenderManager: PyAV H.264/AAC muxing, audio mixing & cover art
8. ReelQualityValidator: 10-point automated quality inspection
9. ReelApprovalManager: Zero-leak human approval gate & ledger persistence
"""

from __future__ import annotations

import concurrent.futures
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.character_consistency_manager import character_consistency_manager
from core.hindi_story_engine import HindiReelStory, hindi_story_engine
from core.hindi_voice_engine import VoiceSynthesisResult, hindi_voice_engine
from core.reel_approval_manager import reel_approval_manager
from core.reel_quality_validator import QualityValidationReport, reel_quality_validator
from core.video_providers import video_provider_manager
from core.video_render_manager import VideoRenderResult, video_render_manager

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class MixedReelJob:
    job_id: str
    reel_id: str
    style: str
    character_id: str
    custom_prompt: Optional[str]
    provider_id: str
    status: str  # "queued", "generating_story", "synthesizing_voice", "rendering_scenes", "muxing_audio", "validating", "completed", "failed"
    progress_pct: int
    step_description: str
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    story: Optional[Dict[str, Any]] = None
    render_result: Optional[Dict[str, Any]] = None
    quality_report: Optional[Dict[str, Any]] = None
    ledger_entry: Optional[Dict[str, Any]] = None


class MixedAIReelsStudio:
    """
    Central coordinator for Hindi Mixed-Style AI Reels production.
    """

    def __init__(self):
        self._jobs: Dict[str, MixedReelJob] = {}
        self._lock = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="MixedReelGen")

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return {
                "job_id": job.job_id,
                "reel_id": job.reel_id,
                "style": job.style,
                "character_id": job.character_id,
                "status": job.status,
                "progress_pct": job.progress_pct,
                "step_description": job.step_description,
                "error": job.error,
                "created_at": job.created_at,
                "completed_at": job.completed_at,
                "story": job.story,
                "render_result": job.render_result,
                "quality_report": job.quality_report,
                "ledger_entry": job.ledger_entry,
            }

    def start_generation_job(
        self,
        style: str = "ai_animals",
        character_id: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        provider_id: str = "local_cinematic",
    ) -> str:
        """Starts asynchronous background generation and returns a job_id."""
        job_id = f"job_mixed_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        reel_id = f"reel_hindi_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        if not character_id:
            if style == "talking_objects":
                character_id = "iron_dumbbell"
            elif style == "cinematic_story":
                character_id = "rocky_seb"
            elif style == "motion_comic":
                character_id = "prof_gyani"
            elif style == "ai_animals":
                character_id = "sheru_bhai"
            elif style in ["realistic_ai", "cinematic_3d", "ai_transformations"]:
                character_id = "human_characters"
            else:
                character_id = "sheru_bhai"

        job = MixedReelJob(
            job_id=job_id,
            reel_id=reel_id,
            style=style,
            character_id=character_id,
            custom_prompt=custom_prompt,
            provider_id=provider_id,
            status="queued",
            progress_pct=5,
            step_description="Job queued for processing",
        )

        with self._lock:
            self._jobs[job_id] = job

        self._executor.submit(self._run_pipeline, job_id)
        return job_id

    def generate_sync(
        self,
        style: str = "ai_animals",
        character_id: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        provider_id: str = "local_cinematic",
    ) -> Dict[str, Any]:
        """Synchronously runs the complete generation pipeline and returns the result."""
        job_id = self.start_generation_job(style, character_id, custom_prompt, provider_id)
        # Wait for completion
        while True:
            time.sleep(0.5)
            job_data = self.get_job(job_id)
            if not job_data:
                raise RuntimeError("Job disappeared during execution.")
            if job_data["status"] in ["completed", "failed"]:
                return job_data

    def _update_job(self, job_id: str, status: str, progress: int, description: str, error: Optional[str] = None):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = status
                job.progress_pct = progress
                job.step_description = description
                if error:
                    job.error = error

    def _run_pipeline(self, job_id: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return

        reel_id = job.reel_id
        style = job.style
        char_id = job.character_id
        prompt = job.custom_prompt
        provider_id = job.provider_id

        try:
            # ── 1. STORY GENERATION ──────────────────────────────────────────
            self._update_job(job_id, "generating_story", 15, "Generating original Hindi story and scene breakdown...")
            story = hindi_story_engine.generate_story(
                style=style,
                character_id=char_id,
                custom_prompt=prompt,
                use_ai_llm=bool(prompt),
            )
            with self._lock:
                job.story = story.to_dict()

            # ── 2. HINDI VOICE SYNTHESIS ─────────────────────────────────────
            self._update_job(job_id, "synthesizing_voice", 35, f"Synthesizing Hindi neural voiceovers for {len(story.scenes)} scenes...")
            voice_results = hindi_voice_engine.synthesize_story_voiceover(story, reel_id)

            # Check if any voice synthesis failed
            failed_voices = [vr for vr in voice_results if not vr.success]
            if failed_voices:
                err_msg = failed_voices[0].error_message or "Unknown voice synthesis failure"
                self._update_job(job_id, "failed", 35, f"Voice synthesis error: {err_msg}", error=err_msg)
                return

            # ── 3. SCENE RENDERING & VIDEO MUXING ────────────────────────────
            self._update_job(job_id, "rendering_scenes", 60, "Rendering multi-layered cinematic scene frames & mouth visemes...")
            render_res = video_render_manager.render_full_reel(
                story=story,
                voice_results=voice_results,
                provider_id=provider_id,
                reel_id=reel_id,
                width=720,
                height=1280,
                fps=30,
            )

            if not render_res.success:
                self._update_job(job_id, "failed", 60, f"Render error: {render_res.error_message}", error=render_res.error_message)
                return

            with self._lock:
                job.render_result = {
                    "video_path": render_res.video_path,
                    "cover_path": render_res.cover_image_path,
                    "srt_path": render_res.srt_path,
                    "duration_sec": render_res.duration_sec,
                    "total_frames": render_res.total_frames,
                    "resolution": render_res.resolution,
                    "fps": render_res.fps,
                    "file_size_bytes": render_res.file_size_bytes,
                    "provider_id": render_res.provider_id,
                    "is_generative_ai": render_res.is_generative_ai,
                    "is_procedural_fallback": render_res.is_procedural_fallback,
                }

            # ── 4. QUALITY VALIDATION ────────────────────────────────────────
            self._update_job(job_id, "validating", 85, "Running automated 10-point quality & Hindi compliance check...")
            quality_report = reel_quality_validator.validate_reel(story, render_res)
            with self._lock:
                job.quality_report = quality_report.to_dict()

            if not quality_report.overall_passed:
                fail_summary = "; ".join(quality_report.failure_reasons)
                self._update_job(job_id, "failed", 85, f"Quality check failed: {fail_summary}", error=fail_summary)
                return

            # ── 5. APPROVAL GATE & LEDGER REGISTRATION ───────────────────────
            self._update_job(job_id, "registering", 95, "Enforcing WAITING_FOR_APPROVAL and persisting to ledger...")
            ledger_entry = reel_approval_manager.register_new_reel(
                reel_id=reel_id,
                title=story.title_hindi,
                style=style,
                video_path=render_res.video_path,
                cover_path=render_res.cover_image_path,
                srt_path=render_res.srt_path,
                caption=story.caption_hindi,
                hashtags=story.hashtags,
                duration_sec=render_res.duration_sec,
                provider_id=render_res.provider_id,
                is_generative_ai=render_res.is_generative_ai,
                is_procedural_fallback=render_res.is_procedural_fallback,
            )

            with self._lock:
                job.ledger_entry = ledger_entry
                job.status = "completed"
                job.progress_pct = 100
                job.step_description = "Hindi AI Reel successfully generated and awaiting your approval."
                job.completed_at = time.time()

        except Exception as e:
            self._update_job(job_id, "failed", 0, f"Unexpected pipeline exception: {str(e)}", error=str(e))


mixed_ai_reels_studio = MixedAIReelsStudio()
