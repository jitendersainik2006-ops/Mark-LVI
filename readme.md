# J.A.R.V.I.S. MARK LVI — ULTIMATE HUMAN-LIKE DESKTOP AI COMPANION

[![Platform: Windows 64-bit](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20(x64)-blue.svg)]()
[![Brain: Local Ollama](https://img.shields.io/badge/LLM-Local%20Ollama%20(qwen2.5%3A3b)-purple.svg)]()
[![Voice: Neural TTS & STT](https://img.shields.io/badge/Voice-Hindi%20%7C%20Hinglish%20%7C%20English-green.svg)]()
[![Privacy: Local-First](https://img.shields.io/badge/Privacy-100%25%20Local--First-brightgreen.svg)]()
[![Architecture: 13 Modules](https://img.shields.io/badge/Modules-13%20Integrated%20Suites-orange.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)]()

> **J.A.R.V.I.S. (Just A Rather Very Intelligent System) Mark LVI** is a next-generation, voice-first personal desktop AI companion and autonomous assistant for Windows. Engineered with a **local-first, privacy-preserving dual brain**, natural multi-lingual conversational voice with barge-in interruption, a modern visual dashboard with dark/light themes, and 13 comprehensive capability modules.

---

## 🌟 KEY CAPABILITIES & FEATURES

### 1. Natural Conversational Voice & Real-Time Barge-In
- **Indian & Global Neural Voices:** Default **Swara (Hindi Neural)**, plus Radhika, Ananya, Kabir, and Aarav.
- **Client-Side Speech Barge-In:** Immediate audio stream cancellation the millisecond the user begins speaking, delivering fluid human-like turn-taking.
- **Phonetic Pronunciation Dictionary:** Rules in `config/pronunciation_rules.json` guarantee precise phonetics for Indian names, greetings, and technical terminology across Hindi, Hinglish, and English.
- **Listening Modes:** 4 switchable modes: **Hands-Free**, **Wake-Word ("Hey Jarvis")**, **Push-to-Talk**, and **Privacy Mute**.

### 2. Dual-Mode Visual Interface (Inspired by Stonic AI)
- **Modern Companion Mode:** Deep charcoal `#090D16` foundation, purple/violet `#8B5CF6` primary accents, cyan `#06B6D4` and gold `#D4A853` highlights, glassmorphic cards, and a 60 FPS real-time audio-reactive 3D companion canvas.
- **Light Theme Toggle:** Instant switch to a clean `#F8FAFC` daylight theme with high contrast and accessible typography.
- **Tactical HUD Mode:** Switch instantly to the classic holographic sci-fi heads-up display.
- **Low-Resource Eco Mode:** Throttles canvas animation to 15 FPS and disables heavy CSS blurs for battery conservation on laptops.

### 3. 13 Integrated Enterprise & Desktop Modules

| Module | Core Functionality |
| :--- | :--- |
| 💬 **Chat Sessions** | Multi-threaded conversations, thread renaming, search, and SSE streaming token responses. |
| 🧠 **Memory Engine** | Transparent long-term semantic memory with tag filtering, importance weighting, and full user edit/delete control. |
| 📄 **Document RAG** | Ingest PDF, DOCX, TXT, MD, CSV files with automatic chunking, TF-IDF semantic search, and citations. |
| 🔀 **Visual Workflows** | Drag-and-drop node sequences, multi-step automated jobs, intermediate checkpoints, and operator approval gates. |
| ⏱️ **Schedules** | Timezone-aware cron and interval automation for recurring reminders, backups, and reports. |
| 🔌 **Real Integrations** | Verified connections to GitHub, Notion, Slack, and Discord webhooks with honest status reporting. |
| 🏢 **Workspaces & RBAC**| Multi-user team spaces with Owner, Admin, Member, and Viewer role-based access control. |
| 📜 **Audit Log** | Immutable, append-only security ledger capturing all computer actions, tool invocations, and confirmation records. |
| 📊 **Real Analytics** | Honest live system telemetry (CPU %, RAM %, Disk usage, active sessions, knowledge chunks, latency). |
| 🤖 **7 Autonomous Agents**| Orchestrator, System Agent, Knowledge Agent, Memory Agent, Document Agent, Browser Agent, Creative Agent. |
| ⚙️ **Voice & Personality**| Choose between J.A.R.V.I.S., FRIDAY, or ANALYST personalities, calibrate TTS rate/pitch, and configure wake sensitivity. |
| 🛡️ **Admin & Governance**| Live security audits, snapshot backups, token scrub verification, and system diagnostic self-tests. |
| 📱 **Android & Reels** | Encrypted LAN Android pairing, and automated Instagram Reels studio with strict approval separation. |
| 💬 **WhatsApp Assistant** | Voice-guided contact resolution, draft message preview, and two-phase operator confirmation gate. |
| ⏰ **Smart Reminders** | Natural-language one-time & recurring reminders (`daily`, `hourly`, `weekly`), snooze, and persistent daemon. |

### 4. Safety-Gated PC Automation
- Formal execution lifecycle: `PLAN -> CONFIRM -> ACT -> OBSERVE -> REPORT`.
- Consequential operations (file deletion, app termination, emails, system reboots) strictly require operator confirmation.

---

## 💾 OFFICIAL DOWNLOADS & RELEASES (v56.0.0)

| Package | Format | Size | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **Windows Installer** | [.exe (Setup)](https://github.com/jitendersainik2006-ops/Mark-LVI/releases/download/v56.0.0/JARVIS_Mark_LVI_Setup.exe) | 2.89 MB | `fe08b3ee64c90e03d8d6c7189b0ebfbe6d8f07c718332d9a28943b661535b4d7` |
| **Portable Package** | [.zip (Standalone)](https://github.com/jitendersainik2006-ops/Mark-LVI/releases/download/v56.0.0/JARVIS_Mark_LVI_Windows_x64_Portable.zip) | 1.16 MB | `5d005a9d81b90c3b543d6c8e13e7676fb54d939d24c47c4fb46459a5d8245f16` |
| **Package Manifest** | [.txt (Manifest)](https://github.com/jitendersainik2006-ops/Mark-LVI/releases/download/v56.0.0/SHA256_MANIFEST.txt) | 19.6 KB | `9c374d5a3093de0f8b23bd6cb009de6dc2135f52315f9e9a6943ffb8efe26681` |

---

## 🚀 INSTALLATION & QUICK START

### Prerequisites
- **OS:** Windows 10 (64-bit Build 19041+) or Windows 11 (64-bit)
- **RAM:** 8 GB minimum (16 GB recommended)
- **Disk:** 10 GB free space on any drive (C:, D:, or external SSD)
- **Python:** Python 3.10 to 3.12 (64-bit) with "Add Python to PATH" enabled
- **Local AI:** [Ollama](https://ollama.com) with `qwen2.5:3b` model

### One-Click Setup
1. Extract or clone this repository to any directory (e.g. `C:\JARVIS-AI` or `D:\JARVIS-AI`).
2. Double-click **`install_jarvis.bat`**.
3. The Setup Wizard will detect hardware, verify audio devices, initialize local databases, and create Desktop shortcuts.
4. Launch J.A.R.V.I.S. from your Desktop shortcut or run **`launch_jarvis.bat`**.
5. Open your browser at **`http://127.0.0.1:8000/app`**.

---

## 📚 DOCUMENTATION SUITE

- 📖 [docs/INSTALLATION_GUIDE.md](docs/INSTALLATION_GUIDE.md) — Comprehensive step-by-step setup walkthrough.
- 💻 [docs/SYSTEM_REQUIREMENTS.md](docs/SYSTEM_REQUIREMENTS.md) — Hardware benchmarks, memory limits, and GPU support.
- 🚀 [docs/FIRST_RUN_GUIDE.md](docs/FIRST_RUN_GUIDE.md) — First-time orientation, voice commands, and dashboard tour.
- 🔧 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) — Audio troubleshooting, Ollama diagnostics, and port conflict fixes.
- 🛡️ [docs/SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md) — DPAPI encryption, secret scrubbing, and local isolation.
- 🔄 [docs/UPDATE_AND_UNINSTALL.md](docs/UPDATE_AND_UNINSTALL.md) — Upgrades, data preservation, and clean removal.
- 🗺️ [docs/FEATURE_REFERENCE_MATRIX_13.md](docs/FEATURE_REFERENCE_MATRIX_13.md) — Implementation details of the 13 reference projects.

---

## 🔒 SECURITY & DATA PRIVACY GUARANTEE

J.A.R.V.I.S. is 100% committed to local user privacy:
- **Zero Cloud Leakage:** Conversational prompts and documents remain strictly on your local machine.
- **DPAPI Encryption:** Secrets are encrypted via native Windows DPAPI (`dpapi:v1:`).
- **Reverse Proxy Shield:** Port 8000 is loopback-only. External hooks are restricted to port 8005.

---

## 📄 LICENSE

Released under the [MIT License](LICENSE). Copyright (c) 2026.
