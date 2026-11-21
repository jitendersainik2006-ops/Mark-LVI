"""
test_e2e_integration.py — End-to-End Verification Suite for J.A.R.V.I.S. Smart Personal AI Assistant

Validates:
1. Multi-turn context & conversational reasoning with Ollama Qwen2.5:3b (OpenAICompatLLM)
2. Persistent Personal Memory integration (CRUD, source tracking, credential gating, prompt injection)
3. Background Task Manager & Execution Engine (lifecycle, approval gating, deduplication, sync)
4. Priority Feminine Voice (Microsoft Zira Desktop) synthesis for English, Hinglish, and Hindi (Devanagari transliteration)
5. Dashboard Audio Delivery endpoint GET /api/audio/{audio_id} (Bearer auth gating, WAV delivery)
6. On-demand POST /api/tts endpoint (Bearer auth gating, audio cache generation)
7. Faster-Whisper local STT transcription from 16kHz PCM audio
8. Single-instance process enforcement and port/daemon health check
"""

import asyncio
import os
import sys
import json
import time
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_async(coro):
    return asyncio.run(coro)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Multi-Turn Context & Conversational Reasoning with Ollama Qwen2.5:3b
# ─────────────────────────────────────────────────────────────────────────────
def test_1_conversational_reasoning():
    print("\n--- TEST 1: Conversational Multi-Turn Context & Reasoning (Qwen2.5:3b) ---")
    from providers.llm_openai import OpenAICompatLLM

    llm = OpenAICompatLLM({
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:3b",
        "timeout": 60.0,
    })

    # Multi-turn conversation
    messages = [
        {"role": "system", "content": "You are JARVIS, an intelligent and polite personal AI assistant."},
        {"role": "user", "content": "My primary programming language is Rust, and my secret code phrase is Crimson Falcon."},
        {"role": "assistant", "content": "Understood, Sir. I have noted that your primary programming language is Rust and your secret code phrase is Crimson Falcon."},
        {"role": "user", "content": "What is my primary programming language and what is my secret code phrase?"},
    ]

    t0 = time.time()
    reply, tool_calls = llm.complete(messages)
    elapsed = time.time() - t0

    assert reply, "Received empty response from local Qwen model"
    reply_lower = reply.lower()
    print(f"Qwen response ({elapsed:.2f}s): {reply.strip()}")

    assert "rust" in reply_lower, f"Model failed multi-turn recall for 'Rust': {reply}"
    assert "crimson falcon" in reply_lower or ("crimson" in reply_lower and "falcon" in reply_lower), \
        f"Model failed multi-turn recall for 'Crimson Falcon': {reply}"

    # Multilingual Hinglish query
    messages_hinglish = [
        {"role": "system", "content": "You are JARVIS. Answer politely in Hinglish."},
        {"role": "user", "content": "Jarvis, kal subah 7 baje ka alarm yaad rakhna. Aap kaise ho?"},
    ]
    reply_hinglish, _ = llm.complete(messages_hinglish)
    assert reply_hinglish, "Empty Hinglish response"
    print(f"Hinglish response: {reply_hinglish.strip()}")

    print("✅ TEST 1 PASSED: Multi-turn context retained and Hinglish query answered cleanly.")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Persistent Personal Memory Integration (CRUD + Gating + Credential Redaction)
