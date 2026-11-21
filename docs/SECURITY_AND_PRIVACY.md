# J.A.R.V.I.S. MARK LVI — SECURITY AND PRIVACY SPECIFICATION

**Application:** J.A.R.V.I.S. Mark LVI Core  
**Classification:** Local-First Privacy-Preserving Autonomous Desktop Companion  
**Target Platform:** Windows 10 / Windows 11 (64-bit x64)

---

## 1. PRIVACY ARCHITECTURE & DATA SOVEREIGNTY

J.A.R.V.I.S. Mark LVI is engineered with a strict **Local-First, Privacy-First** paradigm:

1. **Local Neural Brain:** Conversational inference runs locally on your workstation via Ollama (`127.0.0.1:11434`, default model `qwen2.5:3b`). Prompts, personal queries, and responses never leave your machine unless you explicitly configure a third-party cloud provider.
2. **Local Storage:** All conversational memory, uploaded documents, knowledge chunks, schedules, workflows, and task states reside exclusively in the local `data/` directory.
3. **No External Telemetry:** J.A.R.V.I.S. does not send diagnostic logs, analytics, or behavioral telemetry to any remote server.
4. **Offline Voice Processing:** Local speech recognition uses Faster-Whisper, and speech synthesis uses local SAPI5 / Piper neural models, operating without internet access.

---

## 2. CREDENTIAL PROTECTION & WINDOWS DPAPI

### A. Windows Data Protection API (DPAPI) Encryption at Rest
All sensitive secrets, OAuth tokens (e.g. Meta Graph access tokens), and external credentials are encrypted at rest using the native Windows DPAPI (`core/crypto_storage.py`):
- Ciphertext entries are tagged with `dpapi:v1:`.
- Decryption is mathematically bound to the current Windows user profile; other accounts or users on the same machine cannot decrypt these tokens.
- Tokens are decrypted solely in-memory during active authorized requests.

### B. Automated Secret Scrubbing
All text entering conversational memory (`memory/memory_manager.py`), document knowledge base (`core/knowledge_manager.py`), chat sessions, or audit logs is filtered through regex scrubbers:
- `sk-[a-zA-Z0-9_\-]{20,}` (OpenAI / Anthropic keys)
- `AIza[0-9A-Za-z\-_]{30,45}` (Google API keys)
- `EAA[A-Za-z0-9]{15,}` (Meta OAuth tokens)
- `ghp_[a-zA-Z0-9]{36}` (GitHub Personal Access Tokens)
- `dpapi:v1:[A-Za-z0-9+/=]+` (DPAPI ciphertext)
- `(password|token|secret|key)\s*[:=]\s*[^\s,;]+`

---

## 3. NETWORK ISOLATION & ATTACK SURFACE MINIMIZATION

```text
External Internet
       │
       ▼ (HTTPS)
Cloudflare Quick Tunnel (On-Demand 60s TTL)
       │
       ▼ (HTTP loopback)
127.0.0.1:8005 (tools/oauth_callback_proxy.py)
       │
       ├── Path: /api/instagram/oauth/callback  -->  FORWARD to 127.0.0.1:8000
       │
       └── ALL OTHER PATHS (/, /app, /api/*)     -->  BLOCK (HTTP 403 Forbidden)
```

1. **Host Binding:** The core FastAPI backend and dashboard bind strictly to `127.0.0.1:8000` (loopback only). No external interface is opened by default.
2. **Reverse Proxy Hardening:** When an external OAuth callback is required, an isolated proxy on `127.0.0.1:8005` handles the connection. All paths other than `/api/instagram/oauth/callback` return `HTTP 403 Forbidden`.
3. **LAN Companion Pairing:** Android companion pairing requires explicit cryptographic authorization over local Wi-Fi with token authentication.

---

## 4. PERMISSION TIERS & OPERATOR CONFIRMATION GATES

Every skill and action in J.A.R.V.I.S. is categorized into three strict security tiers:

| Tier | Category | Example Actions | Confirmation Policy |
| :--- | :--- | :--- | :--- |
| **READ_ONLY** | Information retrieval | Check system status, read weather, search knowledge base, get battery level | Executed autonomously |
| **SAFE_WRITE** | Reversible creation | Add calendar event, save reminder, create scratch note, add memory entry | Executed autonomously with audit logging |
| **CONSEQUENTIAL** | Permanent / High Impact | Delete files, kill running processes, send emails, publish social media posts, system reboot | **Strict Operator Confirmation Gate Required** |

Destructive or consequential operations can never execute autonomously; they render an interactive confirmation modal on the dashboard or require verbal user confirmation.

---

## 5. IMMUTABLE AUDIT LOGGING & GOVERNANCE

All system operations, skill executions, workflow steps, and permission requests are recorded in append-only JSON logs (`data/audit_log.json` and `data/computer_agent_audit.log`):
- Timestamp (ISO 8601 UTC & Local)
- Initiator (User, Voice, Workflow, Scheduler)
- Skill / Tool ID & Parameters (with credentials scrubbed)
- Execution Status (`SUCCESS`, `BLOCKED_BY_POLICY`, `ERROR`, `CONFIRMATION_REJECTED`)
- Operator IP and session ID

The Audit Log is visible directly within the J.A.R.V.I.S. Dashboard under **Governance & Insights -> Audit Log** for full transparency.

---

## 6. WORKSPACE & ROLE-BASED ACCESS CONTROL (RBAC)

J.A.R.V.I.S. supports multiple user profiles and collaborative workspaces with role-based access:
- **Owner:** Full system administrative control, configuration changes, skill installation.
- **Admin:** Manages workflows, schedules, document collections, and integrations.
- **Member:** Interacts with conversational AI, triggers allowed workflows, searches knowledge.
- **Viewer:** Read-only access to dashboard status, chat logs, and telemetry.

---

## 7. REPORTING SECURITY VULNERABILITIES

If you discover a security concern or vulnerability in J.A.R.V.I.S. Mark LVI:
1. Do not open a public GitHub issue.
2. Send an advisory report to the repository administrator or security contact.
3. Include clear steps to reproduce, affected versions, and system environment.
