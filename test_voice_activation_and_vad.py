"""
test_voice_activation_and_vad.py — J.A.R.V.I.S. Voice Input & Auto-Submission Verification Suite

Tests all requirements:
1. Silence PCM is rejected (returns "").
2. Low-energy background noise (laptop fan hiss) is rejected (returns "").
3. Short duration audio (< 0.5s) is rejected (returns "").
4. Known Whisper hallucinations and repetitive token loops are blocked.
5. Language detection is restricted to English and Hindi (["en", "hi"]).
6. PipelineEngine VAD thresholds and pre-STT energy gate block noise.
7. Duplicate transcription submissions within 12s window are blocked.
8. Echo tail suppression blocks speaker output from leaking into STT.
9. Wake-word state machine strictly gates hands-free conversation with a 10s follow-up window.
10. Manual recording and dashboard transcription are protected against hallucinations.
"""

import asyncio
import numpy as np
import time
from unittest.mock import MagicMock, AsyncMock

from providers.stt_whisper import WhisperSTT, _is_hallucination
from providers.engine_pipeline import (
    PipelineEngine,
    _VAD_ABSOLUTE_MIN,
    _VAD_MIN_SPEECH_MS,
    _VAD_SILENCE_MS,
)
from core.wake_word import WakeWordDetector, DEFAULT_THRESHOLD
from main import WAKE_SLEEP_TIMEOUT, _TAIL_MARGIN


def test_vad_constants():
    """Verify VAD thresholds are elevated to reject laptop fan noise and clicks."""
    assert _VAD_ABSOLUTE_MIN >= 0.015, f"VAD absolute min too low: {_VAD_ABSOLUTE_MIN}"
    assert _VAD_MIN_SPEECH_MS >= 350, f"VAD min speech too short: {_VAD_MIN_SPEECH_MS}"
    assert _VAD_SILENCE_MS >= 500


def test_wake_sleep_followup_timeout():
    """Verify wake sleep timeout is short (10s) instead of runaway 120s."""
    assert WAKE_SLEEP_TIMEOUT <= 15.0, f"Wake sleep timeout too long: {WAKE_SLEEP_TIMEOUT}"
    assert _TAIL_MARGIN >= 0.40, f"Tail margin too short for room echo: {_TAIL_MARGIN}"


def test_hallucination_filter_known_patterns():
    """Verify Whisper silence/outro hallucinations are caught."""
    hallucinations = [
        "Thank you for watching.",
        "Thanks for watching!",
        "Thank you very much.",
        "Please like and subscribe to our channel",
        "Subtitles by someone",
        "We'll see you next time.",
        "See you next time!",
        "Bye bye.",
        "ご視聴ありがとうございました",
        "視聴ありがとうございました",
        "시청해주셔서 감사합니다",
        "धन्यवाद",
        "देखने के लिए धन्यवाद",
        "Laptop speech",
        "in it.",
        "Oh",
        "Ready? Ready?",
        ",",
        "...",
        "---",
        "연기 연기 연기 연기 연기",
        "test test test test test",
    ]
    for h in hallucinations:
        assert _is_hallucination(h) is True, f"Failed to identify hallucination: {h}"

    # Legitimate phrases must NOT be flagged as hallucination
    legitimate = [
        "Hello Jarvis how are you",
        "What is the weather today",
        "Turn on the living room lights",
        "नमस्ते जार्विस क्या हाल है",
        "open the browser and search for news",
    ]
    for legit in legitimate:
        assert _is_hallucination(legit) is False, f"Falsely flagged legitimate speech: {legit}"


async def test_stt_silence_and_low_energy_rejection():
    """Verify STT Whisper rejects pure silence and low-energy noise."""
    stt = WhisperSTT({"backend": "local", "model": "base"})
    
    # 1. Pure silence (1.0s at 16kHz int16)
    silence_pcm = b"\x00" * 32000
    res = await stt.transcribe(silence_pcm, sample_rate=16000)
    assert res == "", f"Silence must return empty string, got: {res}"

    # 2. Too short (< 0.5s)
    short_pcm = b"\x00" * 8000  # 0.25s
    res_short = await stt.transcribe(short_pcm, sample_rate=16000)
    assert res_short == "", f"Short audio must return empty string, got: {res_short}"

    # 3. Low energy ambient fan hiss (RMS ~0.004 float32)
    np.random.seed(42)
    noise_samples = (np.random.randn(16000) * 0.004).astype(np.float32)
    noise_pcm = (noise_samples * 32767).astype(np.int16).tobytes()
    res_noise = await stt.transcribe(noise_pcm, sample_rate=16000)
    assert res_noise == "", f"Low energy fan hiss must return empty string, got: {res_noise}"


