# J.A.R.V.I.S. MARK LVI — 13-REFERENCE VOICE INTELLIGENCE RESEARCH REPORT

**Document ID:** `docs/VOICE_13_REFERENCE_RESEARCH.md`  
**System:** J.A.R.V.I.S. MARK LVI Desktop AI Companion  
**Date:** 2026-11-22  
**Status:** VERIFIED FROM OFFICIAL DOCUMENTATION & SOURCE REPOSITORIES  

---

## 1. EXECUTIVE OVERVIEW

This research audit evaluates 13 industry and open-source voice, desktop assistant, and conversation architectures. The objective is to identify verified engineering patterns that can be cleanly integrated into **J.A.R.V.I.S. MARK LVI** to deliver a genuinely natural, expressive female voice across Hindi, Hinglish, and English, reliable local wake-word standby, hands-free continuous conversation, real barge-in turn-taking, and safety-gated desktop automation.

---

## 2. DETAILED REFERENCE AUDITS

### Reference 1 — Stonic AI
- **Official URL:** `https://stonicai.com/` | `https://stonicai.com/releases`
- **Architecture:** Desktop AI Companion with real-time 3D/2D visual canvas, multi-persona emotional state machine, phone-to-PC encrypted pairing, and voice session continuity.
- **Key Engineering Patterns:**
  - *Companion Continuity:* Personality profiles (`JARVIS`, `FRIDAY`, `ANALYST`) maintain identity consistency across chat and voice turns.
  - *Multi-Modal Audio:* Real-time visual orb reactive to audio levels, emotional states (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`), and speech cadence.
  - *Phone-to-PC Audio:* Decoupled input capture from processing, allowing remote mobile microphone feed into desktop inference.
- **Unsuitable Patterns:** Proprietary cloud backend models; closed-source asset formats.
- **Adopted in J.A.R.V.I.S.:** 60 FPS companion orb canvas, emotional state integration with voice pitch/rate modulation, and LAN device pairing.

---

### Reference 2 — Project Ciel
- **Official URL:** `https://github.com/VuloB1/project-ciel` (License: GPL-3.0)
- **Architecture:** Tauri / Rust backend with React frontend; modular voice call architecture separating STT, LLM, and TTS via provider abstraction layers.
- **Key Engineering Patterns:**
  - *Provider Abstraction:* Clean interfaces for switching between cloud neural TTS and local offline synthesis.
  - *Echo Guard Limitations:* Identified that simple volume thresholds fail on desktop speakers; requires spectral energy comparison between output buffer and microphone input.
  - *Memory Extraction & Deduplication:* Semantic memory extraction from conversational turns with content hashing.
- **Unsuitable Patterns:** Tauri-specific IPC bridges; full UI replacement.
- **Adopted in J.A.R.V.I.S.:** Dual-check `EchoGuard` (spectral band energy subtraction + learned echo gain) for barge-in turn-taking.

---

### Reference 3 — MoHan PC Desktop Assistant
- **Official URL:** `https://github.com/flameblade-studio/MoHan-PC-Desktop-Assistant`
- **Architecture:** Windows-first desktop assistant featuring local female voice synthesis, permission-controlled system actions, and emergency kill-switches.
- **Key Engineering Patterns:**
  - *Safety Gating:* Explicit categorization of desktop tools into non-consequential (read-only) and consequential (file deletion, app termination, reboot).
  - *Local Female Voice:* Default female voice persona with local offline SAPI5 fallback.
  - *Operator Confirmation Gate:* Two-phase commit (`PLAN -> CONFIRM -> EXECUTE`) for consequential operations.
- **Unsuitable Patterns:** Heavy Chinese-only UI elements; monolithic GUI loop.
- **Adopted in J.A.R.V.I.S.:** Consequential risk tiers (`READ_ONLY`, `LOW_RISK`, `CONSEQUENTIAL`), operator confirmation gates for WhatsApp and PC actions.

---

### Reference 4 — Hume AI (Expression APIs & EVI)
- **Official URL:** `https://www.hume.ai/products/expression-apis` | `https://dev.hume.ai/voice/reference/speech-to-speech-evi`
- **Architecture:** Empathic Voice Interface (EVI) analyzing vocal prosody, pitch contours, warmth, hesitation, and emotional expressions.
- **CRITICAL SUNSET AUDIT:** Official documentation states that Hume's legacy TTS and EVI APIs were scheduled for sunset on **13 November 2026**. As of today (22 November 2026), these APIs are deprecated/sunset.
- **Engineering Verdict:** **DO NOT DEPEND ON HUME EVI/TTS IN PRODUCTION.**
- **Adopted in J.A.R.V.I.S.:** Local prosody shaping (pitch/rate modulation across 19 emotional states) and phonetic dictionary without external cloud API lock-in.

---

### Reference 5 — Leon AI
- **Official URL:** `https://github.com/leon-ai/leon` | `https://docs.getleon.ai/`
- **Architecture:** Open-source personal assistant organizing capabilities into modular skills, packages, and actions, with layered memory and offline fallback.
- **Key Engineering Patterns:**
  - *Skill Architecture:* Each skill self-describes inputs, validation parameters, and safety requirements.
  - *Layered Memory:* Working session memory distinct from long-term user facts and entity relationships.
  - *Tool Verification:* Verifies execution result rather than assuming model text output proves success.
- **Adopted in J.A.R.V.I.S.:** Action registry with 21 self-describing tools, unified memory manager (`data/memory.json`, `data/chat_sessions.json`).

---

### Reference 6 — OpenVoiceOS (OVOS)
- **Official URL:** `https://openvoiceos.github.io/beta-technical-manual/`
- **Architecture:** Linux/Python modular voice OS using an internal MessageBus connecting Microphone Plugins, Wake-Word Engine, VAD, STT Plugins, and TTS Plugins.
- **Key Engineering Patterns:**
  - *Continuous Listening Lifecycle:* Strict separation of states: `WAKE_WORD_STANDBY` (zero cloud streaming, low CPU ONNX model) ➔ `LISTENING` (VAD active) ➔ `TRANSCRIBING` ➔ `THINKING` ➔ `SPEAKING`.
  - *Audio Transformer Pipeline:* Pre-filtering noise and DC offset before feeding STT.
- **Adopted in J.A.R.V.I.S.:** Explicit 9-state conversational voice lifecycle and thread-isolated `openwakeword` feed.

---

### Reference 7 — Home Assistant Assist
- **Official URL:** `https://developers.home-assistant.io/docs/voice/pipelines/`
- **Architecture:** Four-stage voice pipeline (`Wake Word ➔ STT ➔ Conversation Agent ➔ TTS`) coordinated via WebSocket events and stage checkpoints.
- **Key Engineering Patterns:**
  - *Pipeline Event Emitters:* Clear lifecycle events emitted to frontend (`wake_word_end`, `stt_start`, `stt_end`, `intent_start`, `tts_start`, `tts_end`).
  - *Configurable Audio Pipeline:* Independent selection of STT, TTS, and language profiles per device.
- **Adopted in J.A.R.V.I.S.:** WebSocket telemetry events to companion dashboard, real-time stage status broadcasting.

---

### Reference 8 — Open WebUI Voice Mode
- **Official URL:** `https://docs.openwebui.com/features/chat-conversations/chat-features/voice-mode/`
- **Architecture:** Web-based conversational voice interface supporting real-time speech streaming, sentence-level response chunking, and automatic mic re-arming.
- **Key Engineering Patterns:**
  - *Sentence-Level Response Streaming:* Does NOT wait for LLM completion; streams tokens into sentence buffer and yields complete sentences to TTS queue immediately.
  - *Voice Interruption & Cancellation:* Frontend mic input immediately cancels active audio playback buffer and aborts in-flight token generation.
- **Adopted in J.A.R.V.I.S.:** Sentence-level regex segmentation (`[.!?…\n|।!?]`), concurrent TTS producer-consumer queue, and immediate playback flush on barge-in.

---

### Reference 9 — Willow
- **Official URL:** `https://heywillow.io/` | `https://heywillow.io/how-willow-works/`
- **Architecture:** Privacy-focused hardware voice assistant pairing ESP32 audio frontends with a high-throughput Whisper/CTranslate2 local inference server.
- **Key Engineering Patterns:**
  - *Fast Local STT:* CTranslate2-based Whisper (`faster-whisper`) with beam size 1, greedy decoding, and VAD silence filtering achieves sub-300ms transcription latency.
  - *VAD Speech Framing:* Uses Silero/energy VAD to segment utterances and suppress ambient background noise.
- **Adopted in J.A.R.V.I.S.:** Local `faster-whisper` (`int8` compute, beam_size=1, VAD filter) for offline transcription.

---

### Reference 10 — Rhasspy
- **Official URL:** `https://rhasspy.readthedocs.io/en/latest/`
- **Architecture:** 100% offline voice assistant platform with modular MQTT audio streams, intent parsing, and local wake-word systems.
- **Key Engineering Patterns:**
  - *Complete Offline Determinism:* Entire voice pipeline capable of functioning with zero internet connectivity.
  - *Pronunciation Dictionary:* Phonetic rules mapping non-standard terminology and localized words to accurate phonemes.
- **Adopted in J.A.R.V.I.S.:** `config/pronunciation_rules.json` phonetic dictionary for Hindi, Hinglish, and English technical terms, plus SAPI5 phonetic transliteration.

---

### Reference 11 — AnythingLLM
- **Official URL:** `https://docs.anythingllm.com/introduction` | `https://github.com/Mintplex-Labs/anything-llm`
- **Architecture:** Desktop RAG and document intelligence suite with workspace isolation, chunking, and cited retrieval.
- **Key Engineering Patterns:**
  - *Document Ingestion & Chunking:* Recursive text chunking with TF-IDF and vector semantic search.
  - *Cited Fact Retrieval:* Answers ground assertions with explicit source citations.
- **Adopted in J.A.R.V.I.S.:** `core/knowledge_manager.py` RAG pipeline with document indexing and citation streaming.

---

### Reference 12 — Jan AI
- **Official URL:** `https://jan.ai/` | `https://docs.jan.ai/`
- **Architecture:** Local-first desktop AI client hosting an OpenAI-compatible server on `127.0.0.1`, streaming chat completions with hardware telemetry.
- **Key Engineering Patterns:**
  - *Local LLM Inference:* Seamless binding to local Ollama runtime (`qwen2.5:3b`) with graceful fallback.
  - *Telemetry:* Live CPU, RAM, and token generation speed telemetry.
- **Adopted in J.A.R.V.I.S.:** Local Ollama connection (`127.0.0.1:11434`), SSE token streaming, and system performance monitoring.

---

### Reference 13 — Open Interpreter
- **Official URL:** `https://www.openinterpreter.com/docs/desktop/install`
- **Architecture:** Local computer automation interface allowing natural-language voice control of desktop applications, terminal, and settings within defined safety boundaries.
- **Key Engineering Patterns:**
  - *Sandboxed Execution:* Operations strictly bounded within approved directory scopes.
  - *Confirmation Required:* High-consequential desktop operations prompt operator before executing.
- **Adopted in J.A.R.V.I.S.:** Strict workspace boundaries, safety permission registry, and human-in-the-loop confirmation.

---

## 3. MASTER COMPARISON MATRIX

| Reference | STT Provider | TTS Provider | Wake Word | Streaming / Barge-In | Local/Offline | Safe PC Actions |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **Stonic AI** | Cloud/Local | Neural TTS | Push / Voice | Yes (Canvas reactive) | Partial | Yes |
| **Project Ciel** | Modular | Modular | No | Echo Guard | Partial | No |
| **MoHan** | Windows SAPI | SAPI5 / Cloud | Yes | No | Yes | Yes (3 tiers) |
| **Hume AI** | EVI (Sunset) | EVI (Sunset) | Cloud | Real-time EVI | No | No |
| **Leon AI** | Coqui / Vosk | Flite / Coqui | Snowboy / Porcupine | No | Yes | Yes |
| **OpenVoiceOS** | Faster-Whisper | Piper / Mimic3 | openWakeWord | Yes (MessageBus) | Yes | Skill-based |
| **Home Assistant**| Whisper | Piper | openWakeWord | Yes (WebSocket) | Yes | Entity-gated |
| **Open WebUI** | Whisper | Edge / Kokoro | Web Audio | Sentence Streaming | Partial | No |
| **Willow** | Whisper C2 | Piper | openWakeWord | Low-Latency | Yes | No |
| **Rhasspy** | Kaldi / Vosk | MaryTTS / Larynx | Porcupine / Snowboy | MQTT chunks | Yes | Intent-gated |
| **AnythingLLM** | Whisper | System | No | SSE Text | Yes | Agent tools |
| **Jan AI** | None (Text) | None | No | SSE Streaming | Yes | No |
| **Open Interpreter**| Whisper | System | Voice Mode | Streamed tools | Yes | Confirmation-gated |
| **J.A.R.V.I.S. LVI**| **Faster-Whisper** | **Neural 5-Voice / SAPI5** | **openWakeWord** | **Sentence Stream + Real Barge-in**| **100% Local Capable** | **3-Tier Permission Gate** |

---

## 4. ARCHITECTURAL RECOMMENDATIONS FOR J.A.R.V.I.S. MARK LVI

1. **TTS Upgrade (Part 4):** Implement a unified, modular `VoiceEngine` integrating Microsoft Neural voices (`hi-IN-SwaraNeural`, `en-IN-NeerjaNeural`, `en-US-AvaNeural`, `en-GB-SoniaNeural`) with tuned SSML prosody contours, pause shaping, and offline SAPI5 fallback (`Zira`).
2. **STT Multilingual Input (Part 5):** Optimize local `faster_whisper` with automatic language detection (`hindi`, `hinglish`, `english`) and code-switching support.
3. **Continuous Conversation & Wake-Word Standby (Part 6):** Embed persistent `WAKE_WORD_STANDBY` state via `openwakeword` with configurable 10-second follow-up listening window.
4. **Real Barge-In Turn-Taking (Part 7):** Activate `EchoGuard` during speech output to subtract speaker echo and instantly trigger `interrupt()` on user speech.
5. **Sentence-Aware Streaming (Part 8):** Implement regex-based sentence chunking to stream audio while LLM generates tokens.
6. **Safety & Workspace Isolation (Part 10):** Enforce three-tier confirmation gating for all consequential desktop skills.
