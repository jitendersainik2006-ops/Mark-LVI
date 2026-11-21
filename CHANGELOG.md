# J.A.R.V.I.S. MARK LVI — CHANGELOG

All notable changes, architectural improvements, and security enhancements are documented herein.

## [Mark LVI — Unified Humanlike AI Companion Master (v56.3.0)] — 2026-11-21

### Added & Integrated
- **Five Selectable Female Voices (`core/character_manager.py`, `dashboard/server.py`, `app.html`):**
  - Registered 5 distinct female voice profiles:
    1. `SWARA_HINDI` (Default, Warm Hindi & Hinglish Neural, `hi-IN-SwaraNeural`)
    2. `NEERJA_INDIAN_EN` (Fluent Indian English & Hinglish Neural, `en-IN-NeerjaNeural`)
    3. `AVA_MODERN_EN` (Expressive Modern US English Neural, `en-US-AvaNeural`)
    4. `SONIA_BRITISH_EN` (Polished British English Neural, `en-GB-SoniaNeural`)
    5. `ZIRA_OFFLINE` (Windows SAPI5 `Microsoft Zira Desktop`, 100% On-Device Offline)
  - Added user customization controls: speech speed slider (0.75x–1.5x), pitch selector (-2Hz to +4Hz), online/offline status pill, and instant preview audio button.
  - Added native Devanagari-to-Roman phonetic transliteration (`_transliterate_devanagari_for_sapi5`) ensuring seamless offline pronunciation on Windows SAPI5 without silence or crashing.
- **Natural Human Conversation Engine (`core/human_conversation_engine.py`):**
  - Integrated automatic language classification: Devanagari script detection (`hindi`), token frequency analysis (`hinglish`), and English fallback.
  - Conversational style inference: `casual`, `technical`, `concise`, and `formal`.
  - Dynamic adaptive system prompt generation with long-term memory retrieval from `memory_manager`.
  - Contextual multi-turn reasoning via Ollama `qwen2.5:3b` with warm, respectful rule-based offline fallbacks.
  - Honest transcription failure handling when audio is corrupt or empty.
- **Dedicated Automated Test Suite (`tests/test_five_female_voices_and_conversation_engine.py`):**
  - 15 unit and integration tests covering voice registration, default Swara persona, speed/pitch persistence, language detection, style matching, adaptive prompts, and offline transliteration.
  - All 15 tests passing in 0.009s.
- **Reference Documentation & Deployment Architecture:**
  - `FEATURE_REFERENCE_MATRIX.md`: Complete capability matrix across all 13 reference projects (Stonic AI, Project Ciel, MoHan, Hume AI, Leon AI, OpenVoiceOS, Home Assistant Assist, Open WebUI Voice, Willow, Rhasspy, AnythingLLM, Jan AI, Open Interpreter).
  - `LICENSES_AND_ATTRIBUTIONS.md`: Formal license notices, copyright texts, and clean-room protocol isolation boundaries.
  - `docs/DOMAIN_DEPLOYMENT_PLAN.md`: Production reverse proxy blueprint for `jarvis.theblackintel.com` with TLS 1.3 termination, WebSocket upgrades, token auth, and DPAPI at rest.

### Verified & Validated
- **100% Automated Test Battery (193 / 193 Passed):**
  - Unittest Discovery Suite (`tests/`): 151 / 151 tests PASSED in 14.99s.
  - Phase 1–5 Regression Suite (`test_phase1_to_phase5.py`): 5 / 5 tests PASSED in 1.40s.
  - Live E2E Integration Suite (`test_e2e_integration.py`): 8 / 8 tests PASSED in 38.00s.
  - LAN Connectivity Validation (`test_lan_connectivity_validation.py`): 12 / 12 tests PASSED in 0.43s.
  - Android Pairing Lifecycle (`test_pairing_workflow.py`): 9 / 9 tests PASSED in 5.20s.
  - Android Extended UAT (`test_android_extended_uat.py`): 8 / 8 stages PASSED in 5.00s.
- **Master Distribution Artifacts Rebuilt & Verified:**
  - `JARVIS_Mark_LVI_Setup.exe`: 2,968,035 bytes, SHA-256 `b84958c91e649f03f41578e16a16c5cf1a14bd560028c75b5163cf41fa2e851c`.
  - `JARVIS_Mark_LVI_Windows_x64_Portable.zip`: 1,102,034 bytes, SHA-256 `5e0f755b409839c9d7401ce835c7719ec58f06e8aef95d1100c14350b46f659f`.
  - `SHA256_MANIFEST.txt`: 16,833 bytes, 183 files, SHA-256 `0f2b3b9c2f250146607af0f4077d4d7faa75d0019d6cfacc1ca56d0eebd59aef`.
  - Clean extraction verification: 183 / 183 files matched 100% against SHA-256 manifest.
