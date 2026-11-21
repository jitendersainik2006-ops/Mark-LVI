"""
core/video_render_manager.py — Final Video Assembly, PyAV Muxing & Media Export for J.A.R.V.I.S.

Assembles scene video frames, Devanagari subtitles, spoken Hindi voiceover, and
synchronized sound effects into a high-definition vertical 9:16 MP4 video (H.264/AAC)
with FastStart optimization and vertical cover art.
"""

from __future__ import annotations

import os
import shutil
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from core.character_consistency_manager import character_consistency_manager
from core.hindi_story_engine import HindiReelStory, HindiScene
from core.hindi_voice_engine import VoiceSynthesisResult
from core.lip_sync_engine import lip_sync_engine
from core.subtitle_engine import subtitle_engine
from core.video_providers import BaseVideoProvider, video_provider_manager

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "reels"
VIDEOS_DIR = DATA_DIR / "videos"
COVERS_DIR = DATA_DIR / "covers"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
COVERS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class VideoRenderResult:
    reel_id: str
    video_path: str
    cover_image_path: str
    srt_path: str
    duration_sec: float
    total_frames: int
    resolution: str
    fps: int
    video_codec: str
    audio_codec: str
    file_size_bytes: int
    cover_size_bytes: int
    provider_id: str
    is_generative_ai: bool
    is_procedural_fallback: bool
    creation_timestamp: str
    success: bool = True
    error_message: Optional[str] = None