# ─────────────────────────────────────────────────────────────────────────────
def test_2_personal_memory():
    print("\n--- TEST 2: Persistent Personal Memory Integration ---")
    import memory.memory_manager as mm

    temp_mem = Path(tempfile.gettempdir()) / "test_e2e_memory.json"
    if temp_mem.exists():
        try: temp_mem.unlink()
        except: pass
    mm.MEMORY_PATH = temp_mem

    from memory.memory_manager import (
        contains_credentials,
        redact_credentials,
        is_memory_enabled,
        set_memory_enabled,
        remember,
        search_memory,
        edit_memory,
        delete_memory,
        all_entries_for_ui,
        format_memory_for_prompt,
        load_memory,
    )

    set_memory_enabled(True)

    # 1. Credential detection & redaction
    assert contains_credentials("sk-proj-abc1234567890abcdef1234567890"), "Failed to detect API key"
    assert contains_credentials("password = hunter2password!"), "Failed to detect password"
    assert not contains_credentials("My favorite beverage is Earl Grey tea"), "False positive on beverage"

    redacted = redact_credentials("My API key is AIzaSyD123456789012345678901234567890 for testing.")
    assert "[REDACTED_CREDENTIAL]" in redacted, "Credential was not redacted"

    # 2. Store facts
    remember("city", "Bengaluru", category="identity", source="user_fact")
    remember("job", "Systems Architect", category="identity", source="user_fact")
    remember("work_schedule", "Early Bird", category="preferences", source="inferred")

    entries = all_entries_for_ui()
    assert len(entries) == 3, f"Expected 3 memory entries, got {len(entries)}"

    # 3. Prompt formatting
    formatted = format_memory_for_prompt(load_memory())
    assert "Bengaluru" in formatted, "Location missing in prompt block"
    assert "Systems Architect" in formatted, "Role missing in prompt block"
    assert "[unconfirmed assumption]" in formatted, "Inferred tag missing in prompt block"

    # 4. Search and update
    res = search_memory("Bengaluru")
    assert "Bengaluru" in res, "Search failed for Bengaluru"

    ok = edit_memory("identity", "city", "Hyderabad", source="user_fact")
    assert ok, "edit_memory returned False"
    assert "Hyderabad" in search_memory("city"), "Memory edit was not reflected"

    # 5. Delete
    ok_del = delete_memory("identity", "city")
    assert ok_del, "delete_memory returned False"
    assert "Hyderabad" not in search_memory("city"), "Memory delete failed"

    # 6. Toggle
    set_memory_enabled(False)
    assert format_memory_for_prompt(load_memory()) == "", "Memory formatting should be empty when disabled"
    set_memory_enabled(True)

    print("✅ TEST 2 PASSED: Memory CRUD, credential filtering, source tracking, and gating verified.")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Real Task Management & Execution Engine
# ─────────────────────────────────────────────────────────────────────────────
def test_3_task_manager():
    print("\n--- TEST 3: Background Task Manager & Execution Engine ---")
    from core.task_manager import TaskManager

    temp_task_file = Path(tempfile.gettempdir()) / "test_e2e_tasks.json"
    if temp_task_file.exists():
        try: temp_task_file.unlink()
        except: pass

    tm = TaskManager(tasks_file=temp_task_file)

    # 1. Allowlisted task creation
    t_safe = tm.create_task(
        title="Check system health",
        action_name="system_status",
        action_args={},
        priority="medium",
        source="voice",
    )
    assert t_safe.status in ("queued", "completed"), f"Unexpected status: {t_safe.status}"

    # 2. Sensitive non-allowlisted task creation (must enter waiting_for_approval)
    t_sensitive = tm.create_task(
        title="Delete temp files and format cache",
        action_name="delete_file",
        action_args={"path": "/tmp/cache"},
        priority="high",
        source="phone",
    )
    assert t_sensitive.status == "waiting_for_approval", f"Expected waiting_for_approval, got {t_sensitive.status}"

    # 3. Approve task
    ok_appr = tm.approve_task(t_sensitive.id)
    assert ok_appr, "Failed to approve task"
    reloaded = tm.get_task(t_sensitive.id)
    assert reloaded.status in ("queued", "completed"), f"Expected queued/completed after approval, got {reloaded.status}"

    # 4. Deduplication
    t_dup = tm.create_task(title="Check system health", action_name="system_status")
    assert t_dup.id == t_safe.id, "Deduplication did not return existing active task"

    # 5. Cancel task
    t_cancel = tm.create_task(title="Temporary background scan", priority="low")
    ok_c = tm.cancel_task(t_cancel.id)
    assert ok_c, "Failed to cancel task"
    assert tm.get_task(t_cancel.id).status == "cancelled"

    # 6. Serialization
    listed = tm.list_tasks(status="all")
    assert len(listed) >= 2, "Expected at least 2 tasks in list"
    assert all("id" in t.to_dict() for t in listed), "to_dict() missing id"

    print("✅ TEST 3 PASSED: Task creation, allowlisting, approval gate, deduplication, and lifecycle verified.")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Priority Feminine Voice (Microsoft Zira Desktop) Synthesis