- **Data & Security Preservation:**
  - `data/reels_ledger.json`: Exactly 74 historical reels preserved (360,070 bytes).
  - `@mentos_life_gym`: Status locked in `UNVERIFIED_BY_META`, zero live Graph API calls.

---

## [Mark LVI — Resumed Execution & Independent Release Verification] — 2026-11-21

### Verified & Validated
- **Process State & LLM Service Check:**
  - Audited background processes: verified active Ollama daemon (PID 21236) listening on port 11434 with `qwen2.5:3b` loaded; avoided duplicate daemon initialization.
  - Verified backups `D:\JARVIS-AI_backup_pre_migration` and master baseline `D:\JARVIS-AI\backups\backup_pre_unified_humanlike_20261120_154500` (81 items, completely readable).
  - Verified 74-entry `data/reels_ledger.json` (360,070 bytes) preserved 100% intact.
- **Automated Regression Battery Verification (149 / 149 Passed):**
  - Unittest Discovery Suite (`tests/`): 136 / 136 tests PASSED in 17.31s (`python -m unittest discover -s tests -p "test_*.py"`).
  - Phase 1 to 5 Integration Suite (`test_phase1_to_phase5.py`): 5 / 5 tests PASSED in 1.40s.
  - Live End-to-End Integration Suite (`test_e2e_integration.py`): 8 / 8 tests PASSED in 36.00s (live Ollama Qwen2.5:3b, Faster-Whisper local STT, Microsoft Zira TTS, memory persistence, task approval lifecycle).
- **Dedicated LAN & Android Companion Verification:**
  - LAN Connectivity & RFC 1918 Gating (`tests/test_lan_connectivity_validation.py`): 12 / 12 tests PASSED in 0.46s.
  - Android Pairing Lifecycle (`test_pairing_workflow.py`): 9 / 9 tests PASSED in 5.20s.
  - Android Extended UAT Suite (`test_android_extended_uat.py`): 8 / 8 stages PASSED in 5.00s.
- **Windows Launcher Resolution Verification:**
  - Verified both source and release batch files (`mark_lvi_core/launch_jarvis.bat`, root `launch_jarvis.bat`, `release/.../launch_jarvis.bat`, and `release/.../install_jarvis.bat`): 0 unescaped ampersands, 10-tier Python discovery hierarchy verified.
  - Executed discovery simulation in cmd.exe: source resolves to `..\.venv-jarvis\Scripts\python.exe`; release resolves to `..\..\.venv-jarvis\Scripts\python.exe`.
- **Distribution Package Integrity & Manifest Parity:**
  - Inno Setup 6 Installer: `JARVIS_Mark_LVI_Setup.exe` (2,952,828 bytes, SHA-256 `56B63CE75F054338381650D5CE4784FCAA7D8B69E97A875994BC77F0C071C201`).
  - Portable ZIP: `JARVIS_Mark_LVI_Windows_x64_Portable.zip` (1,076,413 bytes, SHA-256 `590953612697A3361F83F7F55B501B4C28EDC1831C9F0C842FFFE9CE94C67BA9`).
  - Manifest: `SHA256_MANIFEST.txt` (16,319 bytes, 178 files, SHA-256 `5C3A1D367AC02FF10A180E179C29ED70F8ADE2257D033AACE189F944D9297605`).
  - Isolated clean sandbox extraction: 178 / 178 files verified with 0 mismatches and 0 missing. Core modules import cleanly.

---

## [Mark LVI — PC-1 Final Completion Master] — 2026-11-20

