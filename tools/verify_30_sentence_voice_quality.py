"""
tools/verify_30_sentence_voice_quality.py — Empirical Audio Generation & Latency Benchmark

Generates 30 Hindi, Hinglish, and English benchmark sentences across all 5 female profiles:
1. SWARA_HINDI (EdgeTTS Neural)
2. NEERJA_INDIAN_EN (EdgeTTS Neural)
3. AVA_MODERN_EN (EdgeTTS Neural)
4. SONIA_BRITISH_EN (EdgeTTS Neural)
5. ZIRA_OFFLINE (Windows SAPI5 Offline)

Saves all 150 WAV recordings to D:\JARVIS-AI\mark_lvi_core\test_output\voice_comparison\
and records empirical latencies, audio lengths, and provider identities.
"""

import asyncio
import json
import os
import sys
import time
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


from core.natural_voice_engine import natural_voice_engine

OUTPUT_DIR = PROJECT_ROOT / "test_output" / "voice_comparison"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BENCHMARK_SENTENCES = [
    # ── Category A: Hindi Sentences (Devanagari) ──────────────────────────────
    {"id": 1, "lang": "hindi", "text": "नमस्ते! मैं जार्विस हूँ, आपकी पर्सनल एआई साथी।"},
    {"id": 2, "lang": "hindi", "text": "आज का मौसम कैसा है और तापमान कितना रहेगा?"},
    {"id": 3, "lang": "hindi", "text": "कृपया मेरे सिस्टम की रैम और सीपीयू उपयोग की स्थिति बताइए।"},
    {"id": 4, "lang": "hindi", "text": "वर्कस्टेशन पर सुरक्षा ऑडिट शुरू किया जा रहा है।"},
    {"id": 5, "lang": "hindi", "text": "क्या आप कल सुबह सात बजे की मीटिंग का रिमाइंडर सेट कर सकते हैं?"},
    {"id": 6, "lang": "hindi", "text": "यह दस्तावेज़ पूरी तरह से सुरक्षित और एन्क्रिप्टेड है।"},
    {"id": 7, "lang": "hindi", "text": "फ़ाइल को रीसायकल बिन में भेजने से पहले अनुमति आवश्यक है।"},
    {"id": 8, "lang": "hindi", "text": "हमारे पास आज करने के लिए कुल चौदह महत्वपूर्ण कार्य हैं।"},
    {"id": 9, "lang": "hindi", "text": "इंटरनेट कनेक्शन उपलब्ध न होने पर भी सिस्टम ऑफ़लाइन काम करेगा।"},
    {"id": 10, "lang": "hindi", "text": "धन्यवाद! आपका दिन मंगलमय और उत्पादक हो।"},

    # ── Category B: Hinglish Sentences (Code-Switching) ────────────────────────
    {"id": 11, "lang": "hinglish", "text": "Jarvis, workstation ka complete status check karke batao."},
    {"id": 12, "lang": "hinglish", "text": "Mera kal subah 9:30 AM ka gym schedule kya hai?"},
    {"id": 13, "lang": "hinglish", "text": "Bhai, code me syntax error aa raha hai, please check karo."},
    {"id": 14, "lang": "hinglish", "text": "Reels ledger me total 74 posts verify ho chuki hain."},
    {"id": 15, "lang": "hinglish", "text": "WhatsApp par naya message draft karo aur mujhe preview dikhao."},
    {"id": 16, "lang": "hinglish", "text": "System volume 70 percent par set kar dijiye."},
    {"id": 17, "lang": "hinglish", "text": "Yeh document summarize karo aur main points highlight karo."},
    {"id": 18, "lang": "hinglish", "text": "Device successfully pair ho gaya hai, connection secure hai."},
    {"id": 19, "lang": "hinglish", "text": "Haan theek hai, consequential action approve kar do."},
    {"id": 20, "lang": "hinglish", "text": "Sab kuch ready hai, hum agle step par proceed kar sakte hain."},

    # ── Category C: English Sentences ─────────────────────────────────────────
    {"id": 21, "lang": "english", "text": "Good morning, sir. All core systems and local background monitors are operational."},
    {"id": 22, "lang": "english", "text": "The current memory utilization is at forty-two percent across eight gigabytes of RAM."},
    {"id": 23, "lang": "english", "text": "Live web search returned three authoritative sources from verified research portals."},
    {"id": 24, "lang": "english", "text": "I have paused audio playback immediately to hear your instruction."},
    {"id": 25, "lang": "english", "text": "A confirmation prompt has been dispatched to your primary workstation screen."},
    {"id": 26, "lang": "english", "text": "The local Ollama inference engine is active on loopback port eleven four thirty-four."},
    {"id": 27, "lang": "english", "text": "Would you like me to schedule a persistent reminder for tomorrow evening?"},
    {"id": 28, "lang": "english", "text": "The cryptographic key has been encrypted using native Windows DPAPI protocols."},
    {"id": 29, "lang": "english", "text": "Standby mode active; listening locally for the Hey Jarvis wake phrase."},
    {"id": 30, "lang": "english", "text": "J.A.R.V.I.S. Mark LVI is ready to assist you across all thirteen integrated modules."}
]

