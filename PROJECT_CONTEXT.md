# J.A.R.V.I.S. MARK LVI — PROJECT CONTEXT & MASTER VISION

## 1. Executive Summary
**J.A.R.V.I.S. Mark LVI** is a private, production-grade, Stonic-inspired personal AI desktop companion, automated multimedia production studio, and intelligent local assistant designed specifically for Windows 10/11 x64 systems.

The system combines:
1. **Unified Persistent Companion Stage:** A sticky HTML5 canvas avatar (60 FPS) and cybernetic status bar visible across ALL workspaces (Chat, Tasks, Memory, Knowledge, Reels, Gmail, Diagnostics, Settings). Features 19 reactive emotion states, lip-sync speech oscillation, auto-blinking, audio energy pulse rings, and wholesome floating petals/hearts for female presentation.
2. **Interactive Desktop Companion Widget:** A draggable, frameless, 60 FPS cybernetic HUD widget (software-rendered via PyQt6) with 19 expressive emotional states, audio-reactive energy rings, and customizable presentations (Male, Female with wholesome motifs, and Neutral).
3. **Local AI & Multi-Voice Engine:** Offline intelligence powered by local Ollama (`qwen2.5:3b` at `http://127.0.0.1:11434`), local Faster-Whisper Speech-to-Text (`D:\JARVIS-AI\whisper_models`), Five Selectable Female Voices (`SWARA_HINDI` default, `NEERJA_INDIAN_EN`, `AVA_MODERN_EN`, `SONIA_BRITISH_EN`, and `ZIRA_OFFLINE`), Windows SAPI5 offline fallback (`Microsoft Zira Desktop` with Devanagari transliteration), Natural Human Conversation Engine (`core/human_conversation_engine.py`) with multilingual auto-detection (Hindi/Hinglish/English), and instant barge-in interruption.
4. **Permission-Controlled Desktop Automation:** Autonomous computer agent (`core/computer_agent.py`) enforcing a strict lifecycle (`PLAN -> PERMISSION -> ACT -> OBSERVE -> VERIFY -> REPORT`) where destructive operations require explicit user approval with secret scrubbing.
5. **Instagram AI Reels Studio:** Production and scheduling engine for automated educational and comedy vertical reels (9:16) with strict two-stage human approval gates, duplicate SHA-256 detection, and assisted / Meta Graph API publishing modes.
6. **Google & Gmail Integration:** Secure OAuth 2.0 companion offering granular scope isolation (basic sign-in strictly quarantined from mailbox access), inbox search/summarization, draft creation, and an unbypassable human-in-the-loop preview-and-confirm gate before any external email is dispatched.
7. **Universal Windows Distribution:** Standalone Inno Setup 6 installer (`JARVIS_Mark_LVI_Setup.exe`) and portable zero-install zip package (`JARVIS_Mark_LVI_Windows_x64_Portable.zip`) with verified process termination, clean uninstaller, and user data retention safeguards.

---

## 2. Environment & System Baselines
- **Primary Working Directory:** `D:\JARVIS-AI\mark_lvi_core`
- **Release Directory:** `D:\JARVIS-AI\release\JARVIS_Mark_LVI_Windows_x64`
- **Verified Pre-Migration Backup:** `D:\JARVIS-AI\backups\backup_pre_unified_humanlike_20261120_154500` (Strictly Preserved)
- **Local LLM Engine:** Ollama (`D:\JARVIS-AI\Ollama\ollama.exe`) serving `qwen2.5:3b` at `127.0.0.1:11434`
- **Local STT Model:** Faster-Whisper base model located at `D:\JARVIS-AI\whisper_models`
- **Dashboard Web Interface:** `http://127.0.0.1:8000/app` (HTTP redirector) / `https://127.0.0.1:8005/app` (TLS)
- **Target Instagram Profile:** `@mentos_life_gym` (Account ID: `17841458094701596`, Meta Status: `UNVERIFIED_BY_META`, Live uploads disabled)

---

## 3. Core Operating Principles & Boundaries
1. **No External Publishing Without Explicit Human Action:** Live social media uploads and email dispatches require physical operator review and single-use confirmation token redemption.
2. **Cryptographic Protection at Rest:** All sensitive tokens (Meta access tokens, Google OAuth refresh tokens, user secrets) are encrypted on disk via Windows DPAPI (`core/crypto_storage.py`). Plaintext credentials are never committed, logged, or serialized to client APIs.
3. **Zero Proprietary Stonic Code/Assets:** All vector animations, UI components, and character meshes are clean-room Python/PyQt6/HTML5 implementations without third-party copyrighted assets.
4. **Multi-User Profile Isolation:** User data, memory, and personal preferences reside strictly within isolated subdirectories (`data/users/<uid>/`).
5. **Strict Process Ownership:** Shutdown and uninstall routines (`stop_jarvis.py`, `uninstall_jarvis.py`) verify Windows PID ownership via executable path match, strictly preventing accidental termination of unrelated system processes on shared ports.
6. **Continuous Barge-In & Listening Integrity:** User voice input or manual mic toggle instantly cuts assistant speech playback, transitions emotional state to `LISTENING`, and renders synchronized dialogue subtitles.