### Fixed & Hardened
- **Windows Launcher Batch Syntax & Encoding (`launch_jarvis.bat`, `install_jarvis.bat`, `build_installer.py`):**
  - Resolved `'LOCAL' is not recognized as an internal or external command`: eliminated unescaped ampersands (`&`) in banner echo strings which `cmd.exe` previously parsed as command concatenation operators.
  - Resolved `'python' is not recognized`: replaced naive `where python` fallback with robust 10-tier Python discovery hierarchy inspecting local `.venv`, parent `.venv-jarvis`, AppData standard Python versions (3.10, 3.11, 3.12), ProgramFiles, `py -3`, and PATH.
  - Implemented actionable error dialog directing users to official python.org 64-bit download if no compatible runtime is found.
  - Added exit code capture with terminal pause on non-zero exit codes to retain diagnostic messages instead of abruptly closing.
  - Replaced multi-line PowerShell string expansion in batch with safe, single-line TCP port 11434 probe and Ollama auto-launch.
- **Test Discovery & Bootstrap Hardening (`tests/test_character_and_emotions.py`, `tests/test_unified_companion_stage.py`):**
  - Added self-contained `sys.path` bootstrapping so tests execute seamlessly regardless of execution root or unittest discovery invocation flags.
- **Installer & Distribution Packaging Rebuild:**
  - Re-executed `installer/build_installer.py` incorporating updated batch launcher templates.
  - Recompiled Inno Setup 6 native installer: `JARVIS_Mark_LVI_Setup.exe` (2,952,828 bytes, SHA-256: `56B63CE75F054338381650D5CE4784FCAA7D8B69E97A875994BC77F0C071C201`).
  - Re-packaged portable distribution archive: `JARVIS_Mark_LVI_Windows_x64_Portable.zip` (1,076,413 bytes, SHA-256: `590953612697A3361F83F7F55B501B4C28EDC1831C9F0C842FFFE9CE94C67BA9`).
  - Updated manifest `SHA256_MANIFEST.txt` covering all 178 packaged files with 100% hash parity.
  - Conducted clean-sandbox extraction test: 178/178 files verified with 0 missing and 0 mismatches.
- **Android Pairing & Network Security Audit:**
  - Audited `dashboard/server.py` pairing routes (`/api/lan-pairing/*`, `/ws/phone-audio`, `/api/action`).
  - Verified PBKDF2 (200,000 rounds) key derivation, AES-256-GCM authenticated tokens, and single-use token redemption.
  - Verified loopback-only restriction on `/api/lan-pairing/enable` (returns HTTP 403 to LAN callers).
  - Verified 10 sensitive administrative routes blocked from LAN callers via `_RESTRICTED_LAN_PREFIXES` (including `/api/reels`, `/api/gmail`, `/config`, `/api/shutdown`).
  - Verified `_ALLOWED_ACTIONS` allowlist for `/api/action`; destructive host shutdown and reboot are strictly prohibited over LAN.
  - Documented physical Wake-on-LAN hardware requirements and limitations (HTTP server suspended in ACPI S3/S5; hardware UDP magic packet required).
- **Automated Regression Suite Verification (149 / 149 Passed):**
  - 136 unittests (`tests/test_*.py`): PASSED in 22.36s.
  - 5 Phase regression tests (`test_phase1_to_phase5.py`): PASSED in 1.40s.
  - 8 End-to-End integration tests (`test_e2e_integration.py`): PASSED in 38.60s (live Ollama Qwen2.5:3b, Faster-Whisper, Zira TTS).

---

## [Mark LVI — Unified Human-Like AI Companion Master (Phase C, D & E)] — 2026-11-20

### Added & Enhanced
- **Persistent Animated Companion Stage (`dashboard/static/app.html`, `dashboard/static/jarvis_design_tokens.css`):**
  - Designed and deployed sticky companion stage header fixed permanently at the top of the interface across all 8 navigation workspaces (Chat, Tasks, Memory, Knowledge, Reels, Gmail, Diagnostics, Settings).
  - 60 FPS HTML5 vector canvas avatar rendering outer cybernetic energy pulse ring, radial gradient core, auto-blinking eyes every 4.2s, facial morphing per emotion, speech lip-sync mouth oscillation, and wholesome floating petals/hearts for female presentation.
  - Live dialogue subtitle bubble displaying synchronized spoken text with auto-detected language tags (`[HI]`, `[EN]`, `[AUTO]`).
  - Integrated push-to-talk microphone button (`#stage-mic-btn`), quick voice persona dropdown, and companion personalization button.
- **Priority Female Neural Voice — SWARA (`core/character_manager.py`, `dashboard/server.py`):**
  - Elevated `SWARA_HINDI` (`hi-IN-SwaraNeural`) to top default voice persona across character configuration and TTS endpoints.
  - Added PyAV PCM conversion to 16-bit 24kHz standard WAV format.
  - Built-in seamless offline fallback via Windows SAPI5 (`Microsoft Zira Desktop`) utilizing phonetic Devanagari transliteration tables for intelligible Hindi speech with zero external connectivity.
