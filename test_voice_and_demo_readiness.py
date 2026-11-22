"""
Verification test for:
1. Natural Hindi/Hinglish/English Prompt Configuration
2. 'Hello Jarvis' and 'Hey Jarvis' Wake-Word Detector Tuning
3. Faster-Whisper Local STT on D: Drive
4. Audio Transcribe Endpoint in Server
5. Dashboard Voice & Host Status Reconnection
6. Wake-on-LAN Information & Truthful Constraints
7. Instagram Growth Manager Designated Account
"""
import os
import sys
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
VENV_PYTHON = Path(r"D:\JARVIS-AI\.venv-jarvis\Scripts\python.exe")

def test_prompt_conversational_nature():
    prompt_path = BASE_DIR / "core" / "prompt.txt"
    assert prompt_path.exists(), "prompt.txt must exist"
    content = prompt_path.read_text(encoding="utf-8")
    assert "friendly, helpful, and natural personal assistant" in content, "Voice section missing friendly natural prompt"
    assert "HINGLISH: Respond in natural, everyday conversational Hinglish" in content or "Hinglish: Respond in natural, everyday conversational Hinglish" in content, "Hinglish instructions missing"
    assert "AUTO-DETECT" in content, "Auto-detect language missing"
    print("[PASS] Test 1: Natural Hindi/Hinglish/English prompt verified.")

def test_wake_word_tuning():
    import core.wake_word as ww
    assert ww.DEFAULT_THRESHOLD == 0.35, f"Expected threshold 0.35 for Hello/Hey Jarvis, got {ww.DEFAULT_THRESHOLD}"
    assert ww.WAKE_MODEL == "hey_jarvis", "Wake model should be hey_jarvis"
    assert ww.is_installed(), "openwakeword should be installed"
    assert ww.is_ready(), "openwakeword models should be ready"
    print("[PASS] Test 2: Wake-word detector tuned for 'Hello Jarvis' / 'Hey Jarvis' with auto-gain.")

def test_whisper_local_on_d():
    from faster_whisper import WhisperModel
    from core.path_manager import get_whisper_models_dir
    whisper_dir = get_whisper_models_dir()
    assert whisper_dir.exists(), f"whisper_models dir must exist at {whisper_dir}"
    model = WhisperModel("base", device="cpu", compute_type="int8", download_root=str(whisper_dir))
    assert model is not None, "Failed to load WhisperModel"
    print(f"[PASS] Test 3: Local Faster-Whisper loaded successfully from {whisper_dir}.")

def test_server_transcribe_endpoint():
    server_path = BASE_DIR / "dashboard" / "server.py"
    content = server_path.read_text(encoding="utf-8")
    assert "/api/audio/transcribe" in content, "Endpoint /api/audio/transcribe missing in server.py"
    assert "WhisperModel" in content, "WhisperModel transcription missing in server.py"
    assert "should_execute" in content, "Execution flag missing in server.py"
    print("[PASS] Test 4: Server /api/audio/transcribe endpoint registered.")

def test_dashboard_ui_features():
    html_path = BASE_DIR / "dashboard" / "static" / "app.html"
    content = html_path.read_text(encoding="utf-8")
    assert 'id="voice-record-inp"' in content, "Hidden voice record input missing in app.html"
    assert '_onVoiceRecordFile' in content, "Voice record file handler missing in app.html"
    assert 'HOST SLEEPING / UNREACHABLE' in content, "Host sleeping state missing in app.html"
    assert 'HOST OFFLINE' in content, "Host offline state missing in app.html"
    assert 'id="wol-info-modal"' in content, "Wake-on-LAN info modal missing in app.html"
    assert '28-0C-50-EF-86-98' in content, "Laptop MAC address missing in WoL modal"
    print("[PASS] Test 5: Dashboard UI voice fallback, truthful host states, and WoL modal verified.")

def test_instagram_designated_account():
    from core.instagram_manager import instagram_manager
    raw_accounts = instagram_manager.list_accounts()
    accounts = {acc["username"]: acc for acc in raw_accounts}
    assert "mentos_life_gym" in accounts, "@mentos_life_gym must be present"
    acc = accounts["mentos_life_gym"]
    assert acc.get("designated_reels") is True, "@mentos_life_gym must be designated reels account"
    assert acc.get("status") in ("CONNECTED", "AUTHORIZATION_REQUIRED", "UNVERIFIED_BY_META"), f"Status must be truthful CONNECTED, AUTHORIZATION_REQUIRED, or UNVERIFIED_BY_META, got {acc.get('status')}"
    print("[PASS] Test 6: Instagram designated account @mentos_life_gym confirmed.")

def test_d_drive_paths():
    from core.path_manager import validate_installation_path, get_app_root, get_whisper_models_dir
    app_root = get_app_root()
    valid, msg = validate_installation_path(app_root)
    assert valid, f"Installation path validation failed: {msg}"
    if Path("D:/JARVIS-AI").exists():
        assert Path(r"D:\JARVIS-AI\Ollama\ollama.exe").is_file(), "Ollama exe missing on D:"
        assert Path(r"D:\JARVIS-AI\whisper_models").is_dir(), "Whisper models missing on D:"
    print(f"[PASS] Test 7: Universal J.A.R.V.I.S. installation paths verified ({app_root.drive or 'Current'}).")

if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING VOICE, WAKE-WORD, OFFLINE & DEMO READINESS SUITE")
    print("=" * 70)
    test_prompt_conversational_nature()
    test_wake_word_tuning()
    test_whisper_local_on_d()
    test_server_transcribe_endpoint()
    test_dashboard_ui_features()
    test_instagram_designated_account()
    test_d_drive_paths()
    print("=" * 70)
    print("ALL 7/7 READINESS VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)
