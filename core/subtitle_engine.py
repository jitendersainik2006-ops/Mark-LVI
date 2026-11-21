"""
core/subtitle_engine.py — Native Devanagari Subtitle Generation & Overlay Engine for J.A.R.V.I.S.

Renders high-contrast, synchronized Hindi Devanagari subtitles onto 9:16 vertical video frames
using Nirmala UI TrueType font (C:\\Windows\\Fonts\\Nirmala.ttc).
Also generates standard .srt subtitle files for Instagram upload.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
SUBTITLES_DIR = BASE_DIR / "data" / "reels" / "subtitles"
SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)

FONT_CANDIDATES = [
    "C:/Windows/Fonts/Nirmala.ttc",
    "C:/Windows/Fonts/nirmala.ttf",
    "C:/Windows/Fonts/nirmalab.ttf",
    "C:/Windows/Fonts/mangal.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


class SubtitleEngine:
    """
    Renders synchronized Hindi Devanagari subtitles on video frames
    and generates .srt files.
    """

    def __init__(self, font_path: Optional[str] = None):
        self.font_path = font_path or self._detect_font()

    def _detect_font(self) -> str:
        for p in FONT_CANDIDATES:
            if os.path.exists(p):
                return p
        return "arial.ttf"

    def get_font(self, size: int) -> ImageFont.FreeTypeFont:
        try:
            return ImageFont.truetype(self.font_path, size)
        except Exception:
            return ImageFont.load_default()

    def format_srt_timestamp(self, seconds: float) -> str:
        """Converts seconds float to 00:00:00,000 SRT format."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        msec = int(round((seconds - int(seconds)) * 1000))
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{msec:03d}"

    def export_srt(
        self,
        subtitles: List[Dict[str, Any]],
        reel_id: str,
    ) -> str:
        """
        Exports subtitle cues to standard .srt file.
        Each item in subtitles: {"start_sec": float, "end_sec": float, "text": str}
        """
        srt_path = str(SUBTITLES_DIR / f"{reel_id}.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            for idx, item in enumerate(subtitles, 1):
                start = self.format_srt_timestamp(item["start_sec"])
                end = self.format_srt_timestamp(item["end_sec"])
                text = item["text"]
                f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")
        return srt_path

    def render_subtitle_on_frame(
        self,
        frame_image: Image.Image,
        text: str,
        speaker_name: Optional[str] = None,
        font_size: int = 42,
        y_position_pct: float = 0.78,
    ) -> Image.Image:
        """
        Renders a modern, high-contrast Devanagari subtitle pill box onto the image frame.
        """
        if not text:
            return frame_image

        draw = ImageDraw.Draw(frame_image)
        width, height = frame_image.size

        font = self.get_font(font_size)
        speaker_font = self.get_font(int(font_size * 0.65))

        full_text = text.strip()

        # Wrap text if too wide (width > 80% frame)
        max_text_width = int(width * 0.82)
        words = full_text.split()
        lines: List[str] = []
        cur_line: List[str] = []

        for w in words:
            test_line = " ".join(cur_line + [w])
            bbox = font.getbbox(test_line)
            line_w = bbox[2] - bbox[0]
            if line_w <= max_text_width:
                cur_line.append(w)
            else:
                if cur_line:
                    lines.append(" ".join(cur_line))
                cur_line = [w]
        if cur_line:
            lines.append(" ".join(cur_line))

        # Calculate bounding box for text pill
        line_height = int(font_size * 1.35)
        total_text_h = len(lines) * line_height
        box_padding_x = 24
        box_padding_y = 16

        max_w = 0
        for l in lines:
            bbox = font.getbbox(l)
            w = bbox[2] - bbox[0]
            if w > max_w:
                max_w = w

        center_y = int(height * y_position_pct)
        box_w = max_w + (box_padding_x * 2)
        box_h = total_text_h + (box_padding_y * 2)
        box_x1 = (width - box_w) // 2
        box_y1 = center_y - (box_h // 2)
        box_x2 = box_x1 + box_w
        box_y2 = box_y1 + box_h

        # Draw semi-transparent dark rounded backdrop
        overlay = Image.new("RGBA", frame_image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle(
            [box_x1, box_y1, box_x2, box_y2],
            radius=16,
            fill=(10, 10, 18, 215),  # 85% opacity dark indigo
            outline=(250, 204, 21, 230),  # Golden yellow border
            width=3,
        )

        # Draw speaker tag if provided
        if speaker_name:
            tag_text = f"▶ {speaker_name}"
            sp_bbox = speaker_font.getbbox(tag_text)
            sp_w = sp_bbox[2] - sp_bbox[0]
            sp_x = box_x1 + 16
            sp_y = box_y1 - int(font_size * 0.8)
            overlay_draw.rounded_rectangle(
                [sp_x - 6, sp_y - 2, sp_x + sp_w + 6, sp_y + (sp_bbox[3] - sp_bbox[1]) + 4],
                radius=6,
                fill=(244, 63, 94, 240),  # Rose red badge
            )
            overlay_draw.text((sp_x, sp_y), tag_text, font=speaker_font, fill=(255, 255, 255))

        # Alpha composite overlay
        frame_rgba = frame_image.convert("RGBA")
        frame_rgba = Image.alpha_composite(frame_rgba, overlay)
        draw = ImageDraw.Draw(frame_rgba)

        # Draw text lines with black shadow outline for readability
        cur_y = box_y1 + box_padding_y
        for l in lines:
            bbox = font.getbbox(l)
            line_w = bbox[2] - bbox[0]
            cur_x = (width - line_w) // 2

            # Black outline
            for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                draw.text((cur_x + dx, cur_y + dy), l, font=font, fill=(0, 0, 0, 255))

            # Main text: Vibrant bright yellow
            draw.text((cur_x, cur_y), l, font=font, fill=(255, 245, 157, 255))
            cur_y += line_height

        return frame_rgba.convert("RGB")


subtitle_engine = SubtitleEngine()