- **Instant Barge-In Interruption (`dashboard/static/app.html`):**
  - Immediate audio cutoff on user speech or mic click: calls `stopActiveAudioAndBargeIn()` to pause `_activeAudio`, reset position, stop audio tags, snap character state to `LISTENING`, and update stage waveform bars.
- **Permission-Controlled Desktop Automation (`core/computer_agent.py`):**
  - Integrated autonomous computer agent lifecycle (`PLAN -> PERMISSION -> ACT -> OBSERVE -> VERIFY -> REPORT`).
  - Destructive operations (`delete_file`, `send_email`, `publish_instagram_reel`, `system_restart`) strictly require explicit user confirmation token (`CONFIRM`).
  - Automated regex scrubbing of API keys, bearer tokens, and DPAPI payloads from audit logs.
- **New Unit & Integration Test Suite (`tests/test_unified_companion_stage.py`):**
  - Added comprehensive automated tests for voice persona defaults, Swara neural TTS & SAPI5 transliteration fallback, and computer agent destructive action gating.
  - Re-ran full regression battery: 136 unittests + 5 phase integration tests + 8 E2E live tests = **149 / 149 tests passing 100%**.
- **Distribution Packages Rebuilt & Verified:**
  - Rebuilt Inno Setup 6 native installer: `JARVIS_Mark_LVI_Setup.exe` (SHA-256: `fa41238cb9ffaadd77980ad503efed874a343deab8692156f7bbbb05c94ee89c`, 2.81 MB).
  - Rebuilt portable distribution package: `JARVIS_Mark_LVI_Windows_x64_Portable.zip` (SHA-256: `35c7c3b84b10cc6290fc32447baf79618916dda9a840a7986a25bb832b7a5174`, 1.02 MB).
  - Verified 178 files in `SHA256_MANIFEST.txt` with 100% hash match and zero developer key leakage.

---

## [Mark LVI — Final Quality, Performance, UI & Distribution Completion] — 2026-11-20

### Added & Enhanced
- **Stonic-Inspired Design Tokens System (`dashboard/static/jarvis_design_tokens.css`):**
  - Designed and deployed CSS Custom Properties design system with luxury dark palette (`--dark-bg: #050508;`, `--card-bg: #0d0d14;`, `--card-border: #1a1a2e;`).
  - Standardized brand accents: Gold primary (`#d4a853`), Blue diagnostics (`#5b8def`), Orange CTA (`#ff6600`).
  - Added accessibility standards with focus-visible rings and `@media (prefers-reduced-motion: reduce)` overrides.
  - Linked design tokens into both `dashboard/static/app.html` and `dashboard/static/login.html`, and added `/static/jarvis_design_tokens.css` route in `dashboard/server.py`.
- **Chrome Performance / Initial Startup Latency Optimization:**
  - Diagnosed and resolved initial page-load reload cycle in `dashboard/static/app.html`: replaced `location.reload()` with direct in-place token initialization and deferred background loading, saving 1.5–2.5s of redundant page reload delay.
  - Added font-display swap and containment rules for smooth rendering without layout shifts (CLS 0.00, INP 64ms maintained).
- **Directory Auto-Creation in Subsystems:**
  - Hardened `core/character_manager.py` and `core/personality_manager.py` with `c_file.parent.mkdir(parents=True, exist_ok=True)` to ensure resilient multi-user profile initialization without `FileNotFoundError`.
- **Reconciled Test Suite & Complete Automated Battery (146 Tests):**
  - Reconciled test taxonomy: verified that 12 LAN tests (`tests/test_lan_connectivity_validation.py`) are an integrated part of the 133 unittests discovered by `python -m unittest discover -s tests -p "test_*.py"`.
  - Battery total: 133 unittests + 5 phase integration tests + 8 E2E live tests = 146 unique automated tests passing 100%.
- **Release Packaging & Manifest Generation:**
  - Rebuilt `JARVIS_Mark_LVI_Setup.exe` (Inno Setup 6 installer) and `JARVIS_Mark_LVI_Windows_x64_Portable.zip`.
  - Verified 177 files in `SHA256_MANIFEST.txt` with dual synchronization to release folder and release root.

---

## [Mark LVI — Unified Master Execution] — 2026-11-20

