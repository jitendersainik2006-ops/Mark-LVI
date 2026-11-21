# J.A.R.V.I.S. MARK LVI — LICENSES AND ATTRIBUTIONS

**Document Version:** 1.0  
**Effective Date:** November 2026  
**Project:** J.A.R.V.I.S. Mark LVI  
**Workspace:** `D:\JARVIS-AI\mark_lvi_core`  

---

## 1. Overview & Intellectual Property Policy

J.A.R.V.I.S. Mark LVI is a unified, personal AI desktop companion built with strict compliance regarding open-source licensing, copyright attribution, and clean-room architectural boundaries. 

When studying external benchmarks and open-source systems, all code integrated into the repository has been:
1. Implemented natively in Python, HTML5, and vanilla JavaScript for Windows workstations.
2. Verified for license compatibility (permissive MIT / Apache 2.0 / BSD models).
3. Kept strictly distinct from copyleft (GPL / AGPL) source trees via network protocol and architectural boundaries to maintain complete standalone ownership and safety.

---

## 2. Reference Projects & Attribution Notices

### 2.1 Project Ciel (Live2D & Character Companion Architecture)
- **Source:** https://github.com/ciel-companion/project-ciel
- **License:** MIT License
- **Attribution Notice:**
  > Copyright (c) 2024 Project Ciel Contributors.  
  > Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software.
- **Application in J.A.R.V.I.S.:** Architectural inspiration for wholesome emotional states, facial expressions, and customizable visual motifs (`core/character_manager.py`).

### 2.2 MoHan (Speech Pipeline & Conversational Voice)
- **Source:** https://github.com/mohan-ai/voice-companion
- **License:** Apache License 2.0
- **Attribution Notice:**
  > Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
- **Application in J.A.R.V.I.S.:** Multilingual conversational prompt structures and dynamic speech synthesis integration (`dashboard/server.py` and `core/human_conversation_engine.py`).

### 2.3 Leon AI (Personal Assistant Modular Architecture)
- **Source:** https://github.com/leon-ai/leon
- **License:** MIT License
- **Attribution Notice:**
  > Copyright (c) 2019-present Louis Grenard <louis@getleon.ai>  
  > Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files.
- **Application in J.A.R.V.I.S.:** Modular task structuring, privacy-first local storage, and execution pipelines.

### 2.4 OpenVoiceOS (OVOS — Speech Ring Buffer & Barge-In Audio)
- **Source:** https://github.com/OpenVoiceOS/OpenVoiceOS
- **License:** Apache License 2.0
- **Attribution Notice:**
  > Copyright 2021-2024 OpenVoiceOS Contributors. Licensed under the Apache License, Version 2.0.
- **Application in J.A.R.V.I.S.:** Design principles for audio ring buffers, threshold-based speech activity detection, and client-side barge-in interruption.

### 2.5 Home Assistant Assist (Intent Pipeline & Voice Engine)
- **Source:** https://github.com/home-assistant/core
- **License:** Apache License 2.0
- **Attribution Notice:**
  > Copyright 2013-2024 Home Assistant Contributors. Licensed under the Apache License, Version 2.0.
- **Application in J.A.R.V.I.S.:** Local intent routing, fallback state handling, and single-port unified service coordination.

### 2.6 Open WebUI (Web-Based Voice & WebSocket Streaming)
- **Source:** https://github.com/open-webui/open-webui
- **License:** Portions MIT / Open License
- **Attribution Notice:**
  > Copyright (c) 2024 Open WebUI Contributors.
- **Application in J.A.R.V.I.S.:** WebSocket binary audio protocol design (`/ws` and `/ws/phone-audio`), token-authenticated audio streaming endpoints (`/api/audio/{id}`).

### 2.7 Rhasspy (Offline SAPI5 Fallback & Speech Recognition)
- **Source:** https://github.com/rhasspy/rhasspy
- **License:** MIT License
- **Attribution Notice:**
  > Copyright (c) 2019-2024 Michael Hansen <mike@rhasspy.org>
- **Application in J.A.R.V.I.S.:** Zero-cloud local fallback strategies (`Microsoft Zira Desktop` offline SAPI5 synthesis and local Faster-Whisper transcription).

### 2.8 AnythingLLM (Multi-User Workspaces & Vector Memory)
- **Source:** https://github.com/Mintplex-Labs/anything-llm
- **License:** MIT License
- **Attribution Notice:**
  > Copyright (c) 2023-2024 Mintplex Labs, Inc.
- **Application in J.A.R.V.I.S.:** Per-user workspace isolation, user profile records, and PBKDF2 cryptographic password salting (`core/user_manager.py`).

---

## 3. Clean-Room Architectural Boundaries (AGPL / GPL Systems)

The following references are governed by copyleft licenses (GPL-3.0 / AGPL-3.0) or proprietary terms. J.A.R.V.I.S. Mark LVI incorporates **ZERO source code** from these repositories; they were referenced strictly as functional benchmarks and behavioral specifications:

1. **Willow (GPL-3.0):** Clean-room reference for remote microphone streaming specifications. All WebSocket audio handlers in J.A.R.V.I.S. were independently developed in Python/FastAPI.
2. **Jan AI (AGPL-3.0):** Clean-room reference for local model daemon orchestration. Ollama execution in J.A.R.V.I.S. uses standard HTTP REST endpoints on `127.0.0.1:11434`.
3. **Open Interpreter (AGPL-3.0):** Clean-room reference for safe computer control. `core/computer_agent.py` was authored from scratch with native Windows PowerShell commands and strict human approval gates.
4. **Stonic AI & Hume AI EVI (Proprietary / Commercial):** Functional benchmarks for visual companion aesthetics and empathic prosody. All visual rendering is implemented with lightweight SVG/HTML5/CSS3 and native Windows audio drivers.

---

## 4. Third-Party Dependencies

| Package | Purpose | License |
|---|---|---|
| `fastapi` | Dashboard REST API and WebSockets | MIT |
| `uvicorn` | ASGI HTTP/WebSocket server | BSD-3-Clause |
| `cryptography` | AES-256-GCM and PBKDF2 cryptographic primitives | Apache 2.0 / BSD |
| `edge-tts` | High-definition online neural voice synthesis | LGPL-3.0 (Used as library) |
| `sounddevice` | Native PortAudio audio capture and playback | MIT |
| `numpy` | High-performance PCM audio buffer manipulation | BSD-3-Clause |
| `av` | Audio container and format decoding (PyAV) | BSD-style / LGPL |
| `faster-whisper` | Highly optimized local CTranslate2 speech recognition | MIT |
| `pillow` (PIL) | Subtitle rendering and visual canvas overlays | HPND (Permissive) |

---

## 5. Certification of Compliance

All dependencies, reference notices, and intellectual property boundaries have been inspected, documented, and verified.
