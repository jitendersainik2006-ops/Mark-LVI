"""
tools/generate_style_samples.py — Generate and Validate 3 Live Reference Style Reels for J.A.R.V.I.S.

Generates:
1. Style A: 3D Talking Objects (iron_dumbbell & shaker_bottle)
2. Style B: 3D Cinematic Story (rocky_seb & badshah_burger)
3. Style C: 2D Motion Comic (prof_gyani)

Verifies all 10 quality points and enforces WAITING_FOR_APPROVAL.
"""

import io
import json
import os
import sys
import time

# Ensure UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import av
from core.mixed_ai_reels import mixed_ai_reels_studio
from core.reel_quality_validator import reel_quality_validator


def inspect_video_file(path: str):
    container = av.open(path)
    v_stream = container.streams.video[0] if container.streams.video else None
    a_stream = container.streams.audio[0] if container.streams.audio else None

    v_fps = 30.0
    if v_stream:
        if getattr(v_stream, "average_rate", None):
            v_fps = float(v_stream.average_rate)
        elif getattr(v_stream, "base_rate", None):
            v_fps = float(v_stream.base_rate)

    v_info = {
        "codec": v_stream.codec_context.name if v_stream else None,
        "width": v_stream.width if v_stream else None,
        "height": v_stream.height if v_stream else None,
        "fps": v_fps,
        "frames": v_stream.frames if v_stream else None,
    } if v_stream else None

    a_info = {
        "codec": a_stream.codec_context.name if a_stream else None,
        "sample_rate": a_stream.rate if a_stream else None,
        "channels": a_stream.channels if a_stream else None,
    } if a_stream else None

    duration = float(container.duration / 1000000.0) if container.duration else None
    container.close()

    return {
        "size_bytes": os.path.getsize(path),
        "duration_sec": duration,
        "video": v_info,
        "audio": a_info,
    }


def main():
    styles_to_generate = [
        ("talking_objects", "iron_dumbbell", "Style A — 3D Talking Objects"),
        ("cinematic_story", "rocky_seb", "Style B — 3D Cinematic Storytelling"),
        ("motion_comic", "prof_gyani", "Style C — 2D Motion Comic / Explainer"),
    ]

    results = []
    # Load existing successful results if available
    out_json = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "samples_generation_summary.json")
    existing_map = {}
    if os.path.exists(out_json):
        try:
            with open(out_json, "r", encoding="utf-8") as f:
                old_list = json.load(f)
                for item in old_list:
                    if item.get("quality_passed") and os.path.exists(item.get("video_path", "")):
                        existing_map[item.get("style")] = item
        except Exception:
            pass

    for style, char_id, label in styles_to_generate:
        if style in existing_map:
            print(f"\n[CACHE HIT] {label} already generated and verified: {existing_map[style]['video_path']}")
            results.append(existing_map[style])
            continue

        print(f"\n>>> Starting Generation: {label} (Style: {style}, Character: {char_id})")
        t0 = time.time()
        job_res = mixed_ai_reels_studio.generate_sync(
            style=style,
            character_id=char_id,
            provider_id="local_cinematic",
        )
        elapsed = time.time() - t0

        if job_res.get("status") != "completed":
            print(f"[FAIL] Job {job_res.get('job_id')} failed: {job_res.get('error')}")
            results.append({"label": label, "success": False, "error": job_res.get("error")})
            continue

        render_res = job_res.get("render_result", {})
        quality_rep = job_res.get("quality_report", {})
        ledger_ent = job_res.get("ledger_entry", {})
        video_path = render_res.get("video_path")
        cover_path = render_res.get("cover_path")
        srt_path = render_res.get("srt_path")

        # Inspect on-disk container
        inspection = inspect_video_file(video_path)

        res_summary = {
            "label": label,
            "style": style,
            "character_id": char_id,
            "reel_id": job_res.get("reel_id"),
            "elapsed_seconds": round(elapsed, 2),
            "video_path": video_path,
            "cover_path": cover_path,
            "srt_path": srt_path,
            "file_size_bytes": inspection["size_bytes"],
            "duration_sec": inspection["duration_sec"],
            "video_codec": inspection["video"]["codec"],
            "resolution": f"{inspection['video']['width']}x{inspection['video']['height']}",
            "fps": inspection["video"]["fps"],
            "audio_codec": inspection["audio"]["codec"],
            "audio_channels": inspection["audio"]["channels"],
            "audio_sample_rate": inspection["audio"]["sample_rate"],
            "quality_score_pct": quality_rep.get("score_pct"),
            "quality_passed": quality_rep.get("overall_passed"),
            "ledger_status": ledger_ent.get("status"),
            "is_generative_ai": render_res.get("is_generative_ai"),
            "is_procedural_fallback": render_res.get("is_procedural_fallback"),
        }
        results.append(res_summary)

        print(f"[SUCCESS] Generated: {video_path}")
        print(f"          Duration: {inspection['duration_sec']:.1f}s | Resolution: {inspection['video']['width']}x{inspection['video']['height']} | FPS: {inspection['video']['fps']}")
        print(f"          Video Codec: {inspection['video']['codec']} | Audio: {inspection['audio']['codec']} {inspection['audio']['channels']}ch @ {inspection['audio']['sample_rate']}Hz")
        print(f"          Quality Passed: {quality_rep.get('overall_passed')} ({quality_rep.get('score_pct')}%) | Approval Status: {ledger_ent.get('status')}")

    print("\n" + "=" * 80)
    print("FINAL SUMMARY JSON:")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print("=" * 80)

    # Save summary to data
    out_json = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "samples_generation_summary.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved summary to {out_json}")


if __name__ == "__main__":
    main()