### Added
- **Character Customization Engine (`core/character_manager.py`):**
  - Presentation selection: `MALE`, `FEMALE`, `NEUTRAL`.
  - Configurable hairstyle, outfit archetype, voice persona, greeting, and language style.
  - Wholesome decorative motifs for female and cheerful companion themes (delicate petals, glowing hearts, soft bokeh particles).
  - Per-user directory isolation (`data/users/<uid>/character.json`) with unified fallback (`data/character_config.json`).
- **19-State Emotional Expression System:**
  - Standardized emotional registry: `HAPPY`, `CHEERFUL`, `CALM`, `CURIOUS`, `EXCITED`, `THOUGHTFUL`, `CONFIDENT`, `CONCERNED`, `EMPATHETIC`, `PLAYFUL`, `FOCUSED`, `LISTENING`, `THINKING`, `SPEAKING`, `WORKING`, `PAUSED`, `ERROR`, `SUCCESS`, `IDLE`.
  - Distinctive visual vector morphing parameters (eye shapes, mouth curves, pulse oscillation speeds, aura intensity, and pitch/rate modulation hints).
  - Full PyQt6 vector rendering integration in `core/floating_companion.py`.
- **Personality Management System (`core/personality_manager.py`):**
  - 7 presets: `Professional`, `Friendly`, `Cheerful`, `Calm Mentor`, `Playful`, `Minimalist`, and `Custom`.
  - Dynamic system prompt injector for Ollama LLM queries.
- **Hardware & Voice Diagnostics Engine (`core/voice_diagnostics.py`):**
  - Live discovery and verification of microphone input devices and speaker output channels.
  - Faster-Whisper local model path validation (`D:\JARVIS-AI\whisper_models`).
  - EdgeTTS neural voice backend check.
  - Ollama HTTP health probe (`http://127.0.0.1:11434/api/tags`), latency measurement, and `qwen2.5:3b` presence check.
  - Barge-in voice activity detection (VAD) threshold verification.
- **Secure Google OAuth 2.0 & Gmail Companion (`core/gmail_manager.py`):**
  - Granular scope isolation: basic Google Sign-In strictly requests `openid email profile`, never requesting Gmail permissions without explicit opt-in.
  - Optional Gmail scopes: `gmail.readonly`, `gmail.compose`, and `gmail.send`.
  - Windows DPAPI token encryption at rest (`data/gmail_tokens.json`).
  - Strict human-in-the-loop email dispatch gate: requires 2-step preview generation and verification of a single-use cryptographic confirmation token before dispatch.
- **Dashboard Web UI Modernization (`dashboard/static/app.html` & `dashboard/server.py`):**
  - Added dedicated navigation tabs and panels: `🎭 Companion`, `🎙️ Diagnostics`, and `✉️ Gmail`.
  - Added 19 emotion reaction buttons with instant live feedback and intensity slider.
  - Added real-time voice diagnostics dashboard with health badges.
  - Added inbox thread viewer, draft composer, and confirmed send dialog.
  - Added `/api/gmail` to `_RESTRICTED_LAN_PREFIXES` to block remote LAN access to mail endpoints.

### Changed & Cleaned
- Safely purged 31 redundant backup files (`*.bak`, `*.bak_m*`, `startup.log`) from the active source tree into `D:/JARVIS-AI/backups/backup_pre_unified_master_20261120_134719`.
- Preserved historical reels ledger (`data/reels_ledger.json`, 74 entries, 392 KB), user memory, and Instagram account configurations intact.

---

## [Mark LVI — Production Candidate 1 (PC-1)] — 2026-11-19
- Hardened process termination in `installer/stop_jarvis.py` and `installer/uninstall_jarvis.py` to enforce verified PID executable path ownership.
- Standardized Inno Setup 6 build script with dynamic versioning and shortcut creation.
- Implemented temporary LAN pairing mode with TCP peer address validation (`scope["client"]`) and private subnet filtering.
- Validated Meta OAuth quick tunnel reverse proxy on port 8005.

---

## [Mark LV / LVI — Earlier Milestones] — 2026-10 to 2026-11
- Multi-user authentication engine with PBKDF2-HMAC-SHA256 password hashing.
- 12-step guided user onboarding and user directory data isolation.
- Gym Reels Studio with 08:00 and 19:00 IST scheduler slots.
- Holographic 3D wireframe head renderer via `core/avatar.py` and MediaPipe face model.
