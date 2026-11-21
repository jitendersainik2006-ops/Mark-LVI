# J.A.R.V.I.S. MARK LVI — DISTRIBUTION SECURITY & PRIVACY SPECIFICATION

This document outlines the security architecture, data isolation guarantees, and distribution boundaries implemented in J.A.R.V.I.S. Mark LVI.

---

## 1. MULTI-USER & DEVELOPER DATA ISOLATION

J.A.R.V.I.S. release packages are strictly cleansed of all developer-specific context before packaging:
1. **Zero Hardcoded Paths:** Launcher scripts use `%~dp0` (current script directory) instead of hardcoded paths (`D:\...` or `C:\...`).
2. **Zero Developer Memories:** Distributable packages do not include personal memory stores (`memory/long_term.json`), conversation logs, or personal preferences.
3. **Zero Embedded API Keys / Tokens:** `config/api_keys.json` is not packaged. The First-Run Setup Wizard generates a clean, unpopulated configuration template on the new user's machine.
4. **Credential Redaction:** Memory manager and loggers enforce regular-expression pattern scrubbing to strip OpenAI, Google, Hugging Face, GitHub, and bearer tokens from all audit logs and memory entries.
5. **Multi-User Isolation:** Each Windows user running the application operates with their own separate memory database, configuration, device pairing records, and conversation history.

---

## 2. LOCAL-FIRST PROCESSING GUARANTEES

1. **Default Offline Operation:**
   - LLM inference runs locally via Ollama (`qwen2.5:3b`).
   - Speech-to-Text transcription runs on-device via `faster-whisper`.
   - Text retrieval and RAG search run locally via Scikit-Learn TF-IDF.
   - Speech synthesis runs locally via Kokoro neural TTS (or free Edge-TTS if internet is available).
2. **No Unsolicited Telemetry:** J.A.R.V.I.S. does not send usage metrics, telemetry, transcripts, or personal logs to external cloud servers.
3. **Document Privacy:** Uploaded documents (PDFs, DOCX, text notes, images) are stored locally in `data/knowledge/documents/` and are never uploaded to cloud third parties unless the user explicitly configures a cloud LLM provider (e.g. Gemini API).

---

## 3. NETWORK & ACCESS BOUNDARIES

1. **Localhost-Only Default:**
   - The dashboard server binds strictly to `127.0.0.1:8000`.
   - All external incoming network traffic is refused by default.
2. **Temporary LAN Pairing Gate:**
   - Remote mobile companion access is disabled by default.
   - Enabling LAN pairing requires physical presence on the host machine.
   - Unspoofable peer TCP socket filtering (`scope["client"][0]`) blocks IP header forgery (`X-Forwarded-For`).
   - Host-Header validation prevents DNS rebinding and cross-site request attacks.
   - Sensitive administrative, OAuth, Reels Studio, and config endpoints are permanently inaccessible to LAN clients (HTTP 403 Forbidden).
   - Windows Defender Firewall rule is restricted strictly to `profile=private remoteip=localsubnet`. Zero UPnP or public router port forwarding is ever requested.
3. **OAuth Reverse Proxy Isolation:**
   - Port 8005 proxy forwards exclusively to `/api/instagram/oauth/callback`. All other HTTP paths and methods return HTTP 403 Forbidden.