# ─────────────────────────────────────────────────────────────────────────────
def test_4_tts_sapi():
    print("\n--- TEST 4: Priority Feminine Voice (Microsoft Zira Desktop) ---")
    from providers.tts_system import SystemTTS, list_voices

    voices = list_voices()
    print(f"Detected system voices: {voices}")
    assert any("Zira" in v for v in voices), f"Microsoft Zira Desktop not found in {voices}"

    tts = SystemTTS({"voice": "Microsoft Zira Desktop", "rate": 0})

    # 1. English synthesis
    wav_en = tts._synth_blocking("Good day, Sir. All Mark-LVI systems are currently online.")
    assert len(wav_en) > 50_000, f"English audio too small: {len(wav_en)} bytes"
    assert wav_en[:4] == b"RIFF" and wav_en[8:12] == b"WAVE", "English audio is not a valid WAV file"
    print(f"English audio generated: {len(wav_en):,} bytes")

    # 2. Hinglish synthesis
    wav_hinglish = tts._synth_blocking("Haanji Sir, sabhi local services bilkul theek chal rahi hain.")
    assert len(wav_hinglish) > 50_000, f"Hinglish audio too small: {len(wav_hinglish)} bytes"
    assert wav_hinglish[:4] == b"RIFF" and wav_hinglish[8:12] == b"WAVE", "Hinglish audio is not a valid WAV file"
    print(f"Hinglish audio generated: {len(wav_hinglish):,} bytes")

    # 3. Devanagari Hindi transliterated synthesis
    wav_hindi = tts._synth_blocking("नमस्ते सर, मैं जार्विस हूँ। आपकी क्या सहायता करूँ?")
    assert len(wav_hindi) > 50_000, f"Devanagari audio too small (SAPI silence bug): {len(wav_hindi)} bytes"
    assert wav_hindi[:4] == b"RIFF" and wav_hindi[8:12] == b"WAVE", "Hindi audio is not a valid WAV file"
    print(f"Transliterated Devanagari Hindi audio generated: {len(wav_hindi):,} bytes")

    print("✅ TEST 4 PASSED: Microsoft Zira Desktop successfully synthesized English, Hinglish, and Hindi.")
    return wav_en


# ─────────────────────────────────────────────────────────────────────────────
# 5 & 6. Dashboard Audio Delivery & On-Demand TTS Endpoints
# ─────────────────────────────────────────────────────────────────────────────
def test_5_and_6_dashboard_audio(sample_wav: bytes):
    print("\n--- TEST 5 & 6: Dashboard Audio Delivery & On-Demand TTS ---")
    from dashboard.server import DashboardServer
    from fastapi.testclient import TestClient

    server = DashboardServer()
    client = TestClient(server.app)

    # Generate valid pairing session token
    key = server.new_key(600)
    login_resp = client.post("/login", json={"pin": key})
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Store sample WAV in cache
    audio_id = server.store_audio(sample_wav)
    assert audio_id.startswith("aud_"), f"Unexpected audio_id format: {audio_id}"

    # TEST 5: GET /api/audio/{audio_id}
    # 1. Unauthorized access (no token) -> 401
    r_unauth = client.get(f"/api/audio/{audio_id}")
    assert r_unauth.status_code == 401, f"Expected 401 Unauthorized, got {r_unauth.status_code}"

    # 2. Authorized access -> 200 with audio/wav
    r_auth = client.get(f"/api/audio/{audio_id}", headers=headers)
    assert r_auth.status_code == 200, f"Expected 200 OK, got {r_auth.status_code}"
    assert r_auth.headers.get("content-type") == "audio/wav", f"Expected audio/wav, got {r_auth.headers.get('content-type')}"
    assert r_auth.content[:4] == b"RIFF", "Invalid WAV header in retrieved audio"
    assert len(r_auth.content) == len(sample_wav), "Retrieved audio byte length mismatch"

    # 3. Invalid audio_id -> 404
    r_404 = client.get("/api/audio/aud_nonexistent123", headers=headers)
    assert r_404.status_code == 404, f"Expected 404 for missing audio, got {r_404.status_code}"
    print("✅ TEST 5 PASSED: GET /api/audio/{audio_id} correctly enforces Bearer auth and delivers WAV bytes.")

    # TEST 6: POST /api/tts
    # 1. Unauthorized access -> 401
    r_tts_unauth = client.post("/api/tts", json={"text": "Test phrase"})
    assert r_tts_unauth.status_code == 401, f"Expected 401, got {r_tts_unauth.status_code}"

    # 2. Authorized access -> 200 with audio_id
    r_tts = client.post("/api/tts", json={"text": "Dashboard TTS verification successful."}, headers=headers)
    assert r_tts.status_code == 200, f"Expected 200 OK, got {r_tts.status_code}: {r_tts.text}"
    tts_data = r_tts.json()
    assert tts_data.get("ok") is True, f"TTS generation failed: {tts_data}"
    new_aud_id = tts_data.get("audio_id")
    assert new_aud_id and new_aud_id.startswith("aud_"), f"Missing or invalid audio_id: {new_aud_id}"

    # Verify that the generated audio exists and is retrievable
    r_fetch_new = client.get(f"/api/audio/{new_aud_id}", headers=headers)
    assert r_fetch_new.status_code == 200, "Could not fetch audio produced by /api/tts"
    assert len(r_fetch_new.content) > 30_000, "Produced TTS audio is unexpectedly small"
    print("✅ TEST 6 PASSED: POST /api/tts correctly synthesizes audio on-demand with Bearer auth.")