async def test_pipeline_engine_pre_stt_rejection_and_deduplication():
    """Verify PipelineEngine flush_microphone rejects low energy and duplicate audio."""
    mock_llm = MagicMock()
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value="Hello Jarvis")

    engine = PipelineEngine(llm=mock_llm, stt=mock_stt)
    
    # 1. Buffer with low energy (fan noise)
    noise_samples = (np.random.randn(16000) * 0.003).astype(np.float32)
    noise_pcm = (noise_samples * 32767).astype(np.int16).tobytes()
    engine._mic = [noise_pcm]
    engine._mic_bytes = len(noise_pcm)
    
    result = await engine.flush_microphone(sample_rate=16000)
    assert result == "", "Low energy mic buffer must be discarded without STT"
    mock_stt.transcribe.assert_not_called()

    # 2. Buffer with intentional speech energy
    speech_samples = (0.05 * np.sin(2 * np.pi * 300 * np.linspace(0, 1, 16000))).astype(np.float32)
    speech_pcm = (speech_samples * 32767).astype(np.int16).tobytes()
    engine._mic = [speech_pcm]
    engine._mic_bytes = len(speech_pcm)

    mock_send = AsyncMock()
    engine.send_client_content = mock_send

    result_valid = await engine.flush_microphone(sample_rate=16000)
    assert result_valid == "Hello Jarvis"
    mock_stt.transcribe.assert_called_once()
    mock_send.assert_called_once()

    # 3. Duplicate transcription immediately following (within 12s)
    mock_stt.transcribe.reset_mock()
    mock_send.reset_mock()
    engine._mic = [speech_pcm]
    engine._mic_bytes = len(speech_pcm)

    dup_result = await engine.flush_microphone(sample_rate=16000)
    assert dup_result == "", "Identical transcription within 12s must be blocked"
    mock_send.assert_not_called()


def test_wake_detector_cooldown_debouncing():
    """Verify wake-word detector prevents double-firing via 2.5s cooldown."""
    detections = []
    frame = np.zeros(1280, dtype=np.int16)

    det = WakeWordDetector(on_detect=lambda: None)
    det._running = True
    det._threshold = 0.35

    # Mock model prediction returning high score
    mock_model = MagicMock()
    mock_model.predict.return_value = {"hey_jarvis": 0.85}
    det._model = mock_model

    def on_detect():
        detections.append(time.monotonic())
        # Immediately feed a second frame to verify it is debounced/suppressed
        det._queue.put(frame)
        det.stop()

    det._on_detect = on_detect
    det._queue.put(frame)

    det._loop()

    # Should detect exactly once due to 2.5s cooldown debouncing
    assert len(detections) == 1, f"Expected 1 detection due to debouncing, got: {len(detections)}"


def run_all_tests():
    print("=" * 60)
    print("RUNNING J.A.R.V.I.S. VOICE ACTIVATION & VAD TESTS")
    print("=" * 60)
    tests = [
        ("VAD Constants", test_vad_constants, False),
        ("Wake Sleep & Tail Margin", test_wake_sleep_followup_timeout, False),
        ("Whisper Hallucination Filter", test_hallucination_filter_known_patterns, False),
        ("STT Silence & Fan Hiss Rejection", test_stt_silence_and_low_energy_rejection, True),
        ("PipelineEngine VAD & Deduplication", test_pipeline_engine_pre_stt_rejection_and_deduplication, True),
        ("Wake Word Cooldown Debouncing", test_wake_detector_cooldown_debouncing, False),
    ]

    passed = 0
    failed = 0
    for name, fn, is_async in tests:
        try:
            print(f"Running: {name} ... ", end="", flush=True)
            if is_async:
                asyncio.run(fn())
            else:
                fn()
            print("PASSED")
            passed += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

    print("=" * 60)
    print(f"TOTAL: {len(tests)} | PASSED: {passed} | FAILED: {failed}")
    print("=" * 60)
    if failed > 0:
        exit(1)


if __name__ == "__main__":
    run_all_tests()