class VideoRenderManager:
    """
    Manages final PyAV video encoding, audio mixing, subtitle stamping, and cover generation.
    """

    def __init__(self):
        self.sample_rate = 44100

    def _synthesize_background_audio(
        self,
        duration_sec: float,
        scenes: List[HindiScene],
        voice_results: List[VoiceSynthesisResult],
    ) -> np.ndarray:
        """
        Synthesizes subtle ambient background music with dynamic SFX cues at scene boundaries.
        Returns float32 stereo array of shape (2, total_samples).
        """
        total_samples = int(duration_sec * self.sample_rate)
        t = np.linspace(0, duration_sec, total_samples, endpoint=False)

        # 1. Subtle, warm comedy groove (gentle volume: 0.08 max so voice remains 100% prominent)
        bass = 0.06 * np.sin(2 * np.pi * 73.4 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 4.0 * t))
        chords = 0.03 * np.sin(2 * np.pi * 220.0 * t) * (np.sin(2 * np.pi * 8.0 * t) > 0.4)
        base_groove = bass + chords

        sfx_layer = np.zeros(total_samples, dtype=np.float32)

        # 2. Add SFX cues at scene transition times
        cur_t = 0.0
        for idx, sc in enumerate(scenes):
            sc_dur = voice_results[idx].duration_sec if idx < len(voice_results) and voice_results[idx].success else sc.duration_sec
            start_samp = int(cur_t * self.sample_rate)
            cur_t += sc_dur

            if start_samp >= total_samples:
                continue

            sfx_type = sc.sfx or "whoosh"
            if sfx_type == "record_scratch":
                sfx_len = int(0.35 * self.sample_rate)
                end_samp = min(total_samples, start_samp + sfx_len)
                sub_t = np.linspace(0, 0.35, end_samp - start_samp)
                freq = np.linspace(1400, 200, len(sub_t))
                scratch = 0.35 * np.sin(2 * np.pi * freq * sub_t) * (np.random.rand(len(sub_t)) * 0.4 + 0.6)
                sfx_layer[start_samp:end_samp] += scratch
            elif sfx_type == "rimshot":
                sfx_len = int(0.30 * self.sample_rate)
                end_samp = min(total_samples, start_samp + sfx_len)
                sub_t = np.linspace(0, 0.30, end_samp - start_samp)
                rim = 0.40 * (np.sin(2 * np.pi * 600 * sub_t) + np.sin(2 * np.pi * 1200 * sub_t)) * np.exp(-sub_t * 16.0)
                sfx_layer[start_samp:end_samp] += rim
            elif sfx_type == "whoosh":
                sfx_len = int(0.28 * self.sample_rate)
                end_samp = min(total_samples, start_samp + sfx_len)
                sub_t = np.linspace(0, 0.28, end_samp - start_samp)
                noise = 0.25 * (np.random.rand(len(sub_t)) * 2 - 1) * np.sin(np.pi * sub_t / 0.28)
                sfx_layer[start_samp:end_samp] += noise
            else:  # pop / cartoon boing
                sfx_len = int(0.28 * self.sample_rate)
                end_samp = min(total_samples, start_samp + sfx_len)
                sub_t = np.linspace(0, 0.28, end_samp - start_samp)
                boing = 0.30 * np.sin(2 * np.pi * (160 + 380 * sub_t) * sub_t) * np.exp(-sub_t * 6.0)
                sfx_layer[start_samp:end_samp] += boing

        # Stereo mix: duplicate to 2 channels
        mono_mix = base_groove + sfx_layer
        stereo_mix = np.vstack([mono_mix, mono_mix])
        return stereo_mix

    def _assemble_master_audio(
        self,
        voice_results: List[VoiceSynthesisResult],
        total_duration_sec: float,
        bg_sfx_stereo: np.ndarray,
    ) -> np.ndarray:
        """
        Mixes spoken dialogue tracks with background music and SFX into a mastered int16 stereo array.
        """
        total_samples = int(total_duration_sec * self.sample_rate)
        voice_stereo = np.zeros((2, total_samples), dtype=np.float32)

        cur_sample = 0
        for vr in voice_results:
            if not vr.success or not vr.audio_path_wav or not os.path.exists(vr.audio_path_wav):
                cur_sample += int(vr.duration_sec * self.sample_rate)
                continue

            try:
                with wave.open(vr.audio_path_wav, "rb") as wf:
                    sr = wf.getframerate()
                    nc = wf.getnchannels()
                    nf = wf.getnframes()
                    raw = wf.readframes(nf)
                data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                if nc > 1:
                    data = data.reshape(-1, nc).mean(axis=1)

                # Resample to 44100 if necessary
                if sr != self.sample_rate:
                    target_len = int(len(data) * self.sample_rate / float(sr))
                    data = np.interp(
                        np.linspace(0, len(data), target_len, endpoint=False),
                        np.arange(len(data)),
                        data,
                    )

                end_sample = min(total_samples, cur_sample + len(data))
                actual_len = end_sample - cur_sample
                if actual_len > 0:
                    voice_stereo[0, cur_sample:end_sample] += data[:actual_len]
                    voice_stereo[1, cur_sample:end_sample] += data[:actual_len]

                cur_sample += len(data)
            except Exception:
                cur_sample += int(vr.duration_sec * self.sample_rate)

        # Combine voice (dominant) + bg sfx
        combined = (voice_stereo * 0.92) + (bg_sfx_stereo[:, :total_samples] * 0.40)

        # Normalize and prevent clipping
        peak = np.max(np.abs(combined))
        if peak > 0.98:
            combined = combined * (0.95 / peak)

        # Convert to int16
        mastered_int16 = (combined * 32767.0).astype(np.int16)
        return mastered_int16

    def generate_cover_image(
        self,
        story: HindiReelStory,
        character_id: str,
        output_path: str,
        width: int = 720,
        height: int = 1280,
    ) -> str:
        """
        Renders high-resolution 9:16 vertical cover image with bold Hindi title and character preview.
        """
        char = character_consistency_manager.get_character(character_id)
        img = Image.new("RGB", (width, height), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)

        # Background gradient
        top_c = (20, 20, 35)
        bot_c = char.primary_color
        for y in range(height):
            ratio = y / float(height)
            r = int(top_c[0] + (bot_c[0] - top_c[0]) * (ratio ** 1.5))
            g = int(top_c[1] + (bot_c[1] - top_c[1]) * (ratio ** 1.5))
            b = int(top_c[2] + (bot_c[2] - top_c[2]) * (ratio ** 1.5))
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Title font
        font_title = subtitle_engine.get_font(52)
        font_badge = subtitle_engine.get_font(28)

        # Draw Style Badge
        badge_text = f"★ {story.style.upper().replace('_', ' ')} ★"
        b_bbox = font_badge.getbbox(badge_text)
        b_w = b_bbox[2] - b_bbox[0]
        badge_x = (width - b_w) // 2
        badge_y = int(height * 0.12)
        draw.rounded_rectangle(
            [badge_x - 16, badge_y - 8, badge_x + b_w + 16, badge_y + 36],
            radius=8,
            fill=(244, 63, 94),
        )
        draw.text((badge_x, badge_y), badge_text, font=font_badge, fill=(255, 255, 255))

        # Render Character Center
        provider = video_provider_manager.get_provider("local_cinematic")
        if isinstance(provider, BaseVideoProvider):
            avatar = provider._draw_character_avatar(char, "smug", "open", story.style, box_size=460)  # type: ignore
            cx = (width - 460) // 2
            cy = int(height * 0.35)
            img.paste(avatar, (cx, cy), avatar)

        # Render Bold Hindi Title in Lower Third
        title_text = story.title_hindi
        words = title_text.split()
        lines: List[str] = []
        cur = []
        for w in words:
            if len(" ".join(cur + [w])) <= 16:
                cur.append(w)
            else:
                lines.append(" ".join(cur))
                cur = [w]
        if cur:
            lines.append(" ".join(cur))

        ty = int(height * 0.72)
        for l in lines:
            bbox = font_title.getbbox(l)
            lw = bbox[2] - bbox[0]
            tx = (width - lw) // 2
            # Outline
            for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
                draw.text((tx + dx, ty + dy), l, font=font_title, fill=(0, 0, 0))
            draw.text((tx, ty), l, font=font_title, fill=(255, 245, 157))
            ty += 64

        img.save(output_path, "JPEG", quality=95)
        return output_path

    def render_full_reel(
        self,
        story: HindiReelStory,
        voice_results: List[VoiceSynthesisResult],
        provider_id: str = "local_cinematic",
        reel_id: Optional[str] = None,
        width: int = 720,
        height: int = 1280,
        fps: int = 30,
    ) -> VideoRenderResult:
        """
        Assembles all scene frames, synchronized subtitles, and audio into an MP4 video.
        """
        reel_id = reel_id or f"reel_hindi_{int(time.time())}_{os.urandom(3).hex()}"
        out_video_path = str(VIDEOS_DIR / f"{reel_id}.mp4")
        out_cover_path = str(COVERS_DIR / f"{reel_id}_cover.jpg")

        # Fallback mirrors in data/reels for backward compatibility
        mirror_video_path = str(DATA_DIR / f"{reel_id}.mp4")
        mirror_cover_path = str(DATA_DIR / f"{reel_id}_cover.jpg")

        provider = video_provider_manager.get_provider(provider_id)
        caps = provider.get_capabilities()

        # Calculate exact duration
        scene_durations = [
            vr.duration_sec if vr.success and vr.duration_sec > 1.0 else sc.duration_sec
            for sc, vr in zip(story.scenes, voice_results)
        ]
        total_duration_sec = sum(scene_durations)

        # 1. Synthesize background audio and mix master audio
        bg_sfx = self._synthesize_background_audio(total_duration_sec, story.scenes, voice_results)
        master_audio = self._assemble_master_audio(voice_results, total_duration_sec, bg_sfx)

        # 2. Build Subtitle Cues
        sub_cues: List[Dict[str, Any]] = []
        cur_time = 0.0
        for idx, sc in enumerate(story.scenes):
            sc_dur = scene_durations[idx]
            sub_cues.append({
                "start_sec": cur_time,
                "end_sec": cur_time + sc_dur,
                "text": sc.subtitle_hindi,
                "speaker": sc.speaker,
            })
            cur_time += sc_dur

        srt_path = subtitle_engine.export_srt(sub_cues, reel_id)

        # 3. Render all scene frames with dynamic visemes and stamp subtitles
        all_frames: List[Image.Image] = []
        for idx, sc in enumerate(story.scenes):
            sc_dur = scene_durations[idx]
            vr = voice_results[idx] if idx < len(voice_results) else None
            wav_path = vr.audio_path_wav if vr and vr.success else ""

            # Compute visemes
            viseme_timeline = lip_sync_engine.compute_viseme_timeline(wav_path, sc_dur)

            # Render scene visuals from provider
            raw_frames = provider.render_scene_frames(
                scene=sc,
                character_id=getattr(sc, "character_id", None) or story.character_id,
                style=story.style,
                viseme_timeline=viseme_timeline,
                width=width,
                height=height,
                fps=fps,
            )

            # Stamp synchronized Devanagari subtitles on each frame
            for f in raw_frames:
                frame_with_sub = subtitle_engine.render_subtitle_on_frame(
                    frame_image=f,
                    text=sc.subtitle_hindi,
                    speaker_name=sc.speaker,
                    font_size=42,
                    y_position_pct=0.78,
                )
                all_frames.append(frame_with_sub)

        total_frames = len(all_frames)

        # 4. PyAV Muxing into FastStart MP4
        # Save master audio to temp WAV for robust PyAV streaming
        master_wav_path = str(DATA_DIR / "temporary_render" / f"{reel_id}_master.wav")
        with wave.open(master_wav_path, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            interleaved = master_audio.T.reshape(-1)
            wf.writeframes(interleaved.tobytes())

        container = av.open(out_video_path, mode="w", options={"movflags": "faststart"})

        # Video stream: H.264 High Profile
        v_stream = container.add_stream("libx264" if "libx264" in av.codecs_available else "mpeg4", rate=fps)
        v_stream.width = width
        v_stream.height = height
        v_stream.pix_fmt = "yuv420p"
        v_stream.options = {"crf": "22", "preset": "veryfast"}

        # Audio stream: AAC Stereo with AudioResampler
        astream_out = None
        audio_resampler = None
        audio_reader = None
        try:
            audio_reader = av.open(master_wav_path)
            astream_out = container.add_stream("aac", rate=self.sample_rate, layout="stereo")
            astream_out.format = av.AudioFormat("fltp")
            audio_resampler = av.AudioResampler(
                format=astream_out.format,
                layout="stereo",
                rate=self.sample_rate,
            )
        except Exception:
            pass

        # Encode video frames
        for frame_idx, img in enumerate(all_frames):
            av_frame = av.VideoFrame.from_image(img)
            av_frame.pts = frame_idx
            for packet in v_stream.encode(av_frame):
                container.mux(packet)
        for packet in v_stream.encode():
            container.mux(packet)

        # Mux Audio Packets from master WAV
        if audio_reader and astream_out and audio_resampler:
            try:
                for apacket in audio_reader.demux(audio_reader.streams.audio[0]):
                    for aframe in apacket.decode():
                        resampled_frames = audio_resampler.resample(aframe)
                        for rframe in resampled_frames:
                            for out_packet in astream_out.encode(rframe):
                                container.mux(out_packet)
                # Flush audio
                for out_packet in astream_out.encode():
                    container.mux(out_packet)
                audio_reader.close()
            except Exception:
                pass

        container.close()

        # 5. Generate Cover Image
        self.generate_cover_image(story, story.character_id, out_cover_path, width, height)

        # Copy mirrors for backward compatibility
        try:
            shutil.copy2(out_video_path, mirror_video_path)
            shutil.copy2(out_cover_path, mirror_cover_path)
        except Exception:
            pass

        file_size = os.path.getsize(out_video_path)
        cover_size = os.path.getsize(out_cover_path)

        return VideoRenderResult(
            reel_id=reel_id,
            video_path=out_video_path,
            cover_image_path=out_cover_path,
            srt_path=srt_path,
            duration_sec=total_duration_sec,
            total_frames=total_frames,
            resolution=f"{width}x{height}",
            fps=fps,
            video_codec="h264",
            audio_codec="aac",
            file_size_bytes=file_size,
            cover_size_bytes=cover_size,
            provider_id=caps.provider_id,
            is_generative_ai=caps.is_generative_ai,
            is_procedural_fallback=caps.is_procedural_fallback,
            creation_timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            success=True,
        )


video_render_manager = VideoRenderManager()