# ─────────────────────────────────────────────────────────────────────────────
# 7. Faster-Whisper Local STT Transcription from 16kHz PCM
# ─────────────────────────────────────────────────────────────────────────────
def test_7_whisper_stt(sample_wav: bytes):
    print("\n--- TEST 7: Faster-Whisper Local STT Transcription ---")
    from providers.stt_whisper import WhisperSTT
    from providers import audio

    whisper = WhisperSTT({
        "backend": "local",
        "model": "base",
        "device": "cpu",
        "download_root": "D:\\JARVIS-AI\\whisper_models",
    })

    # Convert our synthesized WAV into 16kHz mono PCM (the format captured by microphone)
    pcm_data = audio.wav_to_pcm(sample_wav, 16000)
    assert len(pcm_data) > 0, "Failed to convert WAV to 16kHz PCM"
    print(f"Converted PCM length: {len(pcm_data):,} bytes (16kHz mono)")

    # Run local transcription
    transcript = run_async(whisper.transcribe(pcm_data))
    print(f"Whisper transcription: '{transcript}'")
    assert transcript, "Faster-Whisper returned empty transcription"
    # Check that key words were recognized
    trans_lower = transcript.lower()
    assert any(w in trans_lower for w in ["systems", "mark", "online", "good", "systems are"]), \
        f"Transcription did not match expected audio content: '{transcript}'"

    print("✅ TEST 7 PASSED: Faster-Whisper loaded locally and transcribed PCM audio accurately.")


# ─────────────────────────────────────────────────────────────────────────────
# 8. Single-Instance Enforcement & Port/Daemon Health
# ─────────────────────────────────────────────────────────────────────────────
def test_8_single_instance_and_health():
    print("\n--- TEST 8: Single-Instance Enforcement & Port/Daemon Health ---")
    import psutil
    from main import _enforce_single_instance

    # Test that _enforce_single_instance runs without error
    _enforce_single_instance()

    # Verify Ollama daemon is running on 127.0.0.1:11434
    req = urllib.request.Request("http://127.0.0.1:11434/v1/models")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200, f"Ollama HTTP returned status {resp.status}"
        data = json.loads(resp.read().decode("utf-8"))
        models = [m.get("id") for m in data.get("data", [])]
        assert any("qwen2.5:3b" in m for m in models), f"qwen2.5:3b not listed in Ollama models: {models}"
        print(f"Ollama health check OK: qwen2.5:3b online ({len(models)} models available)")

    print("✅ TEST 8 PASSED: Single-instance logic healthy and Ollama server verified on 127.0.0.1:11434.")


def main():
    print("=" * 70)
    print("  J.A.R.V.I.S. SMART ASSISTANT END-TO-END VERIFICATION SUITE")
    print("=" * 70)

    test_1_conversational_reasoning()
    test_2_personal_memory()
    test_3_task_manager()
    sample_wav = test_4_tts_sapi()
    test_5_and_6_dashboard_audio(sample_wav)
    test_7_whisper_stt(sample_wav)
    test_8_single_instance_and_health()

    print("\n" + "=" * 70)
    print("  🎉 ALL 8 COMPREHENSIVE END-TO-END INTEGRATION TESTS PASSED!")
    print("=" * 70)


if __name__ == "__main__":
    main()
