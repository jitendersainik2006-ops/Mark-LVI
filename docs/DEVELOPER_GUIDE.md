# J.A.R.V.I.S. Mark LVI — Developer & Extension Guide

This guide is intended for developers extending J.A.R.V.I.S. Mark LVI Core.

---

## 1. Codebase Architecture & Structure

```text
mark_lvi_core/
├── actions/             # Discovered skill tools (file control, apps, calendar, email, etc.)
├── config/              # Configuration (api_keys.json, icon, named tunnel YAML)
├── core/                # Core subsystems (avatar, audio, ollama, memory, knowledge, agent)
├── dashboard/           # FastAPI backend server & static web assets (server.py, app.html)
├── data/                # Local persistent data stores (reels ledger, accounts, memory)
├── installer/           # Windows installer, setup wizard, and packaging scripts
├── memory/              # Memory manager & configuration manager
├── providers/           # Modular STT, TTS, and LLM backends (Ollama/Whisper/Piper/SAPI)
├── reports/             # System audit and verification reports
├── tests/               # Regression test battery (unittest test_*.py)
├── tools/               # Hardened reverse proxy & tunnel orchestrators
├── main.py              # Main assistant orchestrator
└── ui.py                # PyQt6 desktop HUD & 3D wireframe avatar
```

---

## 2. Adding a New Skill / Tool

J.A.R.V.I.S. uses auto-discovery via `core/action_loader.py`. To add a new skill:
1. Create a new Python file in `actions/` (e.g. `actions/my_custom_tool.py`).
2. Define the handler callable and the module-level `TOOL` dictionary:

```python
"""actions/my_custom_tool.py — Example custom J.A.R.V.I.S. skill."""

def my_custom_handler(parameters: dict, player=None, **_) -> str:
    target = parameters.get("target", "world")
    return f"Processed custom action for: {target}"

TOOL = {
    "name": "my_custom_tool",
    "description": "Performs a custom action on the user's machine.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "target": {"type": "STRING", "description": "Target entity to process."}
        },
        "required": ["target"],
    },
    "handler": my_custom_handler,
    "tier": "extra",  # "core" or "extra"
}
```

3. J.A.R.V.I.S. will auto-discover the tool at startup without modifying `main.py`.

---

## 3. Extending Voice & AI Providers

All speech and language providers implement the contract defined in `providers/base.py`:
- **STT Providers:** Inherit from `STTProvider` and implement `transcribe_stream(pcm_stream)` or `transcribe_bytes(wav_bytes)`.
- **LLM Providers:** Inherit from `LLMProvider` and implement `chat_stream(messages, tools, on_tool_call)`.
- **TTS Providers:** Inherit from `TTSProvider` and implement `synthesize(text, voice_options)`.

---

## 4. Running the Test Suite

J.A.R.V.I.S. includes a comprehensive 76-test regression suite. Run tests from project root:

```powershell
& "D:\JARVIS-AI\.venv-jarvis\Scripts\python.exe" C:\Users\jitendersaini2006\.gemini\antigravity\brain\e7bc7937-0d61-4942-83c4-b3f5a9674d30\scratch\run_tests.py
```

All 8 test suites must pass with 0 failures before proposing any release changes.