VOICE_PERSONAS = [
    "SWARA_HINDI",
    "NEERJA_INDIAN_EN",
    "AVA_MODERN_EN",
    "SONIA_BRITISH_EN",
    "ZIRA_OFFLINE"
]


async def run_benchmark():
    print("=" * 80)
    print("J.A.R.V.I.S. MARK LVI — 30-SENTENCE MULTILINGUAL VOICE BENCHMARK")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 80)

    results = {}
    total_syntheses = len(VOICE_PERSONAS) * len(BENCHMARK_SENTENCES)
    completed = 0

    for voice_id in VOICE_PERSONAS:
        results[voice_id] = {
            "profile": natural_voice_engine._get_voice_profile(voice_id),
            "samples": [],
            "latencies_ms": [],
            "durations_s": [],
            "failures": 0
        }
        print(f"\n>> Benchmarking Voice: {voice_id} ...")

        for item in BENCHMARK_SENTENCES:
            sid = item["id"]
            lang = item["lang"]
            text = item["text"]
            file_name = f"{voice_id}_{sid:02d}_{lang}.wav"
            file_path = OUTPUT_DIR / file_name

            t0 = time.perf_counter()
            try:
                res = await natural_voice_engine.synthesize_chunk_async(text, voice_id=voice_id)
                t1 = time.perf_counter()
                latency_ms = round((t1 - t0) * 1000, 2)

                if res.audio_bytes_wav and len(res.audio_bytes_wav) >= 44:
                    with open(file_path, "wb") as f:
                        f.write(res.audio_bytes_wav)

                    file_size = len(res.audio_bytes_wav)
                    results[voice_id]["latencies_ms"].append(latency_ms)
                    results[voice_id]["durations_s"].append(res.duration_sec)
                    results[voice_id]["samples"].append({
                        "id": sid,
                        "lang": lang,
                        "text": text,
                        "file": str(file_path),
                        "file_size_bytes": file_size,
                        "duration_sec": round(res.duration_sec, 2),
                        "latency_ms": latency_ms,
                        "voice_used": res.voice_used,
                        "is_offline": res.is_offline,
                        "success": True
                    })
                else:
                    results[voice_id]["failures"] += 1
                    results[voice_id]["samples"].append({
                        "id": sid,
                        "lang": lang,
                        "text": text,
                        "file": None,
                        "latency_ms": latency_ms,
                        "success": False,
                        "error": "Empty audio output"
                    })
            except Exception as e:
                t1 = time.perf_counter()
                results[voice_id]["failures"] += 1
                results[voice_id]["samples"].append({
                    "id": sid,
                    "lang": lang,
                    "text": text,
                    "file": None,
                    "latency_ms": round((t1 - t0) * 1000, 2),
                    "success": False,
                    "error": str(e)
                })

            completed += 1
            if completed % 10 == 0 or completed == total_syntheses:
                print(f"  Progress: {completed}/{total_syntheses} ({completed*100//total_syntheses}%)")

    # Statistical compilation
    summary_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_syntheses": total_syntheses,
        "total_completed": completed,
        "profiles": {}
    }

    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY BY VOICE PROFILE:")
    print(f"{'Profile':<20} | {'Count':<5} | {'Failures':<8} | {'Min (ms)':<8} | {'Avg (ms)':<8} | {'Max (ms)':<8}")
    print("-" * 80)

    for vid in VOICE_PERSONAS:
        vdata = results[vid]
        lats = vdata["latencies_ms"]
        fails = vdata["failures"]
        min_lat = min(lats) if lats else 0
        max_lat = max(lats) if lats else 0
        avg_lat = round(sum(lats) / len(lats), 2) if lats else 0

        summary_report["profiles"][vid] = {
            "name": vdata["profile"].get("name", vid),
            "system_voice": vdata["profile"].get("system_voice"),
            "is_offline": vdata["profile"].get("is_offline", False),
            "is_neural": vdata["profile"].get("is_neural", False),
            "samples_generated": len(lats),
            "failures": fails,
            "min_latency_ms": min_lat,
            "avg_latency_ms": avg_lat,
            "max_latency_ms": max_lat,
            "samples": vdata["samples"]
        }
        print(f"{vid:<20} | {len(lats):<5} | {fails:<8} | {min_lat:<8} | {avg_lat:<8} | {max_lat:<8}")

    print("=" * 80)

    # Save complete JSON
    json_path = OUTPUT_DIR / "voice_benchmark_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2, ensure_ascii=False)
    print(f"\nDetailed benchmark JSON saved to: {json_path}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
